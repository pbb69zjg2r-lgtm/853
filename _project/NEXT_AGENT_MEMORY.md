# Next Agent Memory

Updated: 2026-06-26

This file exists so another AI agent can continue without relying on this chat history.

## Current User Intent

The user wants a low-coupling V2 literature extraction project.

Core priority:

```text
stability > efficiency > cost
```

The user does not want the project to become bloated just to use LLMs. If using LLMs requires more code and more fragile process than a deterministic program, that tradeoff must be discussed before implementation.

## Confirmed Design: evidence_units

`evidence_units` are lightweight evidence nodes.

They store:

```text
LLM-extracted candidate evidence units around the scientific questions.
```

They do not perform:

```text
entity normalization
evidence relation linking
cross-paper relation
deduplication / merge
graph construction
```

Every evidence unit must belong to one of these 7 types:

```text
disease_association
detection_method
thermogenesis_modulation
biomarker_panel
mechanism_pathway
pathway_cellular_function_impact
organelle_interaction_impact
```

Every evidence unit must include:

```text
evidence_id
paper_id
evidence_type
claim
structured_fields
raw_entities
experimental_model
condition_context
source_trace
polarity
statistics
measurement
extraction_meta
review_coverage
normalization_status
```

Do not add these fields to evidence_units:

```text
normalized_entity_id
canonical_entity_name
graph_edges
cross_paper_relation
dedup_merge_id
```

These are later-stage analysis outputs.

## Confirmed Output Boundary

Pre-review outputs are candidate, not trusted:

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

Post-review trusted output:

```text
09_export/review_export.json
```

`review_export.json` is the formal trusted output after human review and before normalization / relation linking / graph construction.

It must contain:

```text
package_id
paper_id
stage
schema_version
normalization_status
relation_linking_status
graph_status
reviewed_entries
reviewed_evidence_units
review_audit
```

`reviewed_entries.review.decision` must only be:

```text
approved
rejected
```

`review_export.json` must not contain:

```text
normalized_entity_id
canonical_entity_name
graph_edges
cross_paper_relation
dedup_merge_id
```

## Files Already Updated

The contracts were updated:

```text
contracts/fields.yaml
contracts/dictionaries.yaml
contracts/output_contracts.yaml
contracts/stage_contracts.yaml
```

Project boundary docs were added or updated:

```text
_project/LEGACY_MAP.md
_project/STATUS.md
_project/TASKS.md
_project/CHANGELOG.md
_project/HANDOFF.md
```

## Legacy Boundary

Read this first:

```text
_project/LEGACY_MAP.md
```

Important: old runnable code is not current contract truth.

Known old-code drift:

```text
src/relations/build_relations.py still belongs to old pre-review relation flow.
src/context/build_context_packs.py still requires 04_relations/evidence_relations.json.
src/verification/generate_report.py still requires relations and emits old report fields.
src/evidence/extract_evidence.py still emits old evidence_unit fields.
prompts/evidence_extraction.txt still describes old 5-type schema and old evidence fields.
src/drafting/generate_drafts.py still reads old context_pack fields.
src/export/build_export.py still emits old review_export shape and allows draft states.
src/review/review.html still displays old evidence fields.
src/validation/validate_mock_run.js still hard-codes old file list.
runs/mock_paper_001 and runs/real_paper_001 are legacy fixtures/output, not current truth.
```

## Important Reverted Work

I started to add a TDD scaffold for `src/core/contracts.py`, but the user asked to roll it back before handing off to another AI.

These files were created and then deleted:

```text
tests/test_core_contracts.py
src/core/__init__.py
```

Do not assume `src/core/contracts.py` exists yet.

## Recommended Next Step

Start with a minimal contracts core:

```text
src/core/contracts.py
```

Recommended first API:

```text
load_contracts()
get_stage_outputs(stage_name)
get_required_fields(schema_name)
get_enum_values(name)
```

Then replace hard-coded validation with a contracts-driven validator.

Do not rewrite every pipeline stage at once.

Suggested order:

```text
1. src/core/contracts.py
2. contracts-driven validator
3. evidence_extraction prompt + src/evidence/extract_evidence.py
4. src/context/build_context_packs.py without pre-review relations
5. src/drafting/generate_drafts.py
6. src/verification/generate_report.py
7. review UI
8. src/export/build_export.py trusted export only after complete review
```

## User Communication Preference

The user prefers objective, structured answers.

Avoid overpraise. Explain tradeoffs clearly. If a change increases complexity, say so and ask before continuing.

