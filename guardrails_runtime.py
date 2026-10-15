from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from nemoguardrails import LLMRails,RailsConfig
from nemoguardrails.rails.llm.options import RailStatus,RailType
from dotenv import load_dotenv
@dataclass
class GuardrailDecision:
    allowed: bool
    text: str
    status: str
    rail: str | None = None

# RAG GUARDRAILS
class RAGGuardrails:
    def __init__(self, config_path: str | Path = ("guardrails_config")):
        # LOAD NEMO CONFIGURATION
        load_dotenv(override=True)
        config = RailsConfig.from_path(str(config_path))
        # CREATE RAIL ENGINE ONCE
        self.rails = LLMRails(config)
        
    # INPUT GUARDRAILS
    async def check_input(self,user_text: str) -> GuardrailDecision:
        result = await (
            self.rails.check_async(
                messages=[
                    {"role":"user",
                    "content":user_text
                    }],
                rail_types=[RailType.INPUT])
        )

        # BLOCKED
        if result.status == RailStatus.BLOCKED:
            return GuardrailDecision(
                allowed=False,
                text=(result.content
                    or
                    (
                        "I can only help with "
                        "safe questions related "
                        "to the indexed documents "
                        "and this RAG application."
                    )),
                status="blocked",
                rail=getattr(result,"rail",None))

        if result.status == RailStatus.MODIFIED:
            safe_text = (result.content or user_text)
            return GuardrailDecision(allowed=True, text=safe_text, status="modified",rail=None)
        # PASSED
        return GuardrailDecision(allowed=True,text=user_text,status="passed",rail=None)

    # OUTPUT GUARDRAILS
    async def check_output(self,user_text: str,assistant_text: str) -> GuardrailDecision:
        result = await self.rails.check_async(
                messages=[
                    {
                        "role":"user",
                        "content": user_text,
                    },

                    {
                        "role":"assistant",
                        "content": assistant_text,
                    }],

                rail_types=[RailType.OUTPUT])
        
        # BLOCKED
        if result.status == RailStatus.BLOCKED:
            return GuardrailDecision(
                allowed=False,
                text=(
                    result.content
                    or
                    ("The generated answer was blocked by the security policy.")),
                status="blocked",
                rail=getattr(result,"rail",None)
            )
 
        # output PII was masked.
        if result.status == RailStatus.MODIFIED:
            safe_text = (result.content or assistant_text)
            return GuardrailDecision(
                allowed=True,
                text=safe_text,
                status="modified",
                rail=None)
        # PASSED
        return GuardrailDecision(
            allowed=True,
            text=assistant_text,
            status="passed",
            rail=None)