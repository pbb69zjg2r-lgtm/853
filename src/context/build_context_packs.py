"""build_context_packs.py — Bundle evidence units with source text and relations
into LLM-ready context packs for draft entry generation.

Input:  02_source/source_blocks.jsonl + 03_evidence/evidence_units.jsonl
        + 04_relations/evidence_relations.json
Output: 05_context/context_packs.jsonl
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

TASK_TYPE_MAP = {
    "disease_association": "summarize_disease_association",
    "detection_method": "summarize_detection_method",
    "thermogenesis_modulation": "summarize_thermogenesis_modulation",
    "biomarker_panel": "summarize_biomarker_panel",
    "mechanism_pathway": "summarize_mechanism_pathway",
}

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


def build_context_packs(evidence_units: list[dict], relations: list[dict],
                         source_blocks: list[dict]) -> list[dict]:
    # Index source blocks by block_id
    block_map = {b["block_id"]: b for b in source_blocks}

    # Index relations by evidence_id (incoming and outgoing)
    related = defaultdict(set)
    for r in relations:
        related[r["source_evidence_id"]].add(r["target_evidence_id"])
        related[r["target_evidence_id"]].add(r["source_evidence_id"])

    # Index evidence units by id
    ev_map = {e["evidence_id"]: e for e in evidence_units}

    packs = []
    for eu in evidence_units:
        eid = eu["evidence_id"]
        related_ids = related.get(eid, set())
        task_type = TASK_TYPE_MAP.get(eu["evidence_type"], "summarize_general")

        # Collect all source blocks from anchor + related evidence
        all_block_ids = set(eu.get("source_block_ids", []))
        for rid in related_ids:
            if rid in ev_map:
                all_block_ids.update(ev_map[rid].get("source_block_ids", []))

        # Build source text sections for the LLM
        anchor_text = eu.get("source_text", "")
        related_texts = []
        for rid in sorted(related_ids):
            if rid in ev_map:
                r_unit = ev_map[rid]
                related_texts.append({
                    "evidence_id": rid,
                    "evidence_type": r_unit["evidence_type"],
                    "source_text": r_unit.get("source_text", ""),
                    "relation": [r["relation_type"] for r in relations
                                 if (r["source_evidence_id"] == eid and r["target_evidence_id"] == rid)
                                 or (r["target_evidence_id"] == eid and r["source_evidence_id"] == rid)],
                })

        pack = {
            "pack_id": f"{eu['paper_id']}_P{len(packs)+1:04d}",
            "paper_id": eu["paper_id"],
            "task_type": task_type,
            "anchor_evidence_id": eid,
            "anchor_evidence_type": eu["evidence_type"],
            "related_evidence_ids": sorted(related_ids),
            "source_block_ids": sorted(all_block_ids),
            "anchor_source_text": anchor_text,
            "related_evidence": related_texts,
            "expected_output": EXPECTED_OUTPUT.get(eu["evidence_type"], "JSON object"),
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
    print(f"  Source blocks: {len(source_blocks)}")

    packs = build_context_packs(evidence_units, relations, source_blocks)

    # Stats
    with_related = sum(1 for p in packs if p["related_evidence_ids"])
    avg_related = sum(len(p["related_evidence_ids"]) for p in packs) / max(len(packs), 1)
    total_source_chars = sum(len(p["anchor_source_text"]) for p in packs)

    out_dir = paper_dir / "05_context"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "context_packs.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for p in packs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\n  Context packs: {len(packs)}")
    print(f"  Packs with relations: {with_related}/{len(packs)}")
    print(f"  Avg related per pack: {avg_related:.1f}")
    print(f"  Total anchor source chars: {total_source_chars}")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
