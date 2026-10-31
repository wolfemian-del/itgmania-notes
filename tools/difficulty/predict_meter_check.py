#!/usr/bin/env python3
"""Compare ITGmania's built-in Steps::PredictMeter with each chart's own meter.

Works from the CSV written by extract_chart_features.py, so no in-game
scripting is needed. It re-implements the engine formula (Steps.cpp, v1.3.0)
on the cached radar values and the chart's difficulty label.

Usage:
    python predict_meter_check.py features.csv [OUT.csv] [--steps-type dance-single]
    python predict_meter_check.py features.csv --lookup "part of a song title"

--calibrate adds a fairer comparison: PredictMeter's value is mapped to the
chart labels with a monotone (isotonic) curve learned inside cross-validation
(whole songs held out), so the numbers can be set beside fit_difficulty_model.py's
calibrated results. Options for it: --exclude-pack TEXT (repeatable),
--censor-top N (labels >= N mean "N or harder"), --group-by song|pack.
--lookup prints the radar values and the predicted meter (2 decimals, as the
editor shows it) for matching charts, so you can compare with the editor's
"Predicted Meter" row in the game and confirm this copy of the formula.

Needs: pandas (pip install pandas); --calibrate also needs numpy, scipy and
scikit-learn. Tested on synthetic data only.
"""
import argparse
import sys

import pandas as pd

RADAR = ["radar_Stream", "radar_Voltage", "radar_Air", "radar_Freeze",
         "radar_Chaos"]
DIFF_OFFSET = {"Beginner": -0.877, "Easy": -0.877, "Medium": 0.0,
               "Hard": 0.722, "Challenge": 0.722, "Edit": 0.0}


def predict_meter(stream, voltage, air, freeze, chaos, difficulty):
    """Steps::PredictMeter, float result (the engine's TidyUpData then casts
    with int(), which truncates)."""
    m = 0.775
    m += 10.1 * stream + 5.27 * voltage - 0.905 * air - 1.10 * freeze
    m += 2.86 * chaos
    m += DIFF_OFFSET.get(str(difficulty), 0.0)
    m += -6.35 * (stream * voltage)
    m += -2.58 * (chaos * chaos)
    return max(m, 1.0)


def calibrated_comparison(df, a):
    """PredictMeter -> label through a monotone map learned in cross-validation
    (nested over whole songs or packs), scored like fit_difficulty_model.py."""
    import re

    import numpy as np
    from scipy.stats import spearmanr
    from sklearn.isotonic import IsotonicRegression
    from sklearn.model_selection import GroupKFold

    y = df["meter"].to_numpy(dtype=float)
    p = df["predicted"].to_numpy(dtype=float)
    if a.group_by == "song" and {"title", "artist"} <= set(df.columns):
        norm = lambda v: re.sub(r"[^0-9a-z]+", "", str(v).lower())  # noqa: E731
        groups = (df["title"].map(norm) + "|" + df["artist"].map(norm)).to_numpy()
        gname = "songs"
    elif "pack" in df.columns:
        groups = df["pack"].astype(str).to_numpy()
        gname = "packs"
    else:
        sys.exit("--calibrate needs title+artist or pack columns")
    k = max(2, min(a.folds, len(np.unique(groups))))
    cap = a.censor_top
    cal = np.full(len(y), np.nan)
    for tr, te in GroupKFold(n_splits=k).split(p, y, groups):
        iso = IsotonicRegression(increasing=True, out_of_bounds="clip")
        iso.fit(p[tr], y[tr])
        cal[te] = iso.predict(p[te])

    def score(pred):
        r = np.clip(np.rint(pred), 1, 20)
        cens = (y >= cap) if cap else np.zeros(len(y), dtype=bool)
        err = np.where(cens & (pred >= y), 0.0, pred - y)
        ok1 = (np.abs(r - y) <= 1) | (cens & (r >= y))
        ex = (r == y) | (cens & (r >= y))
        return (np.mean(np.abs(err)), np.sqrt(np.mean(err ** 2)),
                100 * np.mean(ex), 100 * np.mean(ok1),
                spearmanr(y, pred).statistic)

    print()
    print("CALIBRATED COMPARISON (%d charts, %s held out together, %d folds%s)"
          % (len(y), gname, k,
             ", labels >= %d treated as '%d or harder'" % (cap, cap) if cap else ""))
    print("                            MAE   RMSE  exact  within1  spearman")
    for nm, pr in (("PredictMeter as shipped", p),
                   ("PredictMeter, calibrated", cal)):
        m = score(pr)
        print("  %-24s %5.2f  %5.2f  %4.1f%%   %4.1f%%    %.3f" % ((nm,) + m))
    levels = np.unique(y)
    print()
    print("  calibrated PredictMeter by official level (mean prediction, MAE)")
    for lv in levels:
        s_ = y == lv
        print("   %3d  n=%4d  mean_cal=%5.2f  MAE=%.2f"
              % (lv, s_.sum(), cal[s_].mean(), np.abs(cal[s_] - lv).mean()))
    flat = len(np.unique(np.round(cal, 3)))
    print("  distinct calibrated values: %d (isotonic output is a step "
          "function; few steps means PredictMeter cannot separate levels)" % flat)
    print("  Reading: fit_difficulty_model.py's calibrated result for the same "
          "corpus is MAE 0.61, within1 94.9%, spearman 0.985 (v2, Wii "
          "excluded, labels >= 19 censored).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--steps-type", default="dance-single")
    ap.add_argument("--lookup")
    ap.add_argument("--calibrate", action="store_true",
                    help="also report PredictMeter after a cross-validated "
                         "monotone calibration to the labels")
    ap.add_argument("--exclude-pack", action="append", default=[],
                    metavar="TEXT", help="drop packs whose name contains TEXT")
    ap.add_argument("--censor-top", type=int, default=0, metavar="N")
    ap.add_argument("--group-by", choices=["song", "pack"], default="song")
    ap.add_argument("--folds", type=int, default=5)
    a = ap.parse_args()

    df = pd.read_csv(a.csv)
    need = RADAR + ["difficulty", "meter", "steps_type", "title"]
    miss = [c for c in need if c not in df.columns]
    if miss:
        sys.exit("CSV is missing columns: %s" % ", ".join(miss))
    df = df[df["steps_type"] == a.steps_type].copy()
    if "difficulty" in df.columns and a.calibrate:
        df = df[df["difficulty"].astype(str) != "Edit"]
    for ex in a.exclude_pack:
        if "pack" not in df.columns:
            sys.exit("--exclude-pack needs a 'pack' column in the CSV")
        hit = df["pack"].astype(str).str.contains(ex, case=False, regex=False)
        print("excluded by --exclude-pack %r: %d charts" % (ex, int(hit.sum())))
        df = df[~hit]
    for c in RADAR + ["meter"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n0 = len(df)
    df = df.dropna(subset=RADAR + ["meter"])
    df = df[(df[RADAR] >= 0).all(axis=1)]  # -1 means "unknown" in the cache
    print("charts: %d with %s (%d dropped: missing or unknown radar values)"
          % (len(df), a.steps_type, n0 - len(df)))
    if df.empty:
        sys.exit("Nothing to compare.")

    df["predicted"] = [predict_meter(*r) for r in
                       zip(df.radar_Stream, df.radar_Voltage, df.radar_Air,
                           df.radar_Freeze, df.radar_Chaos, df.difficulty)]
    df["predicted_int"] = df["predicted"].astype(int)  # int() truncates

    if a.lookup:
        hit = df[df["title"].astype(str).str.contains(a.lookup, case=False,
                                                      regex=False)]
        if hit.empty:
            sys.exit("No chart title contains %r." % a.lookup)
        for _, r in hit.head(20).iterrows():
            print("%s [%s %s] meter %d | Stream %.3f Voltage %.3f Air %.3f "
                  "Freeze %.3f Chaos %.3f | predicted %.2f"
                  % (r["title"], a.steps_type, r["difficulty"], r["meter"],
                     r.radar_Stream, r.radar_Voltage, r.radar_Air,
                     r.radar_Freeze, r.radar_Chaos, r["predicted"]))
        return

    df["diff"] = df["predicted"] - df["meter"]
    print()
    print("level    n   mean_pred  mean(pred-meter)  int(pred)==meter  within1")
    for lv, g in df.groupby("meter"):
        print("%5d %4d   %8.2f   %+14.2f   %13.0f%%   %6.0f%%"
              % (lv, len(g), g["predicted"].mean(), g["diff"].mean(),
                 100 * (g["predicted_int"] == g["meter"]).mean(),
                 100 * ((g["predicted_int"] - g["meter"]).abs() <= 1).mean()))
    rho = df["predicted"].corr(df["meter"], method="spearman")
    print()
    print("overall: MAE %.2f foot, rank correlation %.3f, exact(int) %.0f%%"
          % (df["diff"].abs().mean(), rho,
             100 * (df["predicted_int"] == df["meter"]).mean()))
    print("highest predicted value in the library: %.2f" % df["predicted"].max())
    over = int((df["radar_Stream"] > 1).sum())
    print("charts with Stream > 1 (average above 7 notes/s): %d (%.0f%%)"
          % (over, 100 * over / len(df)))
    hi = df[df["meter"] >= 12]
    if len(hi):
        print("charts rated 12+: %d, of which predicted below 11: %.0f%%"
              % (len(hi), 100 * (hi["predicted"] < 11).mean()))
    if a.calibrate:
        calibrated_comparison(df, a)
    if a.out:
        keep = [c for c in ("pack", "title", "difficulty", "meter") if c in df]
        df[keep + RADAR + ["predicted", "predicted_int", "diff"]].to_csv(
            a.out, index=False)
        print("per-chart results written to %s" % a.out)


if __name__ == "__main__":
    main()
