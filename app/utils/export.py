"""Генерация выгрузок в форматах CSV, XLSX и PDF."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from enum import StrEnum

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle


class ExportFormat(StrEnum):
    """Поддерживаемые форматы экспорта."""

    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


def to_csv(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> bytes:
    """Сформировать CSV (UTF-8 с BOM для корректного открытия в Excel)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if v is None else str(v) for v in row])
    return buffer.getvalue().encode("utf-8-sig")


def to_xlsx(
    headers: Sequence[str], rows: Sequence[Sequence[object]], *, title: str = "Отчёт"
) -> bytes:
    """Сформировать XLSX-файл."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title[:31]
    sheet.append(list(headers))
    for row in rows:
        sheet.append(["" if v is None else v for v in row])
    for column_cells in sheet.columns:
        length = max((len(str(c.value)) if c.value is not None else 0) for c in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(60, length + 2)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def to_pdf(
    headers: Sequence[str], rows: Sequence[Sequence[object]], *, title: str = "Отчёт"
) -> bytes:
    """Сформировать PDF-таблицу."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        title=title,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    data: list[list[object]] = [list(headers)]
    data.extend([["" if v is None else str(v) for v in row] for row in rows])
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6cdf")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    doc.build([table])
    return buffer.getvalue()


def render(
    fmt: ExportFormat,
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    *,
    title: str = "Отчёт",
) -> tuple[bytes, str]:
    """Сформировать файл в заданном формате.

    :returns: кортеж ``(содержимое, имя_файла)``.
    """
    if fmt is ExportFormat.CSV:
        return to_csv(headers, rows), f"{title}.csv"
    if fmt is ExportFormat.XLSX:
        return to_xlsx(headers, rows, title=title), f"{title}.xlsx"
    return to_pdf(headers, rows, title=title), f"{title}.pdf"
