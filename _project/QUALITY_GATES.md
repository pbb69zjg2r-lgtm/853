# Quality Gates

更新时间：2026-06-26

本文定义 V2 项目的质量门。任何实现都应满足这些基本要求。

## Gate 1: 项目边界

通过条件：

- 所有 V2 文件位于 `v2_lit_review/`。
- 旧项目不依赖 V2。
- V2 不修改旧项目行为。

## Gate 2: contracts-first

通过条件：

- 字段定义在 contracts。
- 字典定义在 contracts。
- 阶段输入输出定义在 contracts。
- prompt、校验、审核界面不各自维护字段真相。

## Gate 3: 阶段输入输出

每个阶段必须明确：

```text
输入文件
输出文件
生成者
消费者
失败记录
可信级别
是否允许人工修改
```

## Gate 4: 证据追溯

通过条件：

- `draft_entry` 能追溯到 `evidence_id`。
- `evidence_id` 能追溯到 `source_block_id`。
- `source_block_id` 能追溯到页码、章节或原文位置。

## Gate 5: 人工审核

通过条件：

- 人工不直接审核原始 JSON。
- 人工通过 `review_workspace` 查看候选结论、证据、风险和审核问题。
- 人工操作能导出 `review_export.json`。

## Gate 6: 最终输出

通过条件：

- `review_export.json` 只保存人工审核后的可信结果和必要追溯。
- `review_export.json` 不复制完整中间文件。
- 后续分析默认只信 `review_export.json`。

## Gate 7: LLM 调用

新增 LLM 调用必须满足：

```text
输出可校验
输出可追溯
失败可记录
可缓存
能提升稳定性或效率
```

## Gate 8: 最小 demo

第一版 demo 通过条件：

```text
1. 一篇论文能生成 evidence_units。
2. evidence_units 能生成 context_packs。
3. context_packs 能生成 draft_entries。
4. draft_entries 能进入 verifier_report。
5. verifier_report 能生成 review_workspace。
6. 人工审核状态能导出 review_export.json。
7. review_export 能追溯回 evidence 和 source block。
```

## Gate 9: 低耦合架构

通过条件：

- 每个阶段只读固定输入，写固定输出。
- 阶段之间通过文件契约通信。
- 后续阶段不得反向修改前序输出。
- 外部工具格式通过 adapter 隔离。
- 关键输出包含 `schema_version` 和 `contract_version`。
- 字段、字典、枚举只从 contracts 获取。
- 新增功能不破坏既有 stage contracts。
