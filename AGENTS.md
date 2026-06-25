# AGENTS.md

本文件是 V2 项目的 agent 工作入口规则。

## 必读入口

开始任何 V2 工作前，先读：

```text
_project/00_START_HERE.md
```

然后按顺序读：

```text
_project/STATUS.md
_project/TASKS.md
_project/DECISIONS.md
_project/AGENT_RULES.md
_project/QUALITY_GATES.md
_project/ARCHITECTURE.md
```

## 工作边界

默认只在本目录内工作：

```text
v2_lit_review/
```

除非用户明确要求，不要修改旧项目代码、脚本、流程、测试或文档。

## 完成后更新

每次任务完成后更新：

```text
_project/STATUS.md
_project/TASKS.md
_project/CHANGELOG.md
_project/HANDOFF.md
```

如果产生新决策，更新：

```text
_project/DECISIONS.md
```

如果发现新风险，更新：

```text
_project/RISK_REGISTER.md
```

## 核心优先级

```text
稳定性 > 效率 > 成本
```

不要为了节省 API 成本牺牲结构稳定、证据追溯、错误可发现和人工可审核。
