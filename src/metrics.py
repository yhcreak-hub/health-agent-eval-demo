"""三层指标体系：检索质量 / 回答质量 / 行为质量。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Metrics:
    total: int = 0
    rule_pass: int = 0
    judge_pass: int = 0
    citation_correct: int = 0
    citation_expected: int = 0
    boundary_ok: int = 0
    boundary_expected: int = 0
    privacy_ok: int = 0
    privacy_expected: int = 0
    badcases: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        def rate(num, den):
            return round(num / den, 3) if den else 0.0

        return {
            "样本数": self.total,
            "规则断言通过率": rate(self.rule_pass, self.total),
            "Judge 语义通过率": rate(self.judge_pass, self.total),
            "引用正确率": rate(self.citation_correct, self.citation_expected),
            "建议边界合规率": rate(self.boundary_ok, self.boundary_expected),
            "隐私脱敏合规率": rate(self.privacy_ok, self.privacy_expected),
            "badcase 数": len(self.badcases),
        }
