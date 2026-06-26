"""consensus_evidence.py — Majority-vote consensus across multiple extraction runs.

Reads evidence_units_run{N}.jsonl files, matches units across runs by
source_text similarity + evidence_type, keeps units appearing in >= min_runs.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def load_units(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def normalize_text(t):
    t = t.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def text_similarity(a, b):
    tokens_a = set(normalize_text(a).split())
    tokens_b = set(normalize_text(b).split())
    if not tokens_a or not tokens_b:
        return 0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def match_units(units_a, units_b, threshold=0.4):
    """Greedy best-match between two unit lists. Returns (idx_a, idx_b, sim)."""
    matches = []
    used_b = set()
    for i, ua in enumerate(units_a):
        best_j = -1
        best_sim = 0
        for j, ub in enumerate(units_b):
            if j in used_b:
                continue
            if ua["evidence_type"] != ub["evidence_type"]:
                continue
            sim = text_similarity(ua["source_text"], ub["source_text"])
            if sim > best_sim:
                best_sim = sim
                best_j = j
        if best_sim >= threshold:
            matches.append((i, best_j, best_sim))
            used_b.add(best_j)
    return matches


def consensus(run_paths, threshold=0.4, min_runs=2):
    all_runs = [load_units(p) for p in run_paths]
    n_runs = len(all_runs)
    reference = all_runs[0]

    vote_counts = [1] * len(reference)
    match_details = [{} for _ in range(len(reference))]

    for run_idx in range(1, n_runs):
        matches = match_units(reference, all_runs[run_idx], threshold)
        for ref_idx, other_idx, sim in matches:
            vote_counts[ref_idx] += 1
            match_details[ref_idx][run_idx] = (other_idx, sim)

    consensus_units = []
    for i, unit in enumerate(reference):
        if vote_counts[i] >= min_runs:
            unit = dict(unit)
            unit["consensus_votes"] = vote_counts[i]
            if match_details[i]:
                avg_sim = sum(s for _, s in match_details[i].values()) / len(match_details[i])
            else:
                avg_sim = 1.0
            unit["consensus_similarity"] = round(avg_sim, 3)
            # Remove per-run metadata from output
            consensus_units.append(unit)

    return consensus_units


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Consensus across extraction runs")
    parser.add_argument("dir", help="Directory containing evidence_units_run*.jsonl files")
    parser.add_argument("--min-runs", type=int, default=2, help="Minimum runs required (default: 2)")
    parser.add_argument("--threshold", type=float, default=0.4, help="Text similarity threshold (default: 0.4)")
    parser.add_argument("-o", "--output", help="Output path (default: <dir>/evidence_units.jsonl)")
    args = parser.parse_args()

    out_dir = Path(args.dir)
    run_files = sorted(out_dir.glob("evidence_units_run*.jsonl"))
    if len(run_files) < 2:
        print(f"ERROR: Need at least 2 run files, found {len(run_files)} in {out_dir}")
        sys.exit(1)

    print(f"Found {len(run_files)} run files:")
    for f in run_files:
        units = load_units(f)
        print(f"  {f.name}: {len(units)} units")

    result = consensus(run_files, threshold=args.threshold, min_runs=args.min_runs)

    out_path = Path(args.output) if args.output else out_dir / "evidence_units.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for u in result:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")

    # Summary
    from collections import Counter
    type_counts = Counter(u["evidence_type"] for u in result)
    vote_dist = Counter(u["consensus_votes"] for u in result)

    print(f"\nConsensus units: {len(result)} (from {sum(len(load_units(f)) for f in run_files)} raw)")
    print(f"Vote distribution: {dict(sorted(vote_dist.items()))}")
    for et, c in type_counts.most_common():
        print(f"  {et}: {c}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
