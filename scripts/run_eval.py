#!/usr/bin/env python3
"""CLI：python scripts/run_eval.py —— 一键跑双版本评测并生成对比报告。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluator import run_eval
from src.report import write_reports


def main():
    v1 = run_eval("v1")
    v2 = run_eval("v2")
    out = write_reports(v1, v2, ROOT / "reports")

    print("=" * 56)
    print("健康管理问答 Agent 评测结果")
    print("=" * 56)
    for label, res in (("v1", v1), ("v2", v2)):
        print(f"\n[{label}] 样本 {res['case_count']} 条，badcase {len(res['badcases'])} 条")
        for k, val in res["metrics"].items():
            if isinstance(val, float):
                print(f"  {k}: {val:.0%}")
            else:
                print(f"  {k}: {val}")
    print(f"\n版本对比报告：{out}")
    print("badcase 归因样例（v1）：")
    for c in v1["badcases"][:5]:
        print(f"  - {c['id']} [{c['type']}] 根因={c['root_cause']}")


if __name__ == "__main__":
    main()
