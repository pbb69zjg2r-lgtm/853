# Start Here

更新时间：2026-06-26

这是 V2 项目的项目管理入口。任何 agent、任何电脑、任何新线程继续本项目时，都应先读本文件。

## 必读顺序

开工前按顺序读取：

```text
1. _project/00_START_HERE.md
2. _project/STATUS.md
3. _project/TASKS.md
4. _project/DECISIONS.md
5. _project/AGENT_RULES.md
6. _project/QUALITY_GATES.md
7. _project/ARCHITECTURE.md
```

如果需要了解完整设计，再读：

```text
V2_design_confirmed.md
```

## 当前项目位置

```text
D:\codex新\v2_lit_review
```

本目录是 V2 重写项目的隔离工作区。它在旧项目仓库内，但不应和旧项目流程混用。

## 当前阶段

```text
设计确认完成。
项目管理层正在建立。
代码骨架尚未生成。
```

## 当前最重要原则

```text
稳定性 > 效率 > 成本
```

执行含义：

- 稳定性优先：结构稳定、字段稳定、证据可追溯、错误可发现、人工可审核。
- 效率第二：减少人工重复劳动、减少规则复杂度、减少维护连锁改动。
- 成本第三：在稳定和效率满足后，再控制 API 次数、token 和缓存。

## 工作边界

默认只在以下目录工作：

```text
v2_lit_review/
```

除非用户明确要求，不要修改旧项目代码、旧项目脚本或旧项目流程。

## 每次任务闭环

开工前：

```text
1. 读必读文件。
2. 看 TASKS.md 当前任务。
3. 明确本次只做什么。
```

工作中：

```text
1. 只改任务范围内的文件。
2. 不引入无关重构。
3. 不把 V2 接入旧项目。
```

完成后：

```text
1. 更新 STATUS.md。
2. 更新 TASKS.md。
3. 更新 CHANGELOG.md。
4. 更新 HANDOFF.md。
5. 必要时更新 DECISIONS.md。
```

## 当前下一步

当前建议下一步：

```text
生成 contracts-first 最小项目骨架。
```

但在生成骨架前，应先确认用户是否要现在开始。
