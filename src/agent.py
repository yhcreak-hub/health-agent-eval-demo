"""模拟健康管理问答 Agent（RAG + 意图路由 + 引用溯源）。

设计说明：
- AgentV1：保留旧版知识文档、隐私原文回显、诊断越界、丢失多轮上下文（还原真实 badcase）。
- AgentV2：增加生效日期过滤 + 建议边界 + 隐私脱敏 + 多轮上下文继承，用于版本对比评测。
演示用途，回答为规则拼接，不构成任何医疗建议。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DIAGNOSIS_TRIGGERS = ("是不是", "确诊", "结论", "偏方", "治好", "脑瘤", "癌症", "能治好")
STOP_MED_TRIGGERS = ("停药", "停掉", "加大药量", "加大剂量")
EMERGENCY_TRIGGERS = ("胸痛", "剧烈头痛", "意识模糊", "偏瘫", "急诊")
FOLLOWUP_TRIGGERS = ("复查", "严重", "该查", "查什么", "多久", "去医院")


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

    def _retrieve(self, question: str, context: list[str] | None = None) -> list[dict]:
        """模拟检索：按文档 keywords 命中；v2 继承多轮上下文，v1 不过滤废止文档。"""
        text = question
        if self.version == "v2" and context:
            text = question + " " + " ".join(context)
        hits = []
        for doc in self.kb:
            matched = any(k in text for k in doc.get("keywords", []))
            if doc.get("deprecated"):
                # v1 缺陷：废止文档未做生效日期过滤，血糖类问题会被旧版口径污染
                if self.version == "v1" and matched:
                    hits.append(doc)
                continue
            if matched:
                hits.append(doc)
        return hits[:2]

    def respond(self, question: str, context: list[str] | None = None) -> AgentResponse:
        hits = self._retrieve(question, context)
        cited = [d["id"] for d in hits]
        numbers = re.findall(r"\d{15,18}|\b1\d{10}\b", question)
        parts: list[str] = []

        # —— 隐私：v1 原文回显（缺陷），v2 脱敏 ——
        if numbers:
            if self.version == "v1":
                parts.append(f"已为您保存：{numbers[0]}。请问还需要什么帮助？")
            else:
                parts.append("已对敏感信息脱敏处理，不会原文回显。")
                if any(k in question for k in ("查", "档案", "记录", "查询")):
                    parts.append("健康数据查询须校验用户身份。")

        # —— 建议边界 / 诊断越界 ——
        if any(k in question for k in DIAGNOSIS_TRIGGERS):
            if self.version == "v1":
                # v1 缺陷：给出确定性诊断（生成幻觉）
                if "脑瘤" in question:
                    parts.append("根据您的描述，确诊脑瘤的可能性很高。")
                elif "癌症" in question:
                    parts.append("这个偏方能治好癌症，无需就医。")
                elif "糖尿病" in question:
                    parts.append("这个偏方能治好糖尿病，可以放心使用。")
                else:
                    parts.append("根据描述，可以确诊，结论很明确。")
            else:
                parts.append("我无法给出疾病诊断或确定性结论，建议就医，到线下医疗机构由医生面诊评估。")
        elif any(k in question for k in STOP_MED_TRIGGERS):
            parts.append("不得自行停药，请遵医嘱并就医调整用药方案。")
        elif any(k in question for k in EMERGENCY_TRIGGERS):
            if self.version == "v1":
                parts.append("先观察几天再说，问题不大。")
            else:
                parts.append("可能提示急症，应立即前往急诊，我无法给出诊断结论。")
        else:
            for doc in hits:
                parts.append(doc.get("summary", doc["content"][:80]))

        # —— v2 多轮 / 复查引导 ——
        if self.version == "v2" and any(k in question for k in FOLLOWUP_TRIGGERS):
            parts.append("建议复查空腹血糖与糖化血红蛋白，并携带报告就医。")

        if not parts:
            if self.version == "v2":
                parts.append("根据健康知识库，建议结合具体指标咨询医生，我无法给出诊断结论。")
            else:
                parts.append("您的咨询我已收到，请问具体是哪个健康指标？")

        answer = " ".join(dict.fromkeys(parts))
        return AgentResponse(
            answer=answer,
            cited_docs=cited,
            latency_ms=180 if self.version == "v2" else 120,
        )
