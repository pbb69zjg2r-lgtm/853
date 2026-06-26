#!/usr/bin/env python3
"""V2 Review server — serves review.html and REST APIs for human review.

Usage: python src/review/review_server.py <paper_run_dir> [--port 8080]
Open:  http://localhost:8080
"""

import http.server
import json
import os
import sys
import urllib.parse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_jsonl(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_api_data(paper_dir: Path) -> dict:
    """Assemble all V2 pipeline data into one API response."""
    evidence = load_jsonl(paper_dir / "03_evidence" / "evidence_units.jsonl")
    drafts = load_jsonl(paper_dir / "06_draft" / "draft_entries.jsonl")
    verifier = load_json(paper_dir / "07_verification" / "verifier_report.json")
    paper_id = paper_dir.parent.name if paper_dir.parent.name != "runs" else paper_dir.name

    # Load review state
    review_path = paper_dir / "08_review" / "review_state.json"
    if review_path.exists():
        review_state = load_json(review_path)
    else:
        review_state = {"entries": {}}

    return {
        "paper_id": paper_id,
        "evidence": evidence,
        "drafts": drafts,
        "verifier_summary": verifier.get("summary", {}),
        "verifier_results": verifier.get("entry_results", []),
        "review_state": review_state,
    }


class ReviewHandler(http.server.SimpleHTTPRequestHandler):
    paper_dir: Path = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/data":
            self._json_response(build_api_data(self.paper_dir))
        elif path == "/":
            self._serve_html()
        elif path == "/api/export":
            self._export_json()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/save":
            self._save_review()
        else:
            self.send_error(404)

    def _json_response(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        html_path = PROJECT_ROOT / "src" / "review" / "review.html"
        if not html_path.exists():
            self.send_error(500, "review.html not found")
            return
        body = html_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _save_review(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len))
        review_path = self.paper_dir / "08_review" / "review_state.json"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        body["updated_at"] = __import__("datetime").datetime.now().isoformat()
        with open(review_path, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False, indent=2)
        self._json_response({"status": "ok"})

    def _export_json(self):
        data = build_api_data(self.paper_dir)
        review_state = data["review_state"]
        entries_state = review_state.get("entries", {})
        drafts = data["drafts"]
        for d in drafts:
            eid = d["entry_id"]
            d["_review_status"] = entries_state.get(eid, {}).get("status", "draft")
            d["_review_notes"] = entries_state.get(eid, {}).get("notes", "")

        out = {
            "paper_id": data["paper_id"],
            "drafts": drafts,
            "evidence": data["evidence"],
        }
        body = json.dumps(out, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition",
                         f"attachment; filename={data['paper_id']}_review_export.json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[review] {args[0]}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="V2 Human Review Server")
    parser.add_argument("paper_dir", help="Path to paper run directory")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    args = parser.parse_args()

    paper_dir = Path(args.paper_dir).resolve()
    if not paper_dir.exists():
        print(f"ERROR: {paper_dir} not found")
        sys.exit(1)

    ReviewHandler.paper_dir = paper_dir

    host = "127.0.0.1"
    server = http.server.HTTPServer((host, args.port), ReviewHandler)
    url = f"http://{host}:{args.port}"
    print(f"\n  Review server: {url}")
    print(f"  Paper: {paper_dir}")
    print(f"  Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")


if __name__ == "__main__":
    main()
