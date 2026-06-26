"""generate_report.py — Quality verification report for draft entries.

Checks evidence linkage, field completeness, entity coverage, and consistency.
No LLM — fully deterministic rules-based validation.

Input:  06_draft/draft_entries.jsonl, 03_evidence/evidence_units.jsonl,
        04_relations/evidence_relations.json
Output: 07_verification/verifier_report.json
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_evidence_linkage(draft: dict, ev_map: dict) -> list[str]:
    """Verify all evidence_links point to existing evidence units."""
    issues = []
    links = draft.get("evidence_links", [])
    unique_links = list(dict.fromkeys(links))  # dedup preserving order
    for eid in unique_links:
        if eid not in ev_map:
            issues.append(f"Broken evidence link: {eid}")
    return issues


def check_field_completeness(draft: dict) -> list[str]:
    """Check required fields are non-empty."""
    issues = []
    if not draft.get("main_claim", "").strip():
        issues.append("main_claim is empty")
    if not draft.get("structured_fields"):
        issues.append("structured_fields is empty or missing")
    if not draft.get("evidence_links"):
        issues.append("evidence_links is empty")
    return issues


def check_entity_coverage(draft: dict, ev_map: dict) -> list[str]:
    """Check that at least some entities from linked evidence appear in main_claim."""
    links = list(dict.fromkeys(draft.get("evidence_links", [])))  # dedup
    claim = draft.get("main_claim", "").lower()
    if not claim or not links:
        return []

    all_entities = set()
    for eid in links:
        eu = ev_map.get(eid)
        if eu:
            for e in eu.get("entities", []):
                name = e.get("name", "").strip().lower()
                if name:
                    all_entities.add(name)

    if not all_entities:
        return []

    found = [name for name in all_entities if name in claim]
    if not found:
        return [f"No entities from evidence appear in main_claim (expected: {sorted(all_entities)[:5]}...)"]
    return []


def check_relation_consistency(drafts: list[dict], relations: list[dict]) -> list[str]:
    """Check that relations are reflected in draft evidence links."""
    issues = []
    related_pairs = set()
    for r in relations:
        related_pairs.add((r["source_evidence_id"], r["target_evidence_id"]))
        related_pairs.add((r["target_evidence_id"], r["source_evidence_id"]))

    # Count drafts that share evidence links (co-citation = implicit relation)
    co_cited = 0
    for i, d1 in enumerate(drafts):
        for d2 in drafts[i+1:]:
            links1 = set(d1.get("evidence_links", []))
            links2 = set(d2.get("evidence_links", []))
            shared = links1 & links2
            if shared:
                co_cited += 1

    if co_cited < len(drafts) * 0.3:
        issues.append(f"Low cross-reference: only {co_cited} draft pairs share evidence links")
    return issues


def generate_report(paper_dir: Path, paper_id: str) -> dict:
    draft_path = paper_dir / "06_draft" / "draft_entries.jsonl"
    evidence_path = paper_dir / "03_evidence" / "evidence_units.jsonl"
    relations_path = paper_dir / "04_relations" / "evidence_relations.json"

    drafts = load_jsonl(draft_path)
    evidence_units = load_jsonl(evidence_path)
    relations = load_json(relations_path)

    ev_map = {eu["evidence_id"]: eu for eu in evidence_units}

    # Per-draft checks
    entry_results = []
    total_issues = 0
    issue_types = Counter()

    for draft in drafts:
        entry_issues = []

        issues = check_evidence_linkage(draft, ev_map)
        if issues:
            entry_issues.extend(issues)
            issue_types["broken_link"] += len(issues)

        issues = check_field_completeness(draft)
        if issues:
            entry_issues.extend(issues)
            for i in issues:
                issue_types[f"field_{i.split()[0]}"] += 1

        issues = check_entity_coverage(draft, ev_map)
        if issues:
            entry_issues.extend(issues)
            issue_types["entity_coverage"] += len(issues)

        entry_results.append({
            "entry_id": draft["entry_id"],
            "pack_id": draft.get("pack_id", ""),
            "issues": entry_issues,
            "issue_count": len(entry_issues),
            "status": "ok" if not entry_issues else "needs_review",
        })
        total_issues += len(entry_issues)

    # Cross-draft checks
    relation_issues = check_relation_consistency(drafts, relations)
    if relation_issues:
        issue_types["relation_consistency"] += len(relation_issues)

    # Summary stats
    entries_ok = sum(1 for e in entry_results if e["status"] == "ok")
    entries_flagged = len(entry_results) - entries_ok

    # Evidence type coverage in drafts
    evidence_used = set()
    for d in drafts:
        for eid in d.get("evidence_links", []):
            evidence_used.add(eid)
    evidence_unused = [eid for eid in ev_map if eid not in evidence_used]

    report = {
        "report_id": f"{paper_id}_VR001",
        "paper_id": paper_id,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "summary": {
            "total_draft_entries": len(drafts),
            "entries_ok": entries_ok,
            "entries_flagged": entries_flagged,
            "total_issues": total_issues,
            "issue_breakdown": dict(issue_types.most_common()),
            "evidence_units_total": len(evidence_units),
            "evidence_units_used": len(evidence_used),
            "evidence_units_unused": len(evidence_unused),
            "relations_total": len(relations),
        },
        "cross_draft_issues": relation_issues,
        "entry_results": entry_results,
        "unused_evidence_ids": evidence_unused,
        "recommendations": [],
    }

    # Generate recommendations
    recs = report["recommendations"]
    if evidence_unused:
        recs.append(f"{len(evidence_unused)} evidence units not linked to any draft entry — review for coverage gaps")
    if entries_flagged > len(drafts) * 0.5:
        recs.append("Over 50% entries flagged — consider re-running draft generation with improved prompts")
    if issue_types.get("entity_coverage", 0) > len(drafts) * 0.3:
        recs.append("High entity coverage issues — main_claims may be too generic, review prompt")
    if issue_types.get("broken_link", 0) > 0:
        recs.append("Broken evidence links detected — check evidence_links dedup and ID consistency")

    return report


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/verification/generate_report.py <paper_run_dir> [paper_id]")
        sys.exit(1)

    paper_dir = Path(sys.argv[1]).resolve()
    paper_id = sys.argv[2] if len(sys.argv) > 2 else paper_dir.parent.name

    report = generate_report(paper_dir, paper_id)

    out_dir = paper_dir / "07_verification"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "verifier_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    s = report["summary"]
    print(f"  Draft entries: {s['total_draft_entries']}")
    print(f"  OK: {s['entries_ok']}, Flagged: {s['entries_flagged']}")
    print(f"  Total issues: {s['total_issues']}")
    print(f"  Issue breakdown: {s['issue_breakdown']}")
    print(f"  Evidence used: {s['evidence_units_used']}/{s['evidence_units_total']}")
    print(f"  Evidence unused: {s['evidence_units_unused']}")
    if report["recommendations"]:
        print(f"\n  Recommendations:")
        for r in report["recommendations"]:
            print(f"  - {r}")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
