# V2 Literature Review Extraction

线粒体产热文献证据提取流水线。Contracts-first 架构，9 阶段全自动 + 人工审核。

## 快速开始

```bash
cd D:\融合版\853
export OPENAI_API_KEY="sk-..." OPENAI_BASE_URL="https://api.deepseek.com"

# 完整跑一篇论文
python src/parsing/run_mineru.py input/paper.pdf runs/<id>/01_raw_parse
python src/parsing/build_raw_parse.py runs/<id> <id>
python src/parsing/build_source.py runs/<id> <id>
python src/evidence/extract_evidence.py runs/<id> <id>
python src/context/build_context_packs.py runs/<id> <id>
python src/drafting/generate_drafts.py runs/<id> <id>
python src/verification/generate_report.py runs/<id> <id>
python src/review/review_server.py                    # → http://localhost:8080
python src/export/build_export.py runs/<id> <id>

# Mock 模式（跳过 LLM，快速测试）
python src/evidence/extract_evidence.py runs/<id> <id> --mock
python src/drafting/generate_drafts.py runs/<id> <id> --mock
```

## 目录

```
contracts/          ← 字典、字段 schema、阶段 I/O（唯一真相来源）
prompts/            ← LLM 提示词（{{DICT_NAME}} 动态注入）
src/                ← Python 代码（不硬编码路径/枚举值）
_project/           ← 项目管理（STATUS / TASKS / CHANGELOG / HANDOFF）
runs/               ← 论文运行输出
```

## 入口

新 agent / 新线程请先读 `_project/00_START_HERE.md`。
