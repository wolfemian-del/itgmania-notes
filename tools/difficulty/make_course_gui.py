#!/usr/bin/env python3
"""Graphical front end for make_course_by_rating.py.

Pick your ITGmania Cache folder, scan the library once, see how many charts
sit at each modeled rating, choose packs, set up a course (one rating, a
range, or a ladder), preview the picks, re-roll or replace single entries,
and save a .crs.

Needs (all in the same folder):
    make_course_gui.py            this file
    make_course_by_rating.py      the engine room (rating + picking + writing)
    extract_chart_features.py     cache parser (from the project's claude/ folder)
    difficulty_model_notech.json  the deployed model (from claude/)
Standard library only (tkinter ships with the python.org Windows installer;
on Linux it may need the python3-tk package).

Run:  python make_course_gui.py
Settings are remembered in make_course_gui_settings.json next to this file.
"""
import argparse
import json
import queue
import random
import re
import sys
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    sys.exit("tkinter is not available in this Python. On Windows, install "
             "Python from python.org (it includes tkinter); on Linux install "
             "the python3-tk package.")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import make_course_by_rating as mcr
except SystemExit as e:  # the engine room exits when extract_chart_features is missing
    sys.exit(str(e))

SETTINGS = HERE / "make_course_gui_settings.json"
CHECKED, UNCHECKED = "☑", "☐"


def safe_filename(s):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s).strip(" .")
    return s or "Course"


class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=8)
        self.root = root
        self.model = None
        self.scanned = None      # rows from scan_library
        self.scan_stats = None
        self.pool = []           # rows after filters (last build)
        self.entries = []        # chosen rows (the preview)
        self.wanted = []         # (lo, hi) per entry
        self.q = queue.Queue()
        self.stop = False
        self.scanning = False
        self.rng = random.Random()
        self.last_seed = None
        self.pack_state = {}     # pack name -> bool (checked)
        self._build_vars()
        self._build_ui()
        self._load_settings()
        self.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        root.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._poll)

    # ------------------------------------------------------------- state --
    def _build_vars(self):
        v = tk.StringVar
        self.v_cache = v(value="")
        self.v_model = v(value=str(HERE / "difficulty_model_notech.json"))
        self.v_root = v(value="")
        self.v_outdir = v(value="")
        self.v_mode = v(value="single")
        self.v_rating = v(value="11")
        self.v_lo = v(value="10")
        self.v_hi = v(value="12")
        self.v_count = v(value="10")
        self.v_ladder = v(value="9,10,11,12,13")
        self.v_sort = v(value="random")
        self.v_seed = v(value="")
        self.v_title = v(value="Modeled 11")
        self.v_scripter = v(value="")
        self.v_lives = v(value="0")
        self.v_minsec = v(value="0")
        self.v_maxsec = v(value="0")
        self.v_maxpack = v(value="0")
        self.v_pin = tk.BooleanVar(value=True)
        self.v_same = tk.BooleanVar(value=False)
        self.v_dups = tk.BooleanVar(value=False)
        self.v_status = v(value="Choose the Cache folder, then press Scan library.")

    def _persist_keys(self):
        return ["v_cache", "v_model", "v_root", "v_outdir", "v_mode",
                "v_rating", "v_lo", "v_hi", "v_count", "v_ladder", "v_sort",
                "v_seed", "v_title", "v_scripter", "v_lives", "v_minsec",
                "v_maxsec", "v_maxpack"]

    def _load_settings(self):
        try:
            d = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except Exception:
            return
        for k in self._persist_keys():
            if k in d:
                getattr(self, k).set(d[k])
        for k in ("v_pin", "v_same", "v_dups"):
            if k in d:
                getattr(self, k).set(bool(d[k]))
        self.pack_state = {k: bool(x) for k, x in
                           d.get("pack_state", {}).items()}
        self._mode_changed()

    def _save_settings(self):
        d = {k: getattr(self, k).get() for k in self._persist_keys()}
        for k in ("v_pin", "v_same", "v_dups"):
            d[k] = bool(getattr(self, k).get())
        d["pack_state"] = {k: v for k, v in self.pack_state.items() if not v}
        d["pack_state"] = {k: False for k in d["pack_state"]}
        try:
            SETTINGS.write_text(json.dumps(d, indent=1), encoding="utf-8")
        except Exception:
            pass  # read-only folder: settings just are not remembered

    def _close(self):
        self.stop = True
        self._save_settings()
        self.root.destroy()

    # ---------------------------------------------------------------- UI --
    def _path_row(self, parent, r, label, var, kind):
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w",
                                           padx=(0, 6), pady=2)
        ttk.Entry(parent, textvariable=var).grid(row=r, column=1,
                                                 sticky="ew", pady=2)
        ttk.Button(parent, text="Browse...",
                   command=lambda: self._browse(var, kind)).grid(
            row=r, column=2, padx=(6, 0), pady=2)

    def _browse(self, var, kind):
        cur = var.get()
        init = cur if cur and Path(cur).exists() else str(HERE)
        if kind == "file":
            p = filedialog.askopenfilename(
                initialdir=str(Path(init).parent if Path(init).is_file()
                               else init),
                filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        else:
            p = filedialog.askdirectory(initialdir=init)
        if p:
            if var is self.v_root and var.get().strip() \
                    and messagebox.askyesno(
                        "Songs location",
                        "Add this folder to the existing list?\n(No = replace "
                        "the list.)"):
                p = var.get().strip().rstrip(";") + ";" + p
            var.set(p)
            if var is self.v_root:
                self._root_changed()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        lib = ttk.LabelFrame(self, text="Library", padding=6)
        lib.grid(row=0, column=0, sticky="ew")
        lib.columnconfigure(1, weight=1)
        self._path_row(lib, 0, "Cache folder", self.v_cache, "dir")
        self._path_row(lib, 1, "Model file", self.v_model, "file")
        self._path_row(lib, 2, "Songs location(s) (optional)", self.v_root,
                       "dir")
        self.root_entry = lib.grid_slaves(row=2, column=1)[0]
        self.root_entry.bind("<FocusOut>", lambda e: self._root_changed())
        self.root_entry.bind("<Return>", lambda e: self._root_changed())
        ttk.Button(lib, text="Detect", command=self.detect_roots).grid(
            row=2, column=3, padx=(6, 0), pady=2)
        self._path_row(lib, 3, "Courses folder", self.v_outdir, "dir")
        bar = ttk.Frame(lib)
        bar.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        bar.columnconfigure(1, weight=1)
        self.btn_scan = ttk.Button(bar, text="Scan library",
                                   command=self.scan)
        self.btn_scan.grid(row=0, column=0)
        self.progress = ttk.Progressbar(bar, mode="determinate")
        self.progress.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Label(lib, text="Songs location = a folder that contains "
                  "Songs/ (several: separate with ;). If set, cache entries "
                  "whose song folder is not found in any of them are ignored. "
                  "Press Detect to try the usual places.",
                  foreground="#666").grid(
            row=5, column=0, columnspan=3, sticky="w")

        body = ttk.PanedWindow(self, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew", pady=8)

        # left: histogram + packs
        left = ttk.Frame(body)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        left.rowconfigure(3, weight=2)
        ttk.Label(left, text="Modeled rating  (click a row to use it)").grid(
            row=0, column=0, sticky="w")
        self.hist = ttk.Treeview(left, columns=("n", "songs", "bar"),
                                 show="headings", height=8,
                                 selectmode="browse")
        for c, t, w in (("n", "Charts", 60), ("songs", "Songs", 60),
                        ("bar", "Rating", 160)):
            self.hist.heading(c, text=t)
            self.hist.column(c, width=w, anchor="w" if c == "bar" else "e")
        self.hist.grid(row=1, column=0, sticky="nsew")
        sbh = ttk.Scrollbar(left, command=self.hist.yview)
        sbh.grid(row=1, column=1, sticky="ns")
        self.hist.configure(yscrollcommand=sbh.set)
        self.hist.bind("<<TreeviewSelect>>", self._hist_click)
        pk = ttk.Frame(left)
        pk.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(pk, text="Packs  (click to include / exclude)").pack(
            side="left")
        ttk.Button(pk, text="None", width=6,
                   command=lambda: self._set_all_packs(False)).pack(
            side="right")
        ttk.Button(pk, text="All", width=6,
                   command=lambda: self._set_all_packs(True)).pack(
            side="right", padx=4)
        self.packs = ttk.Treeview(left, columns=("use", "name", "n"),
                                  show="headings", height=10,
                                  selectmode="none")
        self.packs.heading("use", text="")
        self.packs.heading("name", text="Pack")
        self.packs.heading("n", text="Charts")
        self.packs.column("use", width=28, anchor="center", stretch=False)
        self.packs.column("name", width=200)
        self.packs.column("n", width=60, anchor="e", stretch=False)
        self.packs.grid(row=3, column=0, sticky="nsew")
        self.packs.bind("<Button-1>", self._pack_click)
        sb = ttk.Scrollbar(left, command=self.packs.yview)
        sb.grid(row=3, column=1, sticky="ns")
        self.packs.configure(yscrollcommand=sb.set)
        body.add(left, weight=1)

        # right: options + preview
        right = ttk.Frame(body)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        body.add(right, weight=2)

        opt = ttk.LabelFrame(right, text="Course", padding=6)
        opt.grid(row=0, column=0, sticky="ew")
        for c in (1, 3, 5):
            opt.columnconfigure(c, weight=1)
        m = ttk.Frame(opt)
        m.grid(row=0, column=0, columnspan=6, sticky="w")
        for val, txt in (("single", "One rating"), ("range", "Rating range"),
                         ("ladder", "Ladder")):
            ttk.Radiobutton(m, text=txt, value=val, variable=self.v_mode,
                            command=self._mode_changed).pack(side="left",
                                                             padx=(0, 12))
        self.f_single = ttk.Frame(opt)
        self.f_range = ttk.Frame(opt)
        self.f_ladder = ttk.Frame(opt)
        ttk.Label(self.f_single, text="Rating").pack(side="left")
        ttk.Spinbox(self.f_single, from_=1, to=19, width=4,
                    textvariable=self.v_rating).pack(side="left", padx=6)
        ttk.Label(self.f_range, text="From").pack(side="left")
        ttk.Spinbox(self.f_range, from_=1, to=19, width=4,
                    textvariable=self.v_lo).pack(side="left", padx=6)
        ttk.Label(self.f_range, text="to").pack(side="left")
        ttk.Spinbox(self.f_range, from_=1, to=19, width=4,
                    textvariable=self.v_hi).pack(side="left", padx=6)
        ttk.Label(self.f_ladder, text="One entry per item, in order "
                  "(N or LO-HI):").pack(side="left")
        ttk.Entry(self.f_ladder, textvariable=self.v_ladder,
                  width=24).pack(side="left", padx=6)
        self.f_count = ttk.Frame(opt)
        ttk.Label(self.f_count, text="Songs").pack(side="left")
        ttk.Spinbox(self.f_count, from_=1, to=99, width=4,
                    textvariable=self.v_count).pack(side="left", padx=6)
        ttk.Label(self.f_count, text="Order").pack(side="left", padx=(12, 0))
        ttk.Combobox(self.f_count, textvariable=self.v_sort, width=14,
                     state="readonly",
                     values=("random", "easy to hard", "hard to easy")
                     ).pack(side="left", padx=6)
        self.f_single.grid(row=1, column=0, columnspan=6, sticky="w",
                           pady=3)
        self.f_range.grid(row=1, column=0, columnspan=6, sticky="w", pady=3)
        self.f_ladder.grid(row=1, column=0, columnspan=6, sticky="w", pady=3)
        self.f_count.grid(row=2, column=0, columnspan=6, sticky="w", pady=3)

        def lab(r, c, t):
            ttk.Label(opt, text=t).grid(row=r, column=c, sticky="e",
                                        padx=(8, 4), pady=2)

        def ent(r, c, var, w=14):
            e = ttk.Entry(opt, textvariable=var, width=w)
            e.grid(row=r, column=c, sticky="ew", pady=2)
            return e
        lab(3, 0, "Title")
        ent(3, 1, self.v_title)
        lab(3, 2, "Scripter")
        ent(3, 3, self.v_scripter)
        lab(3, 4, "Lives")
        ent(3, 5, self.v_lives, 5)
        lab(4, 0, "Min seconds")
        ent(4, 1, self.v_minsec, 6)
        lab(4, 2, "Max seconds")
        ent(4, 3, self.v_maxsec, 6)
        lab(4, 4, "Max / pack")
        ent(4, 5, self.v_maxpack, 5)
        lab(5, 0, "Seed")
        ent(5, 1, self.v_seed, 10)
        ttk.Label(opt, text="(blank = new random pick each time; the seed "
                  "used is shown)", foreground="#666").grid(
            row=5, column=2, columnspan=4, sticky="w")
        ck = ttk.Frame(opt)
        ck.grid(row=6, column=0, columnspan=6, sticky="w", pady=(4, 0))
        ttk.Checkbutton(ck, text="Pin charts (nodifficult)",
                        variable=self.v_pin).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(ck, text="Allow the same song twice",
                        variable=self.v_same).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(ck, text="Keep duplicate charts",
                        variable=self.v_dups).pack(side="left")
        self._mode_changed()

        act = ttk.Frame(right)
        act.grid(row=1, column=0, sticky="ew", pady=6)
        self.btn_build = ttk.Button(act, text="Build / re-roll",
                                    command=self.build, state="disabled")
        self.btn_build.pack(side="left")
        self.btn_repl = ttk.Button(act, text="Replace selected",
                                   command=self.replace_selected,
                                   state="disabled")
        self.btn_repl.pack(side="left", padx=6)
        self.btn_del = ttk.Button(act, text="Remove selected",
                                  command=self.remove_selected,
                                  state="disabled")
        self.btn_del.pack(side="left")
        self.btn_save = ttk.Button(act, text="Save .crs...",
                                   command=self.save, state="disabled")
        self.btn_save.pack(side="right")

        cols = ("i", "rating", "value", "slot", "title", "pack", "meter")
        self.tree = ttk.Treeview(right, columns=cols, show="headings",
                                 selectmode="extended")
        for c, t, w, a in (("i", "#", 30, "e"), ("rating", "Model", 50, "e"),
                           ("value", "Value", 55, "e"),
                           ("slot", "Slot", 75, "w"),
                           ("title", "Title", 220, "w"),
                           ("pack", "Pack", 150, "w"),
                           ("meter", "Official", 60, "e")):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=a)
        self.tree.grid(row=2, column=0, sticky="nsew")
        sb2 = ttk.Scrollbar(right, command=self.tree.yview)
        sb2.grid(row=2, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb2.set)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._buttons())

        ttk.Label(self, textvariable=self.v_status, anchor="w",
                  relief="sunken", padding=(6, 2)).grid(
            row=2, column=0, sticky="ew")

    def _mode_changed(self):
        m = self.v_mode.get()
        for f, k in ((self.f_single, "single"), (self.f_range, "range"),
                     (self.f_ladder, "ladder")):
            if m == k:
                f.grid()
            else:
                f.grid_remove()
        if m == "ladder":
            self.f_count.grid_remove()
        else:
            self.f_count.grid()

    def _buttons(self):
        ready = self.scanned is not None and not self.scanning
        self.btn_build.configure(state="normal" if ready else "disabled")
        have = bool(self.entries)
        sel = bool(self.tree.selection())
        self.btn_save.configure(state="normal" if have else "disabled")
        self.btn_repl.configure(state="normal" if have and sel
                                else "disabled")
        self.btn_del.configure(state="normal" if have and sel
                               else "disabled")

    def status(self, text):
        self.v_status.set(text)

    # -------------------------------------------------------------- scan --
    def scan(self):
        if self.scanning:
            return
        try:
            self.model = mcr.load_model(self.v_model.get().strip())
        except (SystemExit, OSError, ValueError) as e:
            messagebox.showerror("Model file", "Cannot use the model file:\n%s"
                                 % e)
            return
        try:
            cache_dir = mcr.ecf.find_song_cache(self.v_cache.get().strip())
        except SystemExit as e:
            messagebox.showerror("Cache folder", str(e))
            return
        self.scanning = True
        self.scanned = None
        self.entries, self.wanted = [], []
        self._show_entries()
        self.btn_scan.configure(state="disabled")
        self.progress.configure(value=0, maximum=100)
        self.status("Scanning the cache...")
        self._buttons()
        model = self.model

        def work():
            try:
                res = mcr.scan_library(
                    cache_dir, model,
                    progress=lambda n, t: self.q.put(("p", n, t)),
                    should_stop=lambda: self.stop)
                self.q.put(("done", res))
            except Exception as e:  # report instead of dying silently
                self.q.put(("err", repr(e)))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "p":
                    self.progress.configure(maximum=max(msg[2], 1),
                                            value=msg[1])
                elif msg[0] == "done":
                    self._scan_done(msg[1])
                else:
                    self.scanning = False
                    self.btn_scan.configure(state="normal")
                    self.status("Scan failed: %s" % msg[1])
                    messagebox.showerror("Scan failed", msg[1])
        except queue.Empty:
            pass
        if not self.stop:
            self.after(100, self._poll)

    def _scan_done(self, res):
        self.scanning = False
        self.btn_scan.configure(state="normal")
        if res is None:
            return
        rows, st = res
        self.scanned, self.scan_stats = rows, st
        self.progress.configure(value=self.progress["maximum"])
        self._last_root = self.v_root.get().strip()
        npacks = self._populate_packs()
        self._refresh_hist()
        if not self.v_root.get().strip():
            self.status("%d cache files, %d charts; %d rated dance-single "
                        "charts in %d packs. (Skipped: %d not dance-single, "
                        "%d Edit, %d unusable data, %d names with : ; #.) "
                        "Songs location is empty, so packs deleted from disk "
                        "are still listed." % (
                            st["files"], st["charts"], len(rows), npacks,
                            st["not_single"], st["edit"],
                            st["flagged"] + st["no_song_dir"],
                            st["bad_name"]))
        self._buttons()

    def _present_rows(self):
        """Scanned rows whose song folder exists under the Songs location(s)
        (all rows when none is set). Returns (rows, roots)."""
        roots = mcr.parse_roots(self.v_root.get())
        if not roots:
            return self.scanned, roots
        ok = {}
        out = []
        for c in self.scanned:
            v = ok.get(c["rel"])
            if v is None:
                v = ok[c["rel"]] = mcr.song_dir_present(c["rel"], roots)
            if v:
                out.append(c)
        return out, roots

    def _populate_packs(self):
        """(Re)build the pack list from the rows that exist on disk."""
        rows, roots = self._present_rows()
        counts = {}
        for c in rows:
            counts[c["pack"]] = counts.get(c["pack"], 0) + 1
        allpacks = {c["pack"] for c in self.scanned}
        self.packs.delete(*self.packs.get_children())
        for name in sorted(counts, key=str.lower):
            on = self.pack_state.get(name, True)
            self.pack_state[name] = on
            self.packs.insert("", "end", iid=name,
                              values=(CHECKED if on else UNCHECKED, name,
                                      counts[name]))
        hidden = len(allpacks) - len(counts)
        self._hidden_packs = hidden if roots else 0
        return len(counts)

    def _root_changed(self):
        if self.scanned is None or self.scanning:
            return
        key = self.v_root.get().strip()
        if key == getattr(self, "_last_root", None):
            return
        self._last_root = key
        self._populate_packs()
        self._refresh_hist()

    def detect_roots(self):
        """Try the usual places for Songs/ and keep those that hold at least
        one cached song."""
        if self.scanned is None:
            messagebox.showinfo("Detect", "Scan the library first.")
            return
        cache = Path(self.v_cache.get().strip() or ".")
        cands = []
        for c in [cache.parent, cache.parent.parent,
                  Path(self.v_outdir.get().strip() or ".").parent] + \
                mcr.parse_roots(self.v_root.get()):
            if c not in cands and c.is_dir():
                cands.append(c)
        sample = {}
        for c in self.scanned:
            sample.setdefault(c["rel"], c)
        rels = list(sample)
        found = []
        report = []
        for c in cands:
            n = sum(1 for r in rels if (c / r).is_dir())
            report.append("%s : %d of %d song folders" % (c, n, len(rels)))
            if n:
                found.append(c)
        if not found:
            messagebox.showwarning(
                "Detect", "No song folders were found under:\n\n%s\n\n"
                "Use Browse to point at the folder that contains Songs/ "
                "(on Windows: %%APPDATA%%\\ITGmania, the install folder, or "
                "both)." % "\n".join(report or ["(no candidate folders)"]))
            return
        self.v_root.set(";".join(str(c).replace("\\", "/") for c in found))
        self._last_root = None
        self._root_changed()
        self.status("Detect: " + "; ".join(report))

    # ------------------------------------------------------ pack picking --
    def _pack_click(self, event):
        if self.packs.identify_region(event.x, event.y) != "cell":
            return
        iid = self.packs.identify_row(event.y)
        if not iid:
            return
        on = not self.pack_state.get(iid, True)
        self.pack_state[iid] = on
        self.packs.set(iid, "use", CHECKED if on else UNCHECKED)
        self._refresh_hist()
        return "break"

    def _set_all_packs(self, on):
        for iid in self.packs.get_children():
            self.pack_state[iid] = on
            self.packs.set(iid, "use", CHECKED if on else UNCHECKED)
        self._refresh_hist()

    # ----------------------------------------------------------- filters --
    def _int(self, var, name, lo=0):
        try:
            n = int(float(var.get().strip() or "0"))
        except ValueError:
            raise ValueError("%s must be a number." % name)
        if n < lo:
            raise ValueError("%s must be at least %d." % (name, lo))
        return n

    def _filtered(self):
        inc = None
        listed = list(self.packs.get_children())  # packs on disk only
        names = [k for k in listed if self.pack_state.get(k, True)]
        if listed and len(names) != len(listed):
            inc = {n.lower() for n in names}
        rows, cnt = mcr.filter_library(
            self.scanned, inc, None, self.v_root.get().strip() or None,
            self._int(self.v_minsec, "Min seconds"),
            self._int(self.v_maxsec, "Max seconds"), self.v_dups.get())
        return rows, cnt

    def _refresh_hist(self):
        if self.scanned is None:
            return
        try:
            rows, cnt = self._filtered()
        except ValueError:
            rows = self.scanned
        hist = {}
        for c in rows:
            h = hist.setdefault(c["rating"], [0, set()])
            h[0] += 1
            h[1].add(c["key"])
        top = max([h[0] for h in hist.values()] or [1])
        self.hist.delete(*self.hist.get_children())
        for k in sorted(hist):
            bar = "%2d  %s" % (k, "█" * max(1, round(18 * hist[k][0]
                                                          / top)))
            self.hist.insert("", "end", iid=str(k),
                             values=(hist[k][0], len(hist[k][1]), bar))
        if not rows and self.v_root.get().strip():
            roots = mcr.parse_roots(self.v_root.get())
            ex = next((c["rel"] for c in self.scanned), "Songs/<pack>/<song>")
            self.status("0 charts match. No cached song folder was found "
                        "under: %s  (looked for e.g. %s/%s). Press Detect, or "
                        "Browse to the folder that contains Songs/."
                        % (", ".join(str(r) for r in roots),
                           roots[0], ex))
        else:
            extra = ""
            if getattr(self, "_hidden_packs", 0):
                extra = " %d pack(s) in the cache are not on disk and are " \
                        "hidden." % self._hidden_packs
            self.status("%d charts match the pack / folder / length "
                        "filters.%s" % (len(rows), extra))

    def _hist_click(self, _e):
        sel = self.hist.selection()
        if not sel:
            return
        r = sel[0]
        self.v_rating.set(r)
        self.v_lo.set(r)
        self.v_hi.set(r)
        if self.v_mode.get() == "ladder":
            self.v_mode.set("single")
            self._mode_changed()
        t = self.v_title.get()
        if re.fullmatch(r"Modeled \d+", t) or not t:
            self.v_title.set("Modeled %s" % r)

    # ------------------------------------------------------------- build --
    def _args(self):
        a = argparse.Namespace()
        a.title = self.v_title.get().strip()
        a.scripter = self.v_scripter.get().strip()
        a.lives = self._int(self.v_lives, "Lives")
        a.style = ""
        a.allow_same_song = self.v_same.get()
        a.max_per_pack = self._int(self.v_maxpack, "Max / pack")
        a.no_pin = not self.v_pin.get()
        return a

    def _wanted(self):
        mode = self.v_mode.get()
        try:
            if mode == "ladder":
                items = [s for s in self.v_ladder.get().split(",") if s.strip()]
                if not items:
                    raise ValueError("The ladder is empty.")
                return [mcr.parse_range(s) for s in items], "ladder"
            n = self._int(self.v_count, "Songs", 1)
            if mode == "single":
                lo = hi = self._int(self.v_rating, "Rating", 1)
                if hi > 19:
                    raise ValueError("Rating must be 1-19.")
            else:
                lo = self._int(self.v_lo, "From", 1)
                hi = self._int(self.v_hi, "To", 1)
                if lo > hi or hi > 19:
                    raise ValueError("The range must be within 1-19, low "
                                     "to high.")
            return [(lo, hi)] * n, mode
        except SystemExit as e:  # parse_range exits with a message
            raise ValueError(str(e))

    def build(self):
        if self.scanned is None:
            return
        try:
            a = self._args()
            wanted, mode = self._wanted()
            pool, cnt = self._filtered()
            seed_txt = self.v_seed.get().strip()
            seed = int(seed_txt) if seed_txt else random.randrange(10 ** 8)
        except ValueError as e:
            messagebox.showerror("Check the settings", str(e))
            return
        if not pool:
            messagebox.showwarning("Nothing to pick from",
                                   "No charts pass the current filters.")
            return
        self.last_seed = seed
        self.rng = random.Random(seed)
        chosen, fail = mcr.pick(pool, wanted, a, self.rng)
        if fail:
            lo, hi = fail
            messagebox.showwarning(
                "Not enough charts",
                "Found %d of %d entries; ran out of charts rated %s. Widen "
                "the range, allow the same song, raise Max / pack, or ask "
                "for fewer songs." % (len(chosen), len(wanted),
                                      lo if lo == hi else "%d-%d" % (lo, hi)))
            return
        sort = self.v_sort.get()
        if mode != "ladder" and sort != "random":
            chosen.sort(key=lambda c: c["cal"], reverse=(sort ==
                                                         "hard to easy"))
        self.pool = pool
        self.entries = chosen
        self.wanted = (wanted if mode == "ladder"
                       else [wanted[0]] * len(chosen))
        self._show_entries()
        self.status("Built %d entries from %d candidate charts (seed %d)."
                    % (len(chosen), len(pool), seed))

    def _show_entries(self):
        self.tree.delete(*self.tree.get_children())
        for i, c in enumerate(self.entries):
            self.tree.insert("", "end", iid=str(i), values=(
                i + 1, c["rating"], "%.2f" % c["cal"], c["slot"],
                c["title"], c["pack"], c["meter"]))
        self._buttons()

    def replace_selected(self):
        sel = sorted(int(i) for i in self.tree.selection())
        if not sel:
            return
        try:
            a = self._args()
        except ValueError as e:
            messagebox.showerror("Check the settings", str(e))
            return
        failed = 0
        for i in sel:
            others = [c for j, c in enumerate(self.entries) if j != i]
            used = {c["key"] for c in others}
            packs = {}
            for c in others:
                packs[c["pack"].lower()] = packs.get(c["pack"].lower(), 0) + 1
            lo, hi = self.wanted[i]
            pool = [c for c in self.pool if lo <= c["rating"] <= hi
                    and c is not self.entries[i]
                    and (a.allow_same_song or c["key"] not in used)
                    and (not a.max_per_pack
                         or packs.get(c["pack"].lower(), 0) < a.max_per_pack)]
            if not pool:
                failed += 1
                continue
            bysong = {}
            for c in pool:
                bysong.setdefault(c["key"], []).append(c)
            song = self.rng.choice(sorted(bysong))
            self.entries[i] = self.rng.choice(bysong[song])
        self._show_entries()
        for i in sel:
            if self.tree.exists(str(i)):
                self.tree.selection_add(str(i))
        if failed:
            self.status("No other chart is available for %d selected "
                        "entr%s." % (failed, "y" if failed == 1 else "ies"))
        else:
            self.status("Replaced %d entr%s." % (len(sel), "y" if len(sel)
                                                 == 1 else "ies"))

    def remove_selected(self):
        sel = sorted((int(i) for i in self.tree.selection()), reverse=True)
        for i in sel:
            del self.entries[i]
            del self.wanted[i]
        self._show_entries()
        self.status("Removed %d entr%s." % (len(sel), "y" if len(sel) == 1
                                            else "ies"))

    # -------------------------------------------------------------- save --
    def save(self):
        if not self.entries:
            return
        try:
            a = self._args()
        except ValueError as e:
            messagebox.showerror("Check the settings", str(e))
            return
        if not a.title:
            messagebox.showerror("Title", "Give the course a title.")
            return
        if mcr.BAD_CHARS.search(a.title) or mcr.BAD_CHARS.search(a.scripter):
            messagebox.showerror(
                "Title", "The title and scripter may not contain : ; # (the "
                "course file cannot escape them).")
            return
        outdir = self.v_outdir.get().strip()
        path = filedialog.asksaveasfilename(
            title="Save course", defaultextension=".crs",
            initialdir=outdir if outdir and Path(outdir).is_dir()
            else str(HERE),
            initialfile=safe_filename(a.title) + ".crs",
            filetypes=[("Course files", "*.crs")])
        if not path:
            return
        mode = self.v_mode.get()
        if mode == "ladder":
            label = "Modeled difficulty ladder: " + self.v_ladder.get().strip()
        else:
            r = (self.v_rating.get() if mode == "single"
                 else "%s-%s" % (self.v_lo.get(), self.v_hi.get()))
            label = "Modeled difficulty %s, %d songs" % (r, len(self.entries))
        try:
            mcr.write_crs(Path(path), self.entries, a, label)
        except (SystemExit, OSError) as e:
            messagebox.showerror("Could not save", str(e))
            return
        self.v_outdir.set(str(Path(path).parent))
        self._save_settings()
        self.status("Saved %s  (%d entries, seed %s). Games with FastLoad on "
                    "may keep showing an older course of the same name until "
                    "its entry in Cache/Courses is removed." %
                    (path, len(self.entries), self.last_seed))


def main():
    try:  # sharper text on high-DPI Windows screens
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    root.title("ITGmania course builder (modeled difficulty)")
    root.geometry("1180x760")
    root.minsize(980, 620)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
