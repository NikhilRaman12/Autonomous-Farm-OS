from __future__ import annotations
import os
from .models import FarmState, Proposal

def explain_decision(s: FarmState, p: Proposal) -> str:
    # LangChain is optional at runtime so the competition demo works without an API key.
    if os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage
            llm = ChatOpenAI(model=os.getenv("FIELDNODE_LLM_MODEL", "gpt-4o-mini"), temperature=0)
            msg = llm.invoke([HumanMessage(content=f"Explain this farm decision in one concise operational sentence: {p.model_dump()}")])
            return str(msg.content).strip()
        except Exception:
            pass
    return f"{p.agent} selected {p.action} from current farm state using urgency, crop stage and resource constraints."
