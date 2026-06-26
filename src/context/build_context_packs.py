"""build_context_packs.py — Bundle evidence units with source text and relations
into LLM-ready context packs for draft entry generation.

Uses relation graph connected components to cluster related evidence into
thematic packs. One pack = one cohesive theme, not 1:1 with evidence units.

Input:  02_source/source_blocks.jsonl + 03_evidence/evidence_units.jsonl
        + 04_relations/evidence_relations.json
Output: 05_context/context_packs.jsonl
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_OUTPUT = {
    "disease_association": "JSON with disease, thermogenesis_phenotype, supporting_evidence_summary, confidence_assessment",
    "detection_method": "JSON with method_name, detection_category, what_it_measures, advantages, limitations",
    "thermogenesis_modulation": "JSON with intervention, target, direction, effect_size, mechanism_brief, evidence_strength",
    "biomarker_panel": "JSON with panel_name, biomarkers, what_status_indicated, clinical_utility",
    "mechanism_pathway": "JSON with pathway_name, steps, key_entities, upstream_activators, downstream_effects",
}


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_adjacency(relations: list[dict]) -> dict[str, set[str]]:
    """Build undirected adjacency from relation edges."""
    adj = defaultdict(set)
    for r in relations:
        s, t = r["source_evidence_id"], r["target_evidence_id"]
        adj[s].add(t)
        adj[t].add(s)
    return adj


def find_clusters(evidence_ids: set[str], adj: dict[str, set[str]],
                  max_size: int = 20) -> list[list[str]]:
    """Find clusters by splitting connected components to max_size via BFS."""
    visited = set()
    clusters = []

    # Sort by degree descending so high-connectivity nodes seed clusters first
    def degree(eid):
        return len(adj.get(eid, set()) & evidence_ids)
    sorted_ids = sorted(evidence_ids, key=degree, reverse=True)

    for eid in sorted_ids:
        if eid in visited:
            continue
        cluster = []
        queue = [eid]
        while queue and len(cluster) < max_size:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            cluster.append(node)
            # Add neighbors, sorted by degree
            neighbors = [(n, degree(n)) for n in adj.get(node, set())
                        if n not in visited and n in evidence_ids]
            neighbors.sort(key=lambda x: -x[1])
            for n, _ in neighbors:
                if n not in queue and n not in visited:
                    queue.append(n)
        clusters.append(cluster)

    return clusters


def pick_task_type(cluster: list[str], ev_map: dict) -> str:
    """Determine the best task type for a cluster based on majority evidence_type."""
    type_counts = Counter(ev_map[eid]["evidence_type"] for eid in cluster if eid in ev_map)
    dominant = type_counts.most_common(1)[0][0]
    # If cluster has >1 type, use a general task
    if len(type_counts) > 1:
        return "summarize_theme"
    return f"summarize_{dominant}"


def build_context_packs(evidence_units: list[dict], relations: list[dict],
                         source_blocks: list[dict]) -> list[dict]:
    ev_map = {e["evidence_id"]: e for e in evidence_units}
    all_eids = set(ev_map.keys())

    # Build adjacency from relations
    adj = build_adjacency(relations)
    # Ensure all evidence units are in adjacency (even isolates)
    for eid in all_eids:
        if eid not in adj:
            adj[eid] = set()

    # Find clusters (connected components)
    clusters = find_clusters(all_eids, adj)

    # Build relation lookup for intra-cluster relations
    rel_map = defaultdict(list)
    for r in relations:
        rel_map[(r["source_evidence_id"], r["target_evidence_id"])].append(r["relation_type"])
        rel_map[(r["target_evidence_id"], r["source_evidence_id"])].append(r["relation_type"])

    packs = []
    for cluster in clusters:
        cluster_set = set(cluster)
        task_type = pick_task_type(cluster, ev_map)

        # Collect all source block IDs for this cluster
        all_block_ids = set()
        for eid in cluster:
            all_block_ids.update(ev_map[eid].get("source_block_ids", []))

        # Build evidence summaries for the prompt
        evidence_items = []
        for eid in sorted(cluster):
            eu = ev_map[eid]
            # Find relations to other members of this cluster
            intra_rels = []
            for other in cluster:
                if other != eid:
                    intra_rels.extend(rel_map.get((eid, other), []))

            evidence_items.append({
                "evidence_id": eid,
                "evidence_type": eu["evidence_type"],
                "source_text": eu.get("source_text", ""),
                "intra_cluster_relations": sorted(set(intra_rels)),
            })

        anchor_evidence = evidence_items[0] if evidence_items else {}
        pack = {
            "pack_id": f"{ev_map[cluster[0]]['paper_id']}_P{len(packs)+1:04d}",
            "paper_id": ev_map[cluster[0]]["paper_id"],
            "task_type": task_type,
            "cluster_size": len(cluster),
            "member_evidence_ids": sorted(cluster),
            "source_block_ids": sorted(all_block_ids),
            "evidence_items": evidence_items,
            "expected_output": EXPECTED_OUTPUT.get(
                task_type.replace("summarize_", ""),
                "JSON with synthesized_summary, key_findings array, entities array, confidence_assessment"
            ),
            "missing_context": [],
        }
        packs.append(pack)

    return packs


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/context/build_context_packs.py <paper_run_dir> [paper_id]")
        sys.exit(1)

    paper_dir = Path(sys.argv[1]).resolve()
    paper_id = sys.argv[2] if len(sys.argv) > 2 else paper_dir.parent.name

    evidence_path = paper_dir / "03_evidence" / "evidence_units.jsonl"
    relations_path = paper_dir / "04_relations" / "evidence_relations.json"
    source_path = paper_dir / "02_source" / "source_blocks.jsonl"

    for p, name in [(evidence_path, "evidence"), (relations_path, "relations"),
                     (source_path, "source")]:
        if not p.exists():
            raise FileNotFoundError(f"{p} not found. Run earlier stages first.")

    evidence_units = load_jsonl(evidence_path)
    relations = load_json(relations_path)
    source_blocks = load_jsonl(source_path)

    print(f"  Evidence units: {len(evidence_units)}")
    print(f"  Relations: {len(relations)}")

    # Cluster stats
    adj = build_adjacency(relations)
    all_eids = set(e["evidence_id"] for e in evidence_units)
    for eid in all_eids:
        if eid not in adj:
            adj[eid] = set()
    clusters_raw = find_clusters(all_eids, adj)
    cluster_sizes = [len(c) for c in clusters_raw]
    print(f"  Clusters: {len(clusters_raw)} (sizes: min={min(cluster_sizes)}, "
          f"max={max(cluster_sizes)}, avg={sum(cluster_sizes)/len(cluster_sizes):.1f})")

    packs = build_context_packs(evidence_units, relations, source_blocks)

    # Type distribution
    type_counts = Counter(p["task_type"] for p in packs)
    total_chars = sum(
        sum(len(e["source_text"]) for e in p["evidence_items"]) for p in packs
    )

    out_dir = paper_dir / "05_context"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "context_packs.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for p in packs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\n  Context packs: {len(packs)} (from {len(evidence_units)} evidence units)")
    print(f"  Task type distribution:")
    for tt, c in type_counts.most_common():
        print(f"    {tt}: {c} packs")
    print(f"  Total evidence chars: {total_chars}")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
