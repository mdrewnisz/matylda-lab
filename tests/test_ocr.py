from __future__ import annotations

from pathlib import Path


def test_image_uses_ocr(monkeypatch, tmp_path: Path):
    from matylda_lite import docs_manager
    from matylda_lite.ocr import OCRResult

    image = tmp_path / "scan.png"
    image.write_bytes(b"fake image")
    monkeypatch.setattr(
        docs_manager,
        "recognize_file",
        lambda _path: OCRResult("Rozpoznany tekst dokumentu", "macos_vision"),
    )

    text, method, error = docs_manager.extract_text_details(image)

    assert text == "Rozpoznany tekst dokumentu"
    assert method == "macos_vision"
    assert error is None


def test_scanned_pdf_falls_back_to_ocr(monkeypatch, tmp_path: Path):
    from matylda_lite import docs_manager
    from matylda_lite.ocr import OCRResult
    import pdfminer.high_level

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"fake pdf")
    monkeypatch.setattr(pdfminer.high_level, "extract_text", lambda _path: "  \n")
    monkeypatch.setattr(
        docs_manager,
        "recognize_file",
        lambda _path: OCRResult("Tekst ze skanu PDF", "macos_vision"),
    )

    text, method, error = docs_manager.extract_text_details(pdf)

    assert text == "Tekst ze skanu PDF"
    assert method == "macos_vision"
    assert error is None


def test_text_pdf_skips_ocr(monkeypatch, tmp_path: Path):
    from matylda_lite import docs_manager
    import pdfminer.high_level

    pdf = tmp_path / "text.pdf"
    pdf.write_bytes(b"fake pdf")
    extracted = "To jest zwykły dokument PDF zawierający wystarczająco dużo czytelnego tekstu."
    monkeypatch.setattr(pdfminer.high_level, "extract_text", lambda _path: extracted)

    def fail_if_called(_path):
        raise AssertionError("OCR should not run for a text PDF")

    monkeypatch.setattr(docs_manager, "recognize_file", fail_if_called)

    text, method, error = docs_manager.extract_text_details(pdf)

    assert text == extracted
    assert method == "pdf_text"
    assert error is None


def test_upload_reports_ocr_method(monkeypatch, tmp_path: Path):
    from matylda_lite import docs_manager
    from matylda_lite.ocr import OCRResult

    monkeypatch.setattr(docs_manager, "ROOT", tmp_path)
    monkeypatch.setattr(docs_manager, "DOCS_ATTACHED_DIR", tmp_path)
    monkeypatch.setattr(
        docs_manager,
        "recognize_file",
        lambda _path: OCRResult("Treść faktury", "macos_vision"),
    )

    doc = docs_manager.save_uploaded("faktura.jpg", b"fake image")

    assert doc["extracted_text"] == "Treść faktury"
    assert doc["extraction_method"] == "macos_vision"
    assert doc["extraction_error"] is None
