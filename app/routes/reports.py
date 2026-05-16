from flask import Blueprint, render_template, request, send_file, flash
from flask_login import login_required
from sqlalchemy import func
from app import db
from app.models import WasteRecord, WasteType, Location
from app.forms import ReportFilterForm
import pandas as pd
import io
import os
from datetime import date

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

# ── Organisation details (used in PDF header) ─────────────────────────────────
ORG_NAME    = 'Distributed Environmental Systems'
ORG_ADDRESS = 'Abule Egba, Labak Estate, Lagos, Nigeria'
ORG_PHONE   = '+2348081625419'
ORG_EMAIL   = 'distributedenvironmentalsystems@gmail.com'


def _populate_filter_choices(form):
    form.waste_type_id.choices = [(0, 'All Types')] + \
        [(t.id, t.name) for t in WasteType.query.order_by('name').all()]
    form.location_id.choices = [(0, 'All Locations')] + \
        [(l.id, l.name) for l in Location.query.order_by('name').all()]


def _build_query(form):
    """Apply form filters and return a SQLAlchemy query (all users)."""
    query = db.session.query(
        WasteRecord.date_collected,
        WasteRecord.quantity_kg,
        WasteRecord.vehicle_id,
        WasteRecord.disposal_method,
        WasteRecord.notes,
        WasteType.name.label('waste_type'),
        Location.name.label('location'),
    ).join(WasteType).join(Location)

    if form.date_from.data:
        query = query.filter(WasteRecord.date_collected >= form.date_from.data)
    if form.date_to.data:
        query = query.filter(WasteRecord.date_collected <= form.date_to.data)
    if form.waste_type_id.data and form.waste_type_id.data != 0:
        query = query.filter(WasteRecord.waste_type_id == form.waste_type_id.data)
    if form.location_id.data and form.location_id.data != 0:
        query = query.filter(WasteRecord.location_id == form.location_id.data)

    return query.order_by(WasteRecord.date_collected.desc())


@reports_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = ReportFilterForm()
    _populate_filter_choices(form)

    records = []
    summary = {}

    if form.validate_on_submit() or request.method == 'GET':
        rows = _build_query(form).all()
        records = rows

        if rows:
            df = pd.DataFrame(rows, columns=[
                'date', 'quantity_kg', 'vehicle_id',
                'disposal_method', 'notes', 'waste_type', 'location'
            ])
            summary = {
                'total_kg':      round(df['quantity_kg'].sum(), 2),
                'total_records': len(df),
                'by_type':       df.groupby('waste_type')['quantity_kg'].sum().round(2).to_dict(),
                'by_location':   df.groupby('location')['quantity_kg'].sum().round(2).to_dict(),
                'by_disposal':   df.groupby('disposal_method')['quantity_kg'].sum().round(2).to_dict(),
            }

    return render_template(
        'reports/index.html',
        title='Reports',
        form=form,
        records=records,
        summary=summary,
    )


@reports_bp.route('/export/excel', methods=['POST'])
@login_required
def export_excel():
    form = ReportFilterForm()
    _populate_filter_choices(form)
    form.validate()

    rows = _build_query(form).all()
    if not rows:
        flash('No records to export.', 'warning')
        return render_template('reports/index.html', form=form, records=[], summary={})

    df = pd.DataFrame(rows, columns=[
        'Date', 'Quantity (kg)', 'Vehicle ID',
        'Disposal Method', 'Notes', 'Waste Type', 'Location'
    ])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Waste Records')

        # Summary sheet
        summary_data = {
            'Metric': ['Total Records', 'Total Weight (kg)'],
            'Value':  [len(df), round(df['Quantity (kg)'].sum(), 2)]
        }
        pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')

    output.seek(0)
    filename = f'waste_report_{date.today()}.xlsx'
    return send_file(output, download_name=filename, as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@reports_bp.route('/export/pdf', methods=['POST'])
@login_required
def export_pdf():
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable, Image)
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    form = ReportFilterForm()
    _populate_filter_choices(form)
    form.validate()

    rows = _build_query(form).all()
    if not rows:
        flash('No records to export.', 'warning')
        return render_template('reports/index.html', form=form, records=[], summary={})

    output   = io.BytesIO()
    doc      = SimpleDocTemplate(output, pagesize=landscape(A4),
                                  leftMargin=1.5*cm, rightMargin=1.5*cm,
                                  topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles   = getSampleStyleSheet()
    elements = []

    # ── Colour palette ────────────────────────────────────────────
    GREEN     = colors.HexColor('#198754')
    LIGHT_ROW = colors.HexColor('#f0faf4')
    GREY_LINE = colors.HexColor('#dee2e6')

    # ── Custom styles ─────────────────────────────────────────────
    org_style = ParagraphStyle('org', fontSize=16, textColor=GREEN,
                                fontName='Helvetica-Bold', spaceAfter=2)
    sub_style = ParagraphStyle('sub', fontSize=9,  textColor=colors.HexColor('#6c757d'),
                                fontName='Helvetica', spaceAfter=1)
    title_style = ParagraphStyle('title', fontSize=12, textColor=colors.black,
                                  fontName='Helvetica-Bold', spaceBefore=6, spaceAfter=4)

    # ── Header: logo + org details side by side ───────────────────
    logo_path = os.path.join(
        os.path.dirname(__file__), '..', 'static', 'images', 'logo.png'
    )
    logo_path = os.path.normpath(logo_path)

    header_data = [[]]
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2*cm, height=2*cm)
        header_data = [[logo,
                        [Paragraph(ORG_NAME,    org_style),
                         Paragraph(ORG_ADDRESS, sub_style),
                         Paragraph(f'Tel: {ORG_PHONE}', sub_style),
                         Paragraph(f'Email: {ORG_EMAIL}', sub_style)]]]
    else:
        header_data = [[[Paragraph(ORG_NAME,    org_style),
                         Paragraph(ORG_ADDRESS, sub_style),
                         Paragraph(f'Tel: {ORG_PHONE}', sub_style),
                         Paragraph(f'Email: {ORG_EMAIL}', sub_style)]]]

    header_table = Table(header_data, colWidths=[2.5*cm, None] if os.path.exists(logo_path) else [None])
    header_table.setStyle(TableStyle([
        ('VALIGN',  (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width='100%', thickness=1.5, color=GREEN, spaceAfter=6))

    # ── Report title + date range ─────────────────────────────────
    date_range = ''
    if form.date_from.data or form.date_to.data:
        d_from = str(form.date_from.data) if form.date_from.data else 'All time'
        d_to   = str(form.date_to.data)   if form.date_to.data   else 'Present'
        date_range = f'  |  Period: {d_from} to {d_to}'

    elements.append(Paragraph(f'Waste Management Report{date_range}', title_style))
    elements.append(Paragraph(f'Generated: {date.today()}   |   Total records: {len(rows)}',
                               ParagraphStyle('meta', fontSize=8,
                                              textColor=colors.HexColor('#6c757d'),
                                              spaceAfter=8)))

    # ── Summary row ───────────────────────────────────────────────
    df = pd.DataFrame(rows, columns=[
        'date', 'quantity_kg', 'vehicle_id',
        'disposal_method', 'notes', 'waste_type', 'location'
    ])
    total_kg = round(df['quantity_kg'].sum(), 2)
    by_type  = df.groupby('waste_type')['quantity_kg'].sum().round(2).to_dict()

    summary_items = [f'Total: {total_kg} kg'] + \
                    [f'{k}: {v} kg' for k, v in by_type.items()]
    elements.append(Paragraph('  |  '.join(summary_items),
                               ParagraphStyle('summ', fontSize=8, textColor=GREEN,
                                              fontName='Helvetica-Bold', spaceAfter=8)))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=GREY_LINE, spaceAfter=6))

    # ── Data table ────────────────────────────────────────────────
    table_data = [['Date', 'Waste Type', 'Location', 'Vehicle ID', 'Disposal', 'Qty (kg)', 'Notes']]
    for r in rows:
        table_data.append([
            str(r.date_collected),
            r.waste_type,
            r.location,
            r.vehicle_id or '—',
            r.disposal_method or '—',
            f'{r.quantity_kg:.2f}',
            (r.notes or '')[:40],
        ])

    col_widths = [2.5*cm, 3*cm, 4*cm, 2.5*cm, 2.8*cm, 2*cm, None]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND',   (0, 0), (-1, 0), GREEN),
        ('TEXTCOLOR',    (0, 0), (-1, 0), colors.white),
        ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING',(0, 0), (-1, 0), 7),
        ('TOPPADDING',   (0, 0), (-1, 0), 7),
        # Data rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_ROW]),
        ('FONTSIZE',     (0, 1), (-1, -1), 8),
        ('FONTNAME',     (0, 1), (-1, -1), 'Helvetica'),
        ('TOPPADDING',   (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 1), (-1, -1), 5),
        # Grid
        ('GRID',         (0, 0), (-1, -1), 0.4, GREY_LINE),
        ('LINEBELOW',    (0, 0), (-1, 0),  1,   GREEN),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)

    # ── Footer ────────────────────────────────────────────────────
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=GREY_LINE))
    elements.append(Paragraph(
        f'{ORG_NAME}  |  {ORG_ADDRESS}  |  {ORG_PHONE}  |  {ORG_EMAIL}',
        ParagraphStyle('footer', fontSize=7, textColor=colors.HexColor('#6c757d'),
                       alignment=TA_CENTER, spaceBefore=4)
    ))

    doc.build(elements)
    output.seek(0)
    filename = f'waste_report_{date.today()}.pdf'
    return send_file(output, download_name=filename,
                     as_attachment=True, mimetype='application/pdf')
