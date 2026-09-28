"""Extração rastreável de documentos, com OCR local e falhas por página."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Section:
    text: str
    locator: str
    page: int | None = None
    method: str = "native"
    confidence: float | None = None


@dataclass
class Extraction:
    sections: list[Section] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    pages: int = 0

    def to_dict(self):
        return asdict(self)


class TesseractOCR:
    def __init__(self, executable: str | Path | None = None, languages: str = "por+eng"):
        candidate = Path(executable or os.getenv("AL_IADO_TESSERACT_CMD") or
                         shutil.which("tesseract") or "data/tools/tesseract/tesseract.exe")
        # No Windows, subprocess não localiza executável por caminho relativo; resolve-se aqui.
        self.executable = str(candidate.resolve() if candidate.is_file() else candidate)
        self.languages = languages

    def extract(self, path: Path, page: int) -> tuple[str, float | None]:
        import pypdfium2 as pdfium

        if not Path(self.executable).is_file() and not shutil.which(self.executable):
            raise ValueError("Tesseract não encontrado; configure AL_IADO_TESSERACT_CMD.")
        with tempfile.TemporaryDirectory(prefix="aliado-ocr-") as folder:
            target = Path(folder) / "page.png"
            with pdfium.PdfDocument(str(path)) as document:
                pdf_page = document[page - 1]
                bitmap = pdf_page.render(scale=300 / 72)
                image = bitmap.to_pil()
                image.save(target)
                image.close()
                bitmap.close()
                pdf_page.close()
            result = subprocess.run(
                [self.executable, str(target), "stdout", "-l", self.languages, "--psm", "3", "tsv"],
                capture_output=True, encoding="utf-8", errors="replace", timeout=120,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode:
                raise ValueError("OCR falhou; confira o executável e os idiomas por/eng.")
            lines: dict[tuple[str, ...], list[str]] = {}
            confidence = []
            for row in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
                text = (row.get("text") or "").strip()
                if not text:
                    continue
                key = tuple(row.get(k, "") for k in ("block_num", "par_num", "line_num"))
                lines.setdefault(key, []).append(text)
                value = float(row.get("conf", "-1"))
                if value >= 0:
                    confidence.append(value)
            return "\n".join(" ".join(words) for words in lines.values()), (
                sum(confidence) / len(confidence) if confidence else None
            )


def extract_document(path: Path, *, ocr=None, force_ocr: bool = False, progress=None) -> Extraction:
    """`progress(etapa, atual, total)` recebe o andamento por página; opcional."""
    result = Extraction()
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError

        try:
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                raise ValueError("PDF protegido; forneça uma cópia acessível.")
            pages = list(reader.pages)
        except PyPdfError as exc:
            raise ValueError("PDF ilegível; confira o original.") from exc
        result.pages = len(pages)
        for number, page in enumerate(pages, 1):
            if progress:
                progress("lendo", number, len(pages))
            try:
                try:
                    text = page.extract_text() or ""
                except (PyPdfError, ValueError):
                    text = ""
                method, confidence = "native", None
                if force_ocr or len(re.sub(r"\W", "", text)) < 20 or "\ufffd" in text:
                    if progress:
                        progress("ocr", number, len(pages))
                    text, confidence = (ocr or TesseractOCR()).extract(path, number)
                    method = "ocr"
                if not text.strip():
                    result.issues.append(f"Página {number}: sem texto utilizável; conferir original.")
                    continue
                if confidence is not None and confidence < 50:
                    result.issues.append(f"Página {number}: OCR com baixa confiança; requer conferência.")
                result.sections.append(Section(text.strip(), f"página PDF {number}", number, method, confidence))
            except (PyPdfError, ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                result.issues.append(f"Página {number}: extração falhou ({type(exc).__name__}); conferir original/OCR.")
        return result
    text = path.read_text(encoding="utf-8-sig")
    if suffix == ".json":
        data = json.loads(text)

        def walk(value, pointer=""):
            if isinstance(value, dict):
                for key, item in value.items():
                    escaped = str(key).replace("~", "~0").replace("/", "~1")
                    walk(item, pointer + "/" + escaped)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    walk(item, pointer + "/" + str(i))
            else:
                rendered = json.dumps(value, ensure_ascii=False, allow_nan=False)
                result.sections.append(Section(f"{pointer or '/'}: {rendered}", f"JSON {pointer or '/'}"))

        walk(data)
    elif suffix == ".md":
        # Blocos sem alterar o texto; localizadores mantêm linhas do original.
        lines = text.splitlines(keepends=True)
        start = 0
        for i, line in enumerate(lines):
            if i > start and re.match(r"^#{1,6}\s", line):
                block = "".join(lines[start:i]).strip()
                if block:
                    result.sections.append(Section(block, f"linhas {start + 1}–{i}"))
                start = i
        block = "".join(lines[start:]).strip()
        if block:
            result.sections.append(Section(block, f"linhas {start + 1}–{len(lines)}"))
    else:
        raise ValueError("Formato não suportado; use PDF, Markdown ou JSON.")
    if not result.sections:
        result.issues.append("Documento sem texto utilizável.")
    return result
