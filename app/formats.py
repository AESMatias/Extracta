"""The file types Extracta accepts and how each one reaches the LLM.

- PDF with a text layer: its text (app/pdf_text.py).
- PDF without one (a scan): the file itself, read by the LLM's vision.
- XML e-invoices (Chile's DTE, Mexico's CFDI, UBL...): their cleaned text. Parsed with defusedxml
  and no DTDs at all, so entity expansion ("billion laughs") and external references (reading
  server files) are impossible; digital signatures and base64 blobs (certificates, embedded PDFs)
  are dropped, since they cost tokens and hold nothing to extract.
- Photos (JPEG, PNG, WebP, HEIC): decoded under a pixel cap (no decompression bombs), turned
  upright, shrunk to at most 2048 px and re-encoded as JPEG, which also drops every metadata block
  (EXIF, including the GPS position phones store).

The type comes from the file's first bytes, never from its name. XML files and photos count as
one page each.
"""

import io
import re
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from xml.etree.ElementTree import Element, ParseError, tostring

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

Format = Literal["pdf", "xml", "jpeg", "png", "webp", "heic"]
Kind = Literal["pdf", "xml", "image"]

EXTENSIONS: dict[Format, str] = {
    "pdf": ".pdf",
    "xml": ".xml",
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
    "heic": ".heic",
}
IMAGE_FORMATS: frozenset[Format] = frozenset({"jpeg", "png", "webp", "heic"})
SUPPORTED = "a PDF, an XML e-invoice or a photo (JPG, PNG, WebP, HEIC)"

MAX_XML_BYTES = 2 * 1024 * 1024  # e-invoices weigh 10-200 KB; anything bigger is not one
MAX_IMAGE_PIXELS = 60_000_000  # 60 MP covers any phone photo; a bomb claims billions
MAX_IMAGE_SIDE = 2048  # enough for the LLM to read small print; larger only costs tokens

_HEADER_WINDOW = 1024
_HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1", b"heif"}
_NOT_XML = re.compile(r"<!doctype\s+html|<html[\s>]|<svg[\s>]", re.IGNORECASE)
_XML_START = re.compile(r"<(\?xml|[A-Za-z_])")
_BOMS = ((b"\xef\xbb\xbf", "utf-8"), (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"))
_BASE64 = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")
_BLOB_NOTE = "[binary data removed]"


class UnreadableFileError(ValueError):
    """An XML file or a photo that cannot be parsed, or that is unsafe to parse."""


def sniff(head: bytes) -> Format | None:
    """The format of a file from its first bytes (at least the first 1 KB), or None."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[4:8] == b"ftyp" and head[8:12] in _HEIF_BRANDS:
        return "heic"
    if b"%PDF-" in head[:_HEADER_WINDOW]:  # the PDF spec allows the header anywhere in the first 1 KB
        return "pdf"
    prefix = _text_prefix(head)
    if _XML_START.match(prefix) and not _NOT_XML.search(prefix):
        return "xml"
    return None


def _text_prefix(head: bytes) -> str:
    for bom, encoding in _BOMS:
        if head.startswith(bom):
            return head[len(bom) :].decode(encoding, "ignore").lstrip()
    return head.decode("latin-1").lstrip()  # UTF-8 and ISO-8859-1 both start with plain ASCII markup


def format_of(path: Path) -> Format:
    """The format of a stored upload, from the extension save_stream() gave it."""
    for fmt, extension in EXTENSIONS.items():
        if path.suffix == extension:
            return fmt
    raise ValueError(f"not an upload: {path.name}")


def kind_of(fmt: Format) -> Kind:
    return "image" if fmt in IMAGE_FORMATS else fmt  # type: ignore[return-value]


# --------------------------------------------------------------------------- XML


def _parse_xml(path: Path) -> Element:
    from defusedxml import DefusedXmlException
    from defusedxml.ElementTree import parse

    try:
        root = parse(path, forbid_dtd=True).getroot()  # no DTD: no entities, no external references
    except DefusedXmlException:
        raise UnreadableFileError("This XML declares a DTD or entities, which are not allowed.") from None
    except (ParseError, RecursionError):
        raise UnreadableFileError("This XML file is damaged and cannot be read.") from None
    if root is None:
        raise UnreadableFileError("This XML file is empty.")
    return root


def check_xml(path: Path) -> None:
    """Refuse an XML file that is malformed or unsafe (called on upload, before queueing)."""
    _parse_xml(path)


def xml_text(path: Path, *, max_chars: int) -> tuple[str, bool]:
    """The XML without signatures and base64 blobs, compacted; and whether it was cut to max_chars."""
    root = _parse_xml(path)
    for parent in list(root.iter()):
        for child in list(parent):
            if isinstance(child.tag, str) and child.tag.rsplit("}", 1)[-1] == "Signature":
                parent.remove(child)  # XML-DSig: certificates and hashes, never invoice data
    for element in root.iter():
        if element.text and _is_blob(element.text):
            element.text = _BLOB_NOTE
        for name, value in element.attrib.items():
            if _is_blob(value):
                element.attrib[name] = _BLOB_NOTE  # e.g. CFDI's Sello and Certificado attributes
    try:
        text = tostring(root, encoding="unicode")
    except RecursionError:
        raise UnreadableFileError("This XML file is nested too deeply to read.") from None
    text = re.sub(r">\s+<", "><", text).strip()
    truncated = len(text) > max_chars
    return f"--- XML e-invoice ---\n{text[:max_chars]}", truncated


def _is_blob(value: str) -> bool:
    """Base64 data (a certificate, a signature, an embedded PDF): long and without spaces. Line
    breaks are allowed (base64 is often wrapped); a real description always has spaces."""
    return " " not in value and bool(_BASE64.fullmatch(re.sub(r"\s", "", value)))


# --------------------------------------------------------------------------- photos


def _open_image(path: Path) -> "PILImage":
    from PIL import Image, UnidentifiedImageError
    from pillow_heif import register_heif_opener

    register_heif_opener()  # teaches Pillow to open HEIC (iPhone photos); safe to call again
    try:
        image = Image.open(path)  # reads the header only: the size is known before decoding
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise UnreadableFileError("This image could not be read.") from None
    if image.width * image.height > MAX_IMAGE_PIXELS:
        image.close()
        raise UnreadableFileError(
            f"This image is too large ({image.width} x {image.height} pixels; the limit is 60 megapixels)."
        )
    return image


def check_image(path: Path) -> None:
    """Refuse a photo that cannot be opened or claims too many pixels (called on upload)."""
    _open_image(path).close()


def prepare_image(path: Path) -> bytes:
    """An upright JPEG of at most MAX_IMAGE_SIDE px per side, with no metadata at all."""
    from PIL import Image, ImageOps

    with _open_image(path) as original:
        try:
            original.draft("RGB", (MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))  # JPEG: decode already scaled down
            upright = ImageOps.exif_transpose(original)  # phones store rotation in EXIF
            if upright.mode in ("RGBA", "LA", "P", "PA"):
                rgba = upright.convert("RGBA")
                flat = Image.new("RGB", rgba.size, "white")  # transparent areas become paper, not black
                flat.paste(rgba, mask=rgba.getchannel("A"))
            else:
                flat = upright.convert("RGB")
            flat.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            buffer = io.BytesIO()
            flat.save(buffer, "JPEG", quality=85, optimize=True)  # no exif= argument: metadata is dropped
        except (OSError, ValueError, Image.DecompressionBombError):
            raise UnreadableFileError("This image could not be read.") from None
    return buffer.getvalue()
