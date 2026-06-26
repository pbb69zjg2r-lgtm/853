"""
Draft entry generation (step 6 of V2 pipeline).

Reads context_packs.jsonl + evidence_units.jsonl, calls LLM to synthesize
a structured draft entry for each context pack. Batched by evidence_type,
max 4 packs per batch. Parse failures trigger individual retry.

Usage:
    python generate_drafts.py <run_dir> <paper_id>
    python generate_drafts.py <run_dir> <paper_id> --mock
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.contracts import format_prompt, stage_input_paths, stage_output_paths
from src.validation.validate_stage import validate_record

API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL = os.environ.get("EVIDENCE_LLM_MODEL", "deepseek-chat")

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")
MAX_PACKS_PER_BATCH = 4
MAX_RETRIES = 3
RETRY_DELAY = 5


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


def load_prompt():
    path = os.path.join(PROMPT_DIR, "draft_generation.txt")
    with open(path, "r", encoding="utf-8") as f:
        template = f.read()
    return format_prompt(template)


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------

def build_pack_context(pack, evidence_map):
    """Build the full context object for a single pack, including evidence details."""
    member_ids = pack.get("member_evidence_ids", [])
    units = []
    for eid in member_ids:
        if eid in evidence_map:
            u = evidence_map[eid]
            # Include only fields relevant for synthesis
            units.append({
                "evidence_id": u.get("evidence_id"),
                "evidence_type": u.get("evidence_type"),
                "claim": u.get("claim"),
                "raw_entities": u.get("raw_entities", []),
                "experimental_model": u.get("experimental_model", {}),
                "condition_context": u.get("condition_context", {}),
                "polarity": u.get("polarity"),
                "statistics": u.get("statistics", {}),
                "measurement": u.get("measurement", {}),
            })

    return {
        "pack_id": pack.get("pack_id"),
        "evidence_type": pack.get("evidence_type"),
        "pack_reason": pack.get("pack_reason"),
        "missing_context": pack.get("missing_context", []),
        "evidence_units": units,
        "unit_count": len(units),
    }


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def call_llm(system_prompt, user_input):
    url = f"{BASE_URL}/chat/completions"
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "temperature": 0,
        "max_tokens": 8192,
        "stream": False,
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; V2Pipeline/1.0)")

    for attempt in range(MAX_RETRIES):
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8") if e.fp else ""
            if e.code == 429:
                wait = RETRY_DELAY * (attempt + 1) * 2
                print(f"  Rate limited (429), retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {e.code}: {body_text}")
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  API error: {e}, retrying ({attempt + 2}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)
                continue
            raise

    raise RuntimeError("Max retries exceeded")


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def parse_llm_response(text):
    """Parse LLM output into a dict. Handles markdown fences and multi-line JSON."""
    text = text.strip()

    # Remove markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object boundaries
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse LLM response as JSON: {text[:200]}...")


# ---------------------------------------------------------------------------
# Batch generation
# ---------------------------------------------------------------------------

def generate_drafts_for_packs(packs, evidence_map, paper_id, prompt, mock=False):
    """Generate one draft entry per context pack."""
    drafts = []
    entry_idx = 0

    # Group packs by evidence_type for batching
    by_type = {}
    for p in packs:
        etype = p.get("evidence_type", "unknown")
        by_type.setdefault(etype, []).append(p)

    for etype, type_packs in by_type.items():
        print(f"\n  Evidence type: {etype} ({len(type_packs)} packs)")

        # Batch into groups of MAX_PACKS_PER_BATCH
        for batch_start in range(0, len(type_packs), MAX_PACKS_PER_BATCH):
            batch = type_packs[batch_start:batch_start + MAX_PACKS_PER_BATCH]
            print(f"    Batch {batch_start // MAX_PACKS_PER_BATCH + 1}: {len(batch)} pack(s)")

            if mock:
                for pack in batch:
                    draft = mock_draft(pack, paper_id, entry_idx)
                    drafts.append(draft)
                    entry_idx += 1
                continue

            # Build batch input
            contexts = [build_pack_context(p, evidence_map) for p in batch]
            user_input = json.dumps(
                {"packs": contexts, "instruction": "为每个 pack 生成一条 draft entry"},
                ensure_ascii=False
            )

            try:
                response = call_llm(prompt, user_input)
            except Exception as e:
                print(f"      LLM call failed: {e}")
                continue

            # Parse response — could be a single object or a list
            try:
                parsed = parse_llm_response(response)
            except ValueError as e:
                print(f"      Parse error: {e}")
                # Retry each pack individually
                for pack in batch:
                    try:
                        draft = retry_single_pack(pack, evidence_map, prompt)
                        if draft:
                            draft = finalize_draft(draft, pack, paper_id, entry_idx)
                            drafts.append(draft)
                            entry_idx += 1
                    except Exception as e2:
                        print(f"      Individual retry failed for {pack['pack_id']}: {e2}")
                continue

            # Handle response: could be list of drafts or single draft
            if isinstance(parsed, list):
                draft_list = parsed
            elif isinstance(parsed, dict):
                # Could be {"drafts": [...]} or a single draft
                if "drafts" in parsed:
                    draft_list = parsed["drafts"]
                elif "pack_id" in parsed or "main_claim" in parsed:
                    draft_list = [parsed]
                else:
                    # Single key per pack? Try to extract
                    draft_list = list(parsed.values())
            else:
                print(f"      Unexpected response type: {type(parsed)}")
                continue

            for i, draft in enumerate(draft_list):
                if not isinstance(draft, dict):
                    continue
                pack = batch[min(i, len(batch) - 1)]
                draft = finalize_draft(draft, pack, paper_id, entry_idx)
                drafts.append(draft)
                entry_idx += 1

            print(f"      → {len(draft_list)} draft(s) generated")

    return drafts


def retry_single_pack(pack, evidence_map, prompt):
    """Retry a single pack with its own LLM call."""
    context = build_pack_context(pack, evidence_map)
    user_input = json.dumps(
        {"pack": context, "instruction": "为这个 pack 生成一条 draft entry"},
        ensure_ascii=False
    )
    response = call_llm(prompt, user_input)
    return parse_llm_response(response)


def finalize_draft(draft, pack, paper_id, entry_idx):
    """Fill auto-generated fields and ensure all required fields exist."""
    draft["entry_id"] = f"D{entry_idx + 1:04d}"
    draft["paper_id"] = paper_id
    draft["evidence_type"] = pack.get("evidence_type", "unknown")

    # Ensure required fields
    if not isinstance(draft.get("evidence_links"), list):
        draft["evidence_links"] = []
    if not isinstance(draft.get("experimental_model_summary"), dict):
        draft["experimental_model_summary"] = {}
    if not isinstance(draft.get("review_questions"), list):
        draft["review_questions"] = []
    if not isinstance(draft.get("uncertainty_map"), dict):
        draft["uncertainty_map"] = {}
    if not isinstance(draft.get("structured_fields"), dict):
        draft["structured_fields"] = {}
    if not draft.get("status") or draft["status"] not in ("draft", "needs_review"):
        draft["status"] = "draft"
    if not draft.get("main_claim"):
        draft["main_claim"] = "(LLM failed to generate claim)"

    # Add pack reference to evidence_links
    if not any(link.get("pack_id") == pack.get("pack_id") for link in draft.get("evidence_links", [])):
        pass  # evidence_links should reference individual evidence units, not packs

    return draft


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def mock_draft(pack, paper_id, idx):
    """Generate a trivial mock draft entry."""
    member_ids = pack.get("member_evidence_ids", [])
    return {
        "entry_id": f"D{idx + 1:04d}",
        "paper_id": paper_id,
        "evidence_type": pack.get("evidence_type", "unknown"),
        "main_claim": f"[Mock] 基于 {len(member_ids)} 条证据的综合结论: {pack.get('pack_reason', '')}",
        "structured_fields": _mock_structured_fields(pack.get("evidence_type", "")),
        "evidence_links": [
            {"evidence_id": eid, "relevance": "直接支持", "note": "mock"}
            for eid in member_ids
        ],
        "experimental_model_summary": {
            "model_levels": ["unknown"],
            "species": [],
            "cell_or_tissue_types": [],
            "in_vivo_in_vitro_mix": "mixed",
            "model_diversity": "低",
            "limitations": "mock data",
        },
        "review_questions": [
            "此条为 mock 数据，请以真实 LLM 生成替代",
            "结论是否有足够的证据支持？",
        ],
        "uncertainty_map": {
            "evidence_consistency": "证据不足",
            "statistical_confidence": "低",
            "gaps": ["mock data"],
            "alternative_interpretations": [],
            "requires_follow_up": True,
        },
        "status": "draft",
    }


MOCK_STRUCTURED_FIELDS = {
    "disease_association": {"disease": "mock", "association_type": "相关性"},
    "detection_method": {"method_category": "other", "method_summary": "mock"},
    "thermogenesis_modulation": {"intervention": "mock", "modulation_direction": "increases"},
    "biomarker_panel": {"biomarker_list": ["mock"], "clinical_context": "诊断"},
    "mechanism_pathway": {"pathway_name": "mock", "core_finding": "mock"},
    "pathway_cellular_function_impact": {"pathway": "mock", "cellular_function_affected": "mock"},
    "organelle_interaction_impact": {"interacting_organelles": ["mock"], "functional_impact": "mock"},
}


def _mock_structured_fields(evidence_type):
    """Return mock structured_fields for a given evidence_type."""
    return MOCK_STRUCTURED_FIELDS.get(evidence_type, {})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_drafts(drafts):
    errors_total = 0
    for d in drafts:
        errs, warns = validate_record(d, "draft_entry")
        if errs:
            errors_total += len(errs)
            print(f"  [VALIDATE] {d['entry_id']}: {len(errs)} error(s)")
            for e in errs[:5]:
                print(f"    - {e}")
    return errors_total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    run_dir = sys.argv[1]
    paper_id = sys.argv[2]
    mock = "--mock" in sys.argv

    if not API_KEY and not mock:
        print("ERROR: OPENAI_API_KEY not set. Use --mock for mock mode.")
        sys.exit(1)

    print(f"=== Draft Entry Generation ===")
    print(f"Run dir: {run_dir}")
    print(f"Paper ID: {paper_id}")
    print(f"Mode: {'mock' if mock else 'LLM'}")
    print()

    # Load data
    inputs = stage_input_paths("draft_entries", run_dir)
    outputs = stage_output_paths("draft_entries", run_dir)
    packs = load_jsonl(inputs["context_packs.jsonl"])
    evidence_units = load_jsonl(inputs["evidence_units.jsonl"])
    evidence_map = {u["evidence_id"]: u for u in evidence_units}

    print(f"Loaded {len(packs)} context packs, {len(evidence_units)} evidence units")

    prompt = load_prompt() if not mock else None

    # Generate drafts
    drafts = generate_drafts_for_packs(packs, evidence_map, paper_id, prompt, mock=mock)

    # Renumber sequentially
    for i, d in enumerate(drafts):
        d["entry_id"] = f"D{i + 1:04d}"

    print(f"\n=== Validation ===")
    errs = validate_drafts(drafts)
    print(f"Total: {len(drafts)} draft entries, {errs} validation errors")

    # Write output
    out_path = outputs["draft_entries.jsonl"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for d in drafts:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"\nOutput: {out_path}")
    print(f"Done. {len(drafts)} draft entries written.")


if __name__ == "__main__":
    main()
