# -*- coding: utf-8 -*-
"""從 電流急急棒零件清單_完整版.xlsx 擷取內嵌圖片並產生 buzzwire-parts-data.json"""
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
XLSX = BASE / "電流急急棒零件清單_完整版.xlsx"
OUT_DIR = BASE / "assets" / "buzzwire-parts"
OUT_JSON = BASE / "assets" / "buzzwire-parts-data.json"
OUT_JS = BASE / "assets" / "buzzwire-parts-data.js"

# Excel 未內嵌圖片時，改用網站既有元件照片（若檔案不存在瀏覽器顯示破圖）
IMAGE_FALLBACK = {
    "rgb_LED": "元件圖片區/三色LED.JPG",
    "機械按鈕": "元件圖片區/按鈕.JPG",
}

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
}


def col_letters_to_index(s):
    n = 0
    for ch in s:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def parse_shared_strings(z):
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    strings = []
    for si in root.findall("main:si", NS):
        t = si.find("main:t", NS)
        if t is not None and t.text is not None:
            strings.append(t.text)
            continue
        parts = []
        for r in si.findall("main:r", NS):
            rt = r.find("main:t", NS)
            if rt is not None and rt.text:
                parts.append(rt.text)
        strings.append("".join(parts))
    return strings


def load_drawing_anchors(z, drawing_rels_path, drawing_xml_path):
    rels_root = ET.fromstring(z.read(drawing_rels_path))
    rid_to_target = {}
    for rel in rels_root:
        rid = rel.get("Id")
        tgt = rel.get("Target")
        if tgt:
            rid_to_target[rid] = "xl/" + tgt.replace("../", "")

    droot = ET.fromstring(z.read(drawing_xml_path))

    def local(tag):
        return tag.split("}")[-1]

    anchors = []
    xdr_ns = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
    a_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
    r_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    for elem in droot.iter():
        if local(elem.tag) not in ("oneCellAnchor", "twoCellAnchor"):
            continue
        frm = elem.find(f"{{{xdr_ns}}}from")
        if frm is None:
            continue
        col = int(frm.find(f"{{{xdr_ns}}}col").text)
        row = int(frm.find(f"{{{xdr_ns}}}row").text)
        pic = elem.find(f".//{{{xdr_ns}}}pic")
        if pic is None:
            continue
        blip = pic.find(f".//{{{a_ns}}}blip")
        if blip is None:
            continue
        embed = blip.get(f"{{{r_ns}}}embed")
        media_path = rid_to_target.get(embed, "")
        anchors.append({"col": col, "row": row, "media": media_path})
    return anchors


def parse_sheet_rows(z, sheet_path, strings):
    root = ET.fromstring(z.read(sheet_path))
    rows_out = []
    for row in root.findall("main:sheetData/main:row", NS):
        r = int(row.get("r"))
        cells = {}
        for c in row.findall("main:c", NS):
            ref = c.get("r")
            m = re.match(r"^([A-Z]+)", ref)
            if not m:
                continue
            t = c.get("t")
            v = c.find("main:v", NS)
            if v is not None and v.text is not None:
                val = v.text
                if t == "s":
                    val = strings[int(val)]
                cells[ref] = val
            else:
                cells[ref] = None
        rows_out.append((r, cells))
    return rows_out


def main():
    if not XLSX.is_file():
        raise SystemExit(f"找不到: {XLSX}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(XLSX, "r") as z:
        strings = parse_shared_strings(z)
        anchors1 = load_drawing_anchors(
            z, "xl/drawings/_rels/drawing1.xml.rels", "xl/drawings/drawing1.xml"
        )
        # sheet1: 圖片錨點在 A 欄；OOXML row 為 0-based → Excel 列 = row + 1
        # 依列號排序後「每列只取第一個錨點」，避免 XML 順序造成覆寫錯誤
        row_to_media = {}
        for a in sorted(anchors1, key=lambda x: (x["row"], x["col"])):
            if a["col"] != 0:
                continue
            excel_row = a["row"] + 1
            if excel_row not in row_to_media:
                row_to_media[excel_row] = a["media"]

        rows = parse_sheet_rows(z, "xl/worksheets/sheet1.xml", strings)

        parts = []
        used_media = set()

        for r, cells in rows:
            if r < 2:
                continue
            name = cells.get("B" + str(r))
            if not name or not str(name).strip():
                continue
            qty = cells.get("C" + str(r))
            loc = cells.get("D" + str(r))
            slot = cells.get("E" + str(r))
            media = row_to_media.get(r)
            safe_slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", str(name).strip())[:40]
            ext = Path(media).suffix.lower() if media else ""
            file_key = f"row-{r:02d}{ext}" if media else None
            web_path = f"assets/buzzwire-parts/{file_key}" if file_key else None

            if media and media in z.namelist():
                data = z.read(media)
                out_path = OUT_DIR / file_key
                out_path.write_bytes(data)
                used_media.add(media)

            final_img = web_path
            src_note = "excel"
            if not final_img:
                fb = IMAGE_FALLBACK.get(str(name).strip())
                if fb:
                    final_img = fb
                    src_note = "fallback"

            parts.append(
                {
                    "row": r,
                    "name": name,
                    "qty": qty,
                    "location": loc,
                    "slot": slot,
                    "image": final_img,
                    "imageSource": src_note if final_img else None,
                    "slug": safe_slug,
                }
            )

    payload = {"title": "電流急急棒零件清單", "parts": parts}
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    OUT_JS.write_text(
        "window.BUZZWIRE_PARTS_DATA = "
        + json.dumps(payload, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )
    print(f"已輸出 {len(parts)} 筆 → {OUT_JSON}")
    print(f"已輸出 JS → {OUT_JS}")
    print(f"圖片目錄: {OUT_DIR} ({len(list(OUT_DIR.glob('*')))} 個檔案)")


if __name__ == "__main__":
    main()
