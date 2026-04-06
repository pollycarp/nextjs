"""
Shared pytest fixtures for all phases.
"""

import io
import pytest
import chromadb

import app.services.ingestion as ingestion_module


# ── ChromaDB isolation ────────────────────────────────────────────────────── #

@pytest.fixture(autouse=True)
def reset_chroma():
    """Give every test its own empty in-memory ChromaDB."""
    ingestion_module._chroma_client = chromadb.EphemeralClient()
    yield
    ingestion_module._chroma_client = None


# ── Document fixtures ─────────────────────────────────────────────────────── #

def _build_minimal_pdf(text: str) -> bytes:
    """
    Build a minimal but valid PDF-1.4 with one page containing *text*.
    Parentheses and backslashes in *text* must be escaped for PDF string syntax.
    """
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET".encode()

    objs: list[bytes] = [
        b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n",
        b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n",
        (
            b"3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>>\nendobj\n"
        ),
        f"4 0 obj\n<</Length {len(content_stream)}>>\nstream\n".encode()
        + content_stream
        + b"\nendstream\nendobj\n",
        b"5 0 obj\n<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>\nendobj\n",
    ]

    pdf = b"%PDF-1.4\n"
    offsets: list[int] = []
    for obj in objs:
        offsets.append(len(pdf))
        pdf += obj

    xref_pos = len(pdf)
    xref = f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"
    trailer = (
        f"trailer\n<</Size {len(objs) + 1} /Root 1 0 R>>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    )
    pdf += (xref + trailer).encode()
    return pdf


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return _build_minimal_pdf(
        "This document discusses methodology and research approaches in social science."
    )


@pytest.fixture
def sample_docx_bytes() -> bytes:
    from docx import Document as DocxDocument

    doc = DocxDocument()
    doc.add_heading("Research Methodology", 0)
    doc.add_paragraph(
        "This document discusses methodology and research approaches. "
        "The methodology section outlines the key research methods used in social science."
    )
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
def sample_txt_bytes() -> bytes:
    return (
        b"This document discusses methodology and research approaches in social science. "
        b"The study examines various methodological frameworks used in field research. "
        b"Qualitative and quantitative methods are both covered extensively."
    )
