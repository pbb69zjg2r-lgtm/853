"""
run_mineru.py — Call MinerU Precision Extract API, save raw output.

Usage:
    python src/parsing/run_mineru.py <pdf_path> <output_dir>
"""

import json
import ssl
import sys
import time
from pathlib import Path

# Disable SSL verification BEFORE importing mineru/httpx
ssl._create_default_https_context = ssl._create_unverified_context

import httpx
import mineru
from mineru import MinerU

# Patch httpx at module level
_original_get = httpx.get
_original_post = httpx.post
def _get(*args, **kwargs):
    kwargs.setdefault("verify", False)
    return _original_get(*args, **kwargs)
def _post(*args, **kwargs):
    kwargs.setdefault("verify", False)
    return _original_post(*args, **kwargs)
httpx.get = _get
httpx.post = _post

# Also patch internal httpx.Client
_original_client_request = httpx.Client.request
def _patched_request(self, *args, **kwargs):
    return _original_client_request(self, *args, **kwargs)
httpx.Client.request = _patched_request

API_KEY = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI1MTQwMDk5MiIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc4MjEyMzkxMCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiNjg0ZmI2MDMtOTk5NC00NmU1LWFhNDYtZDkwMjA1MzAyOTc4IiwiZW1haWwiOiIiLCJleHAiOjE3ODk4OTk5MTB9.OVGotXJLWJS9tRSc6RlI9uzqGWBiAqTV2C1ScKoRYslsih17ffzbpSihsA3-wA0vMoNcsEu55YTeVI9TTMAEBA"


def save_result(result, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "full.md"
    md_path.write_text(result.markdown, encoding="utf-8")
    print(f"  full.md: {len(result.markdown)} chars")

    if hasattr(result, "content_list") and result.content_list:
        cl_path = output_dir / "content_list.json"
        cl_path.write_text(
            json.dumps(result.content_list, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"  content_list.json: {len(result.content_list)} entries")

    if hasattr(result, "images") and result.images:
        img_dir = output_dir / "images"
        img_dir.mkdir(exist_ok=True)
        for i, img in enumerate(result.images):
            try:
                if isinstance(img, dict):
                    name = img.get("filename", f"image_{i}.png")
                    data = img.get("data")
                else:
                    name = getattr(img, "filename", f"image_{i}.png")
                    data = getattr(img, "data", None)
                if data:
                    (img_dir / name).write_bytes(data)
            except Exception:
                pass
        print(f"  images/: saved")

    manifest = {
        "pdf_path": str(getattr(result, "pdf_path", "")),
        "md_chars": len(result.markdown),
    }
    manifest_path = output_dir / "parse_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/parsing/run_mineru.py <pdf_path> [output_dir]")
        sys.exit(1)

    pdf_path = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path.cwd() / "01_raw_parse"

    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"PDF: {pdf_path}")
    print(f"Output: {output_dir}")

    client = MinerU(API_KEY)
    batch_id = client.submit(str(pdf_path))
    print(f"Batch ID: {batch_id}")

    retries = 0
    while retries < 8:
        time.sleep(15)
        try:
            results = client.get_batch(batch_id)
            result = results[0]
            state = result.state
            print(f"  [{retries+1}] state={state}")
            if state == "done":
                save_result(result, output_dir)
                print("Done.")
                return
            elif state == "failed":
                print(f"ERROR: MinerU failed — {getattr(result, 'error', 'unknown')}")
                sys.exit(1)
        except Exception as e:
            print(f"  [{retries+1}] retry after error: {e}")
        retries += 1

    print("ERROR: Timeout waiting for MinerU")
    sys.exit(1)


if __name__ == "__main__":
    main()
