"""
Context pack builder (step 5 of V2 pipeline).

Groups evidence units into context packs WITHOUT using evidence relations.
Strategy: evidence_type → entity overlap → source proximity.

Each pack contains evidence units of a SINGLE evidence_type, grouped by
shared entities and nearby source sections.

Usage:
    python build_context_packs.py <run_dir> <paper_id>
"""

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.contracts import get_dictionary, stage_input_paths, stage_output_paths

VALID_EVIDENCE_TYPES = get_dictionary("evidence_type")
MAX_PACK_SIZE = 20


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_evidence_units(run_dir):
    inputs = stage_input_paths("context_packs", run_dir)
    return load_jsonl(inputs["evidence_units.jsonl"])


def load_source_blocks(run_dir):
    inputs = stage_input_paths("context_packs", run_dir)
    return load_jsonl(inputs["source_blocks.jsonl"])


# ---------------------------------------------------------------------------
# Entity extraction helpers
# ---------------------------------------------------------------------------

def get_entity_names(unit):
    """Return set of normalized entity names from an evidence unit."""
    names = set()
    for e in unit.get("raw_entities", []):
        if isinstance(e, dict) and e.get("raw_name"):
            names.add(e["raw_name"].lower())
    return names


def get_entity_types(unit):
    """Return set of entity types in a unit."""
    types = set()
    for e in unit.get("raw_entities", []):
        if isinstance(e, dict) and e.get("entity_type"):
            types.add(e["entity_type"])
    return types


def get_source_block_ids(unit):
    """Return list of source block IDs for a unit."""
    st = unit.get("source_trace", {})
    if isinstance(st, dict):
        return st.get("source_block_ids", [])
    return []


# ---------------------------------------------------------------------------
# Section proximity
# ---------------------------------------------------------------------------

def build_section_index(source_blocks):
    """Map block_id → section, page."""
    idx = {}
    for b in source_blocks:
        bid = b.get("block_id", "")
        idx[bid] = {
            "section": b.get("section", ""),
            "section_type": b.get("section_type", ""),
            "page": b.get("page", 0),
        }
    return idx


def get_sections(unit, block_index):
    """Return set of (section, section_type) tuples for a unit."""
    sections = set()
    for bid in get_source_block_ids(unit):
        if bid in block_index:
            info = block_index[bid]
            sections.add((info["section"], info["section_type"]))
    return sections


def section_overlap(u1, u2, block_index):
    """Check if two units share at least one section or adjacent section types."""
    s1 = get_sections(u1, block_index)
    s2 = get_sections(u2, block_index)
    if not s1 or not s2:
        return False
    # Direct overlap
    if s1 & s2:
        return True
    # Adjacent IMRaD section types
    imrad_order = ["abstract", "introduction", "methods", "results", "discussion", "conclusion"]
    for sec1, stype1 in s1:
        for sec2, stype2 in s2:
            try:
                i1 = imrad_order.index(stype1)
                i2 = imrad_order.index(stype2)
                if abs(i1 - i2) <= 1:
                    return True
            except ValueError:
                pass
    return False


# ---------------------------------------------------------------------------
# Clustering within a single evidence_type
# ---------------------------------------------------------------------------

def cluster_by_overlap(units, block_index):
    """Cluster units of the same evidence_type.

    1. Cluster by entity overlap (share at least 1 named entity)
    2. Attach singletons to nearby clusters by section proximity
    3. Split oversized clusters
    """
    n = len(units)

    # All singletons: group by section proximity
    if n == 1:
        return [units]

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

    # Phase 1: entity overlap
    for i in range(n):
        entities_i = get_entity_names(units[i])
        if not entities_i:
            continue
        for j in range(i + 1, n):
            entities_j = get_entity_names(units[j])
            if entities_i & entities_j:
                union(i, j)

    components = defaultdict(list)
    for i in range(n):
        components[find(i)].append(i)

    # Phase 2: merge small clusters (size < 3) into larger ones by section proximity
    small_roots = [r for r, idx in components.items() if len(idx) < 3]
    large_roots = [r for r, idx in components.items() if len(idx) >= 3]

    for sr in small_roots:
        # Try attaching to a large cluster first
        best_root = None
        best_overlap = 0
        for lr in large_roots:
            for si in components[sr]:
                for li in components[lr]:
                    if section_overlap(units[si], units[li], block_index):
                        s1 = get_sections(units[si], block_index)
                        s2 = get_sections(units[li], block_index)
                        overlap = len(s1 & s2)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_root = lr
        if best_root is not None:
            union(components[sr][0], components[best_root][0])

    # Re-gather
    components = defaultdict(list)
    for i in range(n):
        components[find(i)].append(i)

    # Phase 2b: merge remaining small clusters if they share SPECIFIC entity types.
    # Use entity types that are discriminative (specific, not ubiquitous).
    # Exclude: protein, gene, phenotype, pathway (too common), tissue/cell (too broad).
    _all_entity_types = set(get_dictionary("entity_type"))
    DISCRIMINATIVE_TYPES = _all_entity_types - {"protein", "gene", "phenotype", "pathway", "tissue", "cell", "cell_type", "cell_line"}
    small_roots = [r for r, idx in components.items() if len(idx) < 3]
    processed = set()
    for sr in small_roots:
        if sr in processed:
            continue
        sr_entity_types = set()
        for si in components[sr]:
            sr_entity_types.update(get_entity_types(units[si]))
        sr_disc = sr_entity_types & DISCRIMINATIVE_TYPES

        if not sr_disc:
            continue  # nothing discriminative to match on

        for sr2 in small_roots:
            if sr2 <= sr or sr2 in processed:
                continue
            sr2_entity_types = set()
            for si2 in components[sr2]:
                sr2_entity_types.update(get_entity_types(units[si2]))
            sr2_disc = sr2_entity_types & DISCRIMINATIVE_TYPES

            if sr_disc & sr2_disc:
                union(components[sr][0], components[sr2][0])
                processed.add(sr)
                processed.add(sr2)

    # Re-gather
    components = defaultdict(list)
    for i in range(n):
        components[find(i)].append(i)

    # Phase 3: split oversized
    result = []
    for indices in components.values():
        if len(indices) <= MAX_PACK_SIZE:
            result.append([units[i] for i in indices])
        else:
            result.extend(_split_oversized([units[i] for i in indices], block_index))

    return result


def _chunk_sorted(units, block_index):
    """Split units into fixed-size chunks ordered by page."""
    ordered = sorted(units, key=lambda u: (
        min((block_index.get(bid, {}).get("page", 0) for bid in get_source_block_ids(u)), default=0)
    ))
    return [ordered[k:k + MAX_PACK_SIZE] for k in range(0, len(ordered), MAX_PACK_SIZE)]


def _split_oversized(units, block_index):
    """Split an oversized cluster into smaller packs using tighter entity overlap."""
    n = len(units)
    if n <= MAX_PACK_SIZE:
        return [units]

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

    # Only connect if entity overlap >= 2 entities (stricter)
    for i in range(n):
        entities_i = get_entity_names(units[i])
        for j in range(i + 1, n):
            entities_j = get_entity_names(units[j])
            if len(entities_i & entities_j) >= 2:
                union(i, j)

    components = defaultdict(list)
    for i in range(n):
        components[find(i)].append(i)

    result = []
    for indices in components.values():
        sub_units = [units[i] for i in indices]
        if len(sub_units) > MAX_PACK_SIZE:
            # Still too big: split into fixed-size chunks, keeping sections together
            sub_units.sort(key=lambda u: (
                min((block_index.get(bid, {}).get("page", 0) for bid in get_source_block_ids(u)), default=0)
            ))
            for k in range(0, len(sub_units), MAX_PACK_SIZE):
                result.append(sub_units[k:k + MAX_PACK_SIZE])
        else:
            result.append(sub_units)

    return result


# ---------------------------------------------------------------------------
# Anchor selection
# ---------------------------------------------------------------------------

def select_anchors(units, max_anchors=3):
    """Select anchor (most representative) evidence units from a cluster.

    Score based on: confidence, entity count, source count, presence of statistics.
    """
    def score(u):
        s = 0
        meta = u.get("extraction_meta", {})
        if isinstance(meta, dict):
            conf = meta.get("confidence", 0.5)
            if isinstance(conf, (int, float)):
                s += conf * 20

        s += len(u.get("raw_entities", [])) * 2
        s += len(get_source_block_ids(u)) * 3

        stats = u.get("statistics", {})
        if isinstance(stats, dict):
            if stats.get("p_value"):
                s += 5
            if stats.get("effect_size"):
                s += 5
            if stats.get("sample_size"):
                s += 3

        # Prefer longer claims (more informative)
        s += min(len(u.get("claim", "")), 300) / 60

        return s

    ranked = sorted(units, key=score, reverse=True)
    return ranked[:min(max_anchors, len(ranked))]


# ---------------------------------------------------------------------------
# Missing context detection
# ---------------------------------------------------------------------------

def detect_missing_context(pack, all_units, source_blocks):
    """Identify what context is missing from this pack.

    Returns a list of missing-context descriptions.
    """
    missing = []

    # Which evidence types are completely absent from the paper?
    present_types = set()
    for u in all_units:
        present_types.add(u.get("evidence_type", ""))
    for etype in VALID_EVIDENCE_TYPES:
        if etype not in present_types:
            if etype not in [m for m in missing]:
                missing.append(f"evidence_type_not_found_in_paper: {etype}")

    # Which entity types are missing from this pack?
    pack_entity_types = set()
    for u in pack:
        pack_entity_types.update(get_entity_types(u))
    all_entity_types = {"protein", "gene", "disease", "drug", "metabolite", "pathway", "phenotype", "assay_method"}
    for et in all_entity_types - pack_entity_types:
        if et not in missing:
            pass  # entity type gaps are informational, not always "missing"

    # Check for lack of statistics
    units_with_stats = sum(1 for u in pack if u.get("statistics", {}).get("p_value"))
    if units_with_stats == 0 and len(pack) > 3:
        missing.append("no_statistics_reported_in_pack")

    # Check for lack of polarity diversity
    polarities = set(u.get("polarity", "") for u in pack)
    if len(polarities) <= 1 and len(pack) > 2:
        missing.append(f"low_polarity_diversity: only {polarities}")

    return missing


# ---------------------------------------------------------------------------
# Pack reason generation
# ---------------------------------------------------------------------------

def generate_pack_reason(pack, evidence_type):
    """Generate a human-readable reason for why these units are grouped."""
    entities = set()
    for u in pack:
        entities.update(get_entity_names(u))
    top_entities = sorted(entities)[:5]

    sections = set()
    for u in pack:
        st = u.get("source_trace", {})
        if isinstance(st, dict):
            sec = st.get("section", "")
            if sec:
                sections.add(sec)

    parts = [f"{len(pack)} evidence units of type '{evidence_type}'"]

    if top_entities:
        parts.append(f"shared entities: {', '.join(top_entities[:5])}")
    if sections:
        parts.append(f"sections: {', '.join(sorted(sections)[:3])}")

    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_context_packs(run_dir, paper_id):
    """Build context packs from evidence units without using relations.

    Returns list of context pack dicts.
    """
    evidence_units = load_evidence_units(run_dir)
    source_blocks = load_source_blocks(run_dir)
    block_index = build_section_index(source_blocks)

    print(f"Loaded {len(evidence_units)} evidence units, {len(source_blocks)} source blocks")

    # Group by evidence_type
    by_type = defaultdict(list)
    for u in evidence_units:
        etype = u.get("evidence_type", "unknown")
        by_type[etype].append(u)

    print(f"Evidence type distribution: {dict((k, len(v)) for k, v in by_type.items())}")

    # Build packs per type
    all_packs = []
    for etype in sorted(by_type.keys()):
        units = by_type[etype]
        if not units:
            continue

        clusters = cluster_by_overlap(units, block_index)
        print(f"  {etype}: {len(units)} units → {len(clusters)} clusters")

        for cluster in clusters:
            anchors = select_anchors(cluster)
            pack = build_pack(cluster, anchors, etype, paper_id, evidence_units, source_blocks)
            all_packs.append(pack)

    # Sort packs by size (largest first) then by type
    all_packs.sort(key=lambda p: (-len(p["member_evidence_ids"]), p["evidence_type"]))

    # Assign pack IDs
    for i, p in enumerate(all_packs):
        p["pack_id"] = f"CP{i + 1:04d}"

    return all_packs


def build_pack(cluster, anchors, etype, paper_id, all_units, source_blocks):
    """Build a single context pack from a cluster of evidence units."""
    member_ids = sorted(u["evidence_id"] for u in cluster)
    anchor_ids = sorted(u["evidence_id"] for u in anchors)

    all_source_ids = set()
    for u in cluster:
        all_source_ids.update(get_source_block_ids(u))
    source_ids = sorted(all_source_ids)

    pack_reason = generate_pack_reason(cluster, etype)
    missing = detect_missing_context(cluster, all_units, source_blocks)

    return {
        "pack_id": "",  # filled later
        "paper_id": paper_id,
        "evidence_type": etype,
        "member_evidence_ids": member_ids,
        "anchor_evidence_ids": anchor_ids,
        "source_block_ids": source_ids,
        "pack_reason": pack_reason,
        "missing_context": missing,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_packs(packs):
    """Validate all packs against contracts."""
    from src.validation.validate_stage import validate_record

    errors = 0
    for p in packs:
        errs, warns = validate_record(p, "context_pack")
        if errs:
            errors += len(errs)
            print(f"  [VALIDATE] {p['pack_id']}: {len(errs)} error(s)")
            for e in errs[:5]:
                print(f"    - {e}")
    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    run_dir = sys.argv[1]
    paper_id = sys.argv[2]

    print(f"=== Context Pack Builder ===")
    print(f"Run dir: {run_dir}")
    print(f"Paper ID: {paper_id}")
    print()

    packs = build_context_packs(run_dir, paper_id)

    print(f"\n=== Validation ===")
    errs = validate_packs(packs)
    print(f"Total: {len(packs)} packs, {errs} validation errors")

    outputs = stage_output_paths("context_packs", run_dir)
    out_path = outputs["context_packs.jsonl"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for p in packs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\nOutput: {out_path}")
    print(f"Done. {len(packs)} context packs written.")


if __name__ == "__main__":
    main()
