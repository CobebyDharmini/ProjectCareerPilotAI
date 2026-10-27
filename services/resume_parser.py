from pathlib import Path

import pymupdf

from services.resume_matcher import MAX_INPUT_CHARS


MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def extract_resume_text(filename: str, content: bytes) -> str:
    """Extract bounded UTF-8 TXT or selectable text from a PDF resume."""
    if not content:
        raise ValueError("The selected file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("The file must be 5 MB or smaller.")

    extension = Path(filename).suffix.casefold()
    if extension == ".txt":
        try:
            extracted_text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError("This TXT file is not readable as UTF-8. Save it as UTF-8 and upload it again.") from error
    elif extension == ".pdf":
        extracted_too_long = False
        try:
            with pymupdf.open(stream=content, filetype="pdf") as document:
                text_parts = []
                extracted_length = 0
                for page in document:
                    page_text = page.get_text("text")
                    extracted_length += len(page_text)
                    if extracted_length > MAX_INPUT_CHARS:
                        extracted_too_long = True
                        break
                    text_parts.append(page_text)
                extracted_text = "\n".join(text_parts)
        except (pymupdf.FileDataError, RuntimeError, ValueError) as error:
            raise ValueError("This PDF could not be read. Check that it is a valid, unencrypted PDF.") from error
        if extracted_too_long:
            raise ValueError(f"Extracted resume text must be {MAX_INPUT_CHARS:,} characters or fewer.")
        if not extracted_text.strip():
            raise ValueError(
                "No selectable text was found in this PDF. It may be scanned; use a text-based PDF or paste the resume text."
            )
    else:
        raise ValueError("Choose a .txt or .pdf resume file.")

    if not extracted_text.strip():
        raise ValueError("No text was found in this file.")
    if len(extracted_text) > MAX_INPUT_CHARS:
        raise ValueError(f"Extracted resume text must be {MAX_INPUT_CHARS:,} characters or fewer.")
    return extracted_text