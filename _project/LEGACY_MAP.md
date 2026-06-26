# Legacy Map

Updated: 2026-06-26

Purpose: separate the current contracts-first V2 design from older runnable code and sample outputs.

This file does not delete or move code. It marks which files are current authority, which files are legacy reference, and which files must not be treated as the current V2 truth.

## Current Authority

The current design truth is:

```text
contracts/dictionaries.yaml
contracts/fields.yaml
contracts/output_contracts.yaml
contracts/stage_contracts.yaml
```

Meaning:

```text
fields.yaml
  Defines the allowed structure of evidence_units, context_packs, draft_entries, verifier_report, and review_export.

dictionaries.yaml
  Defines closed enums such as evidence_type and review_decision.

output_contracts.yaml
  Defines pre-review candidate outputs and post-review trusted outputs.

stage_contracts.yaml
  Defines which stage reads and writes which files.
```

Current reviewed-output rule:

```text
review_export.json is the only trusted post-review output.
It must be generated only after review is complete.
It still must not contain normalized_entity_id, canonical_entity_name, graph_edges,
cross_paper_relation, or dedup_merge_id.
```

## Current Formal Flow

Current pre-review outputs:

```text
03_evidence/evidence_units.jsonl
05_context/context_packs.jsonl
06_draft/draft_entries.jsonl
07_verification/verifier_report.json
08_review/review.html
08_review/review_preview.json
```

Internal review state:

```text
08_review/review_state.json
```

Current post-review trusted output:

```text
09_export/review_export.json
```

Current formal flow:

```text
raw_parse
  -> source_normalization
  -> evidence_units
  -> context_packs
  -> draft_entries
  -> verifier_report
  -> review_workspace
  -> review_export
```

Important boundary:

```text
evidence_relations, entity normalization, cross-paper relation linking,
deduplication, and graph building are not part of the current pre-review flow.
```

## Legacy Or Out-Of-Contract Files

These files may still be useful as reference, but they do not match the current contracts.

| File | Current status | Why legacy / out of contract | Suggested handling |
|---|---|---|---|
| `src/relations/build_relations.py` | Legacy reference | Builds `04_relations/evidence_relations.json`, but relation linking is now a later analysis module, not pre-review output. | Keep as reference. Do not call in current pre-review flow. Later move to `src/analysis/relations` or rewrite after review_export is stable. |
| `src/context/build_context_packs.py` | Needs rewrite | Still requires `04_relations/evidence_relations.json` and emits old fields such as `task_type`, `evidence_items`, `expected_output`. | Rewrite to use only `evidence_units.jsonl`, `source_blocks.jsonl`, and contracts. |
| `src/verification/generate_report.py` | Needs rewrite | Still requires relations and emits old report fields such as `cross_draft_issues` and `unused_evidence_ids`. | Rewrite around current `verifier_report` contract. |
| `src/evidence/extract_evidence.py` | Needs rewrite | Emits old evidence_unit fields: `source_text`, `entities`, `disease`, `model_system`, `review_status`. | Update after prompt is aligned to current `evidence_unit`. |
| `prompts/evidence_extraction.txt` | Needs rewrite | Still describes old evidence_unit schema and old 5-type evidence_type set. | Rewrite from `contracts/fields.yaml` and `contracts/dictionaries.yaml`. |
| `src/drafting/generate_drafts.py` | Needs rewrite | Reads old context_pack fields: `task_type`, `expected_output`, `evidence_items.source_text`. | Rewrite after context_pack builder is updated. |
| `prompts/draft_generation.txt` | Needs rewrite | Describes old `main_claim + structured_fields` only and depends on `task_type/expected_output`. | Rewrite after draft_entry contract is final. |
| `src/export/build_export.py` | Needs rewrite | Emits old `export_id`, `summary`, `linked_evidence`, and allows draft/needs_review in final export. | Rewrite so it only generates trusted `review_export.json` after all entries are approved/rejected. |
| `src/review/review.html` | Needs update | Displays old evidence fields: `source_text`, `entities`, `section_type`, `task_type`. | Update after evidence_units and draft_entries are aligned. |
| `src/review/build_review_html.py` | Legacy or optional | Static HTML builder duplicates review UI assumptions and old fields. | Prefer server-based `review_server.py`; keep static builder only if needed. |
| `src/validation/validate_mock_run.js` | Needs replacement | Hard-codes old file list including `04_relations/evidence_relations.json` and misses `review_preview.json`. | Replace with contracts-driven validator. |
| `tests/validate_mock_run.test.js` | Needs update | Uses old mock structures and old required files. | Update after validator is rewritten. |
| `runs/mock_paper_001` | Legacy fixture | Represents old contract shape. | Keep as legacy fixture until a new minimal fixture exists. |
| `runs/real_paper_001` | Legacy run output | Produced by old pipeline with relations and old review_export shape. | Keep as evidence of old runnable pipeline, not as current contract truth. |

## Do Not Treat These As Current Truth

Do not use the following as authority for new V2 design:

```text
04_relations/evidence_relations.json
old review_export.json shape
old evidence_unit fields: source_text, entities, disease, model_system, review_status
old context_pack fields: task_type, evidence_items, expected_output
old review decisions: accepted, modified, needs_recheck
```

## Migration Priority

Recommended low-risk sequence:

```text
1. Add src/core/contracts.py
   Load contracts in one place.

2. Replace hard-coded validation with contracts-driven validation.
   This makes file and field drift visible early.

3. Rewrite evidence_extraction prompt and extract_evidence.py.
   evidence_units are the base material; if this remains old, every later stage breaks.

4. Rewrite context_packs without pre-review evidence_relations.
   Group by evidence_type, source proximity, shared raw_entities, source_trace, and missing_context.

5. Rewrite draft generation around current context_pack and draft_entry contracts.

6. Rewrite verifier_report around current advisory-only contract.

7. Update review UI to show current evidence_units and draft_entries.

8. Rewrite export so review_export.json is only generated after review is complete.

9. After new mock and one real paper run pass, move or archive legacy modules.
```

## Cleanup Rule

Do not delete legacy files until these conditions are true:

```text
new contracts-driven validator exists
new mock fixture matches current contracts
one real paper can run to review_workspace
review_export refuses incomplete review
the old file is no longer needed as implementation reference
```

Until then, legacy files should be treated as reference code only.

