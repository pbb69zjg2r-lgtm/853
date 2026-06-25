# TASK: Dictionaries V1

创建时间：2026-06-26

任务对象：另一台电脑上的 agent

## 任务目标

设计 V2 第一版字典文件：

```text
v2_lit_review/contracts/dictionaries.yaml
```

本任务只负责字典设计，不负责代码实现、流程实现、UI 实现或真实文献抽取。

## 必读文件

开始前按顺序读取：

```text
v2_lit_review/AGENTS.md
v2_lit_review/_project/00_START_HERE.md
v2_lit_review/_project/DECISIONS.md
v2_lit_review/_project/ARCHITECTURE.md
v2_lit_review/_project/QUALITY_GATES.md
v2_lit_review/contracts/dictionaries.yaml
v2_lit_review/contracts/fields.yaml
v2_lit_review/contracts/stage_contracts.yaml
```

如需完整背景，再读：

```text
v2_lit_review/V2_design_confirmed.md
```

## 允许修改

本任务允许修改：

```text
v2_lit_review/contracts/dictionaries.yaml
v2_lit_review/_project/STATUS.md
v2_lit_review/_project/TASKS.md
v2_lit_review/_project/CHANGELOG.md
v2_lit_review/_project/HANDOFF.md
```

如果发现新的关键设计决策，可以修改：

```text
v2_lit_review/_project/DECISIONS.md
```

如果发现新的风险，可以修改：

```text
v2_lit_review/_project/RISK_REGISTER.md
```

## 禁止修改

本任务禁止修改：

```text
v2_lit_review/src/
v2_lit_review/tests/
v2_lit_review/runs/
v2_lit_review/review_app/
v2_lit_review/prompts/
v2_lit_review/contracts/fields.yaml
v2_lit_review/contracts/stage_contracts.yaml
v2_lit_review/contracts/output_contracts.yaml
```

除非用户明确要求，不要修改旧项目任何文件。

## 核心原则

```text
稳定性 > 效率 > 成本
```

字典设计要服务第一版 demo，不要做完整知识图谱。

优先保证：

- 字典稳定。
- 字典不臃肿。
- 字典能被程序校验。
- 字典能支持人工审核。
- 后续扩展时不需要大改整体结构。

## 第一版建议设计的字典

请评估并设计以下字典。

必要字典：

```text
evidence_type
entity_type
intervention_type
measurement_type
result_direction
claim_strength
relation_type
relation_status
draft_entry_status
review_decision
reviewed_evidence_decision
recommended_action
alignment_status
missing_context_type
risk_flag
support_level
llm_profile
```

可以考虑但不一定进入第一版：

```text
tissue_type
model_system
species
assay_type
statistics_type
uncertainty_type
review_question_type
```

## 第一版不建议做

不要在第一版设计以下复杂字典：

```text
完整疾病 ontology
完整细胞类型 ontology
完整分子通路 ontology
完整药物靶点字典
跨论文知识图谱关系全集
复杂因果图谱类型
完整机制网络
完整 MeSH / GO / KEGG 体系
```

如果认为某个复杂字典未来需要，先写到 `notes` 或注释说明，不要强行进入第一版主字典。

## 字典格式要求

保持 YAML 简洁。

每个字典建议包含：

```text
key:
  - value_a
  - value_b
```

如果需要分组，可以使用：

```text
key:
  core:
    - value_a
  advanced:
    - value_b
```

不要引入过深层级。

## 必须保留

保留文件顶部：

```text
schema_version
contract_version
description
```

如修改字典结构，应保持这三个字段存在。

## 完成后必须更新

完成后更新：

```text
v2_lit_review/_project/STATUS.md
v2_lit_review/_project/TASKS.md
v2_lit_review/_project/CHANGELOG.md
v2_lit_review/_project/HANDOFF.md
```

更新内容至少包括：

- 本次改了哪些字典。
- 哪些字典进入第一版。
- 哪些字典被暂缓。
- 下一步建议。

## 验收标准

任务完成后应满足：

```text
1. dictionaries.yaml 仍然是合法 YAML。
2. schema_version、contract_version、description 保留。
3. 第一版必要字典都有明确值。
4. 没有引入完整知识图谱或过重 ontology。
5. 字典值能服务 evidence_units、relations、draft_entries、verifier_report、review_export。
6. 项目管理文件已更新。
```

## 交付说明

完成后请给出简短报告：

```text
1. 修改了哪些字典。
2. 哪些字典暂缓。
3. 是否发现和 fields.yaml / stage_contracts.yaml 的不一致。
4. 下一步建议。
```
