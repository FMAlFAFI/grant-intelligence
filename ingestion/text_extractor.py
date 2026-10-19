"""Extract text from Word (.docx) grant forms, Arabic or English."""
import logging
import sys
from pathlib import Path

from docx import Document

logger = logging.getLogger(__name__)


def extract_text(path):
    """Return all text in a .docx: paragraphs first, then table rows."""
    doc = Document(path)
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = []
            seen = set()
            for cell in row.cells:
                if cell._tc in seen:  # a merged cell appears once per column it spans
                    continue
                seen.add(cell._tc)
                cells.append(cell.text.strip())
            if any(cells):
                lines.append(" | ".join(cells))
    logger.info("Extracted %d lines from %s", len(lines), Path(path).name)
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.stdout.reconfigure(encoding="utf-8")
    print(extract_text(sys.argv[1]))
