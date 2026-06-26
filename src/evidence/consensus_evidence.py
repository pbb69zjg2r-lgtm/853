"""
Multi-run consensus for evidence units (step 3b).

Reads multiple independent extraction runs, matches evidence units
by Jaccard similarity of claim text, and keeps units that appear in
at least --min-runs runs (default 2).

Usage:
    python consensus_evidence.py <run_dir>/03_evidence [--min-runs 2] [--threshold 0.4]
"""

import json
import os
import sys
from collections import defaultdict


# ---------------------------------------------------------------------------
# Jaccard similarity
# ---------------------------------------------------------------------------

def tokenize(text):
    """Simple tokenization: lowercase, split on non-alphanumeric."""
    import re
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a, b):
    """Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def claim_similarity(u1, u2):
    """Similarity between two evidence units based on claim text + evidence type."""
    # Evidence type must match
    if u1.get("evidence_type") != u2.get("evidence_type"):
        return 0.0

    claim1 = u1.get("claim", "")
    claim2 = u2.get("claim", "")
    tok1 = tokenize(claim1)
    tok2 = tokenize(claim2)

    # Also consider entity overlap for disambiguation
    entities1 = set()
    entities2 = set()
    for e in u1.get("raw_entities", []):
        if isinstance(e, dict):
            entities1.add(e.get("raw_name", "").lower())
    for e in u2.get("raw_entities", []):
        if isinstance(e, dict):
            entities2.add(e.get("raw_name", "").lower())

    claim_sim = jaccard(tok1, tok2)
    entity_sim = jaccard(entities1, entities2) if entities1 or entities2 else 1.0

    # Weighted: 70% claim text, 30% entity overlap
    return 0.7 * claim_sim + 0.3 * entity_sim


# ---------------------------------------------------------------------------
# Graph-based matching
# ---------------------------------------------------------------------------

def build_similarity_graph(all_units, threshold):
    """Build undirected graph of unit pairs with similarity >= threshold."""
    edges = []
    n = len(all_units)

    for i in range(n):
        for j in range(i + 1, n):
            # Only compare across different runs
            if all_units[i]["_run"] == all_units[j]["_run"]:
                continue
            sim = claim_similarity(all_units[i], all_units[j])
            if sim >= threshold:
                edges.append((i, j, sim))

    return edges


def find_connected_components(n, edges):
    """Union-Find to find connected components."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i, j, _ in edges:
        union(i, j)

    components = defaultdict(list)
    for i in range(n):
        components[find(i)].append(i)

    return list(components.values())


# ---------------------------------------------------------------------------
# Canonical unit selection
# ---------------------------------------------------------------------------

def select_canonical(units_in_component):
    """From a group of matched units, pick the best representative.

    Prefers: the unit with the most complete fields, longest claim,
    and highest number of source blocks.
    """
    def score(u):
        s = 0
        claim_len = len(u.get("claim", ""))
        s += min(claim_len, 300) // 10  # longer claim is better, up to 300 chars
        s += len(u.get("raw_entities", [])) * 5
        s += len(u.get("source_trace", {}).get("source_block_ids", [])) * 3
        s += len(u.get("source_trace", {}).get("quote", "")) // 50
        if u.get("statistics", {}).get("p_value"):
            s += 10
        if u.get("statistics", {}).get("effect_size"):
            s += 5
        if u.get("condition_context", {}):
            s += 3
        return s

    return max(units_in_component, key=score)


def merge_runs(units_in_component):
    """Merge multiple runs of the same unit, taking the union of fields.

    Returns a single unit with:
    - The canonical (highest-scoring) unit's core fields
    - Union of raw_entities (deduplicated by name)
    - Union of source_block_ids
    - Updated extraction_meta with consensus info
    """
    canonical = select_canonical(units_in_component)
    merged = dict(canonical)

    # Union of entities
    entity_map = {}
    for u in units_in_component:
        for e in u.get("raw_entities", []):
            if isinstance(e, dict) and e.get("raw_name"):
                key = e["raw_name"].lower()
                if key not in entity_map:
                    entity_map[key] = e
    merged["raw_entities"] = list(entity_map.values())

    # Union of source_block_ids
    all_block_ids = set()
    for u in units_in_component:
        ids = u.get("source_trace", {}).get("source_block_ids", [])
        all_block_ids.update(ids)
    if "source_trace" not in merged:
        merged["source_trace"] = {}
    merged["source_trace"]["source_block_ids"] = sorted(all_block_ids)

    # Consensus meta
    run_nums = sorted(set(u.get("_run", 0) for u in units_in_component))
    merged["extraction_meta"] = dict(merged.get("extraction_meta", {}))
    merged["extraction_meta"]["consensus_votes"] = len(units_in_component)
    merged["extraction_meta"]["consensus_similarity"] = 1.0  # placeholder
    merged["extraction_meta"]["consensus_runs"] = run_nums

    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_run_units(run_dir, run_num):
    """Load evidence units from a single run file."""
    path = os.path.join(run_dir, f"evidence_units_run{run_num}.jsonl")
    if not os.path.exists(path):
        print(f"  Warning: {path} not found, skipping")
        return []

    units = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                u = json.loads(line)
                u["_run"] = run_num
                units.append(u)
    return units


def run_consensus(evidence_dir, min_runs=2, threshold=0.4):
    """Run consensus on all run files in evidence_dir.

    Returns list of consensus evidence units.
    """
    # Find all run files
    run_files = []
    for fname in sorted(os.listdir(evidence_dir)):
        if fname.startswith("evidence_units_run") and fname.endswith(".jsonl"):
            run_num = int(fname.replace("evidence_units_run", "").replace(".jsonl", ""))
            run_files.append(run_num)

    if len(run_files) < 2:
        print("ERROR: Need at least 2 runs for consensus. Found:")
        for f in sorted(os.listdir(evidence_dir)):
            print(f"  {f}")
        sys.exit(1)

    print(f"Found {len(run_files)} runs: {run_files}")

    # Load all units
    all_units = []
    for run_num in run_files:
        units = load_run_units(evidence_dir, run_num)
        print(f"  Run {run_num}: {len(units)} units")
        all_units.extend(units)

    if not all_units:
        print("No units loaded. Aborting.")
        return []

    print(f"Total: {len(all_units)} units across all runs")

    # Build graph and find components
    edges = build_similarity_graph(all_units, threshold)
    print(f"Similarity graph: {len(edges)} edges (threshold={threshold})")

    components = find_connected_components(len(all_units), edges)

    # Filter by min_runs, merge, and build consensus
    consensus = []
    alone_count = 0
    below_min = 0

    for comp in components:
        run_counts = len(set(all_units[i]["_run"] for i in comp))
        if run_counts < min_runs:
            below_min += len(comp)
            continue

        comp_units = [all_units[i] for i in comp]
        merged = merge_runs(comp_units)
        consensus.append(merged)

    # Count singletons (components of size 1)
    alone_count = sum(1 for c in components if len(c) == 1)

    print(f"Components: {len(components)} total")
    print(f"  Consensus (≥{min_runs} runs): {len(consensus)}")
    print(f"  Below threshold: {below_min}")
    print(f"  Singleton units: {alone_count}")

    return consensus


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    evidence_dir = sys.argv[1]
    min_runs = 2
    threshold = 0.4

    for i, arg in enumerate(sys.argv):
        if arg == "--min-runs" and i + 1 < len(sys.argv):
            min_runs = int(sys.argv[i + 1])
        if arg == "--threshold" and i + 1 < len(sys.argv):
            threshold = float(sys.argv[i + 1])

    print(f"=== Evidence Consensus ===")
    print(f"Directory: {evidence_dir}")
    print(f"Min runs: {min_runs}, Threshold: {threshold}")
    print()

    consensus = run_consensus(evidence_dir, min_runs, threshold)

    # Renumber
    for i, u in enumerate(consensus):
        u["evidence_id"] = f"E{i + 1:04d}"
        # Clean up internal fields
        u.pop("_run", None)

    # Write output
    out_path = os.path.join(evidence_dir, "evidence_units.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for u in consensus:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")

    print(f"\nConsensus output: {out_path}")
    print(f"Done. {len(consensus)} consensus evidence units written.")


if __name__ == "__main__":
    main()
