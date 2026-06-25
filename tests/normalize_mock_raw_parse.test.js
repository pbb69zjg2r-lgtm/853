const assert = require("assert");

const { normalizeRawParse } = require("../src/parsing/normalize_mock_raw_parse");

function testConvertsRawBlocksToSourceBlocks() {
  const rawParse = {
    schema_version: "0.1.0",
    contract_version: "2026-06-26",
    paper_id: "paper_a",
    pages: [
      {
        page: 1,
        blocks: [
          { block_id: "raw_1", section: "Results", text: "First result." },
          { block_id: "raw_2", section: "Results", text: "Second result." },
        ],
      },
    ],
  };

  const result = normalizeRawParse(rawParse);

  assert.deepStrictEqual(result.sourceBlocks, [
    {
      schema_version: "0.1.0",
      contract_version: "2026-06-26",
      paper_id: "paper_a",
      block_id: "SB001",
      source_raw_block_id: "raw_1",
      page: 1,
      section: "Results",
      text: "First result.",
      char_start: 0,
      char_end: 13,
    },
    {
      schema_version: "0.1.0",
      contract_version: "2026-06-26",
      paper_id: "paper_a",
      block_id: "SB002",
      source_raw_block_id: "raw_2",
      page: 1,
      section: "Results",
      text: "Second result.",
      char_start: 14,
      char_end: 28,
    },
  ]);
}

function testBuildsDocumentStructureFromSections() {
  const rawParse = {
    schema_version: "0.1.0",
    contract_version: "2026-06-26",
    paper_id: "paper_b",
    title: "Mock title",
    pages: [
      { page: 1, blocks: [{ block_id: "raw_1", section: "Methods", text: "Method text." }] },
      { page: 2, blocks: [{ block_id: "raw_2", section: "Results", text: "Result text." }] },
    ],
  };

  const result = normalizeRawParse(rawParse);

  assert.deepStrictEqual(result.documentStructure, {
    schema_version: "0.1.0",
    contract_version: "2026-06-26",
    paper_id: "paper_b",
    title: "Mock title",
    sections: [
      {
        section_id: "SEC001",
        title: "Methods",
        page_start: 1,
        page_end: 1,
        source_block_ids: ["SB001"],
      },
      {
        section_id: "SEC002",
        title: "Results",
        page_start: 2,
        page_end: 2,
        source_block_ids: ["SB002"],
      },
    ],
    figures: [],
    tables: [],
  });
}

testConvertsRawBlocksToSourceBlocks();
testBuildsDocumentStructureFromSections();
console.log("normalize_mock_raw_parse tests passed");
