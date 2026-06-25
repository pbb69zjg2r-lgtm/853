# Handoff

更新时间：2026-06-26

## 当前状态

V2 项目已建立隔离目录和项目管理层。

当前仍处于设计和项目组织阶段。最小目录骨架、contracts 样板、mock run 样例、mock source normalizer 和最小 mock 校验脚本已生成，但尚未实现真实业务 pipeline。

项目管理正文统一维护在 `_project/`，根目录的 `PROJECT_STATUS.md`、`DECISIONS.md`、`NEXT_STEPS.md` 仅作为兼容入口。

根目录已新增 `AGENTS.md`，用于提示后续 agent 开工前先读 `_project/00_START_HERE.md`。

如需交给另一个 AI / agent，请让它先读 `_project/AI_HANDOFF_PROMPT.md`。

## 当前目录

```text
D:\codex新\v2_lit_review
```

## 已完成

- 保存完整设计确认稿。
- 创建项目入口 README。
- 创建 `_project/` 管理层。
- 明确关键决策、任务、规则、质量门、风险清单。
- 生成最小目录骨架。
- 编写 contracts 样板。
- 生成 `runs/mock_paper_001/` mock 样例。
- 写入最小可追溯链路：`DE001 -> E001/E002 -> SB001/SB002`。
- 已临时验证 mock JSON/JSONL 可解析，引用链路连通。
- 已实现 `src/validation/validate_mock_run.js`。
- 已实现 `tests/validate_mock_run.test.js`。
- 已验证测试和 CLI 校验通过。
- 已创建另一台电脑 agent 任务：`_project/agent_tasks/TASK_DICTIONARIES_V1.md`。
- 已实现 `src/parsing/normalize_mock_raw_parse.js` 和测试，用于明确 `raw_parse -> source_blocks/document_structure` 边界。

## 下一步建议

下一步建议先等待或并行跟进另一台电脑 agent 的字典设计任务；本机可以继续讨论 MinerU adapter 的真实输入输出边界，不要和字典任务产生冲突。

当前校验脚本已经检查：

```text
1. 必需阶段文件存在。
2. JSON / JSONL 可解析。
3. draft_entries 引用的 evidence_id 存在。
4. evidence_units 引用的 source_block_id 存在。
5. review_export 引用的 draft/evidence 可追溯。
```

先不要接入真实 MinerU 或 LLM。

## 注意事项

- V2 位于旧仓库内，但应保持隔离。
- 不要默认修改旧项目。
- 不要一开始接入真实 LLM。
- 先用 mock 文件链路验证 contracts 和阶段输入输出。
- 成本判断优先级是：稳定性 > 效率 > 成本。
- 低耦合架构原则见 `_project/ARCHITECTURE.md`。

## 给下一个 agent 的开工提示

先读：

```text
_project/00_START_HERE.md
_project/STATUS.md
_project/TASKS.md
_project/DECISIONS.md
_project/AGENT_RULES.md
```

然后向用户确认是否开始生成最小骨架。
