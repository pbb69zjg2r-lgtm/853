# AI Handoff Prompt

创建时间：2026-06-26

本文件用于把 V2 项目交给另一个 AI / agent 接手。新 agent 不应依赖之前对话记忆，应从项目文件恢复上下文。

## 给新 AI 的开工指令

请先阅读以下文件，按顺序执行：

```text
v2_lit_review/AGENTS.md
v2_lit_review/_project/00_START_HERE.md
v2_lit_review/_project/STATUS.md
v2_lit_review/_project/TASKS.md
v2_lit_review/_project/DECISIONS.md
v2_lit_review/_project/ARCHITECTURE.md
v2_lit_review/_project/QUALITY_GATES.md
v2_lit_review/_project/HANDOFF.md
```

如果需要完整背景，再阅读：

```text
v2_lit_review/V2_design_confirmed.md
```

阅读后，先不要写代码。

请先用中文输出以下内容：

```text
1. 当前项目状态
2. 已确认的关键原则
3. 当前不能做什么
4. 下一步建议
5. 你准备修改哪些文件
```

必须等用户确认后，再开始修改文件。

## 当前项目状态摘要

V2 项目当前位于：

```text
v2_lit_review/
```

当前已经完成：

```text
1. V2 设计确认稿
2. 项目管理层 _project/
3. contracts-first 最小目录骨架
4. contracts 样板
5. mock_paper_001 样例运行目录
6. mock run 校验脚本
7. mock raw_parse -> source_blocks/document_structure normalizer
8. 给另一台电脑 agent 的字典设计任务
```

当前尚未完成：

```text
1. 真实 MinerU adapter
2. 真实 PDF 解析链路
3. 真实 LLM 抽取
4. 真实 review_workspace
5. 真实 review_export
```

## 核心原则

优先级：

```text
稳定性 > 效率 > 成本
```

架构原则：

```text
contracts-first
stage-by-file
adapter isolation
schema versioning
append-only process outputs
no backward mutation
review_export as trusted source
```

## 当前禁止事项

未经用户确认，不要做以下事情：

```text
1. 不要修改旧项目代码。
2. 不要把 V2 接入旧项目。
3. 不要接入真实 LLM。
4. 不要继续扩展 mock 样例。
5. 不要新增复杂知识图谱或 ontology。
6. 不要让人工直接审核 JSON。
7. 不要把 draft_entries 当成最终可信输出。
8. 不要修改 contracts/dictionaries.yaml，除非当前任务就是字典设计。
```

## 当前推荐下一步

当前建议停止继续扩展 mock。

下一步应进入真实解析链路的最小范围：

```text
PDF / MinerU output
-> raw_parse.json
-> source_blocks.jsonl
-> document_structure.json
```

边界：

```text
只做到解析和 source_blocks。
不进入 evidence extraction。
不进入 LLM。
不进入 draft_entries。
不进入 review_export。
```

在真正写 MinerU adapter 前，应先确认 MinerU 实际输出结构，包括但不限于：

```text
content_list.json
full.md
images/
tables/
layout/
middle files
```

如果没有真实 MinerU 输出样例，不要凭空猜 adapter。

## 如果任务是设计字典

如果用户让你设计字典，请执行：

```text
v2_lit_review/_project/agent_tasks/TASK_DICTIONARIES_V1.md
```

并且只修改该任务允许的文件。

## 如果任务是继续代码实现

开始实现前必须：

```text
1. 说明本次任务范围。
2. 说明会修改哪些文件。
3. 说明不会修改哪些文件。
4. 按 TDD：先写失败测试，再写最小实现。
5. 完成后运行测试。
6. 更新 _project/STATUS.md、TASKS.md、CHANGELOG.md、HANDOFF.md。
```

## 开工回复模板

新 AI 读完上述文件后，应先回复：

```text
我已阅读 V2 项目入口文件。

当前状态：
...

关键原则：
...

当前禁止事项：
...

建议下一步：
...

我计划修改的文件：
...

请确认是否开始。
```
