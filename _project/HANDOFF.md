# Handoff

## 2026-06-26 Legacy Isolation Note

Before continuing implementation, read:

```text
_project/NEXT_AGENT_MEMORY.md
_project/LEGACY_MAP.md
```

Current important distinction:

```text
contracts/* is the current authority.
Some src/, prompts/, tests/, and runs/ files still reflect the previous runnable pipeline.
Those legacy files are reference material, not current contract truth.
```

Do not assume the old successful pipeline is still the desired V2 flow.

Known mismatches:

```text
old code still uses 04_relations/evidence_relations.json in the pre-review flow
old evidence extraction emits source_text/entities/model_system instead of the confirmed evidence_unit structure
old context packs use task_type/evidence_items/expected_output
old review_export uses export_id/summary/linked_evidence/review_status
old validator hard-codes old files
```

Recommended next implementation step:

```text
1. Add src/core/contracts.py.
2. Replace hard-coded validation with contracts-driven validation.
3. Then rewrite evidence/context/draft/verifier/review/export in that order.
```

更新时间：2026-06-26

## 当前状态

V2 项目已完成全部 9 阶段 pipeline。10 个 Python 脚本全部用真实论文 real_paper_001 跑通。

项目管理正文统一维护在 `_project/`。

根目录已新增 `AGENTS.md`，用于提示后续 agent 开工前先读 `_project/00_START_HERE.md`。

如需交给另一个 AI / agent，请让它先读 `_project/AI_HANDOFF_PROMPT.md`。

## 当前目录

```text
D:\融合版\853
```

## 已完成的 pipeline 阶段

| 阶段 | 脚本 | 输入 → 输出 |
|------|------|------------|
| raw_parse | `src/parsing/run_mineru.py` + `build_raw_parse.py` | PDF → content_list.json → raw_parse.json |
| source_normalization | `src/parsing/build_source.py` | raw_parse.json → source_blocks.jsonl + document_structure.json |
| evidence_units | `src/evidence/extract_evidence.py` | source_blocks → evidence_units.jsonl (LLM + consensus) |
| evidence_relations | `src/relations/build_relations.py` | evidence_units → evidence_relations.json (纯规则引擎) |
| context_packs | `src/context/build_context_packs.py` | evidence + relations + source → context_packs.jsonl |
| draft_entries | `src/drafting/generate_drafts.py` | context_packs → draft_entries.jsonl (LLM 批量生成) |
| verifier_report | `src/verification/generate_report.py` | drafts + evidence → verifier_report.json (质量核查) |
| review_workspace | `src/review/review_server.py` + `review.html` | Server-based review UI (localhost:8080) |
| review_export | `src/export/build_export.py` | drafts + evidence + review_state → review_export.json |

### 辅助脚本

- `src/evidence/consensus_evidence.py` — 多轮 LLM 提取多数投票共识

## Pipeline 用法

### 完整流程

```bash
# 前置：设置 API key
export OPENAI_API_KEY=sk-634a08836afc48a68863df07b6af8c69
export OPENAI_BASE_URL=https://api.deepseek.com
export EVIDENCE_LLM_MODEL=deepseek-chat

# Step 1: MinerU 解析 PDF
python src/parsing/run_mineru.py <pdf_path> runs/<paper_id>/01_raw_parse

# Step 2: 标准化
python src/parsing/build_raw_parse.py runs/<paper_id> <paper_id>

# Step 3: 构建 source blocks
python src/parsing/build_source.py runs/<paper_id> <paper_id>

# Step 4: 提取 evidence units（3 轮提取 + 共识）
python src/evidence/extract_evidence.py runs/<paper_id> <paper_id>
# 重复 3 次，分别保存为 evidence_units_run{1,2,3}.jsonl
python src/evidence/consensus_evidence.py runs/<paper_id>/03_evidence --min-runs 2

# Step 5: 构建关系
python src/relations/build_relations.py runs/<paper_id> <paper_id>

# Step 6: 构建 context packs
python src/context/build_context_packs.py runs/<paper_id> <paper_id>

# Step 7: 生成 draft entries (LLM)
python src/drafting/generate_drafts.py runs/<paper_id> <paper_id>

# Step 8: 质量核查
python src/verification/generate_report.py runs/<paper_id> <paper_id>

# Step 9: 启动审核服务器（多论文模式 — 自动发现 runs/ 下所有论文）
python src/review/review_server.py --port 8080
# 或单论文模式：python src/review/review_server.py runs/<paper_id> --port 8080
# 浏览器打开 http://localhost:8080 进行人工审核
# 审核完成后导出 JSON

# Step 10: 最终导出
python src/export/build_export.py runs/<paper_id> <paper_id>
```

### Mock 模式（跳过 LLM）

```bash
python src/evidence/extract_evidence.py runs/<paper_id> <paper_id> --mock
```

## real_paper_001 运行结果

### 完整链路数据
- 248 MinerU blocks → 123 kept → 91P + 32F + 0T，14 sections
- 27 extraction groups → 5 LLM batches × 3 runs → consensus 66 evidence units
- 66 units → 480 directed relations (8 types: supports:131, targets:100, mediates:91, detects:90, extends:29, modulates:20, causal_chain:18, associated_with:1)
- 66 evidence units → 480 relations → 11 context packs (relation-graph BFS clustering, max_size=20) → 11 draft entries (中文)
- Verifier: 11/11 OK, 66/66 evidence linked

### 证据分布
- mechanism_pathway: 36
- detection_method: 19
- thermogenesis_modulation: 10
- disease_association: 1

## real_paper_002 运行结果

### 完整链路数据
- 201 MinerU blocks → 110 kept → 73P + 37F + 0T，21 sections
- 11 extraction groups → 4 LLM batches × 3 runs → consensus 35 evidence units (25 全票 + 10 两票)
- 35 units → 263 relations (supports:106, detects:89, causal_chain:38, associated_with:17, extends:13)
- 35 evidence units → 5 context packs (BFS clustering max_size=20) → 5 draft entries (中文)
- Verifier: 5/5 OK, 35/35 evidence linked

### 证据分布
- mechanism_pathway: 20
- detection_method: 12
- disease_association: 3

### 论文主题
HSF1 双重调控 SPI1/PU.1 和 HSP70 在单核细胞向巨噬细胞分化中的作用（非线粒体产热，但与 HSF1 热休克通路相关）

### 关键技术决策
- Evidence units: 3-run majority voting (temperature=0, Jaccard threshold=0.4, min_runs=2)
- Evidence relations: 纯规则引擎（实体重叠 + 类型组合），每节点最多 10 条出边
- Context packs: 基于关系图的 BFS 连通分量聚类（max_size=20），66 证据单元 → 11 主题 packs
- Draft entries: 中文 LLM 生成，按 task_type 分批（每批≤4），解析失败自动逐 pack 重试
- Review UI: client-server 架构，多论文自动发现 + 下拉切换 + 按论文独立保存审核状态

## 已知问题

- DeepSeek 即使 T=0 也有非确定性（MoE 架构），提取结果 61-73 波动，通过 3 轮共识缓解
- evidence_units 跨 batch ID 重复 bug 已修复（id_offset）

## Contracts 文件

- `contracts/dictionaries.yaml` v0.2.0 — 16 个字典
- `contracts/fields.yaml` — source_block / evidence_unit / context_pack / draft_entry / review_export
- `contracts/stage_contracts.yaml` — 9 阶段 I/O 定义
- `contracts/output_contracts.yaml` — 可信/候选输出定义

## 下一步建议

- 人工审核 real_paper_001 的 11 条 draft entries（启动 `python src/review/review_server.py runs/real_paper_001`）
- 审核完成后导出最终 `review_export.json`
- 跑更多论文测试泛化性
- 考虑跨论文 relation（当前仅论文内）

## 注意事项

- V2 位于 `D:\融合版\853`，完全独立于旧项目。
- 绝对不要参考 `D:\开放式大模型提取流程\` 下的旧项目文件（除非用户明确要求）。
- 成本判断优先级：稳定性 > 效率 > 成本。
- 低耦合架构原则见 `_project/ARCHITECTURE.md`。

## 给下一个 agent 的开工提示

先读：

```text
_project/00_START_HERE.md
_project/STATUS.md
_project/TASKS.md
_project/DECISIONS.md
_project/AGENT_RULES.md
```
