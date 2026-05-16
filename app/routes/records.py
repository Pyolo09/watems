import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import WasteRecord, WasteType, Location
from app.forms import WasteRecordForm

records_bp = Blueprint('records', __name__, url_prefix='/records')

UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


def _populate_form_choices(form):
    """Helper: load dropdown choices from DB."""
    form.waste_type_id.choices = [(t.id, t.name) for t in WasteType.query.order_by('name').all()]
    form.location_id.choices   = [(l.id, l.name) for l in Location.query.order_by('name').all()]


def _save_photo(file_storage):
    """Save uploaded photo and return the filename, or None."""
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, filename))
    return filename


def _delete_photo(filename):
    """Remove a photo file from disk if it exists."""
    if filename:
        path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        if os.path.exists(path):
            os.remove(path)


@records_bp.route('/')
@login_required
def index():
    page     = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('RECORDS_PER_PAGE', 15)

    type_filter     = request.args.get('type',     type=int)
    location_filter = request.args.get('location', type=int)
    date_from       = request.args.get('date_from')
    date_to         = request.args.get('date_to')

    query = WasteRecord.query
    if type_filter:
        query = query.filter_by(waste_type_id=type_filter)
    if location_filter:
        query = query.filter_by(location_id=location_filter)
    if date_from:
        query = query.filter(WasteRecord.date_collected >= date_from)
    if date_to:
        query = query.filter(WasteRecord.date_collected <= date_to)

    records = query.order_by(WasteRecord.date_collected.desc())\
                   .paginate(page=page, per_page=per_page, error_out=False)

    waste_types = WasteType.query.order_by('name').all()
    locations   = Location.query.order_by('name').all()

    return render_template(
        'records/index.html',
        title='Waste Records',
        records=records,
        waste_types=waste_types,
        locations=locations,
    )


@records_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = WasteRecordForm()
    _populate_form_choices(form)

    if form.validate_on_submit():
        photo_filename = _save_photo(form.photo.data)
        record = WasteRecord(
            date_collected  = form.date_collected.data,
            quantity_kg     = form.quantity_kg.data,
            waste_type_id   = form.waste_type_id.data,
            location_id     = form.location_id.data,
            user_id         = current_user.id,
            vehicle_id      = form.vehicle_id.data.strip(),
            disposal_method = form.disposal_method.data,
            photo_filename  = photo_filename,
            notes           = form.notes.data,
        )
        db.session.add(record)
        db.session.commit()
        flash('Waste record saved successfully.', 'success')
        return redirect(url_for('records.index'))

    return render_template('records/form.html', form=form, title='Log Waste', action='Add')


@records_bp.route('/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit(record_id):
    record = WasteRecord.query.get_or_404(record_id)

    form = WasteRecordForm(obj=record)
    _populate_form_choices(form)

    if form.validate_on_submit():
        # Replace photo only if a new one was uploaded
        if form.photo.data and form.photo.data.filename:
            _delete_photo(record.photo_filename)
            record.photo_filename = _save_photo(form.photo.data)

        record.date_collected  = form.date_collected.data
        record.quantity_kg     = form.quantity_kg.data
        record.waste_type_id   = form.waste_type_id.data
        record.location_id     = form.location_id.data
        record.vehicle_id      = form.vehicle_id.data.strip()
        record.disposal_method = form.disposal_method.data
        record.notes           = form.notes.data
        db.session.commit()
        flash('Record updated.', 'success')
        return redirect(url_for('records.index'))

    return render_template('records/form.html', form=form, title='Edit Record',
                           action='Update', record=record)


@records_bp.route('/delete/<int:record_id>', methods=['POST'])
@login_required
def delete(record_id):
    record = WasteRecord.query.get_or_404(record_id)
    _delete_photo(record.photo_filename)
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted.', 'warning')
    return redirect(url_for('records.index'))
