# Agent Rules

更新时间：2026-06-26

## 1. 开工必读

每次继续 V2 项目前，先读：

```text
_project/00_START_HERE.md
_project/STATUS.md
_project/TASKS.md
_project/DECISIONS.md
_project/AGENT_RULES.md
_project/QUALITY_GATES.md
```

## 2. 工作边界

默认只在以下目录工作：

```text
v2_lit_review/
```

除非用户明确要求，不要修改旧项目代码、脚本、流程、测试或文档。

## 3. 旧项目隔离

不得默认把 V2 接入旧项目。

不得让旧项目依赖 V2 目录。

不得为了 V2 修改旧项目行为。

## 4. 修改原则

- 先明确本次任务范围。
- 只改任务范围内的文件。
- 不做无关重构。
- 不把讨论阶段内容直接写成实现，除非用户确认开始实现。
- 字段、字典、阶段契约必须优先写入 contracts。

## 5. 完成后必须更新

每次任务完成后更新：

```text
_project/STATUS.md
_project/TASKS.md
_project/CHANGELOG.md
_project/HANDOFF.md
```

如果出现新决策，更新：

```text
_project/DECISIONS.md
```

如果发现新风险，更新：

```text
_project/RISK_REGISTER.md
```

## 6. 大模型使用原则

优先级：

```text
稳定性 > 效率 > 成本
```

新增 LLM 步骤前必须说明：

```text
1. 它解决什么问题？
2. 程序规则为什么不够？
3. 输出如何校验？
4. 失败时如何处理？
5. 是否能缓存？
6. 是否减少人工审核负担或维护复杂度？
```

## 7. 禁止事项

- 禁止让人工直接审核原始 JSON 作为正式流程。
- 禁止在 prompt、代码、审核界面各自维护一套字段。
- 禁止让未审核的 `draft_entries` 进入最终可信输出。
- 禁止把 `review_export.json` 做成所有中间文件的大合集。
