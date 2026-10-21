import argparse
import logging
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

logger = logging.getLogger(__name__)

W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
CHECKBOX = f"{{{W14_NS}}}checkbox"
CHECKED = f"{{{W14_NS}}}checked"
W14_VAL = f"{{{W14_NS}}}val"

PLACEHOLDERS = {"choose an item.", "اختر من القائمة", "اختر عنصراً.", "click or tap here to enter text."}

CHECKED_MARK = "[x]"
UNCHECKED_MARK = "[ ]"


def _sdt_kind(sdt):
    props = sdt.find(qn("w:sdtPr"))
    if props is None:
        return None, False
    box = props.find(CHECKBOX)
    if box is not None:
        state = box.find(CHECKED)
        return "checkbox", state is not None and state.get(W14_VAL) in ("1", "true")
    if props.find(qn("w:showingPlcHdr")) is not None:
        return "placeholder", False
    return None, False


def _sdt_content(sdt):
    content = sdt.find(qn("w:sdtContent"))
    return list(content) if content is not None else []


def _run_text(element):
    pieces = []
    for node in element.iter():
        if node.tag == qn("w:t"):
            pieces.append(node.text or "")
        elif node.tag == qn("w:tab"):
            pieces.append(" ")
        elif node.tag in (qn("w:br"), qn("w:cr")):
            pieces.append("\n")
    return "".join(pieces)


def _inline_text(element):
    if element.tag == qn("w:sdt"):
        kind, checked = _sdt_kind(element)
        if kind == "checkbox":
            return CHECKED_MARK if checked else UNCHECKED_MARK
        if kind == "placeholder":
            return ""
        return "".join(_inline_text(child) for child in _sdt_content(element))
    if element.tag in (qn("w:r"), qn("w:hyperlink"), qn("w:ins"), qn("w:smartTag"), qn("w:fldSimple")):
        if element.tag == qn("w:r"):
            return _run_text(element)
        return "".join(_inline_text(child) for child in element)
    return ""


def _paragraph_text(p):
    text = "".join(_inline_text(child) for child in p)
    lines = [" ".join(line.split()) for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    if text.lower() in PLACEHOLDERS:
        return ""
    return text


def _cell_blocks(tc):
    parts = []
    for child in tc:
        if child.tag == qn("w:p"):
            text = _paragraph_text(child).replace("\n", " ")
            if text:
                parts.append(text)
        elif child.tag == qn("w:tbl"):
            for row in _table_rows(child):
                parts.append(" ; ".join(cell for cell in row if cell))
        elif child.tag == qn("w:sdt"):
            kind, checked = _sdt_kind(child)
            if kind == "checkbox":
                parts.append(CHECKED_MARK if checked else UNCHECKED_MARK)
            elif kind != "placeholder":
                parts.extend(_cell_blocks(_wrap(child)))
    return parts


def _wrap(sdt):
    holder = sdt.find(qn("w:sdtContent"))
    return holder if holder is not None else []


def _row_cells(tr):
    cells = []
    for child in tr:
        if child.tag == qn("w:tc"):
            cells.append((child, None))
        elif child.tag == qn("w:sdt"):
            kind, checked = _sdt_kind(child)
            for inner in _sdt_content(child):
                if inner.tag == qn("w:tc"):
                    cells.append((inner, (kind, checked)))
    return cells


def _is_vertical_continuation(tc):
    props = tc.find(qn("w:tcPr"))
    if props is None:
        return False
    merge = props.find(qn("w:vMerge"))
    return merge is not None and merge.get(qn("w:val")) in (None, "continue")


def _table_rows(tbl):
    rows = []
    for tr in _body_elements(tbl):
        if tr.tag != qn("w:tr"):
            continue
        values = []
        for tc, sdt_info in _row_cells(tr):
            if _is_vertical_continuation(tc):
                values.append("")
                continue
            if sdt_info and sdt_info[0] == "checkbox":
                values.append(CHECKED_MARK if sdt_info[1] else UNCHECKED_MARK)
            elif sdt_info and sdt_info[0] == "placeholder":
                values.append("")
            else:
                values.append(" ".join(_cell_blocks(tc)))
        rows.append(values)
    return rows


def _body_elements(container):
    for child in container:
        if child.tag == qn("w:sdt"):
            yield from _body_elements(_wrap(child))
        else:
            yield child


def extract_blocks(path):
    doc = Document(str(path))
    blocks = []
    for element in _body_elements(doc.element.body):
        if element.tag == qn("w:p"):
            text = _paragraph_text(element)
            if text:
                blocks.append(("paragraph", text))
        elif element.tag == qn("w:tbl"):
            rows = [row for row in _table_rows(element) if any(cell.strip() for cell in row)]
            if rows:
                blocks.append(("table", rows))
    return blocks


def extract_lines(path):
    lines = []
    for kind, content in extract_blocks(path):
        if kind == "paragraph":
            lines.extend(content.split("\n"))
        else:
            lines.extend(" | ".join(row) for row in content)
    return lines


def extract_text(path):
    return "\n".join(extract_lines(path))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract text from Word forms in document order.")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for path in args.paths:
        if not path.exists():
            logger.error("File not found: %s", path)
            continue
        lines = extract_lines(path)
        logger.info("Extracted %d lines from %s", len(lines), path.name)
        sys.stdout.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
