# Changelog

## 2026-06-26

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

### Context

建立项目管理层的原因：

- 避免依赖 agent 对话记忆。
- 避免状态、决策、任务散落。
- 方便换电脑、换线程、换 agent 继续。
- 明确 V2 与旧项目隔离。
