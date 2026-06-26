# Status

更新时间：2026-06-26

## 阶段

```text
阶段：Pipeline 全 9 阶段完成（raw_parse → review_export）
代码状态：9 个 Python 脚本全部通过真实论文 real_paper_001 验证
运行状态：real_paper_001 完整链路跑通：PDF → 66 consensus evidence units → 480 relations → 66 draft entries → review workspace
可信输出：review_export.json (66 entries，待人工审核)；review.html (server-based review workspace)
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
| 5 | context_packs | `src/context/build_context_packs.py` | context_packs.jsonl (66 packs) | ✓ |
| 6 | draft_entries | `src/drafting/generate_drafts.py` | draft_entries.jsonl (66 entries) | ✓ |
| 7 | verifier_report | `src/verification/generate_report.py` | verifier_report.json (65/66 OK) | ✓ |
| 8 | review_workspace | `src/review/review_server.py` + `review.html` | Server-based review UI | ✓ |
| 9 | review_export | `src/export/build_export.py` | review_export.json | ✓ |

### 辅助脚本

- `src/evidence/consensus_evidence.py` — 多轮 LLM 提取多数投票共识
- `prompts/evidence_extraction.txt` — 证据提取 prompt（含决策树、INCLUDES/EXCLUDES）
- `prompts/draft_generation.txt` — 草稿生成 prompt

### 关键设计决策

- 证据提取：3 轮 DeepSeek-chat (T=0) + majority voting → 66 consensus units
- 证据关系：纯规则引擎，基于实体重叠 + 类型组合，无 LLM
- 审核界面：Client-server 架构（Python HTTP server + 独立 HTML 前端），参考旧项目模式
- Bug 修复：跨 batch 的 evidence_id 重复（parse_llm_output 需 id_offset）
- Review HTML 嵌入方案从静态内联 JSON 改为 server-based API 动态加载

## 当前建议

- 人工审核：启动 `python src/review/review_server.py runs/real_paper_001`，浏览器打开 http://localhost:8080
- 审核完成后运行 `python src/export/build_export.py runs/real_paper_001` 生成最终 review_export.json
- 后续可跑更多论文测试泛化性
