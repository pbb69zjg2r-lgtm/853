"""build_relations.py — Rule-based evidence relation construction.

Input:  03_evidence/evidence_units.jsonl
Output: 04_relations/evidence_relations.json

Uses entity-overlap pre-filtering + evidence_type-pair rules to classify
directed relations between evidence units. No LLM — fully deterministic.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# Section order for causal/extend rule confidence
SECTION_ORDER = {
    "abstract": 0, "introduction": 1, "methods": 2,
    "results": 3, "discussion": 4, "conclusion": 5, "supplementary": 6,
    "body": 2, "title": 0, "references": 7, "back_matter": 7,
}

# Map (source_type, target_type) → preferred relation type
# Ordered by priority — first match wins
TYPE_PAIR_RULES = [
    # Domain-specific rules (higher priority)
    ("detection_method", "*", "detects"),
    ("disease_association", "*", "associated_with"),
    ("biomarker_panel", "*", "indicates"),
    # Modulation / drug rules
    ("thermogenesis_modulation", "mechanism_pathway", "mediates"),
    # Mechanism rules
    ("mechanism_pathway", "mechanism_pathway", "causal_chain"),
    ("mechanism_pathway", "thermogenesis_modulation", "mediates"),
    # Same-type fallbacks
    ("thermogenesis_modulation", "thermogenesis_modulation", "supports"),
    ("disease_association", "disease_association", "supports"),
    ("detection_method", "detection_method", "extends"),
    ("mechanism_pathway", "disease_association", "supports"),
]


def load_units(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def get_entity_names(unit: dict) -> set[str]:
    """Return normalized entity names from a unit."""
    names = set()
    for e in unit.get("entities") or []:
        name = e.get("name", "").strip().lower()
        if name:
            names.add(name)
    # Also add drug name as implicit entity
    mod = unit.get("modulation") or {}
    drug = (mod.get("drug") or "").strip().lower()
    if drug:
        names.add(drug)
    target = (mod.get("target") or "").strip().lower()
    if target:
        names.add(target)
    return names


def entity_overlap(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of entity name sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def section_before(sec_a: str, sec_b: str) -> bool:
    """True if sec_a typically appears before sec_b in a paper."""
    return SECTION_ORDER.get(sec_a, 2) <= SECTION_ORDER.get(sec_b, 2)


def classify_relation(source: dict, target: dict, entities_a: set[str],
                      entities_b: set[str], overlap: float,
                      same_section: bool = False) -> str | None:
    """Classify the relation type between source and target evidence units."""
    shared = entities_a & entities_b
    st = source["evidence_type"]
    tt = target["evidence_type"]

    # All relations require at least 1 shared entity
    if not shared:
        return None

    mod = source.get("modulation") or {}
    drug = (mod.get("drug") or "").strip().lower()

    # --- Domain-specific rules (higher priority) ---

    # detects: detection method used to measure target's phenotype
    # Requires: same section, shared entities
    if st == "detection_method" and same_section:
        return "detects"

    # targets: drug targets a specific protein/gene
    if drug and tt == "mechanism_pathway":
        for e in (target.get("entities") or []):
            if e.get("type") in ("protein", "gene") and e.get("name", "").strip().lower() in shared:
                return "targets"

    # mediates: mechanism explains how a modulation works
    if st == "mechanism_pathway" and tt == "thermogenesis_modulation":
        return "mediates"

    # modulates: drug/compound changes thermogenesis via mechanism
    if st == "thermogenesis_modulation" and drug and tt == "mechanism_pathway":
        return "modulates"

    # associated_with: disease linked to thermogenesis phenotype
    if st == "disease_association":
        return "associated_with"

    # indicates: biomarker indicates thermogenesis status
    if st == "biomarker_panel":
        return "indicates"

    # --- General rules ---
    # causal_chain: mechanism → mechanism, requires >= 2 shared entities
    if st == "mechanism_pathway" and tt == "mechanism_pathway":
        if len(shared) >= 2:
            return "causal_chain"
        return "supports"

    # extends: same type, different section, later section
    if st == tt and not same_section and section_before(source.get("section_type", ""),
                                                         target.get("section_type", "")):
        return "extends"

    # supports: same type, shared entities
    if st == tt:
        return "supports"

    # Catch-all: any shared entities
    return "supports"


def build_relations(units: list[dict], min_overlap: float = 0.0,
                    max_per_node: int = 10) -> list[dict]:
    """Build relation edges between evidence units."""
    entity_sets = {u["evidence_id"]: get_entity_names(u) for u in units}

    relations = []
    n = len(units)

    for i in range(n):
        for j in range(i + 1, n):
            ua, ub = units[i], units[j]
            id_a, id_b = ua["evidence_id"], ub["evidence_id"]
            ents_a, ents_b = entity_sets[id_a], entity_sets[id_b]
            overlap = entity_overlap(ents_a, ents_b)

            if overlap < min_overlap:
                continue

            same_section = ua.get("section_type") == ub.get("section_type")

            # Try A → B
            rel_type = classify_relation(ua, ub, ents_a, ents_b, overlap, same_section)
            if rel_type:
                relations.append({
                    "relation_id": "",
                    "paper_id": ua["paper_id"],
                    "source_evidence_id": id_a,
                    "target_evidence_id": id_b,
                    "relation_type": rel_type,
                    "shared_entities": sorted(ents_a & ents_b),
                    "entity_overlap": round(overlap, 3),
                    "status": "candidate",
                })
                continue

            # Try B → A
            rel_type = classify_relation(ub, ua, ents_b, ents_a, overlap, same_section)
            if rel_type:
                relations.append({
                    "relation_id": "",
                    "paper_id": ua["paper_id"],
                    "source_evidence_id": id_b,
                    "target_evidence_id": id_a,
                    "relation_type": rel_type,
                    "shared_entities": sorted(ents_a & ents_b),
                    "entity_overlap": round(overlap, 3),
                    "status": "candidate",
                })

    # Cap outgoing relations per node: keep highest entity_overlap first,
    # then by relation type priority
    TYPE_PRIORITY = {
        "targets": 0, "mediates": 1, "modulates": 2, "detects": 3,
        "causal_chain": 4, "associated_with": 5, "indicates": 6,
        "extends": 7, "supports": 8,
    }
    relations.sort(key=lambda r: (
        TYPE_PRIORITY.get(r["relation_type"], 9),
        -r["entity_overlap"],
    ))

    out_counts = defaultdict(int)
    capped = []
    for r in relations:
        if out_counts[r["source_evidence_id"]] < max_per_node:
            capped.append(r)
            out_counts[r["source_evidence_id"]] += 1

    return capped


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/relations/build_relations.py <paper_run_dir> [paper_id]")
        sys.exit(1)

    paper_dir = Path(sys.argv[1]).resolve()
    paper_id = sys.argv[2] if len(sys.argv) > 2 else paper_dir.parent.name

    evidence_path = paper_dir / "03_evidence" / "evidence_units.jsonl"
    if not evidence_path.exists():
        raise FileNotFoundError(f"{evidence_path} not found. Run extract_evidence.py first.")

    units = load_units(evidence_path)
    print(f"  Evidence units: {len(units)}")

    # Entity coverage check
    units_with_entities = sum(1 for u in units if get_entity_names(u))
    total_entities = sum(len(get_entity_names(u)) for u in units)
    print(f"  Units with entities: {units_with_entities}/{len(units)}")
    print(f"  Total entity mentions: {total_entities}")

    relations = build_relations(units, min_overlap=0.0)

    # Deduplicate: same source+target+type → keep highest overlap
    seen = {}
    unique_relations = []
    for r in relations:
        key = (r["source_evidence_id"], r["target_evidence_id"], r["relation_type"])
        if key in seen:
            if r["entity_overlap"] > seen[key].get("entity_overlap", 0):
                seen[key] = r
        else:
            seen[key] = r
            unique_relations.append(r)

    # Re-index relation IDs
    for idx, r in enumerate(unique_relations):
        r["relation_id"] = f"{paper_id}_R{idx+1:04d}"

    # Write output
    out_dir = paper_dir / "04_relations"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "evidence_relations.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unique_relations, f, ensure_ascii=False, indent=2)

    # Summary
    from collections import Counter
    type_counts = Counter(r["relation_type"] for r in unique_relations)
    print(f"\n  Relations: {len(unique_relations)}")
    for rt, c in type_counts.most_common():
        print(f"    {rt}: {c}")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
