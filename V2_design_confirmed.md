# V2 重写设计讨论确认稿

记录时间：2026-06-25

状态：阶段性确认稿。本文只记录已经讨论并阶段性确认的设计方向，不等于最终实现方案。后续每个模块还需要继续逐项确认。

## 1. 项目总目标

V2 项目的核心目标是重写一个以“证据”为中心、以“人工审核”为最终确认环节的文献结构化抽取系统。

V2 要解决的主要问题：

- 字典和字段经常修改，旧项目中修改一次会牵动提示词、校验、导出、审核界面等多处，容易引入新 bug。
- 各阶段耦合过重，一个阶段的格式变化会影响后续多个阶段。
- 旧流程偏向“先生成最终结构化结论”，但用户真正需要的是“可审核、可追溯、可修正”的结构化证据。
- 大模型应主要用于语义理解、证据发现、关系判断、字段解释、审核问题生成等它更擅长的部分。
- 程序应主要负责稳定结构、格式校验、ID 校验、字典约束、引用一致性、流程编排和错误报告。

V2 第一版不追求一次性做成完整知识图谱平台，也不追求复杂预测、自动入库、多 OCR 自动切换或大型 UI 系统。

## 2. 输出格式取舍

阶段性确认：

- V2 不兼容旧格式。
- 旧项目的 `extraction_package.json` 不再作为最终主输出。
- V2 最终主输出以人工审核后的 `review_export.json` 为中心。
- 中间过程可以保留多个过程文件，但最终可信数据必须来自人工审核后的导出。

不兼容旧格式的意义：

- 字段、证据、关系、审核状态可以重新设计，不被旧结构限制。
- 可以减少为了兼容旧格式而产生的转换层、补丁层和重复字段。
- 代价是旧脚本、旧分析代码、旧导入流程需要重写或废弃。

## 3. 四个项目分别吸收什么

### 3.1 当前项目

保留或吸收：

- 人工审核优先的思路。
- `AtlasEntry` 这类“候选结论 + 证据 + 审核辅助信息”的思想。
- `review_assist`、不确定性说明、字段决策理由、审核问题生成等设计方向。
- L1-L4 校验分层思想。
- MinerU 接入经验。

不继承或谨慎继承：

- 大脚本内多阶段强耦合。
- 字典、提示词、代码里各维护一份枚举。
- 通过补丁不断修补字段变化的方式。
- 阶段间格式没有清晰契约的问题。

### 3.2 mistral-ocr-pipeline

保留或吸收：

- 每篇文献独立目录。
- 中间产物可恢复、可断点续跑。
- `failures.jsonl` 记录失败原因。
- API 重试、限速、错误记录。
- 结构化配置和 schema registry 思路。

不继承或谨慎继承：

- 一篇论文一行的扁平表格作为主数据结构。
- 深度合并掩盖字段冲突。
- CSV/Parquet 作为第一主输出。
- 为 OCR 流程引入过多与抽取无关的复杂度。

### 3.3 google/langextract

保留或吸收：

- 抽取结果必须尽量对齐原文。
- 使用 `char_start` / `char_end` 或等价机制定位证据。
- 抽取对象与原文片段之间要有可验证引用。
- 通过示例约束模型输出。
- 对齐失败要显式记录，而不是假装成功。

不继承或谨慎继承：

- 完整 provider 插件框架。
- 默认多轮复杂抽取。
- URL 抓取、通用框架能力等当前项目暂不需要的部分。

### 3.4 EvidenceNet-code

保留或吸收：

- 先抽取证据节点，再形成结构化结论。
- `EvidenceNode` / `evidence_units` 思想。
- 证据质量评分。
- 证据之间的支持、冲突、重复、扩展、因果链等关系。
- 证据去重和证据级审核。

不继承或谨慎继承：

- 完整知识图谱。
- TarKG 实体链接。
- 药物-靶点预测。
- 复杂图算法和重型机器学习依赖。
- 一开始就做跨论文大规模关系网络。

## 4. V2 总流程

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

说明：

- `raw_parse` 保存解析原始结果。
- `document_structure` 表示论文结构地图。
- `evidence_units` 是 V2 的核心证据层。
- `evidence_relations` 表示证据之间的关系。
- `context_packs` 用来给大模型提供小而准的上下文。
- `draft_entries` 是候选结构化条目。
- `verifier_report` 负责记录校验、冲突、风险、轻量 claim 检查和审核提示。
- `review_workspace` 是给人工审核者看的可读审核入口。
- `review_export` 是人工审核后的最终机器可读主输出。

## 5. 统一字典与字段中心

阶段性确认：V2 必须有统一的 contracts 层。

建议文件：

```text
contracts/dictionaries.yaml
contracts/fields.yaml
contracts/output_contracts.yaml
```

原则：

- 字典只在一个地方定义。
- 字段只在一个地方定义。
- 阶段输入输出契约只在一个地方定义。
- 提示词、校验程序、导出程序、审核界面都读取 contracts。
- 不允许提示词里一套枚举、代码里一套枚举、校验里又一套枚举。

这个设计的目的不是让项目更复杂，而是减少后续改字段、改字典时的连锁修改。

## 6. PDF 解析与原文结构

阶段性确认：

- V2 第一版默认使用 MinerU。
- Mistral OCR 暂时只作为未来 adapter，不作为第一版主流程。
- 第一版不做多 OCR 自动切换。

建议输出：

```text
raw_parse.json
source_blocks.jsonl
document_structure.json
figure_index.json
table_index.json
```

定位：

- `raw_parse.json` 保存 MinerU 原始解析结果。
- `source_blocks.jsonl` 是最小可引用原文单位。
- `document_structure.json` 是论文结构地图。
- `figure_index.json` / `table_index.json` 保存图表索引。
- `source_chunks` 可以作为模型输入，但不能作为唯一证据来源。

## 7. 证据节点 evidence_units

阶段性确认：V2 应先抽取证据节点，再生成结构化结论。

建议输出文件：

```text
evidence_units.jsonl
```

建议字段：

```text
evidence_id
paper_id
source.block_id
source.chunk_id
source.page
source.section
source.char_start
source.char_end
evidence_text
evidence_type
entities
condition
measurement
result
statistics
quality
review_hint
```

第一版最低要求：

- 必须有 `evidence_id`。
- 必须能追溯到 source block 或 chunk。
- 必须有页码或章节信息，至少二者之一。
- 必须保留 `evidence_text`。
- 必须标注 `evidence_type`。
- 必须有 `quality.confidence` 或等价置信度字段。

原文对齐规则：

- 优先尝试 `char_start` / `char_end`。
- 如果无法稳定对齐，必须记录 `alignment_status: failed`。
- 不能在对齐失败时伪造成功定位。

职责边界：

- 大模型负责发现候选证据、理解证据语义、生成初步字段。
- 程序负责校验 ID、字典值、字段格式和原文对齐。
- 人工审核负责最终确认、修改或拒绝证据。

## 8. 证据关系 evidence_relations

阶段性确认：证据关系应在 V2 初始数据模型中预留并实现基础能力，避免后续再加时大改结构。

建议输出文件：

```text
evidence_relations.json
```

核心关系类型：

```text
supports
contradicts
duplicates
limits
context_for
```

高级关系类型：

```text
extends
replicates
refines
causal_chain
```

客观取舍：

- 把这些关系类型放进数据模型，不会必然导致项目臃肿。
- 真正会导致臃肿的是：每种关系单独一套 prompt、单独一套文件、单独一套校验、单独一套 UI。
- 第一版应把高级关系作为候选判断和人工审核提示，不应直接当成自动确认事实。

建议关系对象：

```text
relation_id
source_evidence_id
target_evidence_id
relation_type
relation_group
status
scope
basis
confidence
reason
verification_status
review_required
details
```

建议 `status` 值：

```text
candidate
verified
rejected
needs_review
human_confirmed
```

实现原则：

- 不为每种关系类型建立独立文件。
- 不在第一版为每种高级关系设计大量专属字段。
- 统一使用 `details` 保存少量可选补充信息。
- 高级关系默认 `needs_review` 或 `candidate`。
- 关系判断必须能追溯到具体证据文本和判断理由。

防止复杂度失控：

- 不做全量两两证据比较。
- 优先只在同一个 `context_pack` 内比较。
- 只比较实体、干预、测量、结果相近的证据。
- 每个证据只保留 top-k 候选关系。
- 跨论文高级关系第一版不自动生成。

## 9. 大模型智能使用原则

阶段性确认：使用大模型智能必须划算。

可以优先交给大模型的部分：

- 证据候选发现。
- `candidate_claims` 生成。
- 字段决策理由 `field_decisions`。
- 不确定性说明 `uncertainty_map`。
- schema 缺口发现 `schema_gap_notes`。
- 人工审核问题生成 `review_questions`。
- 逻辑冲突解释和 reviewer 提示。
- chunk 相关性排序。
- 章节语义识别。
- 证据关系候选判断。

不应交给大模型主导的部分：

- JSON 格式稳定性。
- ID 唯一性。
- 字典枚举合法性。
- 必填字段检查。
- 文件路径和阶段产物管理。
- 是否引用了不存在的 evidence_id。
- 是否输出了 contracts 不允许的字段。

成本判断原则：

- 如果为了使用大模型而要写比纯程序更多的胶水代码、补丁代码和异常处理，而且效果没有明显提升，就不应使用大模型。
- 如果大模型能明显减少规则数量，并且错误能被 schema、程序校验、人工审核兜住，可以使用。
- 如果大模型效果更好但需要更多程序支撑，必须单独拿出来讨论，不能默认接受。

## 10. 上下文包 context_packs

阶段性确认：V2 第一版采用 evidence-centered context_packs。

`context_pack` 是大模型输入包，不是最终输出。它的作用是把与当前判断有关的证据、原文、章节背景和图表说明组织成一小包，让大模型在有限上下文里做更准确的判断。

基本定位：

```text
source_blocks / evidence_units / evidence_relations
        ↓
context_packs
        ↓
draft_entries / field_decisions / review_questions
```

要解决的问题：

- 避免模型只看到孤立证据句。
- 避免直接把整篇论文或大量 chunks 塞给模型。
- 降低无关上下文干扰。
- 降低 token 成本。
- 保留模型判断依据，方便人工审核和错误追踪。

不能完全解决的问题：

- MinerU 没解析到的页面。
- OCR 错误。
- `evidence_units` 阶段漏掉的关键证据。
- 分组规则本身把相关证据分错。
- 论文原文没有写清楚的信息。

建议输出文件：

```text
context_packs.jsonl
```

建议字段：

```text
pack_id
paper_id
task_type
anchor_evidence_ids
related_evidence_ids
source_block_ids
section_scope
topic
entities
pack_text
token_estimate
relevance_reason
quality_flags
missing_context
expected_output
```

第一版最低要求：

- 必须有 `pack_id`。
- 必须引用 `paper_id`。
- 必须有 `task_type`。
- 必须有 `anchor_evidence_ids`。
- 必须能追溯到 `source_block_ids`。
- 必须有 `expected_output`，限制模型当前任务。
- 如果上下文不足，必须写入 `missing_context`。

上下文补充机制：

- 每个核心证据自动带上前后若干 `source_blocks`。
- 带上章节标题、子章节标题，必要时带简短章节摘要。
- 如果证据来自图表附近，带上 figure/table caption。
- 如果模型发现缺少实验对象、干预、剂量、时间、组织、指标等信息，写入 `missing_context`。
- `missing_context` 严重时，不直接生成可信 `draft_entry`，而是进入补包或人工审核提示。

复杂度控制：

- 第一版不做复杂动态检索系统。
- 第一版不做全量两两证据比较。
- 优先在同一篇论文、同一章节或相邻章节内组包。
- 优先组合共享实体、干预、测量指标或结果方向相近的证据。
- 每个核心证据只保留有限数量的相关证据。

职责边界：

- 大模型可以参与判断哪些证据属于同一个科学问题。
- 大模型可以生成 `topic`、`relevance_reason` 和 `missing_context`。
- 程序负责生成 `pack_id`、控制 token 上限、检查 evidence_id 是否存在。
- 程序负责检查 `source_block_ids` 是否存在。
- 程序负责限制 `expected_output` 和阶段输入输出格式。

## 11. 候选结构化条目 draft_entries

阶段性确认：V2 第一版保留 `draft_entries`，但它只作为候选层，不作为最终可信事实层。

`draft_entry` 是大模型根据 `context_pack` 生成的一版候选结构化条目。它负责把多个证据组织成一个可审核的候选结论，并给出字段草稿、证据引用、不确定性和审核问题。

流程位置：

```text
context_packs
-> draft_entries
-> verifier_report
-> review_workspace
-> review_export
```

基本职责：

- 把多个 `evidence_units` 组织成一个候选结构化结论。
- 给每个关键字段提供证据引用。
- 标记不确定信息。
- 标记冲突信息。
- 标记上下文缺失。
- 生成给人工审核者的问题。

不承担的职责：

- 不做最终事实确认。
- 不做跨论文综合定论。
- 不替代人工审核。
- 不直接进入最终主输出。
- 不负责 ID、字段合法性和 contracts 合规性校验。

建议输出文件：

```text
draft_entries.jsonl
```

建议字段：

```text
entry_id
paper_id
pack_id
entry_type
main_claim
structured_fields
evidence_links
field_decisions
uncertainty_map
conflict_notes
missing_context
review_questions
model_trace
status
```

第一版最低要求：

- 必须有 `entry_id`。
- 必须引用 `paper_id`。
- 必须引用 `pack_id`。
- 必须有 `main_claim`。
- 必须有 `structured_fields`。
- 必须有 `evidence_links`。
- 必须有 `status`。
- 关键字段必须能追溯到 `evidence_id`。

大模型适合负责：

- 生成 `main_claim`。
- 初填 `structured_fields`。
- 生成 `field_decisions`。
- 生成 `uncertainty_map`。
- 生成 `conflict_notes`。
- 生成 `review_questions`。

程序必须负责：

- 生成或校验 `entry_id`。
- 检查 `paper_id` 是否存在。
- 检查 `pack_id` 是否存在。
- 检查 `evidence_id` 是否存在。
- 检查字段是否符合 contracts。
- 检查字典值是否合法。
- 限制 `status` 的可选值。

建议 `status`：

```text
draft
needs_verification
needs_review
rejected
human_confirmed
```

客观风险：

- 如果 `draft_entry` 设计得像最终输出，会回到旧项目“大模型直接生成最终结构，程序到处补漏洞”的问题。
- 如果 `draft_entry` 没有 `evidence_links`，人工审核时无法追溯。
- 如果 `draft_entry` 没有 `uncertainty_map` 和 `review_questions`，大模型的不确定性会被隐藏。
- 如果 `draft_entry` 可以直接进入 `review_export`，人工审核中心的原则会被削弱。

阶段性结论：

```text
draft_entries 是候选层。
每个 draft_entry 必须来自一个 context_pack。
每个关键字段必须能链接到 evidence_id。
不确定、冲突、缺失上下文必须显式记录。
draft_entry 不能直接进入最终输出，必须经过 verifier_report 和人工审核。
```

## 12. 轻量结论拆解 claim_checks

阶段性确认：V2 第一版不把 `atomic_claims` 作为独立主流程文件。

原因：

- 独立 `atomic_claims.jsonl` 会增加一层数据结构。
- 它会增加校验对象数量。
- 如果进入人工审核界面，会明显增加审核负担。
- 第一版的重点应是先稳定跑通证据、候选条目、校验报告和人工审核导出。

但完全删除“最小结论检查”也有风险：

- 复合 `draft_entry` 里可能混入过强推理。
- 模型可能把相关性写成因果。
- 模型可能把单个实验结果扩大成机制结论。
- 人工审核一整段结论时，可能漏掉其中某个小结论证据不足。

折中方案：

```text
第一版不生成独立 atomic_claims.jsonl。
第一版在 verifier_report 中保留轻量 claim_checks。
claim_checks 只用于质量控制和审核提示。
高风险 claim 才提示人工重点查看。
后续如果需要，再升级成独立 atomic_claims 层。
```

建议 `claim_checks` 字段：

```text
claim_text
source_entry_id
evidence_ids
support_level
risk_flags
reason
review_required
```

第一版最低要求：

- 只对高风险或复合型 `draft_entry` 做 claim 拆解。
- 不要求每个 `draft_entry` 都拆成完整 claim 列表。
- 不把 `claim_checks` 作为人工审核主对象。
- 不把 `claim_checks` 作为最终主输出。
- `claim_checks` 的作用是帮助 `verifier_report` 发现过度总结、证据不足和逻辑跳跃。

后续可升级条件：

- 如果真实跑文献后发现复合结论经常夹带错误推理。
- 如果人工审核者需要逐条确认小结论。
- 如果后续要做跨论文 claim 级分析或知识图谱。
- 如果 `review_export` 后续分析确实依赖 claim 粒度。

## 13. 校验报告 verifier_report

阶段性确认：V2 第一版必须有 `verifier_report`。

`verifier_report` 是候选条目进入人工审核前的质检报告。它不负责生成最终结论，也不替代人工审核。它的核心作用是把错误、风险、缺失上下文、证据不足和逻辑冲突暴露出来。

基本定位：

```text
draft_entries
-> verifier_report
-> review_workspace
-> review_export
```

主要职责：

- 把程序可以确定的硬错误拦下来。
- 把大模型不确定的地方标出来。
- 把证据不足、逻辑跳跃、冲突和上下文缺失写清楚。
- 生成给人工审核者的重点问题。
- 为人工审核队列提供排序依据。

不承担的职责：

- 不重新抽取整篇论文。
- 不重新生成一套结构化结论。
- 不自动修复所有问题。
- 不直接产生最终可信数据。
- 不替代人工审核。

建议输出文件：

```text
verifier_report.json
```

建议顶层结构：

```text
paper_id
generated_at
input_files
summary
entry_reports
global_issues
review_queue
```

建议每个 `entry_report` 字段：

```text
entry_id
pack_id
status
schema_checks
evidence_checks
logic_checks
conflict_checks
claim_checks
missing_context
review_questions
recommended_action
```

检查类别：

```text
schema_checks
evidence_checks
logic_checks
conflict_checks
claim_checks
review_questions
```

`schema_checks` 负责：

- 字段是否存在。
- 类型是否正确。
- 枚举是否合法。
- 必填字段是否缺失。
- 状态值是否合法。

`evidence_checks` 负责：

- `evidence_id` 是否存在。
- `source_block_id` 是否存在。
- 关键字段是否有证据支持。
- 证据文本是否能追溯。

`logic_checks` 负责：

- 是否把相关性写成因果。
- 是否把局部结果扩大成全身结论。
- 是否把动物实验扩大成人类治疗结论。
- 是否把表达变化直接写成功能改善。
- 是否存在明显过度总结。

`conflict_checks` 负责：

- 同一条目内部证据是否互相冲突。
- 相关 evidence 之间是否方向相反。
- 结论是否忽略限制条件。

`claim_checks` 负责：

- 对高风险或复合型 `draft_entry` 做轻量结论拆解。
- 检查每个小结论是否有证据支持。
- 发现证据不足、过度推理和逻辑跳跃。
- 不作为独立主流程文件。
- 不作为人工审核主对象。

建议 `recommended_action`：

```text
accept_for_review
needs_human_review
needs_context_retry
needs_evidence_fix
reject_before_review
```

说明：

- `accept_for_review` 只表示可以进入人工审核，不表示结论已经正确。
- `needs_context_retry` 表示上下文不足，需要重新补包。
- `needs_evidence_fix` 表示证据引用或证据抽取存在问题。
- `reject_before_review` 表示结构或证据错误严重，不建议进入人工审核。

程序负责：

- schema 校验。
- ID 存在性校验。
- 字段类型校验。
- 枚举合法性校验。
- 必填字段校验。
- 证据引用是否存在。
- `source_block` 是否存在。
- 状态值是否合法。
- 综合生成最终 `recommended_action`。

大模型适合辅助：

- 逻辑风险解释。
- 轻量 `claim_checks`。
- 冲突解释。
- 缺失上下文说明。
- 人工审核问题生成。
- `recommended_action` 的建议理由。

边界：

- 大模型不能单独决定最终 `recommended_action`。
- `verifier_report` 不能直接改写 `draft_entries`。
- `verifier_report` 只能报告问题和建议下一步动作。
- 最终可信数据仍然来自人工审核后的 `review_export`，但人工审核者不直接审核 JSON。

阶段性结论：

```text
verifier_report 是进入人工审核前的质检层。
它包含 schema_checks、evidence_checks、logic_checks、conflict_checks、claim_checks、review_questions。
程序负责硬校验，大模型负责语义风险解释。
verifier_report 不直接产生最终可信数据，它进入 review_workspace 供人工审核，最终可信数据来自 review_export。
```

## 14. 人工审核工作区 review_workspace

阶段性确认：人工不直接审核 JSON。

JSON / JSONL 是机器交换格式，不适合作为人工审核界面。人工审核者应该看到候选结论、证据原文、字段解释、风险提示和操作按钮，而不是直接编辑结构化 JSON。

基本定位：

```text
draft_entries
+ evidence_units
+ verifier_report
+ source_blocks
        ↓
review_workspace
        ↓
human_review
        ↓
review_export.json
```

`review_workspace` 是给人看的审核材料，不是最终主输出。最终可信机器输出仍然是 `review_export.json`。

第一版建议：

```text
采用本地 HTML 审核页面，或等价的可读审核包。
不做复杂登录系统。
不做数据库型多用户平台。
不要求人工直接编辑 JSON。
```

建议文件：

```text
review.html
review_state.json
review_export.json
```

其中：

- `review.html` 给人工查看和操作。
- `review_state.json` 保存审核过程中的临时状态。
- `review_export.json` 保存人工审核完成后的最终机器可读结果。

第一版审核界面至少应展示：

- 候选条目列表。
- 候选结论。
- 结构化字段。
- 字段对应证据。
- 证据原文。
- 页码、章节、source block 信息。
- `verifier_report` 风险提示。
- 缺失上下文说明。
- 人工审核问题。
- 修改备注。
- 审核决定。

第一版审核操作至少包括：

```text
接受
修改后接受
拒绝
需要复查
证据不足
上下文不足
```

重要原则：

- 人工看到的是可读页面或审核包。
- 后台保存的是结构化状态。
- 人工修改必须能回写到 `review_export.json`。
- `review_export.json` 不能由模型直接生成最终可信结果。
- 人工审核操作必须保留 `review_decisions` 或等价记录。

不建议第一版做：

- 完整用户登录系统。
- 数据库型多人协作平台。
- 复杂权限管理。
- 对所有中间文件做可视化。
- 让人工直接编辑原始 JSON。

阶段性结论：

```text
人工不直接审核 JSON。
review_workspace 是人工审核入口。
第一版采用本地 HTML 审核页面或等价可读审核包。
人工操作结果再导出 review_export.json。
review_export.json 是审核完成后的机器可读最终输出。
```

## 15. 最终审核导出 review_export

阶段性确认：`review_export.json` 是 V2 最终机器可读主输出。

`review_export.json` 不是给人工直接看的文件，而是给后续程序长期使用的可信数据文件。人工审核入口是 `review_workspace`，人工审核完成后的结果导出为 `review_export.json`。

主要用途：

- 后续统计分析。
- 跨论文比较。
- 知识库构建。
- 回滚复查。
- bug 定位。
- 再次导出 Excel、CSV 或报告。

不承担的职责：

- 不作为人工直接审核界面。
- 不复制所有中间文件。
- 不保存完整 PDF 文本。
- 不保存完整模型原始响应。
- 不把未审核的 `draft_entries` 当成可信结果。

建议输出文件：

```text
review_export.json
```

建议顶层结构：

```text
export_id
schema_version
project_id
paper_id
paper_metadata
created_at
review_status
source_files
reviewed_entries
reviewed_evidence
review_decisions
audit_log
export_summary
```

`paper_metadata` 建议字段：

```text
title
doi
pmid
authors
journal
year
pdf_file
```

`source_files` 建议引用：

```text
raw_parse
source_blocks
document_structure
evidence_units
evidence_relations
context_packs
draft_entries
verifier_report
review_state
```

说明：

- `source_files` 只保存引用路径或文件标识。
- 不把中间文件全文复制进 `review_export.json`。
- 需要复查时，通过 `source_files` 回到对应过程文件。

`reviewed_entries` 建议字段：

```text
entry_id
source_draft_entry_id
entry_type
final_claim
final_fields
evidence_ids
decision
reviewer_notes
updated_at
```

建议 `reviewed_entries.decision`：

```text
accepted
modified
rejected
needs_recheck
```

说明：

- `accepted` 表示人工接受。
- `modified` 表示人工修改后接受。
- `rejected` 表示人工拒绝。
- `needs_recheck` 表示暂不进入可信结论，需要后续复查。
- 即使被拒绝，也可以保留最小记录，方便以后追踪为什么被拒绝。

`reviewed_evidence` 建议字段：

```text
evidence_id
decision
reason
reviewer_notes
```

建议 `reviewed_evidence.decision`：

```text
accepted
rejected
needs_recheck
partial
```

说明：

- 证据本身也需要人工判断。
- 有些错误来自底层证据不可靠、证据不相关或证据被过度解释。
- `partial` 表示证据部分可用，但不能支持全部候选结论。

`review_decisions` 建议字段：

```text
decision_id
target_type
target_id
field_path
original_value
final_value
decision
reason
evidence_ids
reviewer_id
timestamp
```

`review_decisions` 的作用：

- 记录人工为什么接受、修改、拒绝或要求复查。
- 记录字段从原始候选值变成最终值的原因。
- 支持以后回滚、复查和 debug。

示例：

```text
target_type: entry_field
field_path: final_fields.mechanism
original_value: local hyperthermia treats obesity by activating mitochondria
final_value: local hyperthermia is associated with increased mitochondrial markers in adipose tissue
decision: modified
reason: 原表述因果过强，证据只支持相关变化
evidence_ids: [E001, E003]
```

`audit_log` 第一版建议字段：

```text
timestamp
reviewer_id
action
target_type
target_id
before
after
note
```

说明：

- 第一版不需要复杂登录系统。
- 如果没有用户系统，可以先用 `reviewer_id: manual_reviewer`。
- 关键是保留“什么时候、对什么、从什么改成什么、为什么改”的记录。

`export_summary` 建议字段：

```text
total_entries
accepted_entries
modified_entries
rejected_entries
needs_recheck_entries
total_evidence
accepted_evidence
rejected_evidence
high_risk_items
```

不建议完整放入 `review_export.json` 的内容：

- 完整 `raw_parse`。
- 完整 `source_blocks`。
- 完整 `context_packs`。
- 完整 `verifier_report`。
- 模型原始响应全文。
- 所有运行日志。
- PDF 文本全文。

后续分析原则：

```text
默认只信 review_export.json。
不把 draft_entries 当成可信数据源。
需要追溯时，通过 source_files 回到过程文件。
```

阶段性结论：

```text
review_export.json 是最终机器可读主输出。
它只保存人工审核后的可信结果、审核决定、证据判断、追溯引用和轻量审计日志。
它不复制所有中间过程。
后续分析默认只信 review_export.json，不信 draft_entries。
source_files 用于必要时追溯原始过程文件。
```

## 16. 最小可运行 demo

阶段性确认：第一版 demo 只验证一篇论文能否跑通 V2 核心闭环。

demo 目标：

```text
一篇 PDF 能不能从解析、证据、候选条目、质检、人工审核，到最终 review_export 跑通闭环。
```

demo 不追求一次性覆盖所有论文、所有字段、所有关系和所有高级分析。

建议 demo 范围：

```text
1 篇论文
1 个 MinerU 解析结果
1 套基础字典
少量 evidence_units
少量 context_packs
少量 draft_entries
1 个 verifier_report
1 个本地 review_workspace
1 个 review_export.json
```

demo 主流程：

```text
PDF
-> MinerU raw_parse
-> source_blocks
-> document_structure
-> evidence_units
-> evidence_relations
-> context_packs
-> draft_entries
-> verifier_report
-> review_workspace
-> review_export
```

第一版必须有的文件：

```text
raw_parse.json
source_blocks.jsonl
document_structure.json
evidence_units.jsonl
evidence_relations.json
context_packs.jsonl
draft_entries.jsonl
verifier_report.json
review.html
review_state.json
review_export.json
```

可以先简化：

- `evidence_relations` 只做 `supports`、`contradicts`、`limits` 等基础关系。
- `context_packs` 只按同章节、相邻章节、共享实体、共享指标进行轻量组包。
- `claim_checks` 只对高风险 `draft_entry` 做。
- `review_workspace` 只做本地 HTML。
- `audit_log` 先使用 `manual_reviewer`。
- 只跑一篇论文。
- 不做跨论文分析。
- 不做数据库。
- 不做完整知识图谱。
- 不做复杂登录系统。
- 不做多 OCR 切换。

不能省：

- 统一 contracts。
- `evidence_id`。
- `source_block_id`。
- `draft_entry -> evidence_id` 链接。
- `verifier_report`。
- `review_workspace`。
- `review_export`。
- 人工审核决策记录。
- `source_files` 追溯。

验收标准：

demo 跑完后至少能回答：

```text
1. 这个最终结论来自哪些 evidence？
2. evidence 来自论文哪一页、哪一节、哪段原文？
3. 哪些字段是模型生成的？
4. 哪些字段被人工修改了？
5. 为什么修改？
6. 哪些结论证据不足？
7. 哪些内容进入了最终可信 review_export？
8. 哪些内容被拒绝或需要复查？
```

demo 不解决：

- 大规模批处理。
- 多论文对比。
- 多人协作。
- 复杂 UI。
- 高级图谱。
- 自动科学发现。
- 长期数据库管理。

阶段性结论：

```text
第一版 demo 只跑一篇论文。
目标是打通 evidence-centered + human-review-centered 闭环。
必须包含 contracts、evidence_units、context_packs、draft_entries、verifier_report、review_workspace、review_export。
不做数据库、不做多用户、不做多 OCR、不做跨论文知识图谱。
验收标准以可追溯、可审核、可导出为主。
```

## 17. 目录结构与文件契约

阶段性确认：V2 使用 contracts-first 目录结构。

目录结构目标：

```text
每个阶段只读固定输入，写固定输出。
字段和字典只在 contracts 定义。
提示词、校验、导出、审核界面都引用 contracts。
```

建议项目结构：

```text
v2_project/
  contracts/
  prompts/
  src/
  runs/
  review_app/
  tests/
  docs/
```

`contracts/` 建议结构：

```text
contracts/
  dictionaries.yaml
  fields.yaml
  output_contracts.yaml
  stage_contracts.yaml
```

职责：

- `dictionaries.yaml`：统一字典。
- `fields.yaml`：统一字段定义。
- `output_contracts.yaml`：最终输出契约。
- `stage_contracts.yaml`：每个阶段输入输出契约。

原则：

- 提示词不能自己写一套字段。
- 校验代码不能自己写一套枚举。
- 审核界面不能自己写一套字段名。
- 字段、枚举、阶段输入输出都以 contracts 为准。

`prompts/` 建议结构：

```text
prompts/
  evidence_extraction.md
  relation_detection.md
  context_pack_labeling.md
  draft_entry_generation.md
  verifier_semantic_checks.md
  review_question_generation.md
```

原则：

- prompt 负责告诉模型任务。
- contracts 负责定义允许输出什么。
- prompt 不作为字段真相来源。
- prompt 中使用的字段和枚举应由程序从 contracts 注入或引用。

`src/` 建议结构：

```text
src/
  pipeline/
  parsing/
  evidence/
  relations/
  context/
  drafting/
  verification/
  review/
  export/
  llm/
  validation/
  io/
```

职责：

- `pipeline/`：流程编排。
- `parsing/`：MinerU 解析适配。
- `evidence/`：`evidence_units` 生成。
- `relations/`：`evidence_relations` 生成。
- `context/`：`context_packs` 生成。
- `drafting/`：`draft_entries` 生成。
- `verification/`：`verifier_report` 生成。
- `review/`：`review_workspace` 生成与状态处理。
- `export/`：`review_export` 生成。
- `llm/`：大模型调用封装。
- `validation/`：contracts/schema 校验。
- `io/`：文件读写、路径管理、JSONL 工具。

`runs/` 建议结构：

```text
runs/
  paper_001/
    input/
    01_raw_parse/
    02_source/
    03_evidence/
    04_relations/
    05_context/
    06_draft/
    07_verification/
    08_review/
    09_export/
    logs/
```

每步建议输出：

```text
01_raw_parse/raw_parse.json
02_source/source_blocks.jsonl
02_source/document_structure.json
03_evidence/evidence_units.jsonl
04_relations/evidence_relations.json
05_context/context_packs.jsonl
06_draft/draft_entries.jsonl
07_verification/verifier_report.json
08_review/review.html
08_review/review_state.json
09_export/review_export.json
logs/failures.jsonl
logs/run_manifest.json
```

`review_app/` 建议结构：

```text
review_app/
  templates/
  static/
  build_review_workspace.py
  export_review_result.py
```

职责：

- 把 `draft_entries`、`evidence_units`、`verifier_report` 转成人能看的页面。
- 保存 `review_state.json`。
- 导出 `review_export.json`。

`tests/` 建议结构：

```text
tests/
  test_contracts.py
  test_stage_io.py
  test_evidence_links.py
  test_verifier_report.py
  test_review_export.py
```

第一版测试重点：

- 字段是否符合 contracts。
- 每个 `evidence_id` 能不能追溯。
- `draft_entry` 是否引用存在的 evidence。
- `review_export` 是否不引用不存在的文件。
- 流程输出文件是否完整。

文件契约原则：

每个阶段都必须写清楚：

```text
输入文件
输出文件
谁生成
谁消费
失败时写什么
是否允许人工修改
是否作为最终可信数据
```

示例：

```text
阶段：draft_entries
输入：
  context_packs.jsonl
  evidence_units.jsonl
  contracts/*
输出：
  draft_entries.jsonl
生成：
  drafting 模块 + LLM
消费：
  verification 模块
失败：
  logs/failures.jsonl
可信级别：
  模型候选，不可信，必须审核
```

阶段性结论：

```text
V2 使用 contracts-first 目录结构。
每篇论文一个 runs/paper_xxx 目录。
每个阶段固定输入输出。
contracts 是字段和字典唯一来源。
prompts 不能定义真实字段，只能引用 contracts。
review_workspace 和 review_export 分开。
第一版先做本地文件流，不做数据库。
```

## 18. 成本控制和 API 调用预算

阶段性确认：V2 的成本判断优先级是“稳定性 > 效率 > 成本”。成本控制不是单纯减少 API 花费，而是在不牺牲稳定性和效率的前提下控制花费。

核心原则：

```text
稳定性 > 效率 > 成本

只有当大模型明显比规则程序更适合，并且输出能被校验、追溯、人工审核时，才调用大模型。
否则使用程序。
```

解释：

- 稳定性优先：结构稳定、字段稳定、证据可追溯、错误可发现、人工可审核。
- 效率第二：在稳定前提下，优先选择能减少人工审核量、减少重复劳动、减少规则代码和减少维护改动的方案。
- 成本第三：在稳定和效率满足后，再通过缓存、合并调用、限制高风险调用、模型分层来降低 API 花费。

判断顺序：

```text
第一问：稳不稳？
第二问：是否提高效率？
第三问：贵不贵？
```

如果一个 LLM 调用很便宜，但会导致输出漂移、难校验、难追溯或增加人工返工，就不采用。

如果一个 LLM 调用更贵，但能明显减少错误、减少人工审核负担、减少规则复杂度，并且输出可校验、可追溯，可以接受。

不应调用大模型的部分：

- 文件路径管理。
- JSON / JSONL 读写。
- ID 生成。
- 字段类型校验。
- 枚举合法性校验。
- 必填字段检查。
- `source_block_id` 是否存在。
- `evidence_id` 是否存在。
- stage 输入输出检查。
- `review_export` 结构校验。
- `run_manifest` 记录。

这些任务用程序更便宜、更稳定，也更容易测试。

适合调用大模型的部分：

- 证据候选发现。
- 证据语义分类。
- `context_pack` 主题判断。
- `draft_entry` 生成。
- `field_decisions` 字段理由。
- `uncertainty_map` 不确定性说明。
- `logic_checks` 语义风险解释。
- `claim_checks` 高风险结论拆解。
- `review_questions` 生成。
- 冲突解释。

这些任务需要理解论文语义，纯规则通常很难写好。

第一版 API 调用预算：

```text
每篇论文控制在 3-6 次主要 LLM 调用。
```

建议分配：

```text
1. evidence_units 候选抽取：1-2 次
2. context_pack 标注 / 排序：0-1 次
3. draft_entries 生成：1-2 次
4. verifier_report 语义检查：1 次
5. review_questions 合并进 verifier_report，不单独调用
```

原则：

- 能合并的调用就合并。
- 不为了模块形式漂亮而强行拆成很多次 API 调用。
- 不让每个小字段都单独调用一次大模型。

模型分层建议：

```text
cheap model:
  分类、排序、简单审核问题、简单字段理由。

strong model:
  evidence extraction、draft_entry、logic_checks、复杂冲突解释。
```

第一版不一定马上实现复杂模型路由，但设计上可以预留：

```text
llm_profile: cheap
llm_profile: strong
```

缓存要求：

相同输入不应重复调用 API。

建议缓存 key：

```text
prompt_name
prompt_version
contract_version
input_hash
model_name
```

缓存输出建议位置：

```text
runs/paper_001/logs/llm_cache/
```

失败处理：

API 调用失败不能悄悄跳过。

至少记录：

```text
stage
prompt_name
input_hash
error_type
error_message
retry_count
timestamp
```

写入：

```text
logs/failures.jsonl
```

新增 LLM 步骤的判断规则：

```text
如果一个 LLM 步骤需要新增大量程序补丁才能变稳定，
且它的效果不明显优于规则程序，
就取消这个 LLM 步骤，改用程序或人工审核。
```

每新增一个 LLM 调用点，必须回答：

```text
1. 它替代了什么人工或规则工作？
2. 输出如何校验？
3. 失败时怎么办？
4. 是否能缓存？
5. 是否真的影响最终质量？
```

阶段性结论：

```text
成本判断优先级是：稳定性 > 效率 > 成本。
第一版每篇论文控制在 3-6 次主要 LLM 调用。
程序负责硬规则、ID、schema、路径、导出。
大模型只负责语义理解、候选生成、风险解释。
review_questions 合并进 verifier_report，不单独调用。
所有 LLM 调用必须可缓存、可追溯、可失败记录。
新增 LLM 步骤必须通过成本-收益判断。
```

## 19. 当前未定事项

以下内容尚未最终确认：

- 是否开始新项目骨架。

## 20. 下一步讨论顺序

建议下一步讨论是否开始新项目骨架。

原因：

- 当前 V2 第一版的核心设计边界已经基本收束。
- 继续讨论容易进入细节循环。
- 开始骨架前需要确认是在现有仓库内新建目录，还是新建独立项目。

建议后续顺序：

```text
1. 确认是否开始新项目骨架
2. 确认骨架位置
3. 生成 contracts-first 最小骨架
```
