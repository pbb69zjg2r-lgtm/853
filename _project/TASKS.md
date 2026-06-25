# Tasks

更新时间：2026-06-26

## In Progress

暂无。

## Pending

- 另一台电脑 agent 执行：`_project/agent_tasks/TASK_DICTIONARIES_V1.md`。
- 评估是否把 mock 校验扩展为通用 stage contract validator。
- 讨论真实文献前的最小 pipeline 范围。
- 讨论 MinerU adapter 的真实输入输出边界。
- 再评估是否接入真实 MinerU 和 LLM。

## Done

- 创建 V2 隔离目录：`v2_lit_review/`。
- 保存完整设计确认稿：`V2_design_confirmed.md`。
- 创建基础入口说明：`README.md`。
- 创建早期状态文件：`PROJECT_STATUS.md`、`DECISIONS.md`、`NEXT_STEPS.md`。
- 建立 `_project/` 项目管理层。
- 将根目录旧管理文件改为指向 `_project/` 的兼容入口。
- 生成 V2 最小目录骨架。
- 编写 `contracts/dictionaries.yaml` 样板。
- 编写 `contracts/fields.yaml` 样板。
- 编写 `contracts/output_contracts.yaml` 样板。
- 编写 `contracts/stage_contracts.yaml`，定义每步输入输出。
- 设计 mock run 目录样例：`runs/mock_paper_001/`。
- 用 mock 数据跑通文件链路：`DE001 -> E001/E002 -> SB001/SB002`。
- 编写最小 mock 链路校验脚本：`src/validation/validate_mock_run.js`。
- 编写校验脚本测试：`tests/validate_mock_run.test.js`。
- 验证校验脚本通过测试和 CLI 运行。
- 编写 mock raw_parse normalizer：`src/parsing/normalize_mock_raw_parse.js`。
- 编写 normalizer 测试：`tests/normalize_mock_raw_parse.test.js`。

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

如果任务产生新的设计决策，还必须更新：

```text
_project/DECISIONS.md
```
