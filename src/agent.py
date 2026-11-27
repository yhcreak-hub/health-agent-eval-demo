"""模拟健康管理问答 Agent（RAG + 意图路由 + 引用溯源）。

设计说明：
- AgentV1：保留旧版知识文档，对时效型问题会引用已废止文档（还原真实 badcase）。
- AgentV2：增加生效日期过滤 + 建议边界 + 隐私脱敏，用于版本对比评测。
演示用途，回答为规则拼接，不构成任何医疗建议。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class AgentResponse:
    answer: str
    cited_docs: list[str] = field(default_factory=list)
    latency_ms: int = 0


class HealthQAAgent:
    """模拟健康问答 Agent，version 控制评测对比的两个版本。"""

    def __init__(self, version: str = "v2", kb_path: Path | None = None):
        assert version in ("v1", "v2"), "version must be v1 or v2"
        self.version = version
        kb_path = kb_path or DATA_DIR / "knowledge_base.json"
        self.kb = json.loads(kb_path.read_text(encoding="utf-8"))["documents"]

    def _retrieve(self, question: str) -> list[dict]:
        """模拟检索：按关键词命中文档，v1 不过滤废止文档。"""
        keywords = self._keywords(question)
        hits = []
        for doc in self.kb:
            matched = any(k in doc["content"] or k in doc["title"] for k in keywords)
            if doc.get("deprecated"):
                # v1 缺陷：废止文档未做生效日期过滤，血糖类问题会被旧版口径污染
                if self.version == "v1" and matched:
                    hits.append(doc)
                continue
            if matched:
                hits.append(doc)
        return hits[:2]

    @staticmethod
    def _keywords(text: str) -> list[str]:
        candidates = ["血糖", "血压", "糖化", "评估问卷", "身份证", "手机号", "偏方", "停药", "头晕"]
        return [k for k in candidates if k in text]

    def respond(self, question: str, context: list[str] | None = None) -> AgentResponse:
        hits = self._retrieve(question)
        cited = [d["id"] for d in hits]

        # —— 隐私脱敏：v2 对敏感信息做处理，v1 直接回显（暴露问题）——
        if self.version == "v1" and re.search(r"\d{15,18}|\d{11}", question):
            numbers = re.findall(r"\d{15,18}|\d{11}", question)
            return AgentResponse(
                answer=f"已为您保存：{numbers[0]}。请问还需要什么帮助？",
                cited_docs=cited,
                latency_ms=120,
            )

        parts = []
        # —— 建议边界：v2 遇到诊断类问题主动拒答并引导就医 ——
        if any(k in question for k in ("是不是", "确诊", "结论", "偏方", "治好")):
            parts.append("我无法给出疾病诊断或确定性结论，建议到线下医疗机构由医生面诊评估。")
        elif "停药" in question:
            parts.append("不得自行停药，请遵医嘱并就医调整用药方案。")
        else:
            for doc in hits:
                snippet = doc["content"]
                if doc["id"] == "KB-001":
                    parts.append("空腹血糖正常参考范围 3.9–6.1 mmol/L；6.1–7.0 mmol/L 为空腹血糖受损，建议复查并就医。")
                elif doc["id"] == "KB-002":
                    parts.append("空腹血糖正常范围 3.9–7.0 mmol/L。")  # 旧版口径：时效 badcase
                elif doc["id"] == "KB-003":
                    parts.append("收缩压持续高于 140 mmHg 建议就医调整用药，不得自行停药。")
                elif doc["id"] == "KB-004":
                    parts.append("健康评估结果仅供风险提示，不能作为疾病诊断依据。")
                elif doc["id"] == "KB-005":
                    parts.append("身份证号、手机号等属于敏感信息，需脱敏处理并校验用户身份。")
                else:
                    parts.append(snippet[:80])

        if self.version == "v2":
            if re.search(r"\d{11,18}", question):
                parts.append("已对敏感信息脱敏处理，不会原文回显。")
            if any(k in question for k in ("复查", "严重", "该查")):
                parts.append("建议复查空腹血糖与糖化血红蛋白，并携带报告就医。")
            if not parts:
                parts.append("根据健康知识库，建议结合具体指标咨询医生，我无法给出诊断结论。")

        answer = " ".join(dict.fromkeys(parts))
        return AgentResponse(
            answer=answer,
            cited_docs=cited,
            latency_ms=180 if self.version == "v2" else 120,
        )
