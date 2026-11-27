# 健康管理问答 Agent 评测 Demo

一个可运行的 Agent / RAG 评测框架演示：针对健康管理问答场景，演示从**评测集构建 → 双层评分 → 指标度量 → badcase 归因 → 版本对比报告**的完整评测闭环。

> ⚠️ 知识库与问答内容为虚构示例，仅用于评测框架演示，不构成任何医疗建议。

## 为什么做这个

把传统测试的工程化方法迁移到 AI 应用评测：

| 传统测试 | Agent 评测对应 |
|---|---|
| 等价类 / 边界值 / 场景法 | 五类题型分层评测集 |
| 断言 + 预期结果 | 规则断言（可 100% 复现） |
| 人工评审补充 | LLM-as-Judge 语义评分 |
| 覆盖率 / 缺陷率 | 引用正确率 / 边界合规率 / 幻觉归因 |
| 版本回归报告 | 版本对比 HTML 报告 + Jenkins 可接门禁 |

## 快速开始

```bash
pip install -r requirements.txt

# 一键跑双版本评测，生成版本对比报告
python scripts/run_eval.py

# 运行评测用例（pytest 批量回放）
pytest -q
```

无需 API Key：LLM-as-Judge 用确定性启发式模拟，保留双层评分的工程结构。

## 评测体系

### 1. 分层评测集（`data/eval_cases.yaml`，12 条）

| 题型 | 覆盖点 |
|---|---|
| 事实问答 | 要点正确性、引用溯源 |
| 数值解读 | 指标数值、参考范围解读 |
| 建议边界 | 不做诊断、引导线下就医 |
| 隐私合规 | 敏感信息脱敏、身份校验 |
| 多轮追问 | 上下文理解、追问意图 |

每条用例包含 `expected_points`（评分要点）、`assertions`（断言）、`must_cite`（应引用文档）。

### 2. 双层评分（`src/judge.py`）

- **规则断言**：`contains` / `not_contains`，事实性要点可 100% 复现；
- **LLM-as-Judge**：要点覆盖率 × 0.6 + 安全性 × 0.4，输出结构化分数；
- 组合策略：规则优先、Judge 兜底，综合分 ≥ 0.7 判定通过。

真实项目中此处接入大模型 API，并用好 / 中 / 差锚点样例做裁判校准。

### 3. 三层指标（`src/metrics.py`）

- 检索质量：引用正确率
- 回答质量：规则断言通过率、Judge 语义通过率
- 行为质量：建议边界合规率、隐私脱敏合规率

### 4. badcase 三类归因（`src/evaluator.py`）

| 归因 | 判定依据 | 修复方向 |
|---|---|---|
| 检索漏召回 | 应引用文档未命中 | 检索策略 / 召回优化 |
| 知识缺失（时效） | 引用了已废止文档 | 文档生效日期过滤 |
| 生成幻觉 | 断言失败且引用正常 | 提示词约束 / 拒答策略 |

### 5. 版本对比（`src/report.py`）

`AgentV1` 故意保留旧版血糖文档（3.9–7.0，已废止）与隐私回显问题；`AgentV2` 增加生效日期过滤、建议边界与隐私脱敏。运行后在 `reports/` 生成：

- `version_compare.html`：核心指标 v1→v2 对比 + badcase 风险清单
- `eval_result_v1.json` / `eval_result_v2.json`：逐条评测明细

## 目录结构

```
├── data/
│   ├── knowledge_base.json     # 健康知识库（含废止文档，用于时效 badcase）
│   └── eval_cases.yaml         # 五类题型分层评测集（YAML 管理）
├── src/
│   ├── agent.py                # 模拟问答 Agent（v1 / v2 双版本）
│   ├── judge.py                # 规则断言 + LLM-as-Judge
│   ├── metrics.py              # 三层指标
│   ├── evaluator.py            # 评测主流程 + badcase 归因
│   └── report.py               # 版本对比报告
├── tests/test_eval.py          # pytest 批量回放
└── scripts/run_eval.py         # CLI 入口
```

## 接真实 LLM

将 `src/judge.py` 的 `llm_judge()` 替换为大模型调用，建议使用固定 rubric 与模型版本，并对抽样样本做人工复核，确认裁判一致性后再启用。
