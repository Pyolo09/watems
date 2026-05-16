import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import func
from app import db
from app.models import User, WasteType, Location, WasteRecord
from app.forms import WasteTypeForm, LocationForm, RegisterForm, SuspendUserForm

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def _save_evidence(file_storage):
    """Save suspension evidence file, return filename or None."""
    if not file_storage or not file_storage.filename:
        return None
    ext      = file_storage.filename.rsplit('.', 1)[-1].lower()
    filename = f"evidence_{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.root_path, 'static', 'evidence')
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, filename))
    return filename


# ── Admin Dashboard ───────────────────────────────────────────────────────────
@admin_bp.route('/')
@admin_required
def index():
    users     = User.query.order_by(User.created_at.desc()).all()
    types     = WasteType.query.order_by('name').all()
    locations = Location.query.order_by('name').all()
    return render_template('admin/index.html', title='Admin Panel',
                           users=users, types=types, locations=locations)


# ── System-wide Report (admin only) ──────────────────────────────────────────
@admin_bp.route('/system-report')
@admin_required
def system_report():
    """All operators' totals side by side."""
    # Per-operator totals
    operator_stats = db.session.query(
        User.username,
        User.email,
        User.account_status,
        func.count(WasteRecord.id).label('total_records'),
        func.sum(WasteRecord.quantity_kg).label('total_kg'),
    ).outerjoin(WasteRecord, WasteRecord.user_id == User.id)\
     .filter(User.role == 'operator')\
     .group_by(User.id)\
     .order_by(func.sum(WasteRecord.quantity_kg).desc().nullslast()).all()

    # Per-operator breakdown by waste type
    type_breakdown = db.session.query(
        User.username,
        WasteType.name.label('waste_type'),
        WasteType.color,
        func.sum(WasteRecord.quantity_kg).label('total_kg'),
    ).join(WasteRecord, WasteRecord.user_id == User.id)\
     .join(WasteType, WasteType.id == WasteRecord.waste_type_id)\
     .group_by(User.id, WasteType.id)\
     .order_by(User.username, WasteType.name).all()

    # Per-operator breakdown by disposal method
    disposal_breakdown = db.session.query(
        User.username,
        WasteRecord.disposal_method,
        func.sum(WasteRecord.quantity_kg).label('total_kg'),
    ).join(WasteRecord, WasteRecord.user_id == User.id)\
     .group_by(User.id, WasteRecord.disposal_method)\
     .order_by(User.username).all()

    # System totals
    system_total_kg      = db.session.query(func.sum(WasteRecord.quantity_kg)).scalar() or 0
    system_total_records = WasteRecord.query.count()

    return render_template(
        'admin/system_report.html',
        title='System-wide Report',
        operator_stats      = operator_stats,
        type_breakdown      = type_breakdown,
        disposal_breakdown  = disposal_breakdown,
        system_total_kg     = round(system_total_kg, 2),
        system_total_records= system_total_records,
    )


# ── Activate account ──────────────────────────────────────────────────────────
@admin_bp.route('/users/activate/<int:user_id>', methods=['POST'])
@admin_required
def activate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot change your own account status.', 'warning')
        return redirect(url_for('admin.index'))
    user.account_status      = 'active'
    user.suspension_reason   = None
    user.suspension_evidence = None
    user.suspended_at        = None
    user.suspended_by_id     = None
    db.session.commit()
    flash(f'{user.username} has been activated.', 'success')
    return redirect(url_for('admin.index'))


# ── Deactivate account ────────────────────────────────────────────────────────
@admin_bp.route('/users/deactivate/<int:user_id>', methods=['POST'])
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot change your own account status.', 'warning')
        return redirect(url_for('admin.index'))
    user.account_status = 'inactive'
    db.session.commit()
    flash(f'{user.username} has been deactivated.', 'info')
    return redirect(url_for('admin.index'))


# ── Suspend account (with reason + evidence) ──────────────────────────────────
@admin_bp.route('/users/suspend/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def suspend_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot suspend yourself.', 'warning')
        return redirect(url_for('admin.index'))

    form = SuspendUserForm()
    if form.validate_on_submit():
        evidence_file = _save_evidence(form.evidence.data)
        user.account_status      = 'suspended'
        user.suspension_reason   = form.reason.data
        user.suspension_evidence = evidence_file
        user.suspended_at        = datetime.utcnow()
        user.suspended_by_id     = current_user.id
        db.session.commit()
        flash(f'{user.username} has been suspended.', 'danger')
        return redirect(url_for('admin.index'))

    return render_template('admin/suspend_form.html',
                           form=form, user=user, title='Suspend Account')


# ── View suspension details ───────────────────────────────────────────────────
@admin_bp.route('/users/suspension/<int:user_id>')
@admin_required
def view_suspension(user_id):
    user = User.query.get_or_404(user_id)
    suspended_by = User.query.get(user.suspended_by_id) if user.suspended_by_id else None
    return render_template('admin/suspension_detail.html',
                           user=user, suspended_by=suspended_by,
                           title='Suspension Details')


# ── Add user ──────────────────────────────────────────────────────────────────
@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter(
            (User.email == form.email.data.lower()) |
            (User.username == form.username.data)
        ).first()
        if existing:
            flash('Email or username already taken.', 'danger')
        else:
            role = request.form.get('role', 'operator')
            user = User(username=form.username.data,
                        email=form.email.data.lower(),
                        role=role,
                        account_status='active')
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(f'User {user.username} created.', 'success')
            return redirect(url_for('admin.index'))
    return render_template('admin/user_form.html', form=form, title='Add User')


# ── Waste Type Management ─────────────────────────────────────────────────────
@admin_bp.route('/types/add', methods=['GET', 'POST'])
@admin_required
def add_type():
    form = WasteTypeForm()
    if form.validate_on_submit():
        wt = WasteType(name=form.name.data, color=form.color.data)
        db.session.add(wt)
        db.session.commit()
        flash(f'Waste type "{wt.name}" added.', 'success')
        return redirect(url_for('admin.index'))
    return render_template('admin/type_form.html', form=form, title='Add Waste Type')


@admin_bp.route('/types/delete/<int:type_id>', methods=['POST'])
@admin_required
def delete_type(type_id):
    wt = WasteType.query.get_or_404(type_id)
    db.session.delete(wt)
    db.session.commit()
    flash(f'Waste type "{wt.name}" deleted.', 'warning')
    return redirect(url_for('admin.index'))


# ── Location Management ───────────────────────────────────────────────────────
@admin_bp.route('/locations/add', methods=['GET', 'POST'])
@admin_required
def add_location():
    form = LocationForm()
    if form.validate_on_submit():
        loc = Location(name=form.name.data)
        db.session.add(loc)
        db.session.commit()
        flash(f'Location "{loc.name}" added.', 'success')
        return redirect(url_for('admin.index'))
    return render_template('admin/location_form.html', form=form, title='Add Location')


@admin_bp.route('/locations/delete/<int:loc_id>', methods=['POST'])
@admin_required
def delete_location(loc_id):
    loc = Location.query.get_or_404(loc_id)
    db.session.delete(loc)
    db.session.commit()
    flash(f'Location "{loc.name}" deleted.', 'warning')
    return redirect(url_for('admin.index'))
