"""
Evidence unit extraction stage (step 3 of V2 pipeline).

Reads source_blocks.jsonl, calls DeepSeek LLM to extract structured evidence units,
validates against contracts, and writes evidence_units.jsonl.

Supports multiple independent runs for downstream consensus voting.

Usage:
    python extract_evidence.py <run_dir> <paper_id>              # LLM extraction
    python extract_evidence.py <run_dir> <paper_id> --mock       # Mock mode
    python extract_evidence.py <run_dir> <paper_id> --run N      # Run number (for consensus)
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.contracts import format_prompt, stage_input_paths, stage_output_paths
from src.validation.validate_stage import validate_record


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL = os.environ.get("EVIDENCE_LLM_MODEL", "deepseek-chat")

MAX_CHARS_PER_BATCH = 25000
MAX_RETRIES = 3
RETRY_DELAY = 5

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def load_prompt():
    path = os.path.join(PROMPT_DIR, "evidence_extraction.txt")
    with open(path, "r", encoding="utf-8") as f:
        template = f.read()
    return format_prompt(template)


# ---------------------------------------------------------------------------
# Source block loading and batching
# ---------------------------------------------------------------------------

def load_source_blocks(run_dir):
    inputs = stage_input_paths("evidence_units", run_dir)
    path = inputs["source_blocks.jsonl"]
    blocks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                blocks.append(json.loads(line))
    return blocks


def group_blocks(blocks):
    """Group blocks into LLM batches based on section proximity and char limit."""
    # Only use paragraph blocks for extraction (figures/tables have no extractable text)
    text_blocks = [b for b in blocks if b.get("source_type") in ("paragraph", None)]

    batches = []
    current_batch = []
    current_chars = 0

    for b in text_blocks:
        text = b.get("text", "")
        text_len = len(text)

        # Start new batch if this block would exceed limit (and batch is non-empty)
        if current_batch and current_chars + text_len > MAX_CHARS_PER_BATCH:
            batches.append(current_batch)
            current_batch = []
            current_chars = 0

        current_batch.append(b)
        current_chars += text_len

    if current_batch:
        batches.append(current_batch)

    return batches


def format_batch(batch, paper_id, batch_idx, total_batches):
    """Format a batch of source blocks as the LLM input."""
    lines = [
        f"Paper: {paper_id}",
        f"Batch {batch_idx + 1} of {total_batches}",
        f"Extract all evidence units from the following source blocks.",
        "",
    ]
    for b in batch:
        sid = b.get("block_id", b.get("source_block_id", "?"))
        section = b.get("section", "unknown")
        section_type = b.get("section_type", "body")
        page = b.get("page", "?")
        text = b.get("text", "")
        lines.append(f"--- BLOCK {sid} | page={page} | section={section} | section_type={section_type} ---")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM API call
# ---------------------------------------------------------------------------

def call_llm(system_prompt, user_input):
    """Call DeepSeek chat API. Returns response text or raises on error."""
    import urllib.request
    import urllib.error

    url = f"{BASE_URL}/chat/completions"
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "temperature": 0,
        "max_tokens": 4096,
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

def parse_response(response_text, batch, paper_id, id_offset):
    """Parse LLM JSONL response into evidence unit records.

    Handles common formatting issues: markdown fences, trailing commas,
    non-JSON text between records.
    """
    evidence_units = []

    # Strip markdown code fences
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # Parse line by line
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("//") or line.startswith("#"):
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            # Try to salvage: find JSON object boundaries
            start = line.find("{")
            end = line.rfind("}")
            if start >= 0 and end > start:
                try:
                    record = json.loads(line[start:end + 1])
                except json.JSONDecodeError:
                    continue
            else:
                continue

        if not isinstance(record, dict):
            continue
        if "evidence_type" not in record:
            continue

        # Normalize and fill fields
        record = normalize_record(record, paper_id, id_offset + len(evidence_units))
        evidence_units.append(record)

    return evidence_units


def normalize_record(record, paper_id, index):
    """Fill auto-generated fields, drop placeholder values."""
    record["paper_id"] = paper_id
    record["evidence_id"] = f"E{index + 1:04d}"

    # Force review_coverage
    if not isinstance(record.get("review_coverage"), dict):
        record["review_coverage"] = {"status": "unreviewed"}

    # Force normalization_status
    if record.get("normalization_status") != "not_normalized":
        record["normalization_status"] = "not_normalized"

    # Ensure extraction_meta.method
    if isinstance(record.get("extraction_meta"), dict):
        record["extraction_meta"].setdefault("method", "LLM")
    else:
        record["extraction_meta"] = {"method": "LLM"}

    # Ensure arrays are arrays, objects are objects
    for array_field in ["raw_entities"]:
        if not isinstance(record.get(array_field), list):
            record[array_field] = []

    for obj_field in ["structured_fields", "experimental_model", "condition_context",
                       "source_trace", "statistics", "measurement"]:
        if not isinstance(record.get(obj_field), dict):
            record[obj_field] = {}

    if isinstance(record.get("source_trace"), dict):
        if not isinstance(record["source_trace"].get("source_block_ids"), list):
            record["source_trace"]["source_block_ids"] = []
        if "quote" not in record["source_trace"]:
            record["source_trace"]["quote"] = ""

    return record


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def mock_extraction(blocks, paper_id):
    """Generate trivial mock evidence units from blocks (no LLM)."""
    units = []
    for i, b in enumerate(blocks):
        if b.get("source_type") not in ("paragraph", None):
            continue
        text = b.get("text", "")
        if len(text) < 50:
            continue

        unit = {
            "evidence_id": f"E{i + 1:04d}",
            "paper_id": paper_id,
            "evidence_type": "mechanism_pathway",
            "claim": text[:200].strip(),
            "structured_fields": {
                "pathway_name": "mock",
                "key_nodes": [],
                "upstream_trigger": None,
                "downstream_effect": None,
                "mechanism_type": "signaling_cascade",
            },
            "raw_entities": [],
            "experimental_model": {
                "model_level": "unknown",
                "model_name": None,
                "species": None,
                "tissue_or_cell_type": None,
                "in_vivo_or_in_vitro": "unknown",
            },
            "condition_context": {},
            "source_trace": {
                "source_block_ids": [b.get("block_id", "")],
                "quote": text[:200].strip(),
                "page": b.get("page"),
                "section": b.get("section"),
            },
            "polarity": "neutral",
            "statistics": {},
            "measurement": {},
            "extraction_meta": {"method": "mock"},
            "review_coverage": {"status": "unreviewed"},
            "normalization_status": "not_normalized",
        }
        units.append(unit)
    return units


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_units(units):
    """Validate all evidence units against contracts. Returns error count."""
    total_errors = 0
    for unit in units:
        errors, warnings = validate_record(unit, "evidence_unit")
        if errors:
            total_errors += len(errors)
            print(f"  [VALIDATE] {unit['evidence_id']}: {len(errors)} error(s)")
            for e in errors[:5]:  # cap output
                print(f"    - {e}")
    return total_errors


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

    # Determine run number
    run_num = None
    for i, arg in enumerate(sys.argv):
        if arg == "--run" and i + 1 < len(sys.argv):
            run_num = int(sys.argv[i + 1])
            break

    # Output path
    outputs = stage_output_paths("evidence_units", run_dir)
    base_out = outputs["evidence_units.jsonl"]
    if run_num:
        out_path = os.path.join(os.path.dirname(base_out), f"evidence_units_run{run_num}.jsonl")
    else:
        out_path = base_out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if not API_KEY and not mock:
        print("ERROR: OPENAI_API_KEY not set. Use --mock for mock mode.")
        sys.exit(1)

    print(f"=== Evidence Extraction ===")
    print(f"Run dir: {run_dir}")
    print(f"Paper ID: {paper_id}")
    print(f"Mode: {'mock' if mock else 'LLM'}")
    if run_num:
        print(f"Run: {run_num}")
    print()

    # Load source blocks
    blocks = load_source_blocks(run_dir)
    print(f"Loaded {len(blocks)} source blocks")

    if mock:
        units = mock_extraction(blocks, paper_id)
        print(f"Mock-extracted {len(units)} evidence units")
    else:
        prompt = load_prompt()
        batches = group_blocks(blocks)
        print(f"Grouped into {len(batches)} batches")

        all_units = []
        global_offset = 0

        for idx, batch in enumerate(batches):
            print(f"\nBatch {idx + 1}/{len(batches)} ({len(batch)} blocks, ~{sum(len(b.get('text', '')) for b in batch)} chars)...")

            user_input = format_batch(batch, paper_id, idx, len(batches))

            try:
                response = call_llm(prompt, user_input)
            except Exception as e:
                print(f"  LLM call failed: {e}")
                continue

            units = parse_response(response, batch, paper_id, global_offset)
            print(f"  Extracted {len(units)} units")
            all_units.extend(units)
            global_offset += len(units)

        units = all_units

        # Renumber sequentially
        for i, u in enumerate(units):
            u["evidence_id"] = f"E{i + 1:04d}"

    # Validate
    print(f"\n=== Validation ===")
    errors = validate_units(units)
    print(f"Total: {len(units)} evidence units, {errors} validation errors")

    # Write output
    with open(out_path, "w", encoding="utf-8") as f:
        for unit in units:
            f.write(json.dumps(unit, ensure_ascii=False) + "\n")

    print(f"\nOutput: {out_path}")
    print(f"Done. {len(units)} evidence units written.")


if __name__ == "__main__":
    main()
