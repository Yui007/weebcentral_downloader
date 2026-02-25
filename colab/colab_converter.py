"""
colab_converter.py — PDF, CBZ (with ComicInfo.xml), and raw Images output
"""

import io
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from PIL import Image
from fpdf import FPDF


# ---------------------------------------------------------------------------
# ComicInfo.xml  (ComicRack / Kavita / Komga / CDisplayEx standard)
# ---------------------------------------------------------------------------

def build_comic_info_xml(manga_info: dict, chapter_number: int, total_chapters: int) -> str:
    """Return a pretty-printed ComicInfo.xml string."""
    root = ET.Element("ComicInfo")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")

    def add(tag, value):
        if value:
            el = ET.SubElement(root, tag)
            el.text = str(value)

    add("Title",       manga_info.get("title", ""))
    add("Series",      manga_info.get("title", ""))
    add("Number",      str(chapter_number))
    add("Count",       str(total_chapters))
    add("Writer",      ", ".join(manga_info.get("authors", [])))
    add("Summary",     manga_info.get("description", ""))
    add("Year",        manga_info.get("released", ""))
    add("Genre",       ", ".join(manga_info.get("tags", [])))
    add("Web",         manga_info.get("series_url", ""))
    add("LanguageISO", "en")
    add("Manga",       "Yes")

    raw      = ET.tostring(root, encoding="unicode")
    reparsed = minidom.parseString(raw)
    return reparsed.toprettyxml(indent="  ", encoding=None)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def images_to_pdf(image_bytes_list: list, output_path: str) -> None:
    """Convert a list of raw image bytes into a single PDF file."""
    pdf = FPDF()
    pdf.set_auto_page_break(False)

    for img_bytes in image_bytes_list:
        if not img_bytes:
            continue
        try:
            img   = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            w, h  = img.size
            pdf_w = 210.0
            pdf_h = round(h * pdf_w / w, 2)
            pdf.add_page(format=(pdf_w, pdf_h))

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            buf.seek(0)
            pdf.image(buf, x=0, y=0, w=pdf_w, h=pdf_h, type="JPEG")
        except Exception as e:
            print(f"    ⚠️  Skipped broken image in PDF: {e}")

    pdf.output(output_path)


# ---------------------------------------------------------------------------
# CBZ
# ---------------------------------------------------------------------------

def images_to_cbz(
    image_bytes_list: list,
    output_path: str,
    manga_info: dict,
    chapter_number: int,
    total_chapters: int,
) -> None:
    """Pack images + ComicInfo.xml into a CBZ archive."""
    comic_info = build_comic_info_xml(manga_info, chapter_number, total_chapters)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("ComicInfo.xml", comic_info)   # must be first for most readers

        page_num = 1
        for img_bytes in image_bytes_list:
            if not img_bytes:
                continue
            try:
                img = Image.open(io.BytesIO(img_bytes))
                fmt = img.format or "JPEG"
                ext = fmt.lower().replace("jpeg", "jpg")
                buf = io.BytesIO()
                img.save(buf, format=fmt)
                zf.writestr(f"{str(page_num).zfill(4)}.{ext}", buf.getvalue())
                page_num += 1
            except Exception as e:
                print(f"    ⚠️  Skipped broken image in CBZ: {e}")


# ---------------------------------------------------------------------------
# Raw images folder
# ---------------------------------------------------------------------------

def images_to_folder(image_bytes_list: list, output_dir: str) -> int:
    """
    Save raw images into a folder, one file per page.
    Returns the number of pages successfully saved.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    saved = 0

    for page_num, img_bytes in enumerate(image_bytes_list, start=1):
        if not img_bytes:
            continue
        try:
            img = Image.open(io.BytesIO(img_bytes))
            fmt = img.format or "JPEG"
            ext = fmt.lower().replace("jpeg", "jpg")
            out = os.path.join(output_dir, f"{str(page_num).zfill(4)}.{ext}")
            with open(out, "wb") as f:
                f.write(img_bytes)
            saved += 1
        except Exception as e:
            print(f"    ⚠️  Skipped broken image on save: {e}")

    return saved
