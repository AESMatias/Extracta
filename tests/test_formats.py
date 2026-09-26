"""XML e-invoices and photos: detection, safe parsing, cleaning and preparation for the LLM."""

import io
import struct
import zlib
from pathlib import Path

import pytest
from PIL import Image

from app.formats import (
    MAX_IMAGE_SIDE,
    MAX_XML_BYTES,
    UnreadableFileError,
    check_image,
    check_xml,
    format_of,
    prepare_image,
    sniff,
    xml_text,
)
from app.storage import UploadTooLargeError, save_stream

MB = 1024 * 1024
CERT = "MIIF" + "A1b2C3d4E5f6G7h8" * 40  # a base64 certificate: long, no spaces
ITEM = (  # a long description: it has spaces, so it is kept
    "Asesor\xeda contable mensual para la empresa, incluye declaraciones y reportes de gesti\xf3n "
    "trimestral para el directorio y la gerencia general"
)
DTE = f"""<?xml version="1.0" encoding="ISO-8859-1"?>
<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
  <Documento ID="F33T1001">
    <Encabezado>
      <IdDoc><TipoDTE>33</TipoDTE><Folio>1001</Folio><FchEmis>2026-09-15</FchEmis></IdDoc>
      <Emisor><RUTEmisor>76543210-K</RUTEmisor><RznSoc>Servicios Andes SpA</RznSoc></Emisor>
      <Totales><MntNeto>824000</MntNeto><IVA>156560</IVA><MntTotal>980560</MntTotal></Totales>
    </Encabezado>
    <Detalle><NmbItem>{ITEM}</NmbItem></Detalle>
    <TED><FRMT algoritmo="SHA1withRSA">{CERT}</FRMT></TED>
  </Documento>
  <Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignatureValue>{CERT}</SignatureValue></Signature>
</DTE>
""".encode("iso-8859-1")
CFDI = f"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" Total="1160.00"
  Sello="{CERT}" Certificado="{CERT}" NoCertificado="00001000000500000000">
  <cfdi:Emisor Rfc="EKU9003173C9" Nombre="ESCUELA KEMPER URGATE"/>
</cfdi:Comprobante>""".encode()


def write(tmp_path: Path, name: str, data: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def photo(fmt: str = "JPEG", size: tuple[int, int] = (400, 300), mode: str = "RGB", **save: object) -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size, "red" if mode == "RGB" else (255, 0, 0, 0)).save(buffer, fmt, **save)  # type: ignore[arg-type]
    return buffer.getvalue()


# --------------------------------------------------------------------------- detection


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"%PDF-1.7\n...", "pdf"),
        (b"junk" * 50 + b"%PDF-1.4", "pdf"),
        (photo("JPEG"), "jpeg"),
        (photo("PNG"), "png"),
        (photo("WEBP"), "webp"),
        (b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00", "heic"),
        (DTE, "xml"),
        (CFDI, "xml"),
        (b"\xef\xbb\xbf<?xml version='1.0'?><a/>", "xml"),
        ("<?xml version='1.0' encoding='UTF-16'?><a/>".encode("utf-16"), "xml"),
        (b"  \n<Invoice xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'/>", "xml"),
        (b"<!DOCTYPE html><html><body>hi</body></html>", None),
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", None),
        (b"#!/bin/sh\nrm -rf /", None),
        (b"MZ\x90\x00", None),
        (b"", None),
    ],
)
def test_the_format_comes_from_the_first_bytes(data: bytes, expected: str | None) -> None:
    assert sniff(data[:1024]) == expected


def test_uploads_are_stored_with_the_extension_of_their_real_format(tmp_path: Path) -> None:
    xml = save_stream(io.BytesIO(DTE), "factura.pdf", upload_dir=tmp_path, max_bytes=MB)
    jpeg = save_stream(io.BytesIO(photo()), "boleta", upload_dir=tmp_path, max_bytes=MB)

    assert (xml.format, xml.path.suffix, format_of(xml.path)) == ("xml", ".xml", "xml")
    assert (jpeg.format, jpeg.path.suffix, jpeg.original_name) == ("jpeg", ".jpg", "boleta")


def test_xml_uploads_are_capped_at_2_mb_whatever_the_plan(tmp_path: Path) -> None:
    huge = b"<?xml version='1.0'?><a>" + b"x" * MAX_XML_BYTES + b"</a>"

    with pytest.raises(UploadTooLargeError, match="2 MB"):
        save_stream(io.BytesIO(huge), "big.xml", upload_dir=tmp_path, max_bytes=50 * MB)
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------- XML


def test_xml_loses_signatures_and_base64_but_keeps_the_invoice(tmp_path: Path) -> None:
    text, truncated = xml_text(write(tmp_path, "a.xml", DTE), max_chars=100_000)

    assert not truncated and text.startswith("--- XML e-invoice ---")
    assert "Servicios Andes SpA" in text and "980560" in text
    assert "Asesoría contable mensual para la empresa" in text  # long, but a description, not a blob
    assert CERT not in text and "SignatureValue" not in text
    assert "[binary data removed]" in text  # the TED signature


def test_cfdi_seal_and_certificate_attributes_are_dropped(tmp_path: Path) -> None:
    text, _ = xml_text(write(tmp_path, "a.xml", CFDI), max_chars=100_000)

    assert CERT not in text and 'Total="1160.00"' in text and "ESCUELA KEMPER URGATE" in text


def test_long_xml_is_cut_and_flagged(tmp_path: Path) -> None:
    text, truncated = xml_text(write(tmp_path, "a.xml", DTE), max_chars=100)

    assert truncated and len(text) < 150


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (  # "billion laughs": entities that expand to gigabytes
            b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">]>'
            b"<lolz>&lol2;</lolz>",
            "DTD",
        ),
        (  # external entity: would read a file from the server
            b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a>&x;</a>',
            "DTD",
        ),
        (b"<?xml version='1.0'?><a><b></a>", "damaged"),
    ],
)
def test_hostile_or_broken_xml_is_refused(tmp_path: Path, data: bytes, message: str) -> None:
    path = write(tmp_path, "a.xml", data)

    with pytest.raises(UnreadableFileError, match=message):
        check_xml(path)
    with pytest.raises(UnreadableFileError):
        xml_text(path, max_chars=1000)


# --------------------------------------------------------------------------- photos


def test_photos_lose_every_metadata_block_including_gps(tmp_path: Path) -> None:
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # camera make
    exif[0x8825] = {1: "S", 2: (33.0, 26.0, 0.0), 3: "W", 4: (70.0, 39.0, 0.0)}  # GPS: Santiago
    path = write(tmp_path, "a.jpg", photo(exif=exif.tobytes()))
    assert Image.open(path).getexif()  # the upload does carry them

    out = Image.open(io.BytesIO(prepare_image(path)))

    assert out.format == "JPEG" and not out.getexif() and "exif" not in out.info


def test_photos_are_turned_upright_and_shrunk(tmp_path: Path) -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: the phone was held sideways
    path = write(tmp_path, "a.jpg", photo(size=(4000, 3000), exif=exif.tobytes()))

    out = Image.open(io.BytesIO(prepare_image(path)))

    assert out.height == MAX_IMAGE_SIDE and out.width == 1536  # rotated to portrait, 2048 px long side


def test_transparent_png_becomes_white_not_black(tmp_path: Path) -> None:
    path = write(tmp_path, "a.png", photo("PNG", mode="RGBA"))

    out = Image.open(io.BytesIO(prepare_image(path))).convert("RGB")

    assert out.getpixel((10, 10)) == (255, 255, 255)


def test_heic_photos_from_iphones_are_read(tmp_path: Path) -> None:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    path = write(tmp_path, "a.heic", photo("HEIF"))

    assert sniff(path.read_bytes()[:1024]) == "heic"
    assert Image.open(io.BytesIO(prepare_image(path))).size == (400, 300)


def png_claiming(width: int, height: int) -> bytes:
    """A tiny PNG whose header claims huge dimensions: a decompression bomb."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b"")) + chunk(b"IEND", b"")


@pytest.mark.parametrize(
    "data",
    [png_claiming(100_000, 100_000), png_claiming(9_000, 9_000), b"\xff\xd8\xff" + b"not really a jpeg"],
)
def test_image_bombs_and_broken_images_are_refused(tmp_path: Path, data: bytes) -> None:
    path = write(tmp_path, "a.png", data)

    with pytest.raises(UnreadableFileError):
        check_image(path)
    with pytest.raises(UnreadableFileError):
        prepare_image(path)
