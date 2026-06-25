const fs = require("fs");
const path = require("path");

const REQUIRED_FILES = [
  "01_raw_parse/raw_parse.json",
  "02_source/source_blocks.jsonl",
  "02_source/document_structure.json",
  "03_evidence/evidence_units.jsonl",
  "04_relations/evidence_relations.json",
  "05_context/context_packs.jsonl",
  "06_draft/draft_entries.jsonl",
  "07_verification/verifier_report.json",
  "08_review/review_state.json",
  "09_export/review_export.json",
  "logs/run_manifest.json",
];

function readJson(runDir, relativePath) {
  const filePath = path.join(runDir, relativePath);
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function readJsonl(runDir, relativePath) {
  const filePath = path.join(runDir, relativePath);
  const text = fs.readFileSync(filePath, "utf8").trim();
  if (!text) return [];
  return text.split(/\r?\n/).map((line, index) => {
    try {
      return JSON.parse(line);
    } catch (error) {
      throw new Error(`${relativePath}:${index + 1}: ${error.message}`);
    }
  });
}

function requireFiles(runDir) {
  for (const relativePath of REQUIRED_FILES) {
    const filePath = path.join(runDir, relativePath);
    if (!fs.existsSync(filePath)) {
      throw new Error(`missing required file ${relativePath}`);
    }
  }
}

function indexBy(rows, key, label) {
  const result = new Map();
  for (const row of rows) {
    const value = row[key];
    if (!value) throw new Error(`${label} row missing ${key}`);
    if (result.has(value)) throw new Error(`duplicate ${label} id ${value}`);
    result.set(value, row);
  }
  return result;
}

function validateRun(runDir) {
  requireFiles(runDir);

  readJson(runDir, "01_raw_parse/raw_parse.json");
  readJson(runDir, "02_source/document_structure.json");
  readJson(runDir, "04_relations/evidence_relations.json");
  readJson(runDir, "07_verification/verifier_report.json");
  readJson(runDir, "08_review/review_state.json");
  readJson(runDir, "logs/run_manifest.json");

  const sourceBlocks = readJsonl(runDir, "02_source/source_blocks.jsonl");
  const evidenceUnits = readJsonl(runDir, "03_evidence/evidence_units.jsonl");
  const contextPacks = readJsonl(runDir, "05_context/context_packs.jsonl");
  const draftEntries = readJsonl(runDir, "06_draft/draft_entries.jsonl");
  const reviewExport = readJson(runDir, "09_export/review_export.json");

  const sourceById = indexBy(sourceBlocks, "block_id", "source_block");
  const evidenceById = indexBy(evidenceUnits, "evidence_id", "evidence");
  const packById = indexBy(contextPacks, "pack_id", "context_pack");

  const evidenceToSource = {};
  for (const evidence of evidenceUnits) {
    const blockId = evidence.source && evidence.source.block_id;
    if (!blockId) throw new Error(`evidence ${evidence.evidence_id} missing source.block_id`);
    if (!sourceById.has(blockId)) {
      throw new Error(`evidence ${evidence.evidence_id} references missing source block ${blockId}`);
    }
    evidenceToSource[evidence.evidence_id] = blockId;
  }

  for (const pack of contextPacks) {
    for (const evidenceId of [
      ...(pack.anchor_evidence_ids || []),
      ...(pack.related_evidence_ids || []),
    ]) {
      if (!evidenceById.has(evidenceId)) {
        throw new Error(`context pack ${pack.pack_id} references missing evidence ${evidenceId}`);
      }
    }
    for (const blockId of pack.source_block_ids || []) {
      if (!sourceById.has(blockId)) {
        throw new Error(`context pack ${pack.pack_id} references missing source block ${blockId}`);
      }
    }
  }

  const draftToEvidence = {};
  for (const draft of draftEntries) {
    if (!packById.has(draft.pack_id)) {
      throw new Error(`draft ${draft.entry_id} references missing context pack ${draft.pack_id}`);
    }
    const linkedEvidence = [];
    for (const link of draft.evidence_links || []) {
      if (!evidenceById.has(link.evidence_id)) {
        throw new Error(`draft ${draft.entry_id} references missing evidence ${link.evidence_id}`);
      }
      linkedEvidence.push(link.evidence_id);
    }
    draftToEvidence[draft.entry_id] = [...new Set(linkedEvidence)];
  }

  for (const entry of reviewExport.reviewed_entries || []) {
    for (const evidenceId of entry.evidence_ids || []) {
      if (!evidenceById.has(evidenceId)) {
        throw new Error(`review export entry ${entry.entry_id} references missing evidence ${evidenceId}`);
      }
    }
  }

  return {
    ok: true,
    counts: {
      source_blocks: sourceBlocks.length,
      evidence: evidenceUnits.length,
      context_packs: contextPacks.length,
      draft_entries: draftEntries.length,
      reviewed_entries: (reviewExport.reviewed_entries || []).length,
    },
    trace: {
      draft_to_evidence: draftToEvidence,
      evidence_to_source: evidenceToSource,
    },
  };
}

function main() {
  const runDir = process.argv[2] || path.join("runs", "mock_paper_001");
  const result = validateRun(runDir);
  console.log("mock run validation ok");
  console.log(JSON.stringify(result.counts, null, 2));
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

module.exports = { validateRun };
