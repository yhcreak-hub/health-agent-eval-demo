"""pytest 批量回放测试：验证断言评分、badcase 归因与版本对比。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import HealthQAAgent
from src.evaluator import run_eval, load_cases
from src.judge import rule_assert, score_case


def test_evalset_loaded():
    cases = load_cases()
    assert len(cases) == 12
    assert {c["type"] for c in cases} == {
        "事实问答", "数值解读", "建议边界", "隐私合规", "多轮追问"
    }


def test_rule_assert():
    resp = HealthQAAgent("v2").respond("空腹血糖正常参考范围是多少？")
    score, failed = rule_assert(resp, ["contains:3.9", "contains:6.1", "not_contains:已废止"])
    assert score == 1.0 and failed == []


def test_v1_exposes_stale_doc_badcase():
    """v1 引用旧版废止文档，应被归类为知识缺失(时效)。"""
    result = run_eval("v1")
    stale = [c for c in result["badcases"] if c["root_cause"] == "知识缺失(时效)"]
    assert stale, "v1 应暴露旧版文档未下线的 badcase"


def test_v2_fixes_privacy_and_boundary():
    """v2 应修复隐私回显问题。"""
    result = run_eval("v2")
    privacy = [c for c in result["badcases"] if c["type"] == "隐私合规"]
    assert not privacy, "v2 不应有隐私合规 badcase"


def test_version_compare_metrics():
    v1, v2 = run_eval("v1"), run_eval("v2")
    assert v2["metrics"]["隐私脱敏合规率"] > v1["metrics"]["隐私脱敏合规率"]
