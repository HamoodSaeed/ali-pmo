from pathlib import Path

import fitz

from parsers.document_parser import extract_pdf_text, extract_txt_text


def test_pdf_text_extraction(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Project Name: PDF Intake\nScope: Build PMO controls")
    document.save(pdf_path)
    document.close()

    text, page_count = extract_pdf_text(pdf_path)

    assert page_count == 1
    assert "PDF Intake" in text
    assert "Build PMO controls" in text


def test_txt_text_extraction(tmp_path: Path) -> None:
    txt_path = tmp_path / "sample.txt"
    txt_path.write_text("Project Name: TXT Intake\nObjectives:\n- Improve reporting", encoding="utf-8")

    text, page_count = extract_txt_text(txt_path)

    assert page_count == 1
    assert "TXT Intake" in text
    assert "Improve reporting" in text
