import json
import time
import sys
sys.path.insert(0, ".")
from pii_mask import PIIMask

def load_dataset(path="test_dataset_7000.json"):
    with open(path) as f:
        data = json.load(f)
    return data["samples"]

def compute_metrics(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1

def run_benchmark():
    print("=" * 72)
    print("  BENCHMARK: PIIMask on 7000 Indian-context samples")
    print("=" * 72)

    print("\nLoading PIIMask...")
    mask = PIIMask()

    print("\nLoading dataset (7000 samples)...")
    samples = load_dataset()
    print(f"  Loaded {len(samples)} samples\n")

    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_times = []
    per_cat = {}
    error_samples = []

    for idx, sample in enumerate(samples):
        text = sample["text"]
        expected = set(sample["expected"])

        t0 = time.perf_counter()
        redacted, spans = mask.analyze(text)
        elapsed = time.perf_counter() - t0
        total_times.append(elapsed)

        detected = set()
        for span in spans:
            label = span.label
            if label == "PER":
                label = "PERSON"
            detected.add(label)

        tp = expected & detected
        fp = detected - expected
        fn = expected - detected

        total_tp += len(tp)
        total_fp += len(fp)
        total_fn += len(fn)

        for label in expected:
            per_cat.setdefault(label, {"tp": 0, "fp": 0, "fn": 0})
            if label in detected:
                per_cat[label]["tp"] += 1
            else:
                per_cat[label]["fn"] += 1
        for label in detected - expected:
            per_cat.setdefault(label, {"tp": 0, "fp": 0, "fn": 0})
            per_cat[label]["fp"] += 1

        if fp or fn:
            error_samples.append({
                "idx": idx,
                "text": text[:120],
                "expected": list(expected),
                "detected": list(detected),
                "false_positives": list(fp),
                "false_negatives": list(fn),
            })

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx+1}/{len(samples)}...")

    avg_ms = (sum(total_times) / len(total_times)) * 1000
    p, r, f1 = compute_metrics(total_tp, total_fp, total_fn)

    print("\n" + "=" * 72)
    print("  OVERALL RESULTS")
    print("=" * 72)
    print(f"  Samples          : {len(samples)}")
    print(f"  Avg inference    : {avg_ms:.2f} ms/sample")
    print(f"  Precision        : {p:.4f}")
    print(f"  Recall           : {r:.4f}")
    print(f"  F1 Score         : {f1:.4f}")
    print(f"  True Positives   : {total_tp}")
    print(f"  False Positives  : {total_fp}")
    print(f"  False Negatives  : {total_fn}")

    print(f"\n  {'─' * 72}")
    print(f"  PER-CATEGORY RESULTS")
    print(f"  {'─' * 72}")
    print(f"  {'Label':<12} {'Precision':>11} {'Recall':>9} {'F1':>8} {'TP':>6} {'FP':>5} {'FN':>5} {'Samples':>8}")
    print(f"  {'─' * 72}")
    sorted_cats = sorted(per_cat.items(), key=lambda x: sum(x[1].values()), reverse=True)
    for label, c in sorted_cats:
        cp, cr, cf1 = compute_metrics(c["tp"], c["fp"], c["fn"])
        total_samples = c["tp"] + c["fn"]
        print(f"  {label:<12} {cp:>11.4f} {cr:>9.4f} {cf1:>8.4f} {c['tp']:>6} {c['fp']:>5} {c['fn']:>5} {total_samples:>8}")

    print(f"\n  ERROR ANALYSIS")
    print(f"  Samples with errors: {len(error_samples)} / {len(samples)} ({100*len(error_samples)/len(samples):.1f}%)")
    
    if error_samples:
        fp_causes = {}
        fn_causes = {}
        for es in error_samples:
            for fp_label in es["false_positives"]:
                fp_causes[fp_label] = fp_causes.get(fp_label, 0) + 1
            for fn_label in es["false_negatives"]:
                fn_causes[fn_label] = fn_causes.get(fn_label, 0) + 1

        print(f"\n  Top false positive categories:")
        for label, count in sorted(fp_causes.items(), key=lambda x: -x[1])[:5]:
            print(f"    {label:<12}: {count}")

        print(f"\n  Top false negative categories:")
        for label, count in sorted(fn_causes.items(), key=lambda x: -x[1])[:5]:
            print(f"    {label:<12}: {count}")

        print(f"\n  Sample errors (first 10):")
        for es in error_samples[:10]:
            print(f"  #{es['idx']}: expected={es['expected']}, got={es['detected']}")
            print(f"       text: {es['text']}...")

    results = {
        "dataset": {"size": len(samples)},
        "overall": {
            "avg_inference_ms": round(avg_ms, 2),
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "true_positives": total_tp,
            "false_positives": total_fp,
            "false_negatives": total_fn,
        },
        "per_category": {
            label: {
                "precision": round(compute_metrics(c["tp"], c["fp"], c["fn"])[0], 4),
                "recall": round(compute_metrics(c["tp"], c["fp"], c["fn"])[1], 4),
                "f1": round(compute_metrics(c["tp"], c["fp"], c["fn"])[2], 4),
                "samples": c["tp"] + c["fn"],
                "tp": c["tp"],
                "fp": c["fp"],
                "fn": c["fn"],
            }
            for label, c in per_cat.items()
        },
        "error_count": len(error_samples),
    }

    with open("benchmark_7000_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: benchmark_7000_results.json")

    with open("benchmark_7000_errors.json", "w") as f:
        json.dump(error_samples, f, indent=2)
    print(f"  Saved: benchmark_7000_errors.json")

if __name__ == "__main__":
    run_benchmark()
