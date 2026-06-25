const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const { validateRun } = require("../src/validation/validate_mock_run");

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function writeJsonl(filePath, rows) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`, "utf8");
}

function makeInvalidRun() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "v2-invalid-run-"));
  writeJson(path.join(dir, "01_raw_parse/raw_parse.json"), { paper_id: "invalid" });
  writeJsonl(path.join(dir, "02_source/source_blocks.jsonl"), [
    { block_id: "SB001", paper_id: "invalid", text: "Source text." },
  ]);
  writeJson(path.join(dir, "02_source/document_structure.json"), { paper_id: "invalid" });
  writeJsonl(path.join(dir, "03_evidence/evidence_units.jsonl"), [
    { evidence_id: "E001", source: { block_id: "SB001" }, evidence_text: "Source text." },
  ]);
  writeJson(path.join(dir, "04_relations/evidence_relations.json"), { relations: [] });
  writeJsonl(path.join(dir, "05_context/context_packs.jsonl"), [
    {
      pack_id: "CP001",
      anchor_evidence_ids: ["E001"],
      related_evidence_ids: [],
      source_block_ids: ["SB001"],
    },
  ]);
  writeJsonl(path.join(dir, "06_draft/draft_entries.jsonl"), [
    {
      entry_id: "DE001",
      pack_id: "CP001",
      evidence_links: [{ evidence_id: "E_MISSING", field_path: "main_claim" }],
    },
  ]);
  writeJson(path.join(dir, "07_verification/verifier_report.json"), { entry_reports: [] });
  writeJson(path.join(dir, "08_review/review_state.json"), { decisions: [] });
  writeJson(path.join(dir, "09_export/review_export.json"), {
    reviewed_entries: [{ entry_id: "FE001", evidence_ids: ["E001"] }],
  });
  writeJson(path.join(dir, "logs/run_manifest.json"), { run_id: "invalid" });
  return dir;
}

function testValidMockRun() {
  const runDir = path.join(__dirname, "..", "runs", "mock_paper_001");
  const result = validateRun(runDir);
  assert.deepStrictEqual(result.counts, {
    source_blocks: 2,
    evidence: 2,
    context_packs: 1,
    draft_entries: 1,
    reviewed_entries: 1,
  });
  assert.strictEqual(result.trace.draft_to_evidence.DE001.length, 2);
  assert.deepStrictEqual(result.trace.evidence_to_source.E001, "SB001");
}

function testRejectsMissingEvidenceLink() {
  const runDir = makeInvalidRun();
  assert.throws(
    () => validateRun(runDir),
    /draft DE001 references missing evidence E_MISSING/
  );
}

testValidMockRun();
testRejectsMissingEvidenceLink();
console.log("validate_mock_run tests passed");
