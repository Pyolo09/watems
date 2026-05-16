from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import WasteRecord, WasteType, Location
from app import db
from datetime import date, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    uid = current_user.id  # scope everything to the logged-in user

    # ── Summary cards (current user only) ────────────────────────
    total_records = WasteRecord.query.filter_by(user_id=uid).count()

    total_kg = db.session.query(func.sum(WasteRecord.quantity_kg))\
        .filter_by(user_id=uid).scalar() or 0

    thirty_days_ago = date.today() - timedelta(days=30)
    recent_kg = db.session.query(func.sum(WasteRecord.quantity_kg))\
        .filter(WasteRecord.user_id == uid,
                WasteRecord.date_collected >= thirty_days_ago).scalar() or 0

    # ── Hazardous waste alert ─────────────────────────────────────
    # Checks the current user's hazardous waste logged this calendar month.
    threshold    = current_app.config.get('HAZARDOUS_ALERT_KG', 500)
    month_start  = date.today().replace(day=1)
    hazardous_type = WasteType.query.filter(
        WasteType.name.ilike('%hazardous%')
    ).first()

    hazardous_kg   = 0
    hazardous_alert = False
    if hazardous_type:
        hazardous_kg = db.session.query(func.sum(WasteRecord.quantity_kg))\
            .filter(WasteRecord.user_id      == uid,
                    WasteRecord.waste_type_id == hazardous_type.id,
                    WasteRecord.date_collected >= month_start).scalar() or 0
        hazardous_alert = hazardous_kg >= threshold

    # ── Chart 1: Waste by type — current user ────────────────────
    by_type = db.session.query(
        WasteType.name,
        WasteType.color,
        func.sum(WasteRecord.quantity_kg).label('total')
    ).join(WasteRecord)\
     .filter(WasteRecord.user_id == uid)\
     .group_by(WasteType.id).all()

    type_labels = [r.name  for r in by_type]
    type_data   = [round(r.total, 2) for r in by_type]
    type_colors = [r.color for r in by_type]

    # ── Chart 2: Monthly trend — current user ────────────────────
    twelve_months_ago = date.today().replace(day=1) - timedelta(days=365)
    monthly = db.session.query(
        func.strftime('%Y-%m', WasteRecord.date_collected).label('month'),
        func.sum(WasteRecord.quantity_kg).label('total')
    ).filter(WasteRecord.user_id == uid,
             WasteRecord.date_collected >= twelve_months_ago)\
     .group_by('month').order_by('month').all()

    month_labels = [r.month for r in monthly]
    month_data   = [round(r.total, 2) for r in monthly]

    # ── Chart 3: By location — current user ──────────────────────
    by_location = db.session.query(
        Location.name,
        func.sum(WasteRecord.quantity_kg).label('total')
    ).join(WasteRecord)\
     .filter(WasteRecord.user_id == uid)\
     .group_by(Location.id)\
     .order_by(func.sum(WasteRecord.quantity_kg).desc()).all()

    loc_labels = [r.name  for r in by_location]
    loc_data   = [round(r.total, 2) for r in by_location]

    # ── Recent records — current user (anonymous system-wide view) ─
    # Own records: show full detail
    own_recent = WasteRecord.query\
        .filter_by(user_id=uid)\
        .order_by(WasteRecord.created_at.desc()).limit(5).all()

    # Other users' records: anonymised (no username shown)
    other_recent = WasteRecord.query\
        .filter(WasteRecord.user_id != uid)\
        .order_by(WasteRecord.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard/index.html',
        title='Dashboard',
        total_records   = total_records,
        total_kg        = round(total_kg, 2),
        recent_kg       = round(recent_kg, 2),
        hazardous_kg    = round(hazardous_kg, 2),
        hazardous_alert = hazardous_alert,
        threshold       = threshold,
        type_labels     = type_labels,
        type_data       = type_data,
        type_colors     = type_colors,
        month_labels    = month_labels,
        month_data      = month_data,
        loc_labels      = loc_labels,
        loc_data        = loc_data,
        own_recent      = own_recent,
        other_recent    = other_recent,
    )
