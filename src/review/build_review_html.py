"""build_review_html.py — Generate a self-contained HTML review workspace.

Embeds evidence, draft entries, and verifier report into an interactive
review page with approve/reject/flag controls and note-taking.

Input:  06_draft/draft_entries.jsonl, 03_evidence/evidence_units.jsonl,
        07_verification/verifier_report.json, 02_source/source_blocks.jsonl
Output: 08_review/review.html
"""

import json
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review — {paper_id}</title>
<style>
*<<box-sizing:border-box;margin:0;padding:0>>
body<<font:14px/1.5 system-ui,sans-serif;display:flex;height:100vh;color:#1a1a2e;background:#f5f5f7>>
#sidebar<<width:320px;background:#fff;border-right:1px solid #e0e0e0;overflow-y:auto;display:flex;flex-direction:column>>
#sidebar h2<<padding:16px;font-size:16px;border-bottom:1px solid #e0e0e0;background:#fafafa>>
#entry-list<<flex:1;overflow-y:auto>>
.entry-item<<padding:10px 16px;border-bottom:1px solid #f0f0f0;cursor:pointer;transition:background .15s>>
.entry-item:hover<<background:#f0f4ff>>
.entry-item.active<<background:#e8f0fe;border-left:3px solid #1a73e8>>
.entry-item .eid<<font-weight:600;font-size:13px;color:#555>>
.entry-item .claim<<font-size:12px;color:#333;margin-top:2px;line-height:1.3>>
.entry-item .badge<<display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;margin-right:4px>>
.badge-ok<<background:#e6f4ea;color:#1e8e3e>>
.badge-flagged<<background:#fce8e6;color:#d93025>>
.badge-draft<<background:#e8eaf6;color:#3f51b5>>
#main<<flex:1;display:flex;flex-direction:column;overflow:hidden>>
#toolbar<<padding:12px 20px;background:#fff;border-bottom:1px solid #e0e0e0;display:flex;gap:8px;align-items:center>>
#toolbar button<<padding:8px 16px;border:1px solid #dadce0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;font-weight:500>>
#toolbar button:hover<<background:#f1f3f4>>
#toolbar button.primary<<background:#1a73e8;color:#fff;border-color:#1a73e8>>
#toolbar button.danger<<color:#d93025;border-color:#fce8e6>>
#toolbar button.success<<color:#1e8e3e;border-color:#e6f4ea>>
#toolbar .stats<<margin-left:auto;font-size:12px;color:#666>>
#content<<flex:1;overflow-y:auto;padding:20px>>
#content h3<<font-size:18px;margin-bottom:12px>>
#content .section<<margin-bottom:20px>>
#content .section h4<<font-size:13px;color:#666;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;border-bottom:1px solid #eee;padding-bottom:4px>>
.evidence-card<<background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:12px 16px;margin-bottom:8px>>
.evidence-card .meta<<font-size:11px;color:#999;margin-bottom:4px>>
.evidence-card .text<<font-size:13px;line-height:1.5>>
.entity-tag<<display:inline-block;background:#e8f5e9;color:#2e7d32;padding:1px 8px;border-radius:10px;font-size:11px;margin:2px>>
.field-table<<width:100%;border-collapse:collapse;font-size:13px>>
.field-table td<<padding:6px 10px;border-bottom:1px solid #f0f0f0;vertical-align:top>>
.field-table td:first-child<<font-weight:600;color:#555;width:180px>>
#notes<<width:100%;min-height:80px;padding:10px;border:1px solid #e0e0e0;border-radius:6px;font-size:13px;resize:vertical;margin-top:8px>>
.empty-state<<text-align:center;padding:60px 20px;color:#999>>
.empty-state h3<<font-size:18px;margin-bottom:8px>>
.stats-bar<<display:flex;gap:16px;padding:8px 16px;font-size:12px;border-bottom:1px solid #e0e0e0;background:#fafafa>>
.stats-bar span<<font-weight:600>>
</style>
</head>
<body>
<div id="sidebar">
  <h2>📋 Draft Entries</h2>
  <div class="stats-bar">
    <span>Total: <b id="stat-total">0</b></span>
    <span style="color:#1e8e3e">✓ <b id="stat-approved">0</b></span>
    <span style="color:#d93025">✗ <b id="stat-rejected">0</b></span>
    <span style="color:#f9ab00">⚑ <b id="stat-flagged">0</b></span>
  </div>
  <div id="entry-list"></div>
</div>
<div id="main">
  <div id="toolbar">
    <button class="success" onclick="reviewEntry('approved')" title="Approve">✓ Approve</button>
    <button class="danger" onclick="reviewEntry('rejected')" title="Reject">✗ Reject</button>
    <button onclick="reviewEntry('needs_review')" title="Flag for later">⚑ Flag</button>
    <button class="primary" onclick="exportState()" title="Download review state">📥 Export</button>
    <span class="stats" id="current-status"></span>
  </div>
  <div id="content">
    <div class="empty-state"><h3>Select an entry from the sidebar</h3><p>Use ✓/✗ to approve or reject each draft entry</p></div>
  </div>
</div>
<script type="application/json" id="review-data">__DATA_PLACEHOLDER__</script>
<script>
const DATA = JSON.parse(document.getElementById('review-data').textContent);
const state = <<
  paper_id: DATA.paper_id,
  entries: <<>>,
  updated_at: new Date().toISOString()
>>;

// Initialize state from stored data
DATA.drafts.forEach(d => <<
  state.entries[d.entry_id] = <<
    status: d.status || 'draft',
    notes: '',
    reviewed_at: null
  >>;
>>);

let activeId = null;

function renderSidebar() <<
  const list = document.getElementById('entry-list');
  const counts = <<total:0,approved:0,rejected:0,flagged:0>>;
  let html = '';
  DATA.drafts.forEach(d => <<
    const s = state.entries[d.entry_id] || <<status:'draft'>>;
    counts.total++;
    if(s.status==='approved') counts.approved++;
    else if(s.status==='rejected') counts.rejected++;
    else if(s.status==='needs_review') counts.flagged++;
    const badge = s.status==='approved' ? '<span class="badge badge-ok">approved</span>' :
                  s.status==='rejected' ? '<span class="badge badge-flagged">rejected</span>' :
                  s.status==='needs_review' ? '<span class="badge badge-flagged">flagged</span>' :
                  '<span class="badge badge-draft">draft</span>';
    html += `<div class="entry-item$<<activeId===d.entry_id?' active':''>>" onclick="selectEntry('$<<d.entry_id>>')">
      <div class="eid">$<<badge>> $<<d.entry_id>></div>
      <div class="claim">$<<escapeHtml(d.main_claim||'(no claim)').substring(0,120)>></div>
    </div>`;
  >>);
  list.innerHTML = html;
  Object.entries(counts).forEach(([k,v]) => <<
    const el = document.getElementById('stat-'+k);
    if(el) el.textContent = v;
  >>);
>>

function selectEntry(eid) <<
  activeId = eid;
  renderSidebar();
  const d = DATA.drafts.find(x => x.entry_id === eid);
  if(!d) return;
  const s = state.entries[eid] || <<status:'draft',notes:''>>;
  document.getElementById('current-status').textContent = `Status: $<<s.status>>`;

  // Collect linked evidence
  const evIds = d.evidence_links || [];
  const evidence = evIds.map(eid => DATA.evidence_map[eid]).filter(Boolean);

  let fieldsHtml = '<table class="field-table">';
  const sf = d.structured_fields || <<>>;
  Object.entries(sf).forEach(([k,v]) => <<
    fieldsHtml += `<tr><td>$<<k>></td><td>$<<escapeHtml(String(v||''))>></td></tr>`;
  >>);
  fieldsHtml += '</table>';

  let evHtml = evidence.map(ev => <<
    const entities = (ev.entities||[]).map(e =>
      `<span class="entity-tag">$<<escapeHtml(e.name||'')>> ($<<e.type||'?'>>)</span>`
    ).join(' ');
    return `<div class="evidence-card">
      <div class="meta">$<<ev.evidence_id>> · $<<ev.evidence_type||'?'>> · $<<ev.section_type||'?'>></div>
      <div class="text">$<<escapeHtml(ev.source_text||'')>></div>
      <div style="margin-top:6px">$<<entities>></div>
    </div>`;
  >>).join('');

  document.getElementById('content').innerHTML = `
    <h3>$<<escapeHtml(d.main_claim||'(No claim)')>></h3>
    <div class="section"><h4>Task</h4><p>$<<d.task_type||'?'>></p></div>
    <div class="section"><h4>Structured Fields</h4>$<<fieldsHtml>></div>
    <div class="section"><h4>Linked Evidence ($<<evidence.length>>)</h4>$<<evHtml>></div>
    <div class="section"><h4>Review Notes</h4>
      <textarea id="notes" placeholder="Add notes..." onchange="saveNotes('$<<eid>>',this.value)">$<<escapeHtml(s.notes||'')>></textarea>
    </div>
  `;
>>

function reviewEntry(status) <<
  if(!activeId) return alert('Select an entry first');
  state.entries[activeId] = <<
    status: status,
    notes: document.getElementById('notes')?.value || '',
    reviewed_at: new Date().toISOString()
  >>;
  renderSidebar();
  document.getElementById('current-status').textContent = `Status: $<<status>>`;
>>

function saveNotes(eid, value) <<
  if(state.entries[eid]) state.entries[eid].notes = value;
>>

function exportState() <<
  state.updated_at = new Date().toISOString();
  const blob = new Blob([JSON.stringify(state, null, 2)], <<type:'application/json'>>);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'review_state.json';
  a.click();
>>

function escapeHtml(s) <<
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
>>

renderSidebar();
</script>
</body>
</html>"""


def build_review(paper_dir: Path, paper_id: str) -> str:
    drafts = load_jsonl(paper_dir / "06_draft" / "draft_entries.jsonl")
    evidence = load_jsonl(paper_dir / "03_evidence" / "evidence_units.jsonl")
    verifier = load_json(paper_dir / "07_verification" / "verifier_report.json")

    ev_map = {e["evidence_id"]: e for e in evidence}

    # Slim down evidence for embedding (keep only display-relevant fields)
    slim_evidence = {}
    for eid, eu in ev_map.items():
        slim_evidence[eid] = {
            "evidence_id": eid,
            "evidence_type": eu.get("evidence_type", ""),
            "source_text": eu.get("source_text", ""),
            "section_type": eu.get("section_type", ""),
            "entities": [{"name": e.get("name", ""), "type": e.get("type", "")}
                        for e in (eu.get("entities") or [])],
        }

    # Slim down drafts
    slim_drafts = []
    for d in drafts:
        slim_drafts.append({
            "entry_id": d["entry_id"],
            "pack_id": d.get("pack_id", ""),
            "task_type": d.get("task_type", ""),
            "main_claim": d.get("main_claim", ""),
            "structured_fields": d.get("structured_fields", {}),
            "evidence_links": d.get("evidence_links", []),
            "status": d.get("status", "draft"),
        })

    data = {
        "paper_id": paper_id,
        "drafts": slim_drafts,
        "evidence_map": slim_evidence,
        "verifier_summary": verifier.get("summary", {}),
    }

    json_data = json.dumps(data, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_data)
    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/review/build_review_html.py <paper_run_dir> [paper_id]")
        sys.exit(1)

    paper_dir = Path(sys.argv[1]).resolve()
    paper_id = sys.argv[2] if len(sys.argv) > 2 else paper_dir.parent.name

    html = build_review(paper_dir, paper_id)

    out_dir = paper_dir / "08_review"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "review.html"
    out_path.write_text(html, encoding="utf-8")

    drafts = load_jsonl(paper_dir / "06_draft" / "draft_entries.jsonl")
    evidence = load_jsonl(paper_dir / "03_evidence" / "evidence_units.jsonl")
    print(f"  Draft entries: {len(drafts)}")
    print(f"  Evidence units embedded: {len(evidence)}")
    print(f"  HTML size: {len(html)} chars")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
