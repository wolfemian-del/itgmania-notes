#!/usr/bin/env python3
"""Fit and evaluate a chart-difficulty model from extract_chart_features.py output.

Usage:
    python fit_difficulty_model.py features.csv OUT_DIR [--steps-type dance-single]
        [--exclude-pack TEXT ...] [--group-by pack|song] [--censor-top 19]
        [--no-calibrate] [--no-tech] [--compare-gbm] [--robust] [--no-dedupe]
        [--min-pack-charts 10] [--folds 5] [--seed 1]

What is new in v2 (relative to the first version):
  --exclude-pack TEXT   drop every pack whose name contains TEXT (case-
                        insensitive; repeat the option for several), before
                        de-duplication. Example: --exclude-pack "DDR II (Wii)"
  --group-by song       cross-validate with whole SONGS held out (title +
                        artist) instead of whole packs. Default is pack.
  --censor-top N        treat labels >= N as "N or harder" (right-censored):
                        a prediction above N is not counted as a miss and the
                        fit does not pull the model down to N. Use 19 for the
                        DDR X scale.
  calibration           (on by default; --no-calibrate turns it off) a
                        monotone map from raw model value to rating, learned
                        from out-of-fold predictions, to remove the S-shaped
                        bias by level. Evaluated with nested cross-validation,
                        so the reported numbers do not see their own labels.
  --no-tech             drop the tech-count features (ablation).
  oof_predictions.csv   now has title, artist, oof_pred, oof_pred_huber,
                        oof_pred_cal, miss.

Duplicate charts (same GrooveStats hash, from the extractor) are collapsed
before fitting; copies carrying different meters are excluded and listed.

Needs: pandas, numpy, scikit-learn, scipy.
Writes to OUT_DIR: fit_report.txt, model.json, oof_predictions.csv,
per_pack_offsets.csv, outliers.csv. Prints the report as well.

Model: ridge regression of the labelled meter on standardized chart features,
optionally followed by a monotone calibration. Tested on synthetic data only;
real-data behaviour is unknown beyond the user's first run of v1.
"""
import argparse
import json
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

RADAR_RATE = ["radar_Stream", "radar_Voltage", "radar_Air", "radar_Freeze",
              "radar_Chaos"]
TECH = ["Crossovers", "HalfCrossovers", "FullCrossovers", "Footswitches",
        "UpFootswitches", "DownFootswitches", "Sideswitches", "Jacks",
        "Brackets", "Doublesteps"]
NPS = ["peak_nps", "mean_nps_active", "p90_nps_active", "sust_nps_8",
       "sust_nps_16", "sust_nps_32"]


def build_features(df, use_tech=True):
    """Return (X DataFrame, list of feature names). Every feature is computed
    from columns the extractor writes, so it could be ported to Lua."""
    X = pd.DataFrame(index=df.index)
    for c in RADAR_RATE:
        X[c] = df[c]
    for c in NPS:
        X[c] = df[c]
    if use_tech:
        for t in TECH:
            X["tech_per100_" + t] = df["tech_per100_" + t]
    rows = df["total_rows"].clip(lower=1)
    X["log_rows"] = np.log(rows)
    X["active_frac"] = df["active_measures"] / df["measure_count"].clip(lower=1)
    X["hands_per_row"] = df["radar_Hands"] / rows
    X["mines_per_row"] = df["radar_Mines"] / rows
    X["holds_per_row"] = (df["radar_Holds"] + df["radar_Rolls"]) / rows
    X["jumps_per_row"] = df["radar_Jumps"] / rows
    return X, list(X.columns)


def collapse_duplicates(df, notes):
    """Collapse charts the extractor grouped as duplicates (same GrooveStats
    hash: identical notes and BPM changes).

    - Same meter in the group: keep one row (first by pack, song file).
    - Different meters (re-rated copies): exclude the whole group from fitting
      and return it separately so it can be reported.
    - Members whose features differ (the hash ignores stops/warps/offset):
      not true duplicates, so all rows are kept.
    Groups are evaluated AFTER any pack exclusion, so a copy left alone in the
    corpus (its twin was in an excluded pack) is simply kept.
    Returns (kept df, conflict-group rows df).
    """
    if "dup_group" not in df.columns:
        notes.append("duplicate columns absent from CSV (older extractor): "
                     "no de-duplication")
        return df, df.iloc[0:0]
    g = pd.to_numeric(df["dup_group"], errors="coerce")
    has = g.notna()
    if "dup_feature_mismatch" in df.columns:
        fmis = pd.to_numeric(df["dup_feature_mismatch"], errors="coerce").fillna(0)
    else:
        fmis = pd.Series(0, index=df.index)
    drop, parts = [], []
    n_groups = n_removed = n_conf = n_fm = 0
    for _, sub in df[has].groupby(g[has]):
        if len(sub) < 2:
            continue
        n_groups += 1
        if sub["meter"].nunique() > 1:
            n_conf += 1
            parts.append(sub)
            drop.extend(sub.index)
        elif fmis.loc[sub.index].max() >= 1:
            n_fm += 1
        else:
            order = sub.sort_values(["pack", "song_file"]).index
            drop.extend(order[1:])
            n_removed += len(order) - 1
    notes.append("duplicate groups still present after filters: %d" % n_groups)
    notes.append("  rows removed as exact duplicates: %d" % n_removed)
    notes.append("  groups excluded for conflicting meters (re-rated): %d" % n_conf)
    notes.append("  groups kept as separate rows (features differ): %d" % n_fm)
    conflicts = pd.concat(parts) if parts else df.iloc[0:0]
    return df.drop(index=drop), conflicts


def song_key(df):
    """Group key for 'same song': lower-cased title + artist, punctuation and
    spacing removed."""
    def norm(s):
        return re.sub(r"[^0-9a-z]+", "", str(s).lower())
    art = df["artist"] if "artist" in df.columns else ""
    return (df["title"].map(norm) + "|" + (art.map(norm) if "artist" in df.columns
                                           else "")).to_numpy()


def load(path, steps_type, notes, dedupe=True, exclude=(), use_tech=True):
    df = pd.read_csv(path, encoding="utf-8-sig")
    notes.append("rows in CSV: %d" % len(df))
    df = df[df["steps_type"] == steps_type]
    notes.append("rows with steps_type %s: %d" % (steps_type, len(df)))
    if "flags" in df.columns:
        bad = df["flags"].fillna("") != ""
        notes.append("dropped (flagged by extractor): %d" % int(bad.sum()))
        df = df[~bad]
    df = df[df["difficulty"].astype(str) != "Edit"]
    df = df.copy()
    df["meter"] = pd.to_numeric(df["meter"], errors="coerce")
    df = df[df["meter"] >= 1]
    for ex in exclude:
        hit = df["pack"].astype(str).str.contains(ex, case=False, regex=False)
        notes.append("excluded by --exclude-pack %r: %d charts in %s"
                     % (ex, int(hit.sum()),
                        sorted(df.loc[hit, "pack"].astype(str).unique())[:6]))
        if not hit.any():
            notes.append("  WARNING: --exclude-pack %r matched nothing" % ex)
        df = df[~hit]
    conflicts = df.iloc[0:0]
    if dedupe:
        df, conflicts = collapse_duplicates(df, notes)
    else:
        notes.append("de-duplication OFF (--no-dedupe)")
    X, names = build_features(df, use_tech)
    ok = np.isfinite(X.to_numpy(dtype=float)).all(axis=1)
    notes.append("dropped (non-finite features): %d" % int((~ok).sum()))
    df, X = df[ok], X[ok]
    notes.append("charts used (Edit excluded): %d in %d packs"
                 % (len(df), df["pack"].nunique()))
    return (df.reset_index(drop=True), X.reset_index(drop=True), names,
            conflicts.reset_index(drop=True))


# ---------------------------------------------------------------- models ---

def fit_model(Xtr, ytr, cens, kind="ridge", alpha=3.0, iters=15):
    """Ridge or Huber fit on standardized features. Rows in `cens` are labels
    of the form 'at least this value': while the model already predicts at or
    above the label the row contributes nothing (its target is set to the
    current prediction), otherwise it acts like an ordinary label. Repeated
    until stable (a simple Tobit-style iteration)."""
    sc = StandardScaler().fit(Xtr)
    Z = sc.transform(Xtr)

    def mk():
        if kind == "huber":
            return HuberRegressor(epsilon=1.35, alpha=alpha, max_iter=2000)
        return Ridge(alpha=alpha)

    def fit(t):
        m = mk()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            return m.fit(Z, t)

    m = fit(ytr)
    if cens.any():
        for _ in range(iters):
            p = m.predict(Z)
            t = ytr.copy()
            up = cens & (p > ytr)
            t[up] = p[up]
            m = fit(t)
    return sc, m


def make_fn(kind, cap):
    def fn(Xtr, ytr, Xte, seed):
        cens = (ytr >= cap) if cap else np.zeros(len(ytr), dtype=bool)
        sc, m = fit_model(Xtr, ytr, cens, kind)
        return m.predict(sc.transform(Xte))
    return fn


def gbm_fn(Xtr, ytr, Xte, seed):
    g = GradientBoostingRegressor(n_estimators=200, max_depth=3,
                                  learning_rate=0.05, subsample=0.8,
                                  random_state=seed)
    return g.fit(Xtr, ytr).predict(Xte)


def clip_round(p):
    return np.clip(np.rint(p), 1, 20)


def metrics(y, p, cap=0):
    """Accuracy numbers. With cap > 0, a label >= cap means 'cap or harder':
    a prediction at or above the label (after rounding for the exact and
    within-1 numbers) counts as correct and has zero error."""
    r = clip_round(p)
    cens = (y >= cap) if cap else np.zeros(len(y), dtype=bool)
    sat = cens & (p >= y)
    err = np.where(sat, 0.0, p - y)
    ok_ex = (r == y) | (cens & (r >= y))
    ok_w1 = (np.abs(r - y) <= 1) | (cens & (r >= y))
    rho = spearmanr(y, p).statistic if len(y) > 2 else float("nan")
    return {
        "n": int(len(y)),
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "exact_%": float(100 * np.mean(ok_ex)),
        "within1_%": float(100 * np.mean(ok_w1)),
        "spearman": float(rho),
    }


def grouped_oof(X, y, groups, folds, model_fn, seed):
    """Out-of-fold predictions with group-held-out folds."""
    n_groups = len(np.unique(groups))
    k = max(2, min(folds, n_groups))
    oof = np.full(len(y), np.nan)
    for tr, te in GroupKFold(n_splits=k).split(X, y, groups):
        oof[te] = model_fn(X.iloc[tr], y[tr], X.iloc[te], seed)
    return oof, k


def make_calibrator(raw, y, step=0.5):
    """Monotone (non-decreasing) map from raw model value to label, as a short
    table of knots (linear interpolation between them). Built by isotonic
    regression and then sampled every `step` units; knots inside flat stretches
    are dropped."""
    iso = IsotonicRegression(increasing=True, out_of_bounds="clip")
    iso.fit(raw, y)
    lo, hi = float(np.min(raw)), float(np.max(raw))
    kx = np.arange(np.floor(lo / step) * step, np.ceil(hi / step) * step + step,
                   step)
    ky = iso.predict(kx)
    keep = np.ones(len(kx), dtype=bool)
    for i in range(1, len(kx) - 1):
        if ky[i] == ky[i - 1] and ky[i] == ky[i + 1]:
            keep[i] = False
    return kx[keep], ky[keep]


def apply_cal(raw, kx, ky):
    return np.interp(raw, kx, ky)


def calibrated_oof(X, y, groups, folds, fn, seed):
    """Nested: for each outer fold the calibration map is learned only from
    out-of-fold predictions made inside the TRAINING part, then applied to the
    held-out part, so calibration never sees held-out labels."""
    n_groups = len(np.unique(groups))
    k = max(2, min(folds, n_groups))
    out = np.full(len(y), np.nan)
    for tr, te in GroupKFold(n_splits=k).split(X, y, groups):
        Xtr, ytr, gtr = X.iloc[tr], y[tr], groups[tr]
        inner, _ = grouped_oof(Xtr, ytr, gtr, 4, fn, seed)
        kx, ky = make_calibrator(inner, ytr)
        raw = fn(Xtr, ytr, X.iloc[te], seed)
        out[te] = apply_cal(raw, kx, ky)
    return out


def learning_curve(X, y, groups, folds, seed, fn,
                   fracs=(0.1, 0.2, 0.4, 0.6, 0.8, 1.0)):
    """Test MAE (on held-out groups) as the TRAINING set grows."""
    rng = np.random.default_rng(seed)
    n_groups = len(np.unique(groups))
    k = max(2, min(folds, n_groups))
    out = []
    splits = list(GroupKFold(n_splits=k).split(X, y, groups))
    for f in fracs:
        maes, sizes = [], []
        for tr, te in splits:
            m = max(int(round(f * len(tr))), 20)
            m = min(m, len(tr))
            sub = rng.choice(tr, size=m, replace=False)
            p = fn(X.iloc[sub], y[sub], X.iloc[te], seed)
            maes.append(np.mean(np.abs(y[te] - p)))
            sizes.append(m)
        out.append((float(np.mean(sizes)), float(np.mean(maes)),
                    float(np.std(maes))))
    return out


def per_level(y, oof):
    rows = []
    for lv in sorted(np.unique(y)):
        s = y == lv
        rows.append((int(lv), int(s.sum()), float(oof[s].mean()),
                     float(np.mean(oof[s] - lv)),
                     float(np.mean(np.abs(oof[s] - lv)))))
    return rows


def per_pack(df, y, oof, min_n):
    res = y - oof  # label minus prediction: positive = pack rated harder
    d = pd.DataFrame({"pack": df["pack"], "res": res})
    g = d.groupby("pack")["res"].agg(["count", "mean", "std"]).reset_index()
    g = g[g["count"] >= min_n].copy()
    g["se"] = g["std"] / np.sqrt(g["count"])
    g["flag"] = (g["mean"].abs() > 2 * g["se"]) & (g["mean"].abs() >= 0.5)
    g = g.rename(columns={"count": "n_charts", "mean": "offset_label_minus_pred"})
    return g.sort_values("offset_label_minus_pred", key=lambda s: -s.abs())


def main():
    for st in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("out_dir")
    ap.add_argument("--steps-type", default="dance-single")
    ap.add_argument("--exclude-pack", action="append", default=[],
                    metavar="TEXT",
                    help="drop packs whose name contains TEXT (repeatable)")
    ap.add_argument("--group-by", choices=["pack", "song"], default="pack",
                    help="what is held out together in cross-validation")
    ap.add_argument("--censor-top", type=int, default=0, metavar="N",
                    help="treat labels >= N as 'N or harder' (e.g. 19)")
    ap.add_argument("--no-calibrate", action="store_true",
                    help="skip the monotone calibration step")
    ap.add_argument("--no-tech", action="store_true",
                    help="drop tech-count features (ablation)")
    ap.add_argument("--min-pack-charts", type=int, default=10)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--compare-gbm", action="store_true")
    ap.add_argument("--robust", action="store_true",
                    help="use the Huber fit for the final model and "
                         "model.json (a ridge-vs-Huber comparison is always "
                         "printed)")
    ap.add_argument("--no-dedupe", action="store_true",
                    help="keep duplicate charts (for comparison only)")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cap = int(a.censor_top)
    kind = "huber" if a.robust else "ridge"
    L = []
    notes = []
    df, X, names, conflicts = load(a.csv, a.steps_type, notes,
                                   dedupe=not a.no_dedupe,
                                   exclude=a.exclude_pack,
                                   use_tech=not a.no_tech)
    L.append("CHART DIFFICULTY MODEL FIT v2  (steps type: %s)" % a.steps_type)
    L.append("=" * 60)
    L.append("options: group-by=%s  censor-top=%s  calibrate=%s  tech-features=%s"
             "  base=%s" % (a.group_by, cap or "off",
                            "off" if a.no_calibrate else "on",
                            "off" if a.no_tech else "on", kind))
    L.extend(notes)
    if len(df) < 50 or df["pack"].nunique() < 3:
        sys.exit("\n".join(L) + "\nToo few charts or packs to fit (need >= 50 "
                 "charts and >= 3 packs).")
    y = df["meter"].to_numpy(dtype=float)
    if a.group_by == "song":
        groups = song_key(df)
        L.append("cross-validation holds out whole songs: %d songs"
                 % len(np.unique(groups)))
    else:
        groups = df["pack"].astype(str).to_numpy()
        L.append("cross-validation holds out whole packs: %d packs"
                 % len(np.unique(groups)))

    L.append("")
    L.append("LABEL COUNTS (meter: charts). Levels with < 20 charts are weak.")
    counts = pd.Series(y).value_counts().sort_index()
    L.append("  " + "  ".join("%d:%d" % (k_, v) for k_, v in counts.items()))
    thin = [int(k_) for k_, v in counts.items() if v < 20]
    if thin:
        L.append("  THIN levels (< 20 charts): %s" % thin)
    if cap:
        L.append("  labels >= %d (%d charts) are treated as '%d or harder'"
                 % (cap, int((y >= cap).sum()), cap))
    L.append("  NOTE: if the corpus mixes rating scales, expect a blurred fit.")

    base_fn = make_fn("ridge", cap)
    huber_fn = make_fn("huber", cap)
    main_fn = huber_fn if a.robust else base_fn

    oof, k = grouped_oof(X, y, groups, a.folds, main_fn, a.seed)
    m = metrics(y, oof, cap)
    L.append("")
    L.append("CROSS-VALIDATED RESULT, %s-grouped, %d folds (%s, raw)"
             % (a.group_by, k, kind))
    L.append("  n=%d  MAE=%.2f  RMSE=%.2f  exact=%.1f%%  within1=%.1f%%  "
             "spearman=%.3f" % (m["n"], m["MAE"], m["RMSE"], m["exact_%"],
                               m["within1_%"], m["spearman"]))
    slope = float(np.polyfit(oof, y, 1)[0])
    L.append("  calibration slope (label vs prediction) = %.2f  "
             "(> 1 means predictions are compressed toward the middle)" % slope)

    oof_cal = None
    mc = None
    if not a.no_calibrate:
        oof_cal = calibrated_oof(X, y, groups, a.folds, main_fn, a.seed)
        mc = metrics(y, oof_cal, cap)
        L.append("  with monotone calibration (nested CV): MAE=%.2f  RMSE=%.2f"
                 "  exact=%.1f%%  within1=%.1f%%  spearman=%.3f"
                 % (mc["MAE"], mc["RMSE"], mc["exact_%"], mc["within1_%"],
                    mc["spearman"]))

    if a.compare_gbm:
        oof_g, _ = grouped_oof(X, y, groups, a.folds, gbm_fn, a.seed)
        mg = metrics(y, oof_g, cap)
        L.append("  gradient boosting (comparison, uncensored fit): MAE=%.2f  "
                 "RMSE=%.2f  exact=%.1f%%  within1=%.1f%%  spearman=%.3f"
                 % (mg["MAE"], mg["RMSE"], mg["exact_%"], mg["within1_%"],
                    mg["spearman"]))
        L.append("    Reading: if boosting is clearly better than the "
                 "calibrated linear model, the features carry interactions a "
                 "linear formula misses; if about equal, keep the formula "
                 "(it can be ported to Lua, boosting cannot, easily).")

    L.append("")
    oof_h, _ = grouped_oof(X, y, groups, a.folds, huber_fn, a.seed)
    oof_r, _ = (grouped_oof(X, y, groups, a.folds, base_fn, a.seed)
                if a.robust else (oof, k))
    m_r, mh = metrics(y, oof_r, cap), metrics(y, oof_h, cap)
    L.append("ROBUST (HUBER) VS RIDGE, same folds")
    for nm, mm in (("ridge", m_r), ("huber", mh)):
        L.append("  %-5s MAE=%.2f  RMSE=%.2f  within1=%.1f%%  spearman=%.3f"
                 % (nm, mm["MAE"], mm["RMSE"], mm["within1_%"], mm["spearman"]))
    L.append("  mean |ridge - huber| prediction difference: %.3f foot"
             % float(np.mean(np.abs(oof_r - oof_h))))
    L.append("  Reading: near-identical numbers mean outliers are not "
             "distorting the fit.")

    resid = y - oof
    if cap:  # a censored chart predicted at or above its label is not a miss
        resid = np.where((y >= cap) & (oof >= y), 0.0, resid)
    med = float(np.median(resid))
    mad = float(np.median(np.abs(resid - med)))
    sig = 1.4826 * mad if mad > 0 else float(resid.std())
    z = (resid - med) / sig if sig > 0 else np.zeros_like(resid)
    L.append("")
    L.append("LARGEST MISSES (label minus out-of-fold raw prediction)")
    L.append("  %d charts beyond 3 robust SDs (SD=%.2f foot from MAD); %d "
             "charts miss by 2 feet or more."
             % (int((np.abs(z) > 3).sum()), sig, int((np.abs(resid) >= 2).sum())))
    order = np.argsort(-np.abs(resid))
    for i in order[:20]:
        L.append("  %-26s %-14s %-9s label %2d  pred %5.1f  miss %+5.1f"
                 % (str(df["title"].iloc[i])[:26], str(df["pack"].iloc[i])[:14],
                    str(df["difficulty"].iloc[i])[:9], int(y[i]), oof[i],
                    resid[i]))
    L.append("  Positive miss = rated harder than the features suggest. Do "
             "not delete these automatically. Top 100 are in outliers.csv.")
    pd.DataFrame({
        "title": df["title"].iloc[order[:100]].to_numpy(),
        "pack": df["pack"].iloc[order[:100]].to_numpy(),
        "difficulty": df["difficulty"].iloc[order[:100]].to_numpy(),
        "song_file": df["song_file"].iloc[order[:100]].to_numpy(),
        "meter": y[order[:100]], "oof_pred": oof[order[:100]],
        "miss": resid[order[:100]], "robust_z": z[order[:100]],
    }).to_csv(out / "outliers.csv", index=False)

    L.append("")
    L.append("BY LABELLED LEVEL (out-of-fold). bias = mean(pred - label)")
    if oof_cal is not None:
        L.append("  level   n   raw_pred  raw_bias  raw_MAE |  cal_pred  "
                 "cal_bias  cal_MAE")
        raw_rows = per_level(y, oof)
        cal_rows = per_level(y, oof_cal)
        for (lv, n, mp, bias, mae), (_, _, mp2, b2, mae2) in zip(raw_rows,
                                                                  cal_rows):
            L.append("  %5d %4d   %7.2f  %+8.2f  %7.2f |  %7.2f  %+8.2f  %7.2f"
                     % (lv, n, mp, bias, mae, mp2, b2, mae2))
    else:
        L.append("  level   n   mean_pred   bias    MAE")
        for lv, n, mp, bias, mae in per_level(y, oof):
            L.append("  %5d %4d   %8.2f  %+6.2f  %5.2f" % (lv, n, mp, bias, mae))
    if cap:
        L.append("  (levels >= %d: a prediction above the label is correct "
                 "by assumption, so their bias/MAE here are the raw numbers "
                 "and look worse than the censored-aware totals.)" % cap)

    L.append("")
    L.append("LEARNING CURVE (raw-model test MAE on held-out %ss vs training "
             "size)" % a.group_by)
    L.append("  train_n   test_MAE   sd_over_folds")
    for n, mae, sd in learning_curve(X, y, groups, a.folds, a.seed, base_fn):
        L.append("  %7.0f   %8.3f   %8.3f" % (n, mae, sd))

    pk = per_pack(df, y, oof, a.min_pack_charts)
    pk.to_csv(out / "per_pack_offsets.csv", index=False)
    L.append("")
    L.append("PACK OFFSETS (label minus raw prediction; packs with >= %d "
             "charts)" % a.min_pack_charts)
    L.append("  Flagged = |offset| >= 0.5 and > 2 standard errors: possible "
             "different rating scale or style.")
    for _, r in pk.head(10).iterrows():
        L.append("  %-40s n=%3d offset=%+.2f se=%.2f %s"
                 % (str(r["pack"])[:40], r["n_charts"],
                    r["offset_label_minus_pred"], r["se"],
                    "FLAG" if r["flag"] else ""))
    L.append("  (full list: per_pack_offsets.csv; flagged packs: %d of %d)"
             % (int(pk["flag"].sum()), len(pk)))
    L.append("  Residual spread per pack (SD of label minus prediction); a "
             "pack far above the others is probably on a different scale:")
    sd_tab = (pd.DataFrame({"pack": df["pack"], "res": y - oof})
              .groupby("pack")["res"].agg(["count", "std"]))
    sd_tab = sd_tab[sd_tab["count"] >= a.min_pack_charts]
    med_sd = float(sd_tab["std"].median())
    for pn, r in sd_tab.sort_values("std", ascending=False).head(5).iterrows():
        L.append("    %-40s SD=%.2f %s" % (str(pn)[:40], r["std"],
                 "<-- well above median %.2f" % med_sd
                 if r["std"] > 1.4 * med_sd else ""))

    # ----- final model ------------------------------------------------------
    cens_all = (y >= cap) if cap else np.zeros(len(y), dtype=bool)
    sc, mdl = fit_model(X, y, cens_all, kind)
    coef = mdl.coef_ / sc.scale_
    intercept = float(mdl.intercept_ - np.sum(mdl.coef_ * sc.mean_ / sc.scale_))
    kx = ky = None
    if not a.no_calibrate:
        inner, _ = grouped_oof(X, y, groups, a.folds, main_fn, a.seed)
        kx, ky = make_calibrator(inner, y)
    mname = "%s (alpha 3)%s" % ("Huber (epsilon 1.35)" if a.robust else "ridge",
                                ", top label censored at %d" % cap if cap else "")
    L.append("")
    L.append("FINAL MODEL (fit on all charts; %s, raw-feature form)" % mname)
    L.append("  raw = b0 + sum(coef_i * feature_i)")
    if kx is not None:
        L.append("  rating = clamp(round(interp(raw, knots)), 1, 20)  "
                 "[knots below]")
    else:
        L.append("  rating = clamp(round(raw), 1, 20)")
    L.append("  b0 = %.4f" % intercept)
    for i in np.argsort(-np.abs(mdl.coef_)):
        L.append("  %-28s coef=%+.5f   (standardized %+.3f)"
                 % (names[i], coef[i], mdl.coef_[i]))
    L.append("  Standardized values are comparable between features; large "
             "ones drive the fit. Correlated features share weight, so do "
             "not read single coefficients as 'causes'.")
    L.append("  These coefficients are in-sample; trust the cross-validated "
             "numbers above, not this fit.")
    if kx is not None:
        L.append("")
        L.append("CALIBRATION KNOTS (raw model value -> rating; linear between "
                 "knots, flat outside)")
        L.append("  " + "  ".join("%.1f->%.2f" % (x_, y_) for x_, y_ in zip(kx, ky)))
        L.append("  Highest calibrated rating: %.2f. The corpus has no labels "
                 "above %d, so the map cannot place anything higher; a 1-20 "
                 "scale needs a separate decision (e.g. rescale, or "
                 "extrapolate and accept it is unvalidated)."
                 % (float(np.max(ky)), int(y.max())))

    def final_value(Xf):
        raw = sc.transform(Xf)
        raw = mdl.predict(raw)
        return raw, (apply_cal(raw, kx, ky) if kx is not None else raw)

    if len(conflicts):
        n_conf = int(conflicts["dup_group"].nunique())
        L.append("")
        L.append("RE-RATED DUPLICATES (identical notes + BPMs, different "
                 "meters; excluded from fitting)")
        L.append("  Model value is from the final model, which never saw "
                 "these charts. %d group(s)." % n_conf)
        Xc, _ = build_features(conflicts, not a.no_tech)
        okc = np.isfinite(Xc.to_numpy(dtype=float)).all(axis=1)
        cc, Xc = conflicts[okc], Xc[okc]
        _, pc = final_value(Xc)
        seen, shown = set(), 0
        for (_, r), p in zip(cc.iterrows(), pc):
            gid = r["dup_group"]
            if gid in seen:
                continue
            seen.add(gid)
            sub = conflicts[conflicts["dup_group"] == gid]
            ms = sorted({int(x) for x in sub["meter"]})
            pks = sorted({str(x) for x in sub["pack"]})
            L.append("  %-30s meters %-9s model %5.1f   packs %s"
                     % (str(r["title"])[:30], "/".join(map(str, ms)), p,
                        ", ".join(pks)[:46]))
            shown += 1
            if shown >= 25:
                L.append("  ... first 25 shown")
                break

    model = {"version": 2, "steps_type": a.steps_type, "intercept": intercept,
             "coefficients": {names[i]: float(coef[i]) for i in range(len(names))},
             "fit": mname, "alpha": 3.0, "n_charts": int(len(df)),
             "group_by": a.group_by, "censor_top": cap,
             "excluded_packs": list(a.exclude_pack),
             "tech_features": not a.no_tech,
             "cv_metrics_raw": m,
             "cv_metrics_calibrated": mc,
             "calibration_knots": (None if kx is None else
                                   {"x": [float(v) for v in kx],
                                    "y": [float(v) for v in ky]}),
             "calibration_slope": slope}
    (out / "model.json").write_text(json.dumps(model, indent=2),
                                    encoding="utf-8")
    cols = {"pack": df["pack"], "title": df["title"]}
    if "artist" in df.columns:
        cols["artist"] = df["artist"]
    cols.update({"song_file": df["song_file"], "difficulty": df["difficulty"],
                 "meter": y, "oof_pred": oof, "oof_pred_huber": oof_h})
    if oof_cal is not None:
        cols["oof_pred_cal"] = oof_cal
    cols["miss"] = y - oof
    pd.DataFrame(cols).to_csv(out / "oof_predictions.csv", index=False)
    text = "\n".join(L)
    (out / "fit_report.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
