"""Export of extracted documents to CSV, XLSX (Excel) and JSON.

Two views of the data, each built once as a table of typed values and then written in any format:
- Individual: one document; commercial documents get one row per line item.
- Unified: a batch, one row per document, with columns derived from DocumentSchema so every
  batch has the same columns in the same order (files can be stacked in a spreadsheet).

CSV is streamed line by line. XLSX keeps numbers and dates typed (Excel can sum and filter them)
and text as plain text. JSON keeps the original nested structure.
"""

import csv
import io
import json
import types
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Any, Union, get_args, get_origin

import xlsxwriter
from pydantic import BaseModel, Field

from app.schemas import SECTION_BY_TYPE, CommercialDocumentData, DocumentSchema, LineItem

MAX_EXPORT_ITEMS = 500  # a batch export request never carries more documents than this
_BOM = "\ufeff"  # lets Excel detect UTF-8 in a CSV, so accents display correctly
_COMMON_COLUMNS = ["filename", "document_type", "language", "title", "summary"]
# Spreadsheets run CSV cells starting with these as formulas (CSV injection): prefix them with "'".
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
# Line items get their own rows in the individual export; in a batch a count keeps rows readable.
_COUNTED_LISTS = {"line_items"}
_XLSX_MAX_TEXT = 32_767  # Excel's limit for a single cell
_XLSX_MAX_WIDTH = 60

Value = str | int | float | bool | date | None


class ExportItem(BaseModel):
    filename: str | None = Field(default=None, max_length=255)
    document: DocumentSchema  # the browser sends JSON back: validate it like any untrusted input


class UnifiedExportRequest(BaseModel):
    items: list[ExportItem] = Field(min_length=1, max_length=MAX_EXPORT_ITEMS)


@dataclass(frozen=True)
class Table:
    columns: list[str]
    rows: Iterable[list[Value]]  # may be a generator: consumed once, row by row


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


# --------------------------------------------------------------------------- values


def _value(raw: Any, *, count_lists: bool = False) -> Value:
    """Turn a schema value into a typed cell value: lists and enums become text, the rest keeps its type."""
    if isinstance(raw, list):
        return f"{len(raw)} items" if count_lists else "; ".join(_list_entry(entry) for entry in raw)
    if raw is None or isinstance(raw, int | float | bool | date):
        return raw
    return str(raw)  # str and StrEnum


def _list_entry(entry: Any) -> str:
    if isinstance(entry, BaseModel):  # e.g. a party: "Northwind | client"
        return " | ".join(_csv_cell(_value(v)) for v in entry.model_dump().values() if v is not None)
    return _csv_cell(_value(entry))


def _get(obj: Any, path: str) -> Any:
    for attribute in path.split("."):
        if obj is None:
            return None
        obj = getattr(obj, attribute)
    return obj


def _common_values(document: DocumentSchema, filename: str | None) -> list[Value]:
    return [filename or "", *(_value(getattr(document, c)) for c in _COMMON_COLUMNS[1:])]


# --------------------------------------------------------------------------- tables


def individual_table(document: DocumentSchema, *, filename: str | None) -> Table:
    section_name = SECTION_BY_TYPE.get(document.document_type)
    section = document.section
    columns = _leaf_columns(_section_model(section_name)) if section_name else []
    values = _common_values(document, filename) + [_value(_get(section, c)) for c in columns if c != "line_items"]

    if not isinstance(section, CommercialDocumentData):
        return Table(_COMMON_COLUMNS + columns, [values])

    # Commercial documents: one row per line item, document columns repeated on each row.
    columns.remove("line_items")
    item_columns = _leaf_columns(LineItem)
    items: list[LineItem | None] = list(section.line_items) or [None]  # no items: still one row
    rows = [values + [_value(_get(item, c)) for c in item_columns] for item in items]
    return Table(_COMMON_COLUMNS + columns + [f"line_item.{c}" for c in item_columns], rows)


def unified_table(items: Iterable[ExportItem]) -> Table:
    section_columns = _unified_columns()[len(_COMMON_COLUMNS) :]

    def rows() -> Iterator[list[Value]]:
        for item in items:
            values = _common_values(item.document, item.filename)
            for column in section_columns:
                section, _, path = column.partition(".")
                values.append(_value(_get(getattr(item.document, section), path), count_lists=path in _COUNTED_LISTS))
            yield values

    return Table(unified_columns(), rows())


# --------------------------------------------------------------------------- CSV


def _csv_cell(value: Value) -> str:
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
    # Only text is escaped, so negative amounts stay numeric.
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value


def to_csv(table: Table) -> Iterator[str]:
    """Yield the header (with the BOM) and then each row as one CSV line."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def line(cells: list[str]) -> str:
        writer.writerow(cells)
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()  # reuse the same small buffer for every row
        return text

    yield _BOM + line(table.columns)
    for row in table.rows:
        yield line([_csv_cell(value) for value in row])


# --------------------------------------------------------------------------- XLSX


def to_xlsx(table: Table, *, sheet_name: str) -> bytes:
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    sheet = workbook.add_worksheet(sheet_name[:31])  # Excel caps sheet names at 31 characters
    header = workbook.add_format({"bold": True, "bg_color": "#E8EEF7", "border": 1})
    date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})
    widths = [len(column) for column in table.columns]

    for col, column in enumerate(table.columns):
        sheet.write_string(0, col, column, header)
    row_count = 0
    for row_count, row in enumerate(table.rows, start=1):
        for col, value in enumerate(row):
            if value is None:
                continue
            if isinstance(value, bool):
                sheet.write_boolean(row_count, col, value)
            elif isinstance(value, int | float):
                sheet.write_number(row_count, col, value)
            elif isinstance(value, date):
                sheet.write_datetime(row_count, col, datetime(value.year, value.month, value.day), date_format)
            else:
                # write_string, never write(): text such as "=HYPERLINK(...)" stays text, not a formula.
                sheet.write_string(row_count, col, value[:_XLSX_MAX_TEXT])
            widths[col] = max(widths[col], len(str(value)))

    for col, width in enumerate(widths):
        sheet.set_column(col, col, min(width + 2, _XLSX_MAX_WIDTH))
    sheet.freeze_panes(1, 0)  # keep the header visible while scrolling
    sheet.autofilter(0, 0, max(row_count, 1), len(table.columns) - 1)
    workbook.close()
    return output.getvalue()


# --------------------------------------------------------------------------- JSON


def _json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode()  # keep accents readable


# --------------------------------------------------------------------------- public API


def individual_csv(document: DocumentSchema, *, filename: str | None) -> Iterator[str]:
    return to_csv(individual_table(document, filename=filename))


def unified_csv(items: Iterable[ExportItem]) -> Iterator[str]:
    return to_csv(unified_table(items))


def individual_xlsx(document: DocumentSchema, *, filename: str | None) -> bytes:
    return to_xlsx(individual_table(document, filename=filename), sheet_name="Document")


def unified_xlsx(items: Iterable[ExportItem]) -> bytes:
    return to_xlsx(unified_table(items), sheet_name="Documents")


def individual_json(item: ExportItem) -> bytes:
    return _json(item.model_dump(mode="json"))


def unified_json(items: list[ExportItem]) -> bytes:
    return _json(
        {
            "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "count": len(items),
            "items": [item.model_dump(mode="json") for item in items],
        }
    )
