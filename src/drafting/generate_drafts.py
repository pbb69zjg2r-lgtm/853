"""generate_drafts.py — Generate structured draft entries from context packs via LLM.

Input:  05_context/context_packs.jsonl
Output: 06_draft/draft_entries.jsonl
"""

import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path


def load_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "draft_generation.txt"
    return prompt_path.read_text(encoding="utf-8")


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def call_llm_api(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("EVIDENCE_LLM_MODEL", "deepseek-chat")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set.")

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 4096,
    }).encode("utf-8")

    for attempt in range(5):
        try:
            req = urllib.request.Request(url, data=body, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
            ctx = ssl.create_default_context()
            resp = urllib.request.urlopen(req, context=ctx, timeout=180)
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            if not content:
                raise RuntimeError("LLM returned empty content")
            return content
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt < 4:
                wait = min(30 * (2 ** attempt), 240)
                print(f"  Rate limited (403), waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Max retries exceeded")


def build_batch_prompt(packs: list[dict]) -> str:
    parts = []
    for i, p in enumerate(packs):
        parts.append(f"## Entry {i+1}")
        parts.append(f"Task: {p['task_type']}")
        parts.append(f"Expected output: {p['expected_output']}")
        parts.append(f"\nAnchor source text:\n{p['anchor_source_text']}")

        if p["related_evidence"]:
            parts.append("\nRelated evidence:")
            for r in p["related_evidence"]:
                parts.append(f"- [{r['evidence_type']}] {r['source_text']}")
        parts.append("")
    return "\n".join(parts)


def parse_draft_output(raw: str, packs: list[dict], paper_id: str) -> list[dict]:
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:]) if lines[0].startswith("```") else raw
        if raw.endswith("```"):
            raw = raw[:raw.rfind("```")].strip()
        extracted = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  WARNING: Failed to parse draft LLM output: {e}")
        print(f"  Raw (first 300 chars): {raw[:300]}")
        return []

    if not isinstance(extracted, list):
        extracted = [extracted]

    entries = []
    for i, entry in enumerate(extracted):
        if not isinstance(entry, dict):
            continue
        pack_idx = min(i, len(packs) - 1)
        pack = packs[pack_idx]

        de = {
            "entry_id": f"{paper_id}_D{len(entries)+1:04d}",
            "paper_id": paper_id,
            "pack_id": pack["pack_id"],
            "task_type": pack["task_type"],
            "main_claim": entry.get("main_claim", ""),
            "structured_fields": entry.get("structured_fields", {}),
            "evidence_links": [pack["anchor_evidence_id"]] + pack.get("related_evidence_ids", []),
            "status": "draft",
        }
        entries.append(de)
    return entries


def generate_drafts(paper_dir: Path, paper_id: str):
    packs_path = paper_dir / "05_context" / "context_packs.jsonl"
    if not packs_path.exists():
        raise FileNotFoundError(f"{packs_path} not found. Run build_context_packs.py first.")

    packs = load_jsonl(packs_path)
    system_prompt = load_prompt()

    # Batch by task_type, then split into chunks of max 4 packs
    from collections import defaultdict
    by_type = defaultdict(list)
    for p in packs:
        by_type[p["task_type"]].append(p)

    batches = []
    for task_type, type_packs in by_type.items():
        for i in range(0, len(type_packs), 4):
            batches.append(type_packs[i:i+4])

    print(f"  Context packs: {len(packs)}")
    print(f"  Batches: {len(batches)}")

    all_entries = []
    for batch_idx, batch in enumerate(batches):
        batch_prompt = build_batch_prompt(batch)
        print(f"  Batch {batch_idx+1}/{len(batches)}: {len(batch)} packs, "
              f"{batch[0]['task_type']}, {len(batch_prompt)} chars")

        raw = call_llm_api(system_prompt, batch_prompt)
        entries = parse_draft_output(raw, batch, paper_id)
        all_entries.extend(entries)
        print(f"    → {len(entries)} entries")

        if batch_idx < len(batches) - 1:
            time.sleep(3)

    # Re-index entry IDs
    for idx, e in enumerate(all_entries):
        e["entry_id"] = f"{paper_id}_D{idx+1:04d}"

    out_dir = paper_dir / "06_draft"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "draft_entries.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for e in all_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    from collections import Counter
    type_counts = Counter(e["task_type"] for e in all_entries)
    print(f"\n  Draft entries: {len(all_entries)}")
    for tt, c in type_counts.most_common():
        print(f"    {tt}: {c}")
    print(f"  Output: {out_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/drafting/generate_drafts.py <paper_run_dir> [paper_id]")
        sys.exit(1)

    paper_dir = Path(sys.argv[1]).resolve()
    paper_id = sys.argv[2] if len(sys.argv) > 2 else paper_dir.parent.name
    generate_drafts(paper_dir, paper_id)


if __name__ == "__main__":
    main()
