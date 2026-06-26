# Changelog

## 2026-06-26 (Session 4)

### Added

- **real_paper_002** 全流程跑通：HSF1/SPI1/PU.1 巨噬细胞分化论文（35 consensus → 5 drafts, 5/5 OK）
- **多论文审核服务器**：自动发现 `runs/` 下所有论文，论文选择下拉框，按论文独立保存审核状态
- **`/api/papers`** 端点：返回所有可用论文列表及 draft 数量

### Changed

- **切换到 DeepSeek 官方直连**：`OPENAI_BASE_URL=https://api.deepseek.com`，弃用代理 `rawchat.cn/codex`
- **审核 UI**：侧边栏顶部新增论文切换器，切换时自动保存当前审核状态，localStorage 记住上次选择的论文

### Fixed

- 审核页面空白 bug：`mock_paper_001` 旧格式 `review_state.json` 缺少 `entries` 字段导致 JS 崩溃
- `selectEntry()` 变量遮蔽 bug：`evIds.forEach(eid => ...)` 遮蔽了函数参数 `eid`，导致 notes 保存到错误 entry

---

## 2026-06-26 (Session 3)

### Changed

- **context_packs**：从 1:1 映射（每证据一包）改为基于关系图的 BFS 连通分量聚类（max_size=20），66 证据单元 → 11 主题 packs
- **draft_generation prompt**：从英文重写为中文，要求 main_claim 用中文、实体保留英文、忠实原文
- **draft entries**：从 66 条减至 11 条，消除主题重叠（用户反馈"前四条都在说同一件事"）
- **聚类粒度迭代**：max_size=8→17 条, 12→13 条, 20→11 条（当前版本）
- **review_workspace**：从静态内联 HTML 改为 client-server 架构（Python HTTP server + 独立 HTML 前端），参考旧项目 `review_server.py`
- **draft 生成稳定性**：按 task_type 分批（每批最多 4 packs），解析失败时自动逐 pack 重试
- **Pipeline 推送到 GitHub**：`git@github-pbb:pbb69zjg2r-lgtm/853.git`

### Fixed

- SSH 推送权限：`github.com`→`github-pbb` host alias（id_ed25519_pbb 密钥）

---

## 2026-06-26 (Session 2)

### Added

- 实现 `src/evidence/consensus_evidence.py` — 多轮 LLM 提取多数投票共识（Jaccard 匹配 + ≥2 票）
- 迭代 `prompts/evidence_extraction.txt` — 新增决策树、INCLUDES/EXCLUDES、边界示例（例 4: Western blot 非 detection_method）
- 实现 `src/relations/build_relations.py` — 纯规则引擎，实体重叠 + 类型组合 → 8 种关系，max 10 出边/节点
- 实现 `src/context/build_context_packs.py` — 证据+关系+源文打包为 LLM 上下文
- 实现 `src/drafting/generate_drafts.py` — LLM 批量生成结构化 draft entries
- 新增 `prompts/draft_generation.txt` — 草稿生成 prompt
- 实现 `src/verification/generate_report.py` — 证据链接、字段完整性、实体覆盖检查
- 实现 `src/review/review_server.py` — Python HTTP review server (client-server 架构)
- 新增 `src/review/review.html` — 审核界面（左侧列表+右侧详情+审批/导出）
- 实现 `src/export/build_export.py` — 最终 review_export.json 生成
- real_paper_001 完整 pipeline 跑通：66 consensus units → 480 relations → 66 drafts → review workspace

### Fixed

- 修复 `extract_evidence.py` 跨 batch evidence_id 重复 bug（parse_llm_output 需 id_offset）
- 修复 review HTML JSON 嵌入转义问题，从静态内联改为 server-based API 动态加载

### Changed

- evidence_units 从单次 LLM 提取改为 3 轮多数投票（temperature=0），提高稳定性

---

## 2026-06-26 (Session 1)

### Added

- 创建 `_project/` 项目管理层。
- 新增 `00_START_HERE.md`，作为 agent 开工入口。
- 新增 `STATUS.md`，记录当前项目状态。
- 新增 `TASKS.md`，记录任务状态。
- 新增 `DECISIONS.md`，集中记录已确认决策。
- 新增 `CHANGELOG.md`，记录项目变更。
- 新增 `AGENT_RULES.md`，规定 agent 工作边界。
- 新增 `HANDOFF.md`，记录交接信息。
- 新增 `QUALITY_GATES.md`，记录质量门。
- 新增 `RISK_REGISTER.md`，记录风险清单。
- 将根目录 `PROJECT_STATUS.md`、`DECISIONS.md`、`NEXT_STEPS.md` 改为指向 `_project/` 的兼容入口，避免维护两份正文。
- 新增根目录 `AGENTS.md`，作为后续 agent 的工作入口规则。
- 新增 `_project/ARCHITECTURE.md`，记录低耦合架构原则。
- 更新 `QUALITY_GATES.md`，加入低耦合架构质量门。
- 创建 V2 最小目录骨架：`contracts/`、`prompts/`、`src/`、`runs/`、`review_app/`、`tests/`、`docs/`。
- 新增 contracts 样板：`dictionaries.yaml`、`fields.yaml`、`output_contracts.yaml`、`stage_contracts.yaml`。
- 为暂时为空的关键目录添加 `.gitkeep`。
- 更新根目录 `README.md`，使入口状态与当前骨架状态一致。
- 新增 mock run 样例目录：`runs/mock_paper_001/`。
- 新增 mock 阶段文件：`raw_parse.json`、`source_blocks.jsonl`、`document_structure.json`、`evidence_units.jsonl`、`evidence_relations.json`、`context_packs.jsonl`、`draft_entries.jsonl`、`verifier_report.json`、`review.html`、`review_state.json`、`review_export.json`。
- 新增 mock run 日志文件：`logs/failures.jsonl`、`logs/run_manifest.json`。
- 临时验证 mock run：JSON/JSONL 可解析，`DE001 -> E001/E002 -> SB001/SB002` 引用链连通。
- 新增最小 mock run 校验脚本：`src/validation/validate_mock_run.js`。
- 新增校验脚本测试：`tests/validate_mock_run.test.js`。
- 验证测试通过，并通过 CLI 校验 `runs/mock_paper_001`。
- 新增 agent 任务文件：`_project/agent_tasks/TASK_DICTIONARIES_V1.md`，用于另一台电脑设计 V1 字典。
- 新增 mock raw_parse normalizer：`src/parsing/normalize_mock_raw_parse.js`。
- 新增 normalizer 测试：`tests/normalize_mock_raw_parse.test.js`。
- 验证 normalizer 测试、mock run 测试和 CLI 校验均通过。
- 新增 `_project/AI_HANDOFF_PROMPT.md`，用于把项目交给另一个 AI 时恢复上下文和约束边界。

- 克隆 3 个参考项目到 `D:\融合版\`：langextract、mistral-ocr-pipeline、EvidenceNet-code。
- 分析参考项目字典设计模式，产出 6 条设计规则，写入 AI 对话记忆。
- 实现 `src/parsing/run_mineru.py`：MinerU Precision Extract API 调用，含 submit-then-poll 轮询、SSL 证书验证绕过（中国网络环境）。
- 实现 `src/parsing/build_raw_parse.py`：content_list.json → raw_parse.json 标准化，含完整 24 种 MinerU BlockType 枚举和确定性 keep/drop 分类。
- 实现 `src/parsing/build_source.py`：raw_parse.json → source_blocks.jsonl + document_structure.json，含 section 检测和 paragraph/figure/table 三分类。
- 用真实论文 real_paper_001 跑通完整解析链路：248 blocks → 123 kept → 91 paragraphs + 32 figures + 0 tables，14 sections。
- 设计完整字典体系 `contracts/dictionaries.yaml` v0.2.0（16 个字典，参考 EvidenceNet + Mistral-OCR 模式）。
- 更新 `contracts/fields.yaml`：source_block 新增 section_type/figure_number；evidence_unit 完全重写为线粒体热医学领域字段。
- 实现 `src/evidence/extract_evidence.py`：source_blocks → evidence_units（直接 HTTP 调 DeepSeek，零第三方依赖）。
- 新增 `prompts/evidence_extraction.txt`：证据提取 prompt 模板。
- 用 DeepSeek-chat 跑通 real_paper_001：27 groups → 5 batches → 63 evidence units（mechanism_pathway:30, detection_method:18, thermogenesis_modulation:13, disease_association:2）。

### Changed

- 项目目录从 `D:\codex新\v2_lit_review` 迁移到 `D:\融合版\853`。
- `_project/HANDOFF.md` 目录路径已更新。
- `build_source.py` 新增 section_type 和 figure_number。
- `evidence_unit` schema 从通用 PICO 改为线粒体热医学领域专用。

### Context

建立项目管理层的原因：

- 避免依赖 agent 对话记忆。
- 避免状态、决策、任务散落。
- 方便换电脑、换线程、换 agent 继续。
- 明确 V2 与旧项目隔离。
