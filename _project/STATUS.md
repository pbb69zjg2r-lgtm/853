# Status

更新时间：2026-06-26

## 阶段

```text
阶段：V2 设计确认完成，项目管理层已建立
代码状态：已生成最小目录骨架，并实现最小 mock run 校验脚本
运行状态：已生成 mock run 样例，尚未运行真实 demo
可信输出：尚无真实 review_export.json；已有 mock review_export.json 样例
```

## 项目目录

```text
D:\codex新\v2_lit_review
```

## 已完成

- 已确认 V2 以证据为中心、以人工审核为最终确认环节。
- 已确认 V2 不兼容旧格式。
- 已确认最终主输出是人工审核后的 `review_export.json`。
- 已确认人工不直接审核 JSON，而是通过 `review_workspace` 审核。
- 已确认第一版 demo 只跑一篇论文。
- 已确认使用 contracts-first 目录结构。
- 已确认成本判断优先级：稳定性 > 效率 > 成本。
- 已保存完整设计确认稿：`V2_design_confirmed.md`。
- 已建立项目管理目录：`_project/`。
- 已将根目录旧管理文件改为兼容入口，正文统一维护在 `_project/`。
- 已新增 `AGENTS.md`，作为后续 agent 的工作入口规则。
- 已生成最小项目目录骨架。
- 已编写 contracts 样板：`dictionaries.yaml`、`fields.yaml`、`output_contracts.yaml`、`stage_contracts.yaml`。
- 已生成 `runs/mock_paper_001/` mock 样例运行目录。
- 已写入一条最小可追溯 mock 链路：`DE001 -> E001/E002 -> SB001/SB002`。
- 已临时验证 mock JSON/JSONL 可解析，引用链路连通。
- 已实现 `src/validation/validate_mock_run.js`。
- 已新增 `tests/validate_mock_run.test.js`。
- 已验证 mock run 校验脚本可通过测试和 CLI 运行。
- 已创建给另一台电脑 agent 的字典设计任务：`_project/agent_tasks/TASK_DICTIONARIES_V1.md`。

## 尚未开始

- 尚未实现文件链路。
- 尚未接入 MinerU。
- 尚未接入真实 LLM。
- 尚未生成真实 `review_workspace`。
- 尚未生成真实 `review_export.json`。

## 当前未定

- 第一版 demo 使用哪一篇 PDF。
- 第一版 contracts 字段范围是否需要继续细化。
- 等待另一台电脑 agent 完成 V1 字典设计。

## 当前建议

下一步建议把 mock 校验扩展为更通用的 stage contract validator，或先讨论是否需要进入真实文献前的最小 pipeline。不要一开始接入真实 LLM。
