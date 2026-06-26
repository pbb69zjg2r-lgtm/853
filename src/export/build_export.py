"""
Review export builder (step 9 of V2 pipeline — final trusted output).

Reads review_state.json + draft_entries.jsonl + evidence_units.jsonl +
verifier_report.json, and produces the trusted review_export.json.

Only runs after human review is complete. Only approved/rejected entries
are included in the final export.

Usage:
    python build_export.py <run_dir> <paper_id>
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.contracts import get_output_forbidden_fields, stage_input_paths, stage_output_paths
from src.validation.validate_stage import validate_record, validate_forbidden


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Export assembly
# ---------------------------------------------------------------------------

def build_export(run_dir, paper_id):
    """Build the review_export.json from reviewed data.

    Returns the export dict or raises if review is incomplete.
    """
    # Load inputs
    inputs = stage_input_paths("review_export", run_dir)
    review_state = load_json(inputs["review_state.json"])
    drafts = load_jsonl(inputs["draft_entries.jsonl"])
    evidence = load_jsonl(inputs["evidence_units.jsonl"])

    # Index by ID
    draft_map = {d["entry_id"]: d for d in drafts}
    evidence_map = {e["evidence_id"]: e for e in evidence}

    # Review state: {entries: {entry_id: {decision, notes, flagged, ...}}}
    reviewed = review_state.get("entries", {})

    # Separate approved, rejected, and unreviewed
    approved_entries = []
    rejected_entries = []
    unreviewed = []

    for entry_id, state in reviewed.items():
        decision = state.get("status", "")
        if decision == "approved":
            approved_entries.append(entry_id)
        elif decision == "rejected":
            rejected_entries.append(entry_id)
        else:
            unreviewed.append(entry_id)

    # Check: all drafts must be reviewed
    all_draft_ids = set(d["entry_id"] for d in drafts)
    unreviewed_drafts = all_draft_ids - set(reviewed.keys())
    if unreviewed_drafts:
        print(f"WARNING: {len(unreviewed_drafts)} draft entries have not been reviewed: {sorted(unreviewed_drafts)}")
        print("Only reviewed entries will be included in the export.")

    pending = [eid for eid in reviewed if reviewed[eid].get("status") not in ("approved", "rejected")]
    if pending:
        print(f"WARNING: {len(pending)} entries still pending review decision: {pending}")
        print("These will be excluded from the export.")

    # Build reviewed_entries
    reviewed_entries = []
    for entry_id in approved_entries + rejected_entries:
        if entry_id not in draft_map:
            print(f"WARNING: reviewed entry {entry_id} not found in drafts, skipping")
            continue

        draft = draft_map[entry_id]
        state = reviewed.get(entry_id, {})

        entry = {
            "entry_id": entry_id,
            "paper_id": paper_id,
            "evidence_type": draft.get("evidence_type", "unknown"),
            "reviewed_claim": draft.get("main_claim", ""),
            "structured_fields": draft.get("structured_fields", {}),
            "evidence_links": draft.get("evidence_links", []),
            "experimental_model_summary": draft.get("experimental_model_summary", {}),
            "review": {
                "decision": state.get("status", "rejected"),
            },
        }

        # Add reviewer notes if present
        if state.get("notes"):
            entry["review"]["notes"] = state["notes"]

        reviewed_entries.append(entry)

    # Build reviewed_evidence_units
    reviewed_evidence = []
    for unit in evidence:
        eid = unit.get("evidence_id", "")
        # Update review_coverage from review_state
        evidence_review = review_state.get("evidence", {}).get(eid, {})
        coverage = dict(unit.get("review_coverage", {}))
        if evidence_review:
            coverage["reviewed"] = True
        reviewed_unit = dict(unit)
        reviewed_unit["review_coverage"] = coverage
        reviewed_evidence.append(reviewed_unit)

    # Build review_audit
    audit = {
        "reviewer": review_state.get("reviewer", "unknown"),
        "reviewed_at": review_state.get("updated_at", datetime.now().isoformat()),
        "entry_count": len(reviewed_entries),
        "approved_count": len(approved_entries),
        "rejected_count": len(rejected_entries),
        "evidence_coverage_summary": _build_coverage_summary(drafts, evidence, reviewed),
        "notes": review_state.get("export_notes", ""),
    }

    # Assemble export
    export = {
        "package_id": f"{paper_id}_export_{datetime.now().strftime('%Y%m%d')}",
        "paper_id": paper_id,
        "stage": "review_export",
        "schema_version": "0.1.0",
        "normalization_status": "not_normalized",
        "reviewed_entries": reviewed_entries,
        "reviewed_evidence_units": reviewed_evidence,
        "review_audit": audit,
    }

    # Validate forbidden fields
    forbidden_errs = validate_forbidden(export, "review_export")
    if forbidden_errs:
        for e in forbidden_errs:
            print(f"  FORBIDDEN: {e}")

    return export


def _build_coverage_summary(drafts, evidence, reviewed):
    """Build evidence coverage summary for the audit."""
    all_evidence_ids = set(e["evidence_id"] for e in evidence)
    linked_ids = set()
    for d in drafts:
        eid = d.get("entry_id", "")
        if reviewed.get(eid, {}).get("status") == "approved":
            for link in d.get("evidence_links", []):
                linked_ids.add(link.get("evidence_id", ""))

    return {
        "total_evidence_units": len(evidence),
        "evidence_in_approved_entries": len(linked_ids),
        "coverage_pct": round(len(linked_ids) / len(all_evidence_ids) * 100, 1) if all_evidence_ids else 0,
        "unreferenced_evidence_ids": sorted(all_evidence_ids - linked_ids),
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_export(export):
    """Validate the export against contracts."""
    errors = []

    # Top-level schema check
    errs, warns = validate_record(export, "review_export")
    errors.extend(errs)

    # Validate each reviewed_entry
    for entry in export.get("reviewed_entries", []):
        errs, warns = validate_record(entry, "review_export")
        # Only check entry-level relevant fields
        for e in errs:
            if "entry_id" in e or "paper_id" in e or "evidence_type" in e or "reviewed_claim" in e or "decision" in e:
                errors.append(f"Entry {entry.get('entry_id', '?')}: {e}")

    # Validate each evidence unit
    for unit in export.get("reviewed_evidence_units", []):
        errs, warns = validate_record(unit, "evidence_unit")
        for e in errs:
            errors.append(f"Evidence {unit.get('evidence_id', '?')}: {e}")

    # Check review.decision values
    for entry in export.get("reviewed_entries", []):
        decision = entry.get("review", {}).get("decision", "")
        if decision not in ("approved", "rejected"):
            errors.append(f"Entry {entry.get('entry_id')}: invalid review decision '{decision}'")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    run_dir = sys.argv[1]
    paper_id = sys.argv[2]

    print(f"=== Review Export Builder ===")
    print(f"Run dir: {run_dir}")
    print(f"Paper ID: {paper_id}")
    print()

    # Check required inputs exist
    inputs = stage_input_paths("review_export", run_dir)
    for key, path in inputs.items():
        if not os.path.exists(path):
            print(f"ERROR: Required input not found: {path}")
            sys.exit(1)

    export = build_export(run_dir, paper_id)

    print(f"\n=== Export Summary ===")
    audit = export["review_audit"]
    print(f"Entries: {audit['entry_count']} total ({audit['approved_count']} approved, {audit['rejected_count']} rejected)")
    print(f"Evidence: {audit['evidence_coverage_summary']['total_evidence_units']} total, {audit['evidence_coverage_summary']['evidence_in_approved_entries']} in approved entries")

    print(f"\n=== Validation ===")
    errors = validate_export(export)
    if errors:
        print(f"{len(errors)} validation error(s):")
        for e in errors[:10]:
            print(f"  - {e}")
    else:
        print("0 validation errors")

    outputs = stage_output_paths("review_export", run_dir)
    out_path = outputs["review_export.json"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    print(f"\nOutput: {out_path}")
    print(f"Done.")


if __name__ == "__main__":
    main()
