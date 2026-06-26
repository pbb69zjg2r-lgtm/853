"""
Verifier report generation (step 7 of V2 pipeline).

Pure logic — no LLM. Checks draft entries and evidence units for:
- Entry-level completeness and consistency
- Cross-entry conflicts
- Evidence coverage gaps
- Schema compliance
- Actionable recommendations

Read-only: does not modify upstream outputs.

Usage:
    python generate_report.py <run_dir> <paper_id>
"""

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.contracts import stage_input_paths, stage_output_paths
from src.validation.validate_stage import validate_record


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


# ---------------------------------------------------------------------------
# Entry-level checks
# ---------------------------------------------------------------------------

def check_entry(entry):
    """Check a single draft entry. Returns list of issues."""
    issues = []

    # Schema validation
    errs, _ = validate_record(entry, "draft_entry")
    for e in errs:
        issues.append({"entry_id": entry.get("entry_id", "?"), "severity": "error", "field": "schema", "detail": e})

    # Main claim: not too short, not a placeholder
    claim = entry.get("main_claim", "")
    if len(claim) < 30:
        issues.append({"entry_id": entry["entry_id"], "severity": "warning", "field": "main_claim", "detail": f"Claim too short ({len(claim)} chars)"})
    if claim.startswith("[Mock]") or claim.startswith("(LLM failed"):
        issues.append({"entry_id": entry["entry_id"], "severity": "error", "field": "main_claim", "detail": "Claim is a placeholder/mock value"})

    # Evidence links: should have at least 1
    links = entry.get("evidence_links", [])
    if not links:
        issues.append({"entry_id": entry["entry_id"], "severity": "warning", "field": "evidence_links", "detail": "No evidence links"})

    # Review questions: should have 3-5
    questions = entry.get("review_questions", [])
    if len(questions) < 2:
        issues.append({"entry_id": entry["entry_id"], "severity": "warning", "field": "review_questions", "detail": f"Only {len(questions)} review question(s)"})

    # Uncertainty map: should have all required sub-fields
    umap = entry.get("uncertainty_map", {})
    for key in ["evidence_consistency", "statistical_confidence", "gaps", "alternative_interpretations", "requires_follow_up"]:
        if key not in umap:
            issues.append({"entry_id": entry["entry_id"], "severity": "warning", "field": f"uncertainty_map.{key}", "detail": "Missing field"})

    # Structured fields: should not be empty
    sf = entry.get("structured_fields", {})
    if not sf:
        issues.append({"entry_id": entry["entry_id"], "severity": "warning", "field": "structured_fields", "detail": "Empty structured_fields"})

    # Status should be draft or needs_review (not a final review status)
    status = entry.get("status", "")
    if status not in ("draft", "needs_review"):
        issues.append({"entry_id": entry["entry_id"], "severity": "error", "field": "status", "detail": f"Invalid status: {status}"})

    return issues


# ---------------------------------------------------------------------------
# Cross-entry checks
# ---------------------------------------------------------------------------

def check_cross_entries(entries):
    """Check for conflicts and overlaps between entries. Returns list of issues."""
    issues = []

    # Check for entries with identical or near-identical claims
    claims = [(e["entry_id"], e.get("main_claim", "")) for e in entries]
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            # Simple overlap check: shared words ratio
            words_i = set(claims[i][1].lower().split())
            words_j = set(claims[j][1].lower().split())
            if words_i and words_j:
                overlap = len(words_i & words_j) / min(len(words_i), len(words_j))
                if overlap > 0.8:
                    issues.append({
                        "severity": "warning",
                        "detail": f"High claim overlap ({overlap:.0%}) between {claims[i][0]} and {claims[j][0]}",
                    })

    # Check for contradicting polarities across entries of the same type
    by_type = defaultdict(list)
    for e in entries:
        by_type[e.get("evidence_type", "")].append(e)

    # Check evidence link overlap
    for etype, group in by_type.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                links_i = set(l.get("evidence_id", "") for l in group[i].get("evidence_links", []))
                links_j = set(l.get("evidence_id", "") for l in group[j].get("evidence_links", []))
                shared = links_i & links_j
                if len(shared) >= 2:
                    issues.append({
                        "severity": "info",
                        "detail": f"{group[i]['entry_id']} and {group[j]['entry_id']} share {len(shared)} evidence links — possible topic overlap",
                    })

    return issues


# ---------------------------------------------------------------------------
# Evidence coverage checks
# ---------------------------------------------------------------------------

def check_evidence_coverage(draft_entries, evidence_units):
    """Check that all evidence units are referenced. Returns list of issues."""
    issues = []

    all_evidence_ids = set(u["evidence_id"] for u in evidence_units)
    linked_ids = set()

    for entry in draft_entries:
        for link in entry.get("evidence_links", []):
            eid = link.get("evidence_id", "")
            if eid:
                linked_ids.add(eid)

    uncovered = all_evidence_ids - linked_ids
    if uncovered:
        issues.append({
            "severity": "warning",
            "detail": f"{len(uncovered)} evidence units not linked to any draft entry: {sorted(uncovered)[:10]}{'...' if len(uncovered) > 10 else ''}",
        })

    # Check for evidence used by too many entries (possible over-reliance)
    usage_count = defaultdict(list)
    for entry in draft_entries:
        for link in entry.get("evidence_links", []):
            eid = link.get("evidence_id", "")
            if eid:
                usage_count[eid].append(entry["entry_id"])

    for eid, entries_using in usage_count.items():
        if len(entries_using) > 3:
            issues.append({
                "severity": "info",
                "detail": f"Evidence {eid} used by {len(entries_using)} entries: {entries_using}",
            })

    # Check evidence not found in evidence_units
    for entry in draft_entries:
        for link in entry.get("evidence_links", []):
            eid = link.get("evidence_id", "")
            if eid and eid not in all_evidence_ids:
                issues.append({
                    "severity": "error",
                    "detail": f"{entry['entry_id']} links to non-existent evidence {eid}",
                })

    coverage_pct = len(linked_ids) / len(all_evidence_ids) * 100 if all_evidence_ids else 0
    issues.append({
        "severity": "info",
        "detail": f"Evidence coverage: {len(linked_ids)}/{len(all_evidence_ids)} ({coverage_pct:.0f}%)",
    })

    return issues


# ---------------------------------------------------------------------------
# Schema issues
# ---------------------------------------------------------------------------

def check_schema(draft_entries, evidence_units):
    """Check schema compliance across all records. Returns list of issues."""
    issues = []

    # Validate draft entries
    for entry in draft_entries:
        errs, warns = validate_record(entry, "draft_entry")
        for e in errs:
            issues.append({"severity": "error", "detail": f"Draft {entry.get('entry_id', '?')}: {e}"})

    # Validate evidence units
    for unit in evidence_units:
        errs, warns = validate_record(unit, "evidence_unit")
        for e in errs:
            issues.append({"severity": "error", "detail": f"Evidence {unit.get('evidence_id', '?')}: {e}"})

    return issues


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def generate_recommendations(entry_issues, cross_issues, coverage_issues, schema_issues):
    """Generate human-readable recommendations from all issues."""
    recs = []

    error_count = sum(1 for i in entry_issues if i.get("severity") == "error")
    error_count += sum(1 for i in schema_issues if i.get("severity") == "error")

    warn_count = sum(1 for i in entry_issues if i.get("severity") == "warning")
    warn_count += sum(1 for i in coverage_issues if i.get("severity") == "warning")

    if error_count > 0:
        recs.append(f"Fix {error_count} error(s) before human review — check schema validation and placeholder claims.")
    if warn_count > 0:
        recs.append(f"Review {warn_count} warning(s) — focus on short claims, missing review questions, and empty structured_fields.")

    # Specific checks
    uncovered = [i for i in coverage_issues if "not linked" in i.get("detail", "")]
    if uncovered:
        recs.append("Some evidence units are not referenced by any draft entry. Consider: (a) adding them to existing entries, (b) creating new entries, or (c) marking them as background-only.")

    if not cross_issues:
        recs.append("No cross-entry conflicts detected. Entries appear to cover distinct topics.")
    else:
        recs.append(f"{len(cross_issues)} cross-entry issue(s) found. Check for overlapping claims and over-used evidence.")

    # Status
    if error_count == 0 and warn_count <= 3:
        recs.append("Overall: ready for human review.")
    elif error_count == 0:
        recs.append("Overall: minor warnings only. Can proceed to review with notes.")
    else:
        recs.append("Overall: errors present. Fix before starting human review.")

    return recs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_report(run_dir, paper_id):
    """Generate verifier report from draft entries and evidence units."""
    inputs = stage_input_paths("verifier_report", run_dir)
    draft_path = inputs["draft_entries.jsonl"]
    evidence_path = inputs["evidence_units.jsonl"]

    drafts = load_jsonl(draft_path) if os.path.exists(draft_path) else []
    evidence = load_jsonl(evidence_path) if os.path.exists(evidence_path) else []

    print(f"Loaded {len(drafts)} draft entries, {len(evidence)} evidence units")

    # Run all checks
    entry_results = []
    all_entry_issues = []
    for entry in drafts:
        issues = check_entry(entry)
        all_entry_issues.extend(issues)
        entry_results.append({
            "entry_id": entry.get("entry_id"),
            "issue_count": len(issues),
            "issues": issues,
            "verdict": "OK" if not any(i["severity"] == "error" for i in issues) else "HAS_ERRORS",
        })

    cross_issues = check_cross_entries(drafts)
    coverage_issues = check_evidence_coverage(drafts, evidence)
    schema_issues = check_schema(drafts, evidence)
    recommendations = generate_recommendations(all_entry_issues, cross_issues, coverage_issues, schema_issues)

    report = {
        "entry_results": entry_results,
        "cross_entry_issues": cross_issues,
        "evidence_coverage_issues": coverage_issues,
        "schema_issues": schema_issues,
        "recommendations": recommendations,
    }

    # Summary
    total_errors = sum(1 for i in all_entry_issues if i.get("severity") == "error")
    total_warnings = sum(1 for i in all_entry_issues if i.get("severity") == "warning")
    ok_count = sum(1 for r in entry_results if r["verdict"] == "OK")

    print(f"\n=== Report Summary ===")
    print(f"Entries: {ok_count}/{len(drafts)} OK")
    print(f"Entry issues: {total_errors} error(s), {total_warnings} warning(s)")
    print(f"Cross-entry issues: {len(cross_issues)}")
    print(f"Coverage issues: {len(coverage_issues)}")
    print(f"Schema issues: {len(schema_issues)}")
    print(f"Recommendations: {len(recommendations)}")

    return report


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    run_dir = sys.argv[1]
    paper_id = sys.argv[2]

    print(f"=== Verifier Report ===")
    print(f"Run dir: {run_dir}")
    print(f"Paper ID: {paper_id}")
    print()

    report = generate_report(run_dir, paper_id)

    outputs = stage_output_paths("verifier_report", run_dir)
    out_path = outputs["verifier_report.json"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nOutput: {out_path}")
    print("Done.")


if __name__ == "__main__":
    main()
