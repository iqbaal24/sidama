"""Build report data and render it to PDF (ReportLab) and Excel (openpyxl)."""
from __future__ import annotations

import io
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.core.models import Setting
from apps.core.utils import month_bounds, rupiah
from apps.finance.services import (
    approved_transactions,
    cash_position,
    expense_by_category,
    fund_balances,
    income_by_category,
    totals,
)
from apps.programs.models import Program
from apps.reports.models import Report
from apps.zakat.services import zakat_summary

GREEN = colors.HexColor("#14532d")
LIGHT_GREEN = colors.HexColor("#ecf4ee")
GREY = colors.HexColor("#6b7280")
LINE = colors.HexColor("#dfe5e0")


def period_range(report) -> tuple:
    if report.report_type == Report.Type.MONTHLY and report.period_month:
        start, end = month_bounds(report.period_year, report.period_month)
    else:
        start = date(report.period_year, 1, 1)
        end = date(report.period_year, 12, 31)
    return start, end


def collect_data(report) -> dict:
    start, end = period_range(report)
    opening = cash_position(until=start - timedelta(days=1))
    summary = totals(start=start, end=end)
    transactions = (
        approved_transactions(until=end)
        .filter(date__gte=start)
        .select_related("category", "fund", "program")
        .order_by("date", "id")
    )
    data = {
        "report": report,
        "start": start,
        "end": end,
        "label": report.period_label,
        "opening": opening,
        "summary": summary,
        "closing": opening + summary["net"],
        "funds": fund_balances(until=end),
        "income_categories": income_by_category(start, end),
        "expense_categories": expense_by_category(start, end),
        "transactions": list(transactions),
        "generated_at": timezone.localtime(),
        "mosque": {
            "name": Setting.get("mosque_name"),
            "address": Setting.get("mosque_address"),
            "phone": Setting.get("mosque_phone"),
        },
    }
    if report.report_type == Report.Type.PROGRAMS:
        data["programs"] = list(Program.objects.all().order_by("-created_at"))
        data["zakat"] = zakat_summary(year=report.period_year)
    return data


def _money(value) -> str:
    return rupiah(value).replace("\u00a0", " ")


def render_pdf(data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Laporan Keuangan {data['label']}",
        author=data["mosque"]["name"] or "SIDAMA",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SidamaTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=16, textColor=GREEN, spaceAfter=2, alignment=0,
    ))
    styles.add(ParagraphStyle(
        name="SidamaSub", parent=styles["Normal"], fontSize=9, textColor=GREY,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, textColor=GREEN, spaceBefore=12, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Cell", parent=styles["Normal"], fontSize=8, leading=10,
    ))
    styles.add(ParagraphStyle(
        name="CellRight", parent=styles["Normal"], fontSize=8, leading=10,
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name="CellHead", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=8, leading=10, textColor=colors.white,
    ))

    story = []
    story.append(Paragraph("LAPORAN KEUANGAN MASJID", styles["SidamaTitle"]))
    story.append(Paragraph(
        f"{data['mosque']['name']} · {data['mosque']['address']}<br/>"
        f"{data['report'].get_report_type_display()} — {data['label']}",
        styles["SidamaSub"],
    ))

    summary_rows = [
        ["Saldo awal periode", _money(data["opening"])],
        ["Total pemasukan", _money(data["summary"]["income"])],
        ["Total pengeluaran", _money(data["summary"]["expense"])],
        ["Saldo akhir periode", _money(data["closing"])],
    ]
    summary_table = Table(summary_rows, colWidths=[110 * mm, 64 * mm])
    summary_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("FONT", (0, 3), (-1, 3), "Helvetica-Bold", 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1f2937")),
        ("BACKGROUND", (0, 3), (-1, 3), LIGHT_GREEN),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)

    story.append(Paragraph("Saldo per Dana", styles["SectionTitle"]))
    fund_rows = [["Dana", "Pemasukan", "Pengeluaran", "Saldo"]]
    for row in data["funds"]:
        fund_rows.append([
            Paragraph(row["fund"].name, styles["Cell"]),
            _money(row["income"]),
            _money(row["expense"]),
            _money(row["balance"]),
        ])
    story.append(_table(fund_rows, [74 * mm, 33 * mm, 33 * mm, 34 * mm], styles))

    story.append(Paragraph("Rincian Pemasukan per Kategori", styles["SectionTitle"]))
    income_rows = [["Kategori", "Jumlah"]]
    for row in data["income_categories"]:
        income_rows.append([Paragraph(row["name"], styles["Cell"]), _money(row["total"])])
    if len(income_rows) == 1:
        income_rows.append(["Tidak ada pemasukan", "Rp 0"])
    story.append(_table(income_rows, [130 * mm, 44 * mm], styles))

    story.append(Paragraph("Rincian Pengeluaran per Kategori", styles["SectionTitle"]))
    expense_rows = [["Kategori", "Jumlah"]]
    for row in data["expense_categories"]:
        expense_rows.append([Paragraph(row["name"], styles["Cell"]), _money(row["total"])])
    if len(expense_rows) == 1:
        expense_rows.append(["Tidak ada pengeluaran", "Rp 0"])
    story.append(_table(expense_rows, [130 * mm, 44 * mm], styles))

    if data["report"].report_type == "programs":
        story.append(Paragraph("Rekap Program Donasi", styles["SectionTitle"]))
        program_rows = [["Program", "Target", "Terkumpul", "Capaian"]]
        for program in data["programs"]:
            program_rows.append([
                Paragraph(program.title, styles["Cell"]),
                _money(program.target_amount),
                _money(program.collected),
                f"{program.progress}%",
            ])
        story.append(_table(program_rows, [80 * mm, 32 * mm, 32 * mm, 30 * mm], styles))

        zakat = data["zakat"]
        story.append(Paragraph("Rekap Zakat", styles["SectionTitle"]))
        story.append(_table([
            ["Penerimaan", "Penyaluran", "Sisa"],
            [_money(zakat["received"]), _money(zakat["distributed"]),
             _money(zakat["remaining"])],
        ], [58 * mm, 58 * mm, 58 * mm], styles))

    story.append(Paragraph("Rincian Transaksi", styles["SectionTitle"]))
    tx_rows = [["Tanggal", "Uraian", "Kategori", "Dana", "Nominal"]]
    for tx in data["transactions"]:
        tx_rows.append([
            tx.date.strftime("%d/%m/%Y"),
            Paragraph(tx.description, styles["Cell"]),
            Paragraph(tx.category.name, styles["Cell"]),
            Paragraph(tx.fund.name, styles["Cell"]),
            _money(tx.signed_amount),
        ])
    if len(tx_rows) == 1:
        tx_rows.append(["—", "Tidak ada transaksi pada periode ini", "", "", ""])
    story.append(_table(
        tx_rows, [22 * mm, 62 * mm, 30 * mm, 32 * mm, 28 * mm], styles,
        align_last_right=True,
    ))

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        f"Dibuat otomatis oleh SIDAMA pada "
        f"{data['generated_at']:%d/%m/%Y %H:%M} WIB. "
        f"Laporan ini bersifat ringkas dan bukan laporan akuntansi formal.",
        ParagraphStyle(name="Footer", parent=styles["Normal"], fontSize=7,
                       textColor=GREY),
    ))

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GREY)
        canvas.drawString(18 * mm, 10 * mm,
                          f"{data['mosque']['name']} — {data['label']}")
        canvas.drawRightString(192 * mm, 10 * mm, f"Halaman {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _table(rows, widths, styles, *, align_last_right: bool = False) -> Table:
    header = [Paragraph(str(cell), styles["CellHead"]) for cell in rows[0]]
    body = []
    for row in rows[1:]:
        cells = []
        for index, cell in enumerate(row):
            if isinstance(cell, Paragraph):
                cells.append(cell)
            elif index == len(row) - 1 and align_last_right:
                cells.append(Paragraph(str(cell), styles["CellRight"]))
            else:
                cells.append(Paragraph(str(cell), styles["Cell"]))
        body.append(cells)
    table = Table([header] + body, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_index in range(1, len(rows)):
        if row_index % 2 == 0:
            style.append(("BACKGROUND", (0, row_index), (-1, row_index), LIGHT_GREEN))
    table.setStyle(TableStyle(style))
    return table


def render_xlsx(data: dict) -> bytes:
    workbook = Workbook()
    header_fill = PatternFill("solid", fgColor="14532D")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="DFE5E0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def style_header(sheet, columns: int):
        for column in range(1, columns + 1):
            cell = sheet.cell(row=1, column=column)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(vertical="center")
            cell.border = border
        sheet.freeze_panes = "A2"

    summary = workbook.active
    summary.title = "Ringkasan"
    summary.append(["Laporan Keuangan Masjid"])
    summary["A1"].font = Font(size=14, bold=True, color="14532D")
    summary.append([data["mosque"]["name"], data["mosque"]["address"]])
    summary.append([data["report"].get_report_type_display(), data["label"]])
    summary.append([])
    summary.append(["Keterangan", "Nilai"])
    for label, value in [
        ("Saldo awal periode", data["opening"]),
        ("Total pemasukan", data["summary"]["income"]),
        ("Total pengeluaran", data["summary"]["expense"]),
        ("Saldo akhir periode", data["closing"]),
    ]:
        summary.append([label, float(value)])
    for row in summary.iter_rows(min_row=5, max_row=9, min_col=1, max_col=2):
        for cell in row:
            cell.border = border
    for cell in summary[5]:
        cell.fill = header_fill
        cell.font = header_font
    for row in summary.iter_rows(min_row=6, max_row=9, min_col=2, max_col=2):
        row[0].number_format = '#,##0'
    summary.column_dimensions["A"].width = 32
    summary.column_dimensions["B"].width = 46

    funds = workbook.create_sheet("Saldo Dana")
    funds.append(["Dana", "Tipe", "Pemasukan", "Pengeluaran", "Saldo"])
    style_header(funds, 5)
    for row in data["funds"]:
        funds.append([row["fund"].name, row["fund"].get_fund_type_display(),
                      float(row["income"]), float(row["expense"]),
                      float(row["balance"])])
    for row in funds.iter_rows(min_row=2, max_row=funds.max_row, min_col=3, max_col=5):
        for cell in row:
            cell.number_format = '#,##0'
    for width, letter in zip([34, 18, 16, 16, 16], "ABCDE"):
        funds.column_dimensions[letter].width = width

    categories = workbook.create_sheet("Per Kategori")
    categories.append(["Jenis", "Kategori", "Jumlah"])
    style_header(categories, 3)
    for row in data["income_categories"]:
        categories.append(["Pemasukan", row["name"], float(row["total"])])
    for row in data["expense_categories"]:
        categories.append(["Pengeluaran", row["name"], float(row["total"])])
    for row in categories.iter_rows(min_row=2, max_row=categories.max_row, min_col=3,
                                    max_col=3):
        row[0].number_format = '#,##0'
    categories.column_dimensions["A"].width = 16
    categories.column_dimensions["B"].width = 34
    categories.column_dimensions["C"].width = 18

    transactions = workbook.create_sheet("Transaksi")
    transactions.append(["Tanggal", "Jenis", "Uraian", "Kategori", "Dana", "Nominal",
                         "Status", "Penanggung jawab"])
    style_header(transactions, 8)
    for tx in data["transactions"]:
        transactions.append([
            tx.date, tx.get_transaction_type_display(), tx.description,
            tx.category.name, tx.fund.name, float(tx.amount),
            tx.get_status_display(), tx.pic,
        ])
    for row in transactions.iter_rows(min_row=2, max_row=transactions.max_row,
                                      min_col=1, max_col=1):
        row[0].number_format = "DD/MM/YYYY"
    for row in transactions.iter_rows(min_row=2, max_row=transactions.max_row,
                                      min_col=6, max_col=6):
        row[0].number_format = '#,##0'
    for width, letter in zip([12, 14, 46, 20, 22, 16, 20, 22], "ABCDEFGH"):
        transactions.column_dimensions[letter].width = width

    if data["report"].report_type == "programs":
        programs = workbook.create_sheet("Program")
        programs.append(["Program", "Target", "Terkumpul", "Capaian", "Status"])
        style_header(programs, 5)
        for program in data["programs"]:
            programs.append([program.title, float(program.target_amount),
                             float(program.collected), program.progress / 100,
                             program.get_status_display()])
        for row in programs.iter_rows(min_row=2, max_row=programs.max_row,
                                      min_col=2, max_col=3):
            for cell in row:
                cell.number_format = '#,##0'
        for row in programs.iter_rows(min_row=2, max_row=programs.max_row,
                                      min_col=4, max_col=4):
            row[0].number_format = "0.0%"
        for width, letter in zip([46, 18, 18, 12, 14], "ABCDE"):
            programs.column_dimensions[letter].width = width

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def generate_report(report) -> "object":
    """Render both files and attach them to the report instance."""
    data = collect_data(report)
    pdf_bytes = render_pdf(data)
    xlsx_bytes = render_xlsx(data)

    if report.pdf_file:
        report.pdf_file.delete(save=False)
    if report.xlsx_file:
        report.xlsx_file.delete(save=False)
    report.pdf_file.save(f"{report.filename_stem}.pdf",
                         ContentFile(pdf_bytes), save=False)
    report.xlsx_file.save(f"{report.filename_stem}.xlsx",
                          ContentFile(xlsx_bytes), save=False)
    report.generated_at = timezone.now()
    report.save(update_fields=["pdf_file", "xlsx_file", "generated_at"])
    return report
