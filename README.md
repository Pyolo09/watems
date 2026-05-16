# Waste Management System

A Flask web application for logging, tracking, and reporting waste collection data.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create the first admin account
python create_admin.py

# 3. Run the app
python run.py
```

Then open http://127.0.0.1:5000 in your browser.

---

## Project Structure

```
waste_management/
├── run.py                        # Entry point
├── config.py                     # App configuration
├── create_admin.py               # One-time admin setup script
├── requirements.txt
└── app/
    ├── __init__.py               # App factory + DB seeding
    ├── models.py                 # Database models
    ├── forms.py                  # WTForms form classes
    ├── routes/
    │   ├── auth.py               # Login / Register / Logout
    │   ├── dashboard.py          # Dashboard + charts
    │   ├── records.py            # Waste log CRUD
    │   ├── reports.py            # Filtered reports + Excel/PDF export
    │   └── admin.py              # User, type, location management
    ├── templates/
    │   ├── base.html             # Shared layout (navbar, footer)
    │   ├── auth/
    │   ├── dashboard/
    │   ├── records/
    │   ├── reports/
    │   └── admin/
    └── static/
        └── css/custom.css        # Your custom styles
```

---

## Your Decision Points (Things You Must Personalise)

### Branding & UI
| File | What to change |
|---|---|
| `base.html` | System name ("WasteMS"), navbar colour, footer text |
| `static/css/custom.css` | Colours, fonts, card styles |
| `auth/login.html` | Add your logo, background image |
| All templates | Layout, column arrangement, colour scheme |

### Data & Categories
| File | What to change |
|---|---|
| `app/__init__.py` | Default waste types and their colours |
| `app/__init__.py` | Default collection locations/zones |
| `config.py` | Records per page, secret key, database URL |

### Business Rules
| File | What to decide |
|---|---|
| `routes/auth.py` | Open registration vs admin-only account creation |
| `routes/records.py` | Who can edit/delete records (any user vs admin only) |
| `models.py` | Extra fields: vehicle ID, GPS, cost, disposal method |
| `forms.py` | Extra form fields to match your operations |

### Reports & Exports
| File | What to change |
|---|---|
| `routes/reports.py` | PDF header: organisation name, logo, address |
| `routes/reports.py` | Add extra Excel sheets (summary tabs) |
| `dashboard.py` | Chart period (12 months vs 30 days vs weekly) |
| `dashboard/index.html` | Chart types (bar, line, doughnut, pie) |

### Admin Setup
| File | What to change |
|---|---|
| `create_admin.py` | Admin username, email, and password |
| `config.py` | Production database (PostgreSQL URL) |
| `config.py` | Secret key (generate a random one for production) |

---

## Default Credentials (after running create_admin.py)
- Email: `admin@example.com`
- Password: `Admin@1234`

**Change these before deploying.**
