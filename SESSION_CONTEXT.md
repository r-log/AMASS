# Session Context – Electrician Log MVP (AMASS)

**Purpose:** Start new conversations with full context. Reference this file when continuing work.

---

## Project Overview

- **Stack:** Flask (Python) backend + Vue.js frontend (vanilla Vue 3 from CDN)
- **Use case:** Electrician work logs on floor plans, critical sectors, role-based access (admin, supervisor, worker)
- **Repo:** https://github.com/r-log/AMASS.git
- **Latest tag:** `post-refactor-checkpoint`

---

## Running the App

```bash
cd backend
python run.py
```

- **URL:** http://localhost:5000/
- Flask serves the frontend and API on port 5000
- No separate HTTP server needed

---

## Architecture Summary

### Backend (Flask)
- **API prefixes:** `/api/auth`, `/api/projects`, `/api/floors`, `/api/work-logs`, `/api/critical-sectors`, `/api/assignments`, `/api/notifications`, `/api/tiles`, `/api/dashboard`
- **Auth:** JWT, roles: admin, supervisor, worker
- **Decorators:** `@token_required`, `@supervisor_required`, `@supervisor_or_admin_required`, `@admin_required`
- **DB:** SQLite (`backend/database.db`)

### Main Models
- **Project** – Building/construction project
- **ProjectUserAssignment** – Worker–project assignments
- **Floor** – Belongs to project, floor plan (PDF/image)
- **WorkLog** – Work performed at coordinates on a floor
- **CriticalSector** – Sensitive areas on floors
- **Assignment** – Work assignments
- **User** – admin, supervisor, worker

### Frontend
- **Pages:** `login.html`, `index.html` (map), `supervisor_dashboard.html`, `worker_dashboard.html`, `admin_dashboard.html`
- **Services:** API clients in `frontend/core/api/`
- **Map:** OpenSeadragon for floor plans, tile-based (DZI)
- **Auth:** `auth.js`, `AuthManager`

---

## Features Implemented (This Session)

### Projects & Floors
- Projects with floors
- Removed "All projects" – project selection required
- **Auto floor names:** Ground Floor, 1st Floor, 2nd Floor, etc. (no manual input)
- Add Floor modal: file upload only, name auto-generated

### Project Delete
- `DELETE /api/projects/<id>` – full cascade delete
- **Backup:** ZIP in `project-backups/` before delete (project data + floor plans)
- `ProjectBackupService`, cascade delete in `ProjectService.delete_project`
- Supervisor or admin only

### Tiles
- Fixed tiles generate 500 – backend accepts `floor_id` from URL, optional body
- `TILES_DIRECTORY` in config
- Tile cache cleared per floor on project delete

### Frontend & Logos
- Flask serves frontend: `/`, `/login.html`, `/index.html`, `/supervisor_dashboard.html`, etc.
- **Logos:** `frontend/assets/Logo.png`, `frontend/assets/Logo (light).png` (AMASS branding)
- `assets/` and `frontend/assets/` in `.gitignore`

### Map-Based Assignments (Supervisor)
- Supervisors create assignments by clicking on the blueprint map
- Click opens "Create Assignment" modal: work type, description, due date, worker multi-select
- Creates work log (pin) at click location, then creates assignments for each selected worker
- Workers must be assigned to the project first (Projects tab)

### Project Restore
- `POST /api/projects/restore` – restore project from backup ZIP (supervisor/admin only)
- `ProjectBackupService.restore_from_backup()` – parses ZIP, recreates project, floors, work logs, sectors, assignments
- Supervisor dashboard: "Restore from Backup" button with file picker

### Config
- `PROJECT_BACKUPS_DIR` – project-backups/
- `TILES_DIRECTORY` – backend/tiles
- `FLOOR_PLANS_DIR` – floor-plans/
- Database backup patterns in `.gitignore`

---

## File Layout (Key Paths)

```
electrician-log-mvp/
├── backend/
│   ├── run.py                 # Entry point
│   ├── app/
│   │   ├── __init__.py        # Flask app, serves frontend
│   │   ├── api/               # Blueprints
│   │   │   ├── projects/      # Projects CRUD, delete
│   │   │   ├── floors/
│   │   │   ├── tiles/
│   │   │   └── ...
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── project_service.py
│   │   │   ├── project_backup_service.py
│   │   │   └── floor_service.py
│   │   └── config.py
│   └── database.db
├── frontend/
│   ├── index.html             # Map view
│   ├── login.html
│   ├── supervisor_dashboard.html
│   ├── worker_dashboard.html
│   ├── admin_dashboard.html
│   ├── app-openseadragon.js    # Main Vue app for map
│   ├── assets/                # Logos (gitignored)
│   └── core/api/
├── assets/                    # Original logos (gitignored)
├── floor-plans/               # PDF floor plans (gitignored)
├── project-backups/           # ZIP backups (gitignored)
└── SESSION_CONTEXT.md         # This file
```

---

## Git State

- **Branch:** main (pushed)
- **Tags:** `pre-refactor-checkpoint`, `post-refactor-checkpoint`
- **Recent commits:**
  1. feat: project management, delete with backup, auto floor names, logos, Flask serves frontend
  2. chore: add logo and assets to gitignore

---

## Known / Resolved (from PROBLEMOVI.md)

- ✅ Role of user in sidebar (currentUser reactive)
- ✅ Critical sectors: visible to all, edit by admin/supervisor only

---

## Suggested Next Steps (If Any)

- Further UI/UX refinements
- Tests for project delete + backup flow

---

*Last updated: Feb 2025*
