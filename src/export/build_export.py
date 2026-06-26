"""build_export.py — Generate final review export from review state.

Input:  08_review/review_state.json (or defaults), 06_draft/draft_entries.jsonl,
        03_evidence/evidence_units.jsonl, 07_verification/verifier_report.json
Output: 09_export/review_export.json
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_export(paper_dir: Path, paper_id: str) -> dict:
    drafts = load_jsonl(paper_dir / "06_draft" / "draft_entries.jsonl")
    evidence = load_jsonl(paper_dir / "03_evidence" / "evidence_units.jsonl")
    verifier = load_json(paper_dir / "07_verification" / "verifier_report.json")

    # Load review state or default to all-draft
    review_path = paper_dir / "08_review" / "review_state.json"
    if review_path.exists():
        review_state = load_json(review_path)
        entries_state = review_state.get("entries", {})
    else:
        entries_state = {d["entry_id"]: {"status": "draft", "notes": "", "reviewed_at": None}
                        for d in drafts}

    ev_map = {e["evidence_id"]: e for e in evidence}

    # Build reviewed entries with embedded evidence
    reviewed = []
    for d in drafts:
        eid = d["entry_id"]
        state = entries_state.get(eid, {"status": "draft", "notes": ""})

        # Collect linked evidence
        linked_evidence = []
        for ev_id in d.get("evidence_links", []):
            eu = ev_map.get(ev_id)
            if eu:
                linked_evidence.append({
                    "evidence_id": ev_id,
                    "evidence_type": eu.get("evidence_type", ""),
                    "source_text": eu.get("source_text", ""),
                    "entities": eu.get("entities", []),
                    "modulation": eu.get("modulation"),
                    "statistics": eu.get("statistics"),
                })

        reviewed.append({
            "entry_id": eid,
            "task_type": d.get("task_type", ""),
            "main_claim": d.get("main_claim", ""),
            "structured_fields": d.get("structured_fields", {}),
            "linked_evidence": linked_evidence,
            "review_status": state.get("status", "draft"),
            "review_notes": state.get("notes", ""),
            "reviewed_at": state.get("reviewed_at"),
        })

    # Summary
    from collections import Counter
    status_counts = Counter(r["review_status"] for r in reviewed)

    export = {
        "export_id": f"{paper_id}_EXPORT",
        "paper_id": paper_id,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_entries": len(reviewed),
            "approved": status_counts.get("approved", 0),
            "rejected": status_counts.get("rejected", 0),
            "flagged": status_counts.get("needs_review", 0),
            "draft": status_counts.get("draft", 0),
            "total_evidence_units": len(evidence),
            "verifier_ok": verifier["summary"].get("entries_ok", 0),
            "verifier_flagged": verifier["summary"].get("entries_flagged", 0),
        },
        "reviewed_entries": reviewed,
    }

    return export


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/export/build_export.py <paper_run_dir> [paper_id]")
        sys.exit(1)

    paper_dir = Path(sys.argv[1]).resolve()
    paper_id = sys.argv[2] if len(sys.argv) > 2 else paper_dir.parent.name

    # Ensure review state exists (default all to draft)
    review_path = paper_dir / "08_review" / "review_state.json"
    if not review_path.exists():
        drafts = load_jsonl(paper_dir / "06_draft" / "draft_entries.jsonl")
        default_state = {
            "paper_id": paper_id,
            "entries": {d["entry_id"]: {"status": "draft", "notes": "", "reviewed_at": None}
                       for d in drafts},
            "updated_at": datetime.now().isoformat(),
        }
        review_path.parent.mkdir(parents=True, exist_ok=True)
        with open(review_path, "w", encoding="utf-8") as f:
            json.dump(default_state, f, ensure_ascii=False, indent=2)
        print(f"  Created default review state: {len(default_state['entries'])} entries as draft")

    export = build_export(paper_dir, paper_id)

    out_dir = paper_dir / "09_export"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "review_export.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    s = export["summary"]
    print(f"  Entries: {s['total_entries']}")
    print(f"  Approved: {s['approved']}, Rejected: {s['rejected']}, "
          f"Flagged: {s['flagged']}, Draft: {s['draft']}")
    print(f"  Evidence units: {s['total_evidence_units']}")
    print(f"  Verifier: {s['verifier_ok']} ok / {s['verifier_flagged']} flagged")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
