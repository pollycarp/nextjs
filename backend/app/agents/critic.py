"""Critic Agent — fact-checks the researcher's output."""

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

_PROMPT = """You are a Fact-Checking Specialist. Review the research summary below and identify any unsupported claims or logical gaps.

For each unsupported claim start the line with "CLAIM: ".
If the research is well-supported respond with exactly: "APPROVED: Research is well-supported."

Research Summary:
{research_output}

Fact-Check Review:"""


def run_critic(research_output: str) -> dict:
    """Return critique text and a list of flagged claim strings."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
    )
    response = llm.invoke([HumanMessage(content=_PROMPT.format(research_output=research_output))])
    critique = response.content

    flagged_claims = [
        line.replace("CLAIM:", "").strip()
        for line in critique.splitlines()
        if line.strip().upper().startswith("CLAIM:")
    ]
    return {"critique_output": critique, "flagged_claims": flagged_claims}
