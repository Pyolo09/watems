from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────────────────────────────────────────────────────────
# USER MODEL
# [DECISION] You may want to add extra profile fields:
#   - phone number, department, profile picture, etc.
# ─────────────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id                  = db.Column(db.Integer, primary_key=True)
    username            = db.Column(db.String(64),  unique=True, nullable=False)
    email               = db.Column(db.String(120), unique=True, nullable=False)
    password_hash       = db.Column(db.String(256), nullable=False)
    role                = db.Column(db.String(20),  default='operator')  # 'admin' or 'operator'
    created_at          = db.Column(db.DateTime,    default=datetime.utcnow)

    # Account status: 'active', 'inactive', 'suspended'
    account_status      = db.Column(db.String(20),  default='active')
    suspension_reason   = db.Column(db.Text,        nullable=True)
    suspension_evidence = db.Column(db.String(256), nullable=True)  # filename of uploaded image
    suspended_at        = db.Column(db.DateTime,    nullable=True)
    suspended_by_id     = db.Column(db.Integer,     db.ForeignKey('users.id'), nullable=True)

    records = db.relationship('WasteRecord', backref='logged_by', lazy=True)

    # Flask-Login requires is_active as a property
    @property
    def is_active(self):
        return self.account_status == 'active'

    def is_admin(self):
        return self.role == 'admin'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def status_badge(self):
        return {
            'active':    ('bg-success',  'Active'),
            'inactive':  ('bg-secondary','Inactive'),
            'suspended': ('bg-danger',   'Suspended'),
        }.get(self.account_status, ('bg-secondary', self.account_status.capitalize()))

    def __repr__(self):
        return f'<User {self.username}>'


# ─────────────────────────────────────────────────────────────────────────────
# WASTE TYPE (lookup table)
# [DECISION] Managed via the admin panel — add your own categories there.
# ─────────────────────────────────────────────────────────────────────────────
class WasteType(db.Model):
    __tablename__ = 'waste_types'

    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(64), unique=True, nullable=False)
    # [DECISION] color is used for chart/badge display — pick your own hex codes
    color   = db.Column(db.String(10), default='#6c757d')

    records = db.relationship('WasteRecord', backref='waste_type', lazy=True)

    def __repr__(self):
        return f'<WasteType {self.name}>'


# ─────────────────────────────────────────────────────────────────────────────
# LOCATION (lookup table)
# [DECISION] Managed via the admin panel — add your collection zones/sites.
# ─────────────────────────────────────────────────────────────────────────────
class Location(db.Model):
    __tablename__ = 'locations'

    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(128), unique=True, nullable=False)

    records = db.relationship('WasteRecord', backref='location', lazy=True)

    def __repr__(self):
        return f'<Location {self.name}>'


# ─────────────────────────────────────────────────────────────────────────────
# WASTE RECORD (main data table)
# [DECISION] You may want to add:
#   - GPS coordinates, truck/vehicle ID, images/attachments,
#     disposal method, cost per kg, compliance flag, etc.
# ─────────────────────────────────────────────────────────────────────────────
class WasteRecord(db.Model):
    __tablename__ = 'waste_records'

    id              = db.Column(db.Integer, primary_key=True)
    date_collected  = db.Column(db.Date,    nullable=False, default=datetime.utcnow)
    quantity_kg     = db.Column(db.Float,   nullable=False)
    waste_type_id   = db.Column(db.Integer, db.ForeignKey('waste_types.id'), nullable=False)
    location_id     = db.Column(db.Integer, db.ForeignKey('locations.id'),   nullable=False)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'),       nullable=False)
    vehicle_id      = db.Column(db.String(64),  nullable=True)
    disposal_method = db.Column(db.String(64),  nullable=True)
    photo_filename  = db.Column(db.String(256), nullable=True)
    notes           = db.Column(db.Text,    nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WasteRecord {self.id} – {self.quantity_kg}kg>'
