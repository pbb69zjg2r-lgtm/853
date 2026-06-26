# Tasks

更新时间：2026-06-26

## In Progress

暂无。

## Pending

- 人工审核 real_paper_001 的 66 条 draft entries
- 审核完成后跑 `build_export.py` 生成最终 review_export.json
- 跑更多论文测试泛化性
- 评估是否把 mock 校验扩展为通用 stage contract validator

## Done

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
