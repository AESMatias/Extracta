"""CSV export of extracted documents.

- Individual CSV: one document; commercial documents get one row per line item.
- Unified CSV: a batch, one row per document, with columns derived from DocumentSchema so every
  batch has the same columns in the same order (files can be stacked in a spreadsheet).

Both are generators: rows are written one at a time and streamed to the browser.
"""

import csv
import io
import types
from collections.abc import Iterable, Iterator
from datetime import date
from functools import lru_cache
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, Field

from app.schemas import SECTION_BY_TYPE, CommercialDocumentData, DocumentSchema, LineItem

MAX_EXPORT_ITEMS = 500  # a batch export request never carries more documents than this
_BOM = "\ufeff"  # lets Excel detect UTF-8, so accents display correctly
_COMMON_COLUMNS = ["filename", "document_type", "language", "title", "summary"]
# Spreadsheets run cells starting with these as formulas (CSV injection): prefix them with "'".
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
# Line items get their own rows in the individual CSV; in a batch a count keeps rows readable.
_COUNTED_LISTS = {"line_items"}


class ExportItem(BaseModel):
    filename: str | None = Field(default=None, max_length=255)
    document: DocumentSchema  # the browser sends JSON back: validate it like any untrusted input


class UnifiedExportRequest(BaseModel):
    items: list[ExportItem] = Field(min_length=1, max_length=MAX_EXPORT_ITEMS)


# --------------------------------------------------------------------------- columns


def _model_type(annotation: Any) -> type[BaseModel] | None:
    """Return the model class behind `Model` or `Model | None`, else None."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    if get_origin(annotation) in (Union, types.UnionType):
        models = [arg for arg in get_args(annotation) if isinstance(arg, type) and issubclass(arg, BaseModel)]
        return models[0] if models else None
    return None


def _leaf_columns(model: type[BaseModel], prefix: str = "") -> list[str]:
    """Dotted paths of every non-model field, e.g. 'issuer.name'. Lists stay a single column."""
    columns: list[str] = []
    for name, field in model.model_fields.items():
        nested = _model_type(field.annotation)
        columns += _leaf_columns(nested, f"{prefix}{name}.") if nested else [f"{prefix}{name}"]
    return columns


def _section_model(section: str) -> type[BaseModel]:
    model = _model_type(DocumentSchema.model_fields[section].annotation)
    assert model is not None
    return model


@lru_cache
def _unified_columns() -> tuple[str, ...]:
    sections = dict.fromkeys(SECTION_BY_TYPE.values())  # unique, in schema order
    return tuple(_COMMON_COLUMNS) + tuple(
        f"{section}.{column}" for section in sections for column in _leaf_columns(_section_model(section))
    )


def unified_columns() -> list[str]:
    return list(_unified_columns())


# --------------------------------------------------------------------------- cells


def _escape(text: str) -> str:
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def _cell(value: Any, *, count_lists: bool = False) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):  # before int: bool is a subclass of int
        return "true" if value else "false"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)  # 119000.0 -> "119000"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        if count_lists:
            return f"{len(value)} items"
        return _escape("; ".join(_list_entry(entry) for entry in value))
    return _escape(str(value))  # numbers are never escaped, so negative amounts stay numeric


def _list_entry(entry: Any) -> str:
    if isinstance(entry, BaseModel):  # e.g. a party: "Northwind | client"
        return " | ".join(_cell(v) for v in entry.model_dump().values() if v is not None)
    return _cell(entry)


def _get(obj: Any, path: str) -> Any:
    for attribute in path.split("."):
        if obj is None:
            return None
        obj = getattr(obj, attribute)
    return obj


def _common_cells(document: DocumentSchema, filename: str | None) -> list[str]:
    return [_escape(filename or ""), *(_cell(getattr(document, c)) for c in _COMMON_COLUMNS[1:])]


def _stream(columns: list[str], rows: Iterable[list[str]]) -> Iterator[str]:
    """Yield the header (with the BOM) and then each row as one CSV line."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def line(row: list[str]) -> str:
        writer.writerow(row)
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()  # reuse the same small buffer for every row
        return text

    yield _BOM + line(columns)
    for row in rows:
        yield line(row)


# --------------------------------------------------------------------------- exports


def individual_csv(document: DocumentSchema, *, filename: str | None) -> Iterator[str]:
    section_name = SECTION_BY_TYPE.get(document.document_type)
    section = document.section
    columns = _leaf_columns(_section_model(section_name)) if section_name else []
    cells = _common_cells(document, filename) + [_cell(_get(section, c)) for c in columns if c != "line_items"]

    if not isinstance(section, CommercialDocumentData):
        yield from _stream(_COMMON_COLUMNS + columns, [cells])
        return

    # Commercial documents: one row per line item, document columns repeated on each row.
    columns.remove("line_items")
    item_columns = _leaf_columns(LineItem)
    items: list[LineItem | None] = list(section.line_items) or [None]  # no items: still one row
    rows = [cells + [_cell(_get(item, c)) for c in item_columns] for item in items]
    yield from _stream(_COMMON_COLUMNS + columns + [f"line_item.{c}" for c in item_columns], rows)


def unified_csv(items: Iterable[ExportItem]) -> Iterator[str]:
    section_columns = _unified_columns()[len(_COMMON_COLUMNS) :]

    def rows() -> Iterator[list[str]]:
        for item in items:
            cells = _common_cells(item.document, item.filename)
            for column in section_columns:
                section, _, path = column.partition(".")
                value = _get(getattr(item.document, section), path)
                cells.append(_cell(value, count_lists=path in _COUNTED_LISTS))
            yield cells

    yield from _stream(unified_columns(), rows())
