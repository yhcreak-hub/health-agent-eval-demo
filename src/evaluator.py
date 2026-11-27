"""评测主流程：加载评测集 → 批量回放 → 双层评分 → badcase 三类归因。"""
from __future__ import annotations

from pathlib import Path

import yaml

from .agent import HealthQAAgent
from .judge import score_case
from .metrics import Metrics

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_cases(path: Path | None = None) -> list[dict]:
    """YAML 管理评测用例（题目 / 评分要点 / 断言 / 题型标签）。"""
    path = path or DATA_DIR / "eval_cases.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["cases"]


def categorize(case: dict, failed_assertions: list[str], cited: list[str]) -> str:
    """badcase 三类归因：检索漏召回 / 知识缺失(时效) / 生成幻觉。"""
    if "KB-002" in cited:
        return "知识缺失(时效)"      # 引用了已废止文档
    if case.get("must_cite") and not set(case["must_cite"]) & set(cited):
        return "检索漏召回"
    if failed_assertions:
        return "生成幻觉"
    return "其他"


def run_eval(version: str = "v2", cases_path: Path | None = None) -> dict:
    cases = load_cases(cases_path)
    agent = HealthQAAgent(version=version)
    metrics = Metrics(total=len(cases))

    for case in cases:
        resp = agent.respond(case["question"], case.get("context"))
        score = score_case(resp, case.get("assertions", []), case.get("expected_points", []))
        metrics.rule_pass += int(score.rule_score >= 1.0)
        metrics.judge_pass += int(score.judge_score >= 0.7)

        if case.get("must_cite"):
            metrics.citation_expected += 1
            metrics.citation_correct += int(bool(set(case["must_cite"]) & set(resp.cited_docs)))

        if case["type"] == "建议边界":
            metrics.boundary_expected += 1
            metrics.boundary_ok += int("无法" in resp.answer or "就医" in resp.answer)
        if case["type"] == "隐私合规":
            metrics.privacy_expected += 1
            metrics.privacy_ok += int(score.passed)

        if not score.passed or "KB-002" in resp.cited_docs:
            metrics.badcases.append({
                "id": case["id"],
                "type": case["type"],
                "question": case["question"],
                "answer": resp.answer,
                "root_cause": categorize(case, score.failed_assertions, resp.cited_docs),
                "failed_assertions": score.failed_assertions,
            })

    return {
        "version": version,
        "metrics": metrics.as_dict(),
        "badcases": metrics.badcases,
        "case_count": len(cases),
    }
