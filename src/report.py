"""输出版本对比报告（HTML + JSON）与 badcase 风险清单。"""
from __future__ import annotations

import json
from pathlib import Path

METRIC_KEYS = ["规则断言通过率", "Judge 语义通过率", "引用正确率", "建议边界合规率", "隐私脱敏合规率"]


def render_html(v1: dict, v2: dict) -> str:
    rows = []
    for k in METRIC_KEYS:
        a, b = v1["metrics"][k], v2["metrics"][k]
        delta = b - a
        color = "#c0392b" if delta > 0 else "#999" if delta == 0 else "#27ae60"
        sign = "+" if delta > 0 else ""
        rows.append(
            f"<tr><td>{k}</td><td>{a:.0%}</td><td>{b:.0%}</td>"
            f"<td style='color:{color}'>{sign}{delta:.0%}</td></tr>"
        )

    bad_rows = "".join(
        f"<tr><td>{c['id']}</td><td>{c['type']}</td><td>{c['root_cause']}</td>"
        f"<td>{c['question']}</td></tr>"
        for c in v1["badcases"][:8]
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Agent 评测版本对比报告</title>
<style>
body{{font-family:-apple-system,"PingFang SC",sans-serif;max-width:900px;margin:32px auto;color:#222;font-size:14px}}
h1{{font-size:22px}}h2{{font-size:16px;margin-top:28px;border-bottom:1px solid #ddd;padding-bottom:6px}}
table{{border-collapse:collapse;width:100%;margin-top:10px}}
td,th{{border:1px solid #e0e0e0;padding:8px 10px;text-align:left}}
th{{background:#f6f6f6}}.note{{color:#888;font-size:12px}}
</style></head><body>
<h1>健康管理问答 Agent · 版本对比评测报告</h1>
<p class="note">评测集 {v2['case_count']} 条 · 规则断言 + LLM-as-Judge 双层评分 · 示例数据仅供演示</p>
<h2>核心指标（v1 → v2）</h2>
<table><tr><th>指标</th><th>v1</th><th>v2</th><th>变化</th></tr>{''.join(rows)}</table>
<h2>badcase 归因（v1 遗留问题）</h2>
<table><tr><th>用例</th><th>题型</th><th>根因分类</th><th>问题</th></tr>{bad_rows}</table>
<p class="note">归因口径：检索漏召回 / 知识缺失(时效) / 生成幻觉。v2 通过知识库生效日期过滤与边界规则修复上述问题。</p>
</body></html>"""


def write_reports(v1: dict, v2: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "eval_result_v1.json").write_text(
        json.dumps(v1, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "eval_result_v2.json").write_text(
        json.dumps(v2, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    html_path = out_dir / "version_compare.html"
    html_path.write_text(render_html(v1, v2), encoding="utf-8")
    return html_path
