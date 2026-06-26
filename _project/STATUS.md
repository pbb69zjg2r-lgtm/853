# Status

## 2026-06-26 Scientific Questions Revised

- Added `_project/SCIENTIFIC_QUESTIONS.md` as the human-readable authority for the 7 scientific questions.
- Updated `prompts/evidence_extraction.txt` with an authoritative taxonomy and overlap rules.
- Updated `prompts/draft_generation.txt` with the same taxonomy so draft synthesis does not collapse type 6/7 into generic mechanisms.
- Stable enum names remain unchanged in `contracts/dictionaries.yaml`.

## 2026-06-26 Decoupling Audit Complete

**去耦合审计全部完成（20 个问题全部修复）**

### HIGH (4/4 fixed)
- H1: verifier_summary 从 entry_results 动态计算（替代硬编码 .summary 读取）
- H2: 删除 build_export.py 死代码 flagged 逻辑
- H3: 统一 review_state 时间戳字段为 updated_at
- H4: review.html 新增 reviewer 输入框 + export_notes 文本框

### MEDIUM (12/12 resolved)
- M1: build_raw_parse.py 路径从 stage_output_paths 派生
- M4: 提示词枚举值动态注入（format_prompt + {{PLACEHOLDER}}）
- M5: draft_entry.status 改为 dictionary 引用
- M6-M8: 清理未使用的 import 和变量
- M9: section_type 字典新增 preamble
- M11: 从 stage_contracts 移除 review.html（源文件非产出）
- M12: 删除 API 中未使用的 verifier_summary/verifier_results
- M2/M10: 判断为合理保留

### 关键新增
- `format_prompt()` in contracts.py: 将 `{{DICT_NAME}}` 占位符替换为字典值
- 提示词中 4 处硬编码枚举值全部改为占位符

### LLM 验证通过
- S3 extract_evidence: 20 units 成功提取（4 batches, real LLM）
- S6 generate_drafts: 5 drafts mock 模式通过

### 已知问题
- S6 mechanism_pathway JSON 截断（LLM max_tokens 不足，提示词已建议改为 claim-first 顺序）
- LLM 偶用 `mixed`/`both` 作为 model_level/in_vivo_or_in_vitro（字典中不存在）

更新时间：2026-06-26

## 阶段

```text
阶段：Pipeline 全 9 阶段完成（raw_parse → review_export）
代码状态：10 个 Python 脚本全部通过真实论文 real_paper_001 验证
运行状态：
  real_paper_001 — PDF → 66 consensus → 480 relations → 11 context packs → 11 draft entries → review workspace ✓
  real_paper_002 — PDF → 35 consensus → 263 relations → 5 context packs → 5 draft entries → review workspace ✓
可信输出：review_export.json (两篇论文，待人工审核)；review.html (多论文 server-based review workspace)
```

## 项目目录

```text
D:\融合版\853
```

## 已完成

### Pipeline 全阶段

| # | 阶段 | 脚本 | 输出 | 状态 |
|---|------|------|------|------|
| 1 | raw_parse | `src/parsing/run_mineru.py` + `build_raw_parse.py` | raw_parse.json | ✓ |
| 2 | source_normalization | `src/parsing/build_source.py` | source_blocks.jsonl + document_structure.json | ✓ |
| 3 | evidence_units | `src/evidence/extract_evidence.py` | evidence_units.jsonl (66 consensus) | ✓ |
| 4 | evidence_relations | `src/relations/build_relations.py` | evidence_relations.json (480 relations) | ✓ |
| 5 | context_packs | `src/context/build_context_packs.py` | context_packs.jsonl (11 packs, BFS clustering max_size=20) | ✓ |
| 6 | draft_entries | `src/drafting/generate_drafts.py` | draft_entries.jsonl (11 entries, 中文) | ✓ |
| 7 | verifier_report | `src/verification/generate_report.py` | verifier_report.json (11/11 OK) | ✓ |
| 8 | review_workspace | `src/review/review_server.py` + `review.html` | Server-based review UI | ✓ |
| 9 | review_export | `src/export/build_export.py` | review_export.json | ✓ |

### 辅助脚本

- `src/evidence/consensus_evidence.py` — 多轮 LLM 提取多数投票共识
- `prompts/evidence_extraction.txt` — 证据提取 prompt（含决策树、INCLUDES/EXCLUDES）
- `prompts/draft_generation.txt` — 草稿生成 prompt

### 关键设计决策

- 证据提取：3 轮 DeepSeek-chat (T=0) + majority voting → 66 consensus units
- 证据关系：纯规则引擎，基于实体重叠 + 类型组合，无 LLM
- 上下文打包：基于关系图的 BFS 连通分量聚类（max_size=20），66 证据单元 → 11 主题 packs
- 草稿生成：中文 prompt，按 task_type 分批（每批最多 4 packs），解析失败时逐 pack 重试
- 审核界面：Client-server 架构，多论文自动发现 + 下拉切换 + 按论文独立保存审核状态
- real_paper_002 验证：HSF1/SPI1 巨噬细胞分化论文全流程跑通（40/37/50 → 35 consensus, 5 draft entries, 5/5 OK）
- 切换到 DeepSeek 官方直连（api.deepseek.com），弃用代理
- Bug 修复：跨 batch 的 evidence_id 重复（parse_llm_output 需 id_offset）
- Review HTML 嵌入方案从静态内联 JSON 改为 server-based API 动态加载

## 当前建议

- 人工审核：启动 `python src/review/review_server.py`（多论文模式），浏览器打开 http://localhost:8080
- 审核完成后运行 `python src/export/build_export.py runs/<paper_id>` 生成最终 review_export.json
- 后续可跑更多论文测试泛化性
- 当前服务器运行中（localhost:8080），含 mock_paper_001 / real_paper_001 / real_paper_002 三篇
