#!/usr/bin/env python3
"""V2 Review server — serves review.html and REST APIs for human review.

Usage:
    python src/review/review_server.py [paper_dir] [--port 8080]
      paper_dir omitted → multi-paper mode, auto-discovers all papers under runs/
      paper_dir given    → single-paper mode (backward compatible)
Open:  http://localhost:8080
"""

import http.server
import json
import os
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def discover_papers(runs_dir: Path) -> list[dict]:
    """Scan runs_dir for paper subdirectories that have 06_draft/draft_entries.jsonl."""
    papers = []
    if not runs_dir.exists():
        return papers
    for child in sorted(runs_dir.iterdir()):
        if not child.is_dir():
            continue
        draft_path = child / "06_draft" / "draft_entries.jsonl"
        if not draft_path.exists():
            continue
        paper_id = child.name
        draft_count = sum(1 for _ in open(draft_path, encoding="utf-8"))
        papers.append({
            "paper_id": paper_id,
            "paper_dir": str(child.resolve()),
            "draft_count": draft_count,
        })
    return papers


def load_jsonl(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_api_data(paper_dir: Path) -> dict:
    """Assemble all V2 pipeline data into one API response."""
    paper_id = paper_dir.name

    ev_path = paper_dir / "03_evidence" / "evidence_units.jsonl"
    evidence = load_jsonl(ev_path) if ev_path.exists() else []

    draft_path = paper_dir / "06_draft" / "draft_entries.jsonl"
    drafts = load_jsonl(draft_path) if draft_path.exists() else []

    ver_path = paper_dir / "07_verification" / "verifier_report.json"
    if ver_path.exists():
        verifier = load_json(ver_path)
    else:
        verifier = {}

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
    papers: dict = {}
    paper_dirs: dict = {}
    single_mode: bool = False

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/api/papers":
            self._json_response(list(self.papers.values()))
        elif path == "/api/data":
            paper_id = qs.get("paper", [None])[0]
            if not paper_id:
                self.send_error(400, "Missing ?paper= parameter")
                return
            paper_dir = self._resolve_paper(paper_id)
            if not paper_dir:
                return
            self._json_response(build_api_data(paper_dir))
        elif path == "/":
            self._serve_html()
        elif path == "/api/export":
            paper_id = qs.get("paper", [None])[0]
            if not paper_id:
                self.send_error(400, "Missing ?paper= parameter")
                return
            paper_dir = self._resolve_paper(paper_id)
            if not paper_dir:
                return
            self._export_json(paper_dir)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/api/save":
            paper_id = qs.get("paper", [None])[0]
            if not paper_id:
                self.send_error(400, "Missing ?paper= parameter")
                return
            paper_dir = self._resolve_paper(paper_id)
            if not paper_dir:
                return
            self._save_review(paper_dir)
        else:
            self.send_error(404)

    def _resolve_paper(self, paper_id: str) -> Path | None:
        paper_dir = self.paper_dirs.get(paper_id)
        if not paper_dir:
            self.send_error(404, f"Paper '{paper_id}' not found")
            return None
        return paper_dir

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

    def _save_review(self, paper_dir: Path):
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len))
        review_path = paper_dir / "08_review" / "review_state.json"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        body["updated_at"] = datetime.now().isoformat()
        with open(review_path, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False, indent=2)
        self._json_response({"status": "ok"})

    def _export_json(self, paper_dir: Path):
        data = build_api_data(paper_dir)
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
    parser.add_argument(
        "paper_dir", nargs="?", default=None,
        help="Path to a single paper run directory (single-paper mode)"
    )
    parser.add_argument(
        "--runs-dir", default=None,
        help="Path to runs directory for multi-paper auto-discovery (default: PROJECT_ROOT/runs)"
    )
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    args = parser.parse_args()

    if args.paper_dir:
        # Single-paper mode (backward compatible)
        paper_dir = Path(args.paper_dir).resolve()
        if not paper_dir.exists():
            print(f"ERROR: {paper_dir} not found")
            sys.exit(1)
        paper_id = paper_dir.name
        ReviewHandler.papers = {
            paper_id: {
                "paper_id": paper_id,
                "paper_dir": str(paper_dir),
                "draft_count": "?",
            }
        }
        ReviewHandler.paper_dirs = {paper_id: paper_dir}
        ReviewHandler.single_mode = True
        print(f"\n  Review server: http://127.0.0.1:{args.port}")
        print(f"  Mode: single-paper")
        print(f"  Paper: {paper_id}  ({paper_dir})")
    else:
        # Multi-paper mode
        runs_dir = Path(args.runs_dir).resolve() if args.runs_dir else (PROJECT_ROOT / "runs")
        papers = discover_papers(runs_dir)
        if not papers:
            print(f"ERROR: No papers with 06_draft/draft_entries.jsonl found under {runs_dir}")
            sys.exit(1)
        ReviewHandler.papers = {p["paper_id"]: p for p in papers}
        ReviewHandler.paper_dirs = {p["paper_id"]: Path(p["paper_dir"]) for p in papers}
        ReviewHandler.single_mode = False
        print(f"\n  Review server: http://127.0.0.1:{args.port}")
        print(f"  Mode: multi-paper  ({len(papers)} papers)")
        for p in papers:
            print(f"    - {p['paper_id']}  ({p['draft_count']} drafts)")

    print(f"  Press Ctrl+C to stop\n")

    host = "127.0.0.1"
    server = http.server.HTTPServer((host, args.port), ReviewHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")


if __name__ == "__main__":
    main()
