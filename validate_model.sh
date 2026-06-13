#!/usr/bin/env python3
"""
validate_model.py
-----------------
Standalone validation script called by Jenkins after training.
Reads output/metadata.json and exits non-zero if model fails gates.
Can also be run manually to check a trained model.

Usage:
    python scripts/validate_model.py --min_acc 0.75 --min_auc 0.80 --min_f1 0.72
"""
import json
import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Validate PoCL model quality gates")
    parser.add_argument("--meta",    default="output/metadata.json")
    parser.add_argument("--min_acc", type=float, default=0.75)
    parser.add_argument("--min_auc", type=float, default=0.80)
    parser.add_argument("--min_f1",  type=float, default=0.72)
    args = parser.parse_args()

    meta_path = Path(args.meta)
    if not meta_path.exists():
        print(f"ERROR: {meta_path} not found. Did training complete?")
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)

    acc  = meta["val_accuracy"]
    auc  = meta["val_auc"]
    f1   = meta["val_f1"]
    prec = meta["val_precision"]
    rec  = meta["val_recall"]

    print("=" * 48)
    print(f"  Node     : {meta['node_id']} — {meta['name']}")
    print(f"  Samples  : {meta['num_samples']}")
    print(f"  Epochs   : {meta['epochs_trained']}")
    print(f"  Trained  : {meta['trained_at']}")
    print("-" * 48)
    print(f"  Accuracy : {acc:.4f}   (min: {args.min_acc})")
    print(f"  AUC      : {auc:.4f}   (min: {args.min_auc})")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall   : {rec:.4f}")
    print(f"  F1       : {f1:.4f}   (min: {args.min_f1})")
    print("=" * 48)

    failures = []
    if acc < args.min_acc:
        failures.append(f"Accuracy {acc:.4f} < {args.min_acc}")
    if auc < args.min_auc:
        failures.append(f"AUC {auc:.4f} < {args.min_auc}")
    if f1 < args.min_f1:
        failures.append(f"F1 {f1:.4f} < {args.min_f1}")

    if failures:
        print("\nQuality gate FAILED:")
        for f in failures:
            print(f"  ✖ {f}")
        sys.exit(1)

    print("\n  ✔ All quality gates passed — model approved for sending")
    sys.exit(0)


if __name__ == "__main__":
    main()