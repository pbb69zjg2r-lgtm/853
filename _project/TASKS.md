# Tasks

更新时间：2026-06-26

## In Progress

暂无。

## Pending

- ~~Build `src/core/contracts.py` to load `contracts/*.yaml` from one place.~~
- ~~Replace the old hard-coded validator with a contracts-driven validator.~~
- ~~Rewrite `prompts/evidence_extraction.txt` and `src/evidence/extract_evidence.py` to emit the confirmed `evidence_unit` structure.~~
- ~~Rewrite `src/context/build_context_packs.py` so it no longer requires `04_relations/evidence_relations.json` in the pre-review flow.~~
- ~~Rewrite `src/export/build_export.py` so `review_export.json` is generated only after all entries are approved/rejected.~~
- ~~Rewrite `src/drafting/generate_drafts.py` with new prompt and schema.~~
- ~~Rewrite `src/verification/generate_report.py` with new field checks.~~
- ~~Update review HTML to reference new evidence_unit fields (source_trace.quote, polarity, experimental_model).~~

- 人工审核 real_paper_001 的 11 条 + real_paper_002 的 5 条 draft entries
- 审核完成后跑 `build_export.py` 生成最终 review_export.json
- 跑更多论文测试泛化性
- 评估是否把 mock 校验扩展为通用 stage contract validator
- 考虑只在 review 页面展示 real_paper_* 论文（过滤 mock_）

## Done

- **去耦合审计（20 问题全部修复）** — 4 HIGH + 12 MEDIUM + 4 LOW，contracts 路径统一、枚举值字典引用、提示词动态注入、死代码清理、review.html 审核字段完善
- **format_prompt() 动态注入** — 提示词中 `{{DETECTION_CATEGORY}}` 等占位符运行时替换为字典值，改字典自动同步提示词
- 真实的 LLM 验证通过：S3 20 units (4 batches) + S6 5 drafts mock

- **Built `src/core/contracts.py`** — unified contracts loader API: `get_dictionary()`, `get_required_fields()`, `get_stage_outputs()`, `get_enum_field_values()`, `load_contracts()`, etc. Works with all 4 contracts YAML files.
- **Built `src/validation/validate_stage.py`** — contracts-driven validator. Validates JSON/JSONL files against field schemas (required fields, enum values, types, nested objects, array items, forbidden fields). Supports single file, single stage, or `--all` stages.
- **Rewrote `prompts/evidence_extraction.txt`** — new prompt with 7 evidence types, decision tree for each, INCLUDES/EXCLUDES rules, type-specific `structured_fields`, 15 new fields, verbatim quote requirement.
- **Rewrote `src/evidence/extract_evidence.py`** — batch source blocks by section, call DeepSeek API, parse JSONL response, auto-fill evidence_id/paper_id/review_coverage/normalization_status, validate against contracts, mock mode support.
- **Rewrote `src/evidence/consensus_evidence.py`** — Jaccard similarity graph matching, Union-Find connected components, min-runs filtering, entity union deduplication, canonical unit selection.
- **Rewrote `src/context/build_context_packs.py`** — context packs WITHOUT relations dependency. Groups by evidence_type → entity overlap (Union-Find) → discriminative entity type merge (assay_method/drug/disease/metabolite). Anchor selection by confidence + entity count + statistics. Missing context detection.
- **Rewrote `prompts/draft_generation.txt`** — Chinese prompt for draft entry synthesis from context packs. 7 type-specific structured_fields, evidence_links, experimental_model_summary, review_questions, uncertainty_map.
- **Rewrote `src/drafting/generate_drafts.py`** — LLM batch generation (max 4 packs/batch, by evidence_type). Parse failure auto-retry per pack. Mock mode support.
- **Rewrote `src/verification/generate_report.py`** — pure-logic quality check. Entry completeness, cross-entry overlap detection, evidence coverage gaps, schema validation, actionable recommendations.
- **Rewrote `src/export/build_export.py`** — trusted export builder. Only includes approved/rejected entries. Excludes draft/pending. Validates forbidden fields (normalized_entity_id, graph_edges, etc.). Builds review_audit with coverage summary.
- **Updated `src/review/review.html`** — fixed legacy field references: `source_text` → `source_trace.quote`, `task_type` → `evidence_type`, added polarity and experimental_model display.
- Added `_project/LEGACY_MAP.md` to separate current contracts-first truth from legacy runnable code and old run outputs.

- 创建 V2 隔离目录
- 保存完整设计确认稿
- 创建项目入口和 `_project/` 管理层
- 明确关键决策、任务、规则、质量门、风险清单
- 生成最小目录骨架
- 编写 contracts 样板
- 生成 mock run 样例
- 实现 mock 校验脚本
- 实现 mock normalizer
- 克隆 3 个参考项目并分析字典设计模式
- 实现解析链路 3 脚本（run_mineru / build_raw_parse / build_source）
- 用 real_paper_001 跑通完整解析链路
- 设计完整字典体系（dictionaries.yaml v0.2.0 + fields.yaml 更新）
- 实现 evidence_units 提取脚本（extract_evidence.py）
- 用 DeepSeek-chat 跑通 real_paper_001 证据提取
- 实现多数投票共识脚本（consensus_evidence.py）
- 迭代 prompt（决策树 + INCLUDES/EXCLUDES + 边界示例）
- 实现 evidence_relations 规则引擎（build_relations.py）
- 实现 context_packs 构建（build_context_packs.py）
- 实现 draft_entries LLM 生成（generate_drafts.py）
- 实现 verifier_report 质量核查（generate_report.py）
- 实现 review_workspace server + HTML（review_server.py + review.html）
- 实现 review_export 最终导出（build_export.py）
- 修复跨 batch evidence_id 重复 bug
- 修复 review HTML JSON 嵌入转义问题，改为 server-based 架构
- 将 context_packs 从 1:1 映射改为 relation-graph BFS 聚类（max_size=20，66→11 packs）
- 将 draft_generation prompt 重写为中文
- 迭代聚类粒度（max_size=8→17, 12→13, 20→11），消除前 4 条 draft entries 主题重叠问题
- 将 review_workspace 从静态 HTML 改为 server-based 架构
- 推送完整 pipeline 到 GitHub (pbb69zjg2r-lgtm/853)
- 用 real_paper_002 (HSF1/SPI1 巨噬细胞分化) 跑通全流程（35 consensus, 5 drafts, 5/5 OK）
- 升级 review_workspace 为多论文模式（自动发现 + 下拉切换 + 按论文独立保存）
- 切换到 DeepSeek 官方直连 API（弃用代理 rawchat.cn/codex）
- 修复审核页面空白 bug（mock_paper_001 旧格式 review_state 兼容）
- 修复 selectEntry 变量遮蔽 bug（evIds.forEach 遮蔽 eid 参数）

## Blocked

暂无。

## Task Rules

每个任务完成后必须更新：

```text
_project/STATUS.md
_project/TASKS.md
_project/CHANGELOG.md
_project/HANDOFF.md
```
