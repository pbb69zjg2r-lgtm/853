# Architecture

更新时间：2026-06-26

本文记录 V2 的低耦合架构原则。目标是减少单点改动对整体流程的影响，便于后续升级。

## 核心原则

```text
每个步骤只通过文件契约连接。
不直接依赖别的步骤内部实现。
字段、字典、状态只从 contracts 来。
```

## 1. contracts-first

字段、字典、枚举、阶段输入输出都必须集中定义在：

```text
contracts/
```

其他模块只能引用 contracts，不能各自维护字段真相。

禁止：

```text
prompt 里一套字段
代码里一套字段
审核界面里一套字段
```

## 2. stage-by-file

每个阶段只读固定输入，写固定输出。

示例：

```text
evidence 阶段：
输入：source_blocks.jsonl + contracts
输出：evidence_units.jsonl

draft 阶段：
输入：context_packs.jsonl + evidence_units.jsonl + contracts
输出：draft_entries.jsonl
```

阶段之间通过文件通信，不直接调用对方内部实现。

## 3. adapter isolation

外部工具或第三方格式必须通过 adapter 隔离。

示例：

```text
MinerU raw_parse
-> parsing adapter
-> source_blocks.jsonl
```

后续阶段只认 `source_blocks.jsonl`，不直接依赖 MinerU 原始格式。

如果以后替换 OCR，只改 adapter，不改 evidence、draft、review 等后续模块。

## 4. schema versioning

关键输出文件应包含版本信息：

```text
schema_version
contract_version
```

升级字段或结构时，不应悄悄改变旧格式。

如果需要升级，应明确：

```text
evidence_units v1
evidence_units v2
```

必要时写迁移器或转换器，而不是让旧数据直接失效。

## 5. append-only process outputs

过程文件尽量追加或生成新文件，不直接覆盖上游结果。

原则：

```text
上一步输出可以被下一步读取。
下一步不能反向修改上一步输出。
```

如果需要修正，应生成新的审核状态、修正记录或新版本输出。

## 6. no backward mutation

后续阶段不得直接修改前序阶段的原始输出。

例如：

- `verifier_report` 只能报告 `draft_entries` 的问题，不能直接改写 `draft_entries`。
- `review_workspace` 记录人工操作，不能直接覆盖 `evidence_units`。
- `review_export` 保存最终审核结果，但不反向修改中间文件。

## 7. review_export as trusted source

最终可信数据只来自：

```text
review_export.json
```

后续分析默认不信：

```text
draft_entries.jsonl
verifier_report.json
model raw outputs
```

这些只能作为追溯和审核辅助。

## 阶段边界

```text
raw_parse
  保存 OCR/解析原始结果。

source_blocks
  统一原文最小引用单位。

document_structure
  保存论文章节、图表、结构地图。

evidence_units
  保存证据节点，不生成最终结论。

evidence_relations
  保存证据之间关系，不改证据本身。

context_packs
  组织模型输入，不改证据和结论。

draft_entries
  生成候选结构化条目，不进入最终可信输出。

verifier_report
  报告问题，不修改 draft_entries。

review_workspace
  给人工审核者查看和操作，记录审核状态。

review_export
  保存人工审核后的最终可信结果。
```

## 每个阶段必须回答的问题

每个阶段设计前必须回答：

```text
1. 我读什么文件？
2. 我写什么文件？
3. 我依赖 contracts 的哪部分？
4. 我是否允许改上一步输出？
5. 我的输出谁会读？
6. 我失败时写到哪里？
7. 我的输出是不是可信数据？
```

如果回答不清楚，说明阶段边界不清楚，未来会产生耦合。

## 升级策略

升级时优先遵守：

```text
改字段 -> 只改 contracts
改 prompt -> 不改输出结构
改 OCR -> 只改 parsing adapter
改审核页面 -> 不改 review_export
改 LLM 模型 -> 不改 stage contracts
加新关系 -> 不改 evidence_units 主结构
加新分析 -> 只读 review_export，不碰旧流程
```

## 禁止事项

- 禁止阶段之间直接依赖内部函数作为主接口。
- 禁止让后续阶段反向修改前序输出。
- 禁止在 prompt、代码、审核界面各自维护字段真相。
- 禁止把未审核候选结果当成最终可信数据。
- 禁止为了新增功能破坏既有阶段契约。
