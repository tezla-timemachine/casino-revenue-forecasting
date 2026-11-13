"""Build the Word copy of a Markdown document: landscape A4, Arial, bordered tables with a shaded header row.

    python3 scripts/build_word.py docs/week4-brief-traceability.md

Writes the .docx next to the .md. Needs pandoc. The Markdown file stays the master copy.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PAGE_W, PAGE_H, MARGIN = 16838, 11906, 850          # landscape A4, 1.5 cm margins, in twips
TABLE_W = PAGE_W - 2 * MARGIN
BORDER = "".join(f'<w:{e} w:val="single" w:sz="4" w:space="0" w:color="A6A6A6"/>'
                 for e in ("top", "left", "bottom", "right", "insideH", "insideV"))
ARIAL = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="Arial" w:cs="Arial" />'


def rewrite(docx: Path, edit) -> None:
    """Apply edit(name, text) -> text to the XML parts of a .docx, in place."""
    with zipfile.ZipFile(docx) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist() if not i.filename.endswith("/")]
    with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            if info.filename in ("word/document.xml", "word/styles.xml"):
                data = edit(info.filename, data.decode("utf-8")).encode("utf-8")
            z.writestr(info, data)


def style_template(name: str, xml: str) -> str:
    if name == "word/styles.xml":
        xml = re.sub(r'<w:rFonts w:asciiTheme="[^"]*"[^/]*/>', ARIAL, xml)
        xml = re.sub(r'(<w:style[^>]*w:styleId="Normal"[^>]*>\s*<w:name w:val="Normal" />\s*<w:qFormat />)',
                     r'\1<w:rPr>' + ARIAL + r'<w:sz w:val="20" /><w:szCs w:val="20" /></w:rPr>', xml, count=1)
        xml = xml.replace('<w:spacing w:after="180" w:before="180" />', '<w:spacing w:after="80" w:before="80" />', 1)
    if name == "word/document.xml":
        xml = xml.replace("<w:sectPr>", f'<w:sectPr><w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}" w:orient="landscape" />'
                          f'<w:pgMar w:top="{MARGIN}" w:right="{MARGIN}" w:bottom="{MARGIN}" w:left="{MARGIN}" w:header="425" w:footer="425" w:gutter="0" />', 1)
    return xml


def format_tables(name: str, xml: str) -> str:
    if name != "word/document.xml":
        return xml

    def one(tbl: str) -> str:
        rows = re.findall(r"<w:tr>.*?</w:tr>|<w:tr [^>]*>.*?</w:tr>", tbl, flags=re.S)
        texts = [["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", c)) for c in re.findall(r"<w:tc>.*?</w:tc>", r, flags=re.S)] for r in rows]
        n = max(len(t) for t in texts)
        weights = [max(8, min(70, max((len(t[k]) for t in texts if k < len(t)), default=8))) for k in range(n)]
        widths = [int(TABLE_W * w / sum(weights)) for w in weights]
        tbl = re.sub(r"<w:tblPr>.*?</w:tblPr>", f'<w:tblPr><w:tblStyle w:val="Table" /><w:tblW w:w="{TABLE_W}" w:type="dxa" />'
                     f'<w:tblBorders>{BORDER}</w:tblBorders><w:tblLayout w:type="fixed" /><w:tblCellMar><w:top w:w="40" w:type="dxa"/>'
                     '<w:left w:w="80" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar>'
                     '<w:tblLook w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="0" w:val="0020" /></w:tblPr>',
                     tbl, count=1, flags=re.S)
        tbl = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}" />' for w in widths) + "</w:tblGrid>",
                     tbl, count=1, flags=re.S)
        for ri, r in enumerate(rows):
            new = r
            for ci, c in enumerate(re.findall(r"<w:tc>.*?</w:tc>", r, flags=re.S)):
                shade = '<w:shd w:val="clear" w:color="auto" w:fill="DCE6F1" />' if ri == 0 else ""
                nc = c.replace("<w:tcPr />", f'<w:tcPr><w:tcW w:w="{widths[min(ci, n - 1)]}" w:type="dxa" />{shade}</w:tcPr>', 1)
                if ri == 0:
                    nc = re.sub(r"<w:r><w:t", "<w:r><w:rPr><w:b /></w:rPr><w:t", nc)
                    nc = re.sub(r"<w:r><w:rPr>(?!<w:b)", "<w:r><w:rPr><w:b />", nc)
                new = new.replace(c, nc, 1)
            tbl = tbl.replace(r, new, 1)
        return tbl

    return "".join(one(p) if p.startswith("<w:tbl>") else p for p in re.split(r"(<w:tbl>.*?</w:tbl>)", xml, flags=re.S))


def main(md_path: str) -> None:
    md = Path(md_path)
    out = md.with_suffix(".docx")
    with tempfile.TemporaryDirectory() as tmp:
        ref = Path(tmp) / "reference.docx"
        ref.write_bytes(subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"], capture_output=True, check=True).stdout)
        rewrite(ref, style_template)
        # gfm-tex_math_dollars: dollar amounts are money, not maths
        subprocess.run(["pandoc", str(md), "-f", "gfm-tex_math_dollars", "-t", "docx", "--reference-doc", str(ref),
                        "--resource-path", str(md.parent), "-o", str(out)], check=True)  # images relative to the .md
    rewrite(out, format_tables)
    print(f"Written: {out}")


if __name__ == "__main__":
    main(sys.argv[1])
