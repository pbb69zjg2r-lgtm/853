# Handoff

## 2026-06-26 Decoupling Complete

去耦合审计全部完成。所有 Python 代码通过 contracts API 获取路径、枚举值和字段 schema。

**关键变更：**
- 提示词不再硬编码枚举值，改用 `{{DICT_NAME}}` 占位符，`format_prompt()` 运行时注入
- 字典从 16 个精简到 6 个（section_type, evidence_type, entity_type, modulation_direction, detection_category, draft_entry_status）
- 所有 stage 模块统一使用 `stage_input_paths()` / `stage_output_paths()`
- review.html 新增 reviewer 和 export_notes 字段

**已知问题：**
- S6 mechanism_pathway JSON 截断（max_tokens 不足）
- LLM 偶用 `mixed`/`both` 值（字典中无）

**下一步：**
- 人工审核 real_paper_001 + real_paper_002
- 考虑 mechanism_pathway 截断修复（提示词改为 claim-first 输出顺序）
- 考虑添加 `mixed`/`both` 到 model_level/in_vivo_or_in_vitro 字典

---

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

V2 项目已完成全部 9 阶段 pipeline，去耦合审计全部通过。所有 Python 代码通过 contracts API 获取路径、枚举值和字段 schema。

项目管理正文统一维护在 `_project/`。

根目录 `AGENTS.md` 用于提示后续 agent 开工前先读 `_project/00_START_HERE.md`。

## 当前目录

```text
D:\融合版\853
```

## 已完成的 pipeline 阶段

| 阶段 | 脚本 | 输入 → 输出 |
|------|------|------------|
| raw_parse | `src/parsing/run_mineru.py` + `build_raw_parse.py` | PDF → content_list.json → raw_parse.json |
| source_normalization | `src/parsing/build_source.py` | raw_parse.json → source_blocks.jsonl + document_structure.json |
| evidence_units | `src/evidence/extract_evidence.py` | source_blocks → evidence_units.jsonl (LLM) |
| evidence_consensus | `src/evidence/consensus_evidence.py` | 3 runs → majority-vote evidence_units.jsonl (可选) |
| context_packs | `src/context/build_context_packs.py` | evidence + source → context_packs.jsonl (纯算法聚类) |
| draft_entries | `src/drafting/generate_drafts.py` | context_packs → draft_entries.jsonl (LLM 批量生成) |
| verifier_report | `src/verification/generate_report.py` | drafts + evidence → verifier_report.json |
| review_workspace | `src/review/review_server.py` + `review.html` | Server-based review UI (localhost:8080) |
| review_export | `src/export/build_export.py` | drafts + evidence + review_state → review_export.json (唯一 trusted output) |

## Pipeline 用法

```bash
export OPENAI_API_KEY="sk-55f49f1f36ff4d9f8ad6ab733f351ca6"
export OPENAI_BASE_URL="https://api.deepseek.com"

python src/parsing/run_mineru.py input/paper.pdf runs/<id>/01_raw_parse
python src/parsing/build_raw_parse.py runs/<id> <id>
python src/parsing/build_source.py runs/<id> <id>
python src/evidence/extract_evidence.py runs/<id> <id>
python src/context/build_context_packs.py runs/<id> <id>
python src/drafting/generate_drafts.py runs/<id> <id>
python src/verification/generate_report.py runs/<id> <id>
python src/review/review_server.py                    # 多论文模式 → http://localhost:8080
python src/export/build_export.py runs/<id> <id>

# Mock 模式（跳过 LLM）
python src/evidence/extract_evidence.py runs/<id> <id> --mock
python src/drafting/generate_drafts.py runs/<id> <id> --mock
```

## Contracts 文件

- `contracts/dictionaries.yaml` v0.2.0 — 6 个字典
- `contracts/fields.yaml` — source_block / evidence_unit / context_pack / draft_entry / review_export
- `contracts/stage_contracts.yaml` — 9 阶段 I/O 定义
- `contracts/output_contracts.yaml` — 可信/候选输出定义

## 已知问题

- S6 mechanism_pathway JSON 截断（max_tokens 不足，建议提示词改为 claim-first 输出顺序）
- LLM 偶用 `mixed`/`both` 值（model_level / in_vivo_or_in_vitro 字典中无）
- DeepSeek 即使 T=0 也有非确定性（MoE 架构）

## 给下一个 agent 的开工提示

先读：

```text
_project/00_START_HERE.md
_project/STATUS.md
_project/TASKS.md
_project/DECISIONS.md
_project/AGENT_RULES.md
```
