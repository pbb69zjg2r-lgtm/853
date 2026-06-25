# V2 Literature Review Extraction

本目录是 V2 重写项目的隔离工作区。

它位于当前仓库内，但与旧项目流程隔离：

- 旧项目代码、脚本、流程不应直接依赖本目录。
- V2 新骨架、contracts、prompts、runs、review_app 后续都放在本目录下。
- 当前已生成 V2 最小目录骨架、contracts 样板、mock run 样例、mock source normalizer 和最小 mock 校验脚本，尚未实现真实业务 pipeline。

当前文件：

```text
AGENTS.md
_project/
V2_design_confirmed.md
contracts/
prompts/
src/
runs/
review_app/
tests/
docs/
```

下一步：

```text
1. 讨论 MinerU adapter 的真实输入输出边界
2. 评估是否扩展为通用 stage contract validator
3. 讨论真实文献前的最小 pipeline
4. 再评估是否接入真实 MinerU 和 LLM
```
