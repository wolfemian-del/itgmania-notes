#!/usr/bin/env python3
"""Apply a fitted model.json (v2) to the extractor CSV: the Python reference
for checking the Lua port.
 
Usage:
    python apply_model.py features.csv model.json [OUT.csv] [--steps-type dance-single]
    python apply_model.py features.csv model.json --lookup "part of a title"
 
--lookup prints, for matching charts, the label, the raw model value, the
calibrated value, and the rating (1..19), plus the feature values the Lua
script should reproduce. Compare these with the in-game output of
DifficultyModel.Rating(steps). Note: the model was fitted on these same
charts, so for the labelled meter the numbers are in-sample.
 
Needs fit_difficulty_model.py in the same folder (pandas, numpy, scikit-learn,
scipy).
"""
import argparse
import json
import sys
from pathlib import Path
 
import numpy as np
import pandas as pd
 
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_difficulty_model import build_features  # noqa: E402
 
 
def rate(df, model):
    X, names = build_features(df, model.get("tech_features", True))
    raw = np.full(len(df), model["intercept"], dtype=float)
    for k, c in model["coefficients"].items():
        if k not in X.columns:
            sys.exit("feature %s in model.json is not computable here" % k)
        raw += c * X[k].to_numpy(dtype=float)
    cal = model.get("calibration_knots")
    val = np.interp(raw, cal["x"], cal["y"]) if cal else raw
    rating = np.clip(np.floor(val + 0.5), 1, 19)
    return X, raw, val, rating
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("model")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--steps-type", default="dance-single")
    ap.add_argument("--lookup")
    a = ap.parse_args()
    model = json.load(open(a.model, encoding="utf-8"))
    df = pd.read_csv(a.csv, encoding="utf-8-sig")
    df = df[df["steps_type"] == a.steps_type].reset_index(drop=True)
    X, raw, val, rating = rate(df, model)
    df["model_raw"], df["model_calibrated"], df["model_rating"] = raw, val, rating
    if a.lookup:
        hit = df[df["title"].astype(str).str.contains(a.lookup, case=False,
                                                      regex=False)]
        if hit.empty:
            sys.exit("No chart title contains %r." % a.lookup)
        for i in hit.index[:12]:
            print("%s [%s %s] label %s | raw %.4f  calibrated %.4f  rating %d"
                  % (df.at[i, "title"], a.steps_type, df.at[i, "difficulty"],
                     df.at[i, "meter"], raw[i], val[i], rating[i]))
            print("   " + "  ".join("%s=%.5g" % (c, X.at[i, c])
                                    for c in model["coefficients"]
                                    if model["coefficients"][c] != 0.0))
        return
    err = rating - df["meter"].to_numpy(dtype=float)
    print("charts: %d  exact %.1f%%  within1 %.1f%%  (in-sample)"
          % (len(df), 100 * np.mean(err == 0), 100 * np.mean(np.abs(err) <= 1)))
    if a.out:
        keep = [c for c in ("pack", "title", "difficulty", "meter") if c in df]
        df[keep + ["model_raw", "model_calibrated", "model_rating"]].to_csv(
            a.out, index=False)
        print("written to %s" % a.out)
 
 
if __name__ == "__main__":
    main()