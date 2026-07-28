"""Local OCR adapter for Matylda Lab.

On macOS this uses the system Vision framework through PyObjC. PDF pages are
rendered with Quartz before recognition, so scanned PDFs do not require
Tesseract or Poppler.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import sys
from typing import Any, Iterable


OCR_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff", ".heic", ".webp"})
OCR_MAX_PDF_PAGES = 30
OCR_MAX_CHARS = 30000


@dataclass(frozen=True)
class OCRResult:
    text: str
    engine: str | None
    error: str | None = None


def recognize_file(path: Path) -> OCRResult:
    """Recognize text from an image or scanned PDF using a local OCR engine."""
    if sys.platform != "darwin":
        return OCRResult("", None, "OCR jest obecnie dostępny lokalnie tylko na macOS.")
    try:
        if path.suffix.lower() == ".pdf":
            images = _render_pdf_pages(path)
        elif path.suffix.lower() in OCR_IMAGE_SUFFIXES:
            image = _load_image(path)
            images = [image] if image is not None else []
        else:
            return OCRResult("", None, f"Nieobsługiwany format OCR: {path.suffix or 'brak'}")

        if not images:
            return OCRResult("", "macos_vision", "Nie udało się przygotować obrazu do OCR.")

        pages: list[str] = []
        for page_number, image in enumerate(images, start=1):
            page_text = _recognize_image(image).strip()
            if page_text:
                if len(images) > 1:
                    pages.append(f"--- Strona {page_number} ---\n{page_text}")
                else:
                    pages.append(page_text)
            if sum(len(page) for page in pages) >= OCR_MAX_CHARS:
                break
        text = "\n\n".join(pages)[:OCR_MAX_CHARS]
        if not text:
            return OCRResult("", "macos_vision", "OCR nie wykrył czytelnego tekstu.")
        return OCRResult(text, "macos_vision")
    except ImportError:
        return OCRResult(
            "",
            None,
            "Brakuje PyObjC/Quartz wymaganych przez lokalny OCR macOS.",
        )
    except Exception as exc:  # noqa: BLE001
        return OCRResult("", "macos_vision", f"Błąd OCR: {exc}")


@lru_cache(maxsize=1)
def _load_vision_classes() -> tuple[Any, Any]:
    import objc  # type: ignore

    objc.loadBundle(
        "Vision",
        globals(),
        bundle_path="/System/Library/Frameworks/Vision.framework",
    )
    return (
        objc.lookUpClass("VNRecognizeTextRequest"),
        objc.lookUpClass("VNImageRequestHandler"),
    )


def _load_image(path: Path) -> Any | None:
    from Foundation import NSURL  # type: ignore
    from Quartz import (  # type: ignore
        CGImageSourceCreateImageAtIndex,
        CGImageSourceCreateWithURL,
    )

    source = CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(str(path)), None)
    if source is None:
        return None
    return CGImageSourceCreateImageAtIndex(source, 0, None)


def _render_pdf_pages(path: Path) -> list[Any]:
    from Foundation import NSURL  # type: ignore
    import Quartz  # type: ignore

    document = Quartz.CGPDFDocumentCreateWithURL(NSURL.fileURLWithPath_(str(path)))
    if document is None:
        return []
    page_count = min(Quartz.CGPDFDocumentGetNumberOfPages(document), OCR_MAX_PDF_PAGES)
    images: list[Any] = []
    for page_number in range(1, page_count + 1):
        page = Quartz.CGPDFDocumentGetPage(document, page_number)
        if page is None:
            continue
        box = Quartz.CGPDFPageGetBoxRect(page, Quartz.kCGPDFMediaBox)
        longest_edge = max(box.size.width, box.size.height)
        scale = min(2.5, 2200 / longest_edge) if longest_edge else 1.0
        width = max(1, int(box.size.width * scale))
        height = max(1, int(box.size.height * scale))
        color_space = Quartz.CGColorSpaceCreateDeviceRGB()
        context = Quartz.CGBitmapContextCreate(
            None,
            width,
            height,
            8,
            width * 4,
            color_space,
            Quartz.kCGImageAlphaPremultipliedLast,
        )
        if context is None:
            continue
        Quartz.CGContextSetRGBFillColor(context, 1, 1, 1, 1)
        Quartz.CGContextFillRect(context, Quartz.CGRectMake(0, 0, width, height))
        transform = Quartz.CGPDFPageGetDrawingTransform(
            page,
            Quartz.kCGPDFMediaBox,
            Quartz.CGRectMake(0, 0, width, height),
            0,
            True,
        )
        Quartz.CGContextConcatCTM(context, transform)
        Quartz.CGContextDrawPDFPage(context, page)
        image = Quartz.CGBitmapContextCreateImage(context)
        if image is not None:
            images.append(image)
    return images


def _recognize_image(image: Any) -> str:
    request_class, handler_class = _load_vision_classes()
    request = request_class.alloc().init()
    request.setRecognitionLevel_(1)  # accurate
    request.setRecognitionLanguages_(["pl-PL", "en-US"])
    request.setUsesLanguageCorrection_(True)
    handler = handler_class.alloc().initWithCGImage_options_(image, {})
    if not handler.performRequests_error_([request], None):
        raise RuntimeError("macOS Vision odrzucił żądanie rozpoznawania tekstu")

    lines: list[str] = []
    for observation in request.results() or []:
        candidates: Iterable[Any] = observation.topCandidates_(1)
        for candidate in candidates:
            value = str(candidate.string()).strip()
            if value:
                lines.append(value)
            break
    return "\n".join(lines)
