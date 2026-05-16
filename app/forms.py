import re
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, SubmitField, SelectField,
                     FloatField, DateField, TextAreaField, BooleanField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                NumberRange, Optional, ValidationError)
from datetime import date


def alphanumeric_password(form, field):
    """Password must contain at least one letter and one number."""
    value = field.data or ''
    if not re.search(r'[A-Za-z]', value):
        raise ValidationError('Password must contain at least one letter.')
    if not re.search(r'[0-9]', value):
        raise ValidationError('Password must contain at least one number.')


# ─────────────────────────────────────────────────────────────────────────────
# AUTH FORMS
# ─────────────────────────────────────────────────────────────────────────────
class LoginForm(FlaskForm):
    # [DECISION] Login by username OR email — currently uses email.
    # Change the field and validator if you prefer username login.
    email    = StringField('Email',    validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit   = SubmitField('Log In')


class RegisterForm(FlaskForm):
    username         = StringField('Username',         validators=[DataRequired(), Length(3, 64)])
    email            = StringField('Email',            validators=[DataRequired(), Email()])
    password         = PasswordField('Password',       validators=[
                           DataRequired(),
                           Length(min=6, message='Password must be at least 6 characters.'),
                           alphanumeric_password,
                       ])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit           = SubmitField('Register')


# ─────────────────────────────────────────────────────────────────────────────
# WASTE RECORD FORM
# [DECISION] Add or remove fields here to match what your operators need to log.
# ─────────────────────────────────────────────────────────────────────────────
class WasteRecordForm(FlaskForm):
    date_collected  = DateField('Date Collected', validators=[DataRequired()],
                                default=date.today)
    quantity_kg     = FloatField('Quantity (kg)',
                                 validators=[DataRequired(),
                                             NumberRange(min=0.01, message='Must be greater than 0')])
    waste_type_id   = SelectField('Waste Type',  coerce=int, validators=[DataRequired()])
    location_id     = SelectField('Location',    coerce=int, validators=[DataRequired()])
    vehicle_id      = StringField('Vehicle / Truck ID',
                                  validators=[DataRequired(), Length(max=64)],
                                  render_kw={'placeholder': 'e.g. TRK-001'})
    disposal_method = SelectField('Disposal Method', validators=[DataRequired()], choices=[
                          ('', '— Select —'),
                          ('Recycling',    'Recycling'),
                          ('Incineration', 'Incineration'),
                          ('Composting',   'Composting'),
                      ])
    photo           = FileField('Photo of Waste (optional)',
                                validators=[Optional(),
                                            FileAllowed(['jpg', 'jpeg', 'png', 'webp'],
                                                        'Images only (jpg, png, webp).')])
    notes           = TextAreaField('Notes (optional)', validators=[Optional(), Length(max=500)])
    submit          = SubmitField('Save Record')


# ─────────────────────────────────────────────────────────────────────────────
# REPORT FILTER FORM
# [DECISION] Add more filter options if needed (e.g. filter by user/operator).
# ─────────────────────────────────────────────────────────────────────────────
class ReportFilterForm(FlaskForm):
    date_from     = DateField('From', validators=[Optional()])
    date_to       = DateField('To',   validators=[Optional()])
    waste_type_id = SelectField('Waste Type', coerce=int)
    location_id   = SelectField('Location',   coerce=int)
    submit        = SubmitField('Apply Filter')


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — WASTE TYPE FORM
# ─────────────────────────────────────────────────────────────────────────────
class WasteTypeForm(FlaskForm):
    name   = StringField('Category Name', validators=[DataRequired(), Length(2, 64)])
    # [DECISION] Color picker — default is a hex input. You can wire this to a
    # proper HTML color picker widget in the template.
    color  = StringField('Badge Color (hex)', validators=[DataRequired()], default='#6c757d')
    submit = SubmitField('Save')


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — LOCATION FORM
# ─────────────────────────────────────────────────────────────────────────────
class LocationForm(FlaskForm):
    name   = StringField('Location Name', validators=[DataRequired(), Length(2, 128)])
    submit = SubmitField('Save')


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — SUSPEND USER FORM
# ─────────────────────────────────────────────────────────────────────────────
class SuspendUserForm(FlaskForm):
    reason   = TextAreaField('Reason for Suspension',
                             validators=[DataRequired(), Length(min=10, max=1000)],
                             render_kw={'rows': 4,
                                        'placeholder': 'Describe the reason for suspending this account...'})
    evidence = FileField('Supporting Evidence (optional image)',
                         validators=[Optional(),
                                     FileAllowed(['jpg', 'jpeg', 'png', 'webp', 'pdf'],
                                                 'Images or PDF only.')])
    submit   = SubmitField('Suspend Account')
