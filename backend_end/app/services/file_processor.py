from __future__ import annotations

"""
FileProcessor — PDF / DOCX / TXT → list of text chunks.

Chunking: ~512 tokens ≈ 2048 chars, overlap 64 tokens ≈ 256 chars.
"""
import io


CHUNK_CHARS = 2048
OVERLAP_CHARS = 256


class FileProcessor:
    def extract_chunks(
        self, content: bytes, filename: str, content_type: str
    ) -> list[str]:
        text = self._extract_text(content, filename, content_type)
        return self._split(text)

    def _extract_text(self, content: bytes, filename: str, ct: str) -> str:
        fname = filename.lower()
        if ct == "application/pdf" or fname.endswith(".pdf"):
            return self._from_pdf(content)
        if (
            ct == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or fname.endswith(".docx")
        ):
            return self._from_docx(content)
        # Fallback: plain text
        return content.decode("utf-8", errors="replace")

    @staticmethod
    def _from_pdf(content: bytes) -> str:
        import pdfplumber

        parts: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        return "\n".join(parts)

    @staticmethod
    def _from_docx(content: bytes) -> str:
        from docx import Document

        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    @staticmethod
    def _split(text: str) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + CHUNK_CHARS
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += CHUNK_CHARS - OVERLAP_CHARS
        return chunks
