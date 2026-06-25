function padId(prefix, number) {
  return `${prefix}${String(number).padStart(3, "0")}`;
}

function normalizeRawParse(rawParse) {
  if (!rawParse || !Array.isArray(rawParse.pages)) {
    throw new Error("raw_parse must contain pages array");
  }

  const sourceBlocks = [];
  const sectionsByTitle = new Map();
  let cursor = 0;
  let blockCounter = 1;

  for (const page of rawParse.pages) {
    for (const rawBlock of page.blocks || []) {
      const text = rawBlock.text || "";
      const blockId = padId("SB", blockCounter++);
      const sourceBlock = {
        schema_version: rawParse.schema_version,
        contract_version: rawParse.contract_version,
        paper_id: rawParse.paper_id,
        block_id: blockId,
        source_raw_block_id: rawBlock.block_id || null,
        page: page.page,
        section: rawBlock.section || "Unknown",
        text,
        char_start: cursor,
        char_end: cursor + text.length,
      };
      sourceBlocks.push(sourceBlock);

      const sectionTitle = sourceBlock.section;
      if (!sectionsByTitle.has(sectionTitle)) {
        sectionsByTitle.set(sectionTitle, {
          section_id: padId("SEC", sectionsByTitle.size + 1),
          title: sectionTitle,
          page_start: page.page,
          page_end: page.page,
          source_block_ids: [],
        });
      }
      const section = sectionsByTitle.get(sectionTitle);
      section.page_start = Math.min(section.page_start, page.page);
      section.page_end = Math.max(section.page_end, page.page);
      section.source_block_ids.push(blockId);

      cursor += text.length + 1;
    }
  }

  return {
    sourceBlocks,
    documentStructure: {
      schema_version: rawParse.schema_version,
      contract_version: rawParse.contract_version,
      paper_id: rawParse.paper_id,
      title: rawParse.title || null,
      sections: [...sectionsByTitle.values()],
      figures: [],
      tables: [],
    },
  };
}

module.exports = { normalizeRawParse };
