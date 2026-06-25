# Decisions

更新时间：2026-06-26

本文记录 V2 已确认的关键决策。完整论证见根目录 `V2_design_confirmed.md`。

## D001 项目定位

V2 是以证据为中心、以人工审核为最终确认环节的文献结构化抽取系统。

目标：

- 证据可追溯。
- 字段可校验。
- 错误可发现。
- 人工可审核。
- 最终输出可复查。

## D002 不兼容旧格式

V2 不兼容旧项目输出格式。

旧项目的 `extraction_package.json` 不再作为最终主输出。

V2 最终主输出：

```text
review_export.json
```

## D003 主流程

阶段性确认的主流程：

```text
PDF
-> raw_parse
-> document_structure
-> evidence_units
-> evidence_relations
-> context_packs
-> draft_entries
-> verifier_report
-> review_workspace
-> review_export
```

## D004 contracts-first

字段、字典、阶段输入输出集中定义在 contracts 中。

原则：

- prompt 不单独定义真实字段。
- 校验代码不单独维护枚举。
- 审核界面不单独维护字段名。
- 所有阶段以 contracts 为准。

## D005 人工不直接审核 JSON

人工审核者不直接看或编辑 JSON。

人工审核入口：

```text
review_workspace
```

审核完成后导出：

```text
review_export.json
```

## D006 atomic_claims 不作为第一版独立层

第一版不生成独立 `atomic_claims.jsonl`。

第一版在 `verifier_report` 中保留轻量：

```text
claim_checks
```

## D007 第一版 demo 范围

第一版 demo 只跑一篇论文。

必须包含：

```text
contracts
evidence_units
context_packs
draft_entries
verifier_report
review_workspace
review_export
```

第一版不做：

- 数据库。
- 多用户。
- 多 OCR 自动切换。
- 跨论文知识图谱。
- 完整 Web 平台。

## D008 成本优先级

成本判断优先级：

```text
稳定性 > 效率 > 成本
```

判断顺序：

```text
第一问：稳不稳？
第二问：是否提高效率？
第三问：贵不贵？
```

便宜但不稳定的 LLM 调用不要。

更贵但能减少错误、减少人工审核负担、减少规则复杂度，并且可校验、可追溯的调用可以接受。

## D009 大模型使用边界

程序负责：

- ID。
- schema。
- 路径。
- JSON / JSONL 读写。
- 枚举校验。
- 必填字段校验。
- evidence/source 引用校验。
- review_export 结构校验。

大模型负责：

- 证据候选发现。
- 语义分类。
- draft entry 生成。
- 字段决策理由。
- 不确定性说明。
- 高风险逻辑检查。
- 冲突解释。
- 人工审核问题生成。

## D010 旧项目隔离

`v2_lit_review/` 是 V2 隔离目录。

旧项目不应依赖本目录。

V2 后续代码、contracts、runs、review_app 都应放在本目录下。
