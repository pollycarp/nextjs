"""Writer Agent — produces the final structured Markdown report."""

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

_PROMPT = """You are a Research Report Writer. Produce a structured Markdown research report.

The report MUST contain these sections (use ## headings):
## Introduction
## Methods
## Findings
## Conclusion
## References

Use in-text citations like [1], [2] where appropriate.

Query: {query}

Research Summary:
{research_output}

Critic Feedback:
{critique_output}

Markdown Report:"""


def run_writer(
    query: str,
    research_output: str,
    critique_output: str,
    sources: list,
) -> dict:
    """Produce a structured Markdown report."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.3,
    )
    response = llm.invoke([
        HumanMessage(content=_PROMPT.format(
            query=query,
            research_output=research_output,
            critique_output=critique_output,
        ))
    ])
    return {"final_report": response.content}
