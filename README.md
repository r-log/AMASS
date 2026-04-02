# Electrician Log MVP

Electrician Log MVP is a full-stack web app for tracking electrical work on floor plans.  
It uses a Flask backend, a modular browser frontend (Vue via CDN), OpenSeadragon for map viewing, JWT auth, role-based dashboards, real-time updates, and offline mutation queueing.

## What Is Implemented

- JWT authentication with role-based access (`worker`, `supervisor`, `admin`)
- Project-based workflow (projects, floor plans, worker assignment to projects)
- Interactive floor map with work log markers
- Critical sector management
- Work assignments and notifications
- Role dashboards (`worker_dashboard`, `supervisor_dashboard`, `admin_dashboard`)
- Tile generation and tile serving for floor plans
- Real-time updates via WebSocket (`/ws`)
- Offline mutation queue + background sync service worker for unstable connections
- Project delete + backup ZIP and restore from backup ZIP

## Tech Stack

- **Backend:** Flask, Flask-CORS, Flask-Sock, SQLite, PyJWT, bcrypt
- **Image/tiles:** pyvips, Pillow, pdf2image
- **Frontend:** Vue 3 (CDN), OpenSeadragon, Tailwind CSS, Chart.js
- **Tests:** pytest

## Project Structure

```text
backend/
  run.py
  run_migrations.py
  requirements.txt
  app/
    __init__.py
    config.py
    api/
      auth/
      projects/
      floors/
      work_logs/
      critical_sectors/
      assignments/
      notifications/
      dashboard/
      tiles/
    realtime/
      __init__.py
    services/
    models/
    database/
    utils/
  tests/
  utils/
    setup_admin.py
    user_manager.py
    tile_generator_safe.py
    regenerate_tiles_safe.py
    regenerate_all_tiles_hd.py

frontend/
  login.html
  index.html
  worker_dashboard.html
  supervisor_dashboard.html
  admin_dashboard.html
  app-openseadragon.js
  auth.js
  sw-offline-sync.js
  core/
    api/
    realtime/
    offline/
    utils/
  map/
  components/
  css/
```

## Quick Start

### 1) Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2) Run migrations

```bash
python run_migrations.py
```

### 3) Create admin user

```bash
python utils/setup_admin.py
```

### 4) Start the app

```bash
python run.py
```

App runs at `http://localhost:5000`.

The backend also serves frontend files, so use:

- [http://localhost:5000/login.html](http://localhost:5000/login.html)
- [http://localhost:5000/index.html](http://localhost:5000/index.html)

## Configuration

Main backend config is in `backend/app/config.py`.

Useful environment variables:

- `FLASK_ENV` (`development` / `production` / `testing`)
- `SECRET_KEY`
- `DATABASE_PATH`
- `FLOOR_PLANS_DIR`
- `PROJECT_BACKUPS_DIR`
- `CORS_ORIGINS` (comma-separated)
- `JWT_EXPIRATION_HOURS`
- Tile settings: `TILES_DIRECTORY`, `TILE_SIZE`, `TILE_OVERLAP`, `TILE_DPI`, `TILE_PNG_COMPRESS_LEVEL`, `TILE_MAX_LEVEL`

Frontend base API URL is defined in `frontend/config/app.config.js` (`api.baseUrl`).

## Main API Groups

Base URL: `http://localhost:5000/api`

- `/auth` - login, logout, verify, refresh, profile, users, password management
- `/projects` - CRUD, worker assignment, restore backup, delete with backup
- `/floors` - CRUD, upload, summaries/statistics/activity
- `/work-logs` - CRUD, dashboard, export, spatial helpers, bulk update
- `/critical-sectors` - CRUD + statistics/check/export/bulk update
- `/assignments` - CRUD + status/statistics/worker queries/bulk create
- `/notifications` - list/read/read-all/clear/statistics
- `/dashboard` - supervisor dashboard aggregates
- `/tiles` - generate/regenerate/status/clear/list/serve/batch

## Real-Time Updates

- WebSocket endpoint: `/ws`
- Authenticated via JWT token in query string (`?token=...`)
- Frontend client: `frontend/core/realtime/ws-client.js`
- Backend broadcast hub: `backend/app/realtime/__init__.py`

## Offline Support

- Offline queue stores mutation requests (POST/PUT/PATCH/DELETE) in IndexedDB
- Queue replays when API is reachable again
- Background Sync integration via `frontend/sw-offline-sync.js`
- Core module: `frontend/core/offline/offline-queue.js`

## User Roles

- `worker`: creates/updates own work logs, sees worker dashboard
- `supervisor`: project/floor operations, assignments, critical sectors, supervision dashboards
- `admin`: full access, administration dashboard and management actions

## Development & Testing

Run tests:

```bash
cd backend
python -m pytest tests/
```

Current test files:

- `backend/tests/test_auth.py`
- `backend/tests/test_project_delete_backup.py`

## Common Commands

Create/manage users:

```bash
cd backend
python utils/user_manager.py
```

Regenerate tiles:

```bash
cd backend
python utils/regenerate_tiles_safe.py
python utils/regenerate_all_tiles_hd.py
```

## Notes

- The repository may contain additional planning docs like `PLAN.md` and `PROBLEMOVI.md`.
- This README is intentionally focused on implemented architecture and practical setup/use.

## License

MIT
# Electrician Work Log System - Refactored Architecture

A professional web application for tracking electrician work logs across multiple floors of a building using high-performance OpenSeadragon tile-based floor plan visualization with JWT authentication and role-based access control.

## ✨ Features

- 🔐 **JWT Authentication** - Secure user authentication with role-based access (Worker, Supervisor, Admin)
- 🗺️ **OpenSeadragon Integration** - High-performance tile-based floor plan viewing with zoom and pan
- 📍 **Interactive Floor Plans** - Click to place work markers with visual feedback
- ⚠️ **Critical Sectors** - Define and manage critical areas on floor plans (Supervisor/Admin)
- 📊 **Role-Based Dashboards** - Customized views for Workers, Supervisors, and Admins
- 📅 **Date Navigation** - Filter and navigate work logs by date with keyboard shortcuts
- 🎨 **Dark Theme** - Modern dark UI with golden accents
- 💾 **SQLite Database** - Lightweight and portable database
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile devices

## 🏗️ Architecture

### Backend - Modular Flask Application

The backend follows a **clean architecture** pattern with separation of concerns:

```
backend/
├── run.py                      # Application entry point (NEW)
├── run_migrations.py           # Database migration runner
├── requirements.txt            # Python dependencies
├── database.db                 # SQLite database (auto-created)
├── app/                        # Main application package
│   ├── __init__.py            # Flask app factory
│   ├── config.py              # Configuration management
│   ├── api/                   # API route blueprints
│   │   ├── auth/              # Authentication routes
│   │   ├── work_logs/         # Work log routes
│   │   ├── floors/            # Floor routes
│   │   ├── critical_sectors/  # Critical sector routes
│   │   ├── assignments/       # Work assignment routes
│   │   ├── dashboard/         # Supervisor stats (uses DashboardService)
│   │   ├── notifications/     # Notification routes
│   │   └── tiles/             # Tile generation routes
│   ├── services/              # Business logic layer
│   │   ├── auth_service.py
│   │   ├── work_log_service.py
│   │   ├── floor_service.py
│   │   ├── dashboard_service.py   # Supervisor stats
│   │   └── ...
│   ├── models/                # Data models
│   │   ├── user.py
│   │   ├── work_log.py
│   │   ├── floor.py
│   │   └── ...
│   ├── database/              # Database management
│   │   ├── connection.py
│   │   └── migrations.py
│   └── utils/                 # Utilities
│       ├── decorators.py      # Auth decorators (_extract_and_validate_token)
│       ├── result.py          # ServiceResult dataclass
│       ├── validators.py
│       └── helpers.py
├── utils/                     # CLI utilities
│   ├── user_manager.py        # User management CLI
│   ├── setup_admin.py         # Admin setup script
│   └── tile_generator_safe.py # Tile generation utility
└── tiles/                     # Generated DZI tiles
    ├── floor-1/
    ├── floor-2/
    └── ...
```

### Frontend - Modular Vue.js Application

The frontend uses Vue.js 3 with a service-oriented architecture:

```
frontend/
├── index.html                 # Main application (OpenSeadragon)
├── login.html                 # Login page
├── worker_dashboard.html      # Worker dashboard
├── supervisor_dashboard.html  # Supervisor dashboard
├── app-openseadragon.js       # Main Vue.js app (uses MarkerManager)
├── auth.js                    # Authentication manager
├── login.js                   # Login page logic
├── theme.js                   # Theme switcher
├── theme.css                  # Theme styles
├── config/
│   └── app.config.js         # Frontend configuration
├── core/
│   ├── api/                  # API service layer
│   │   ├── api.client.js     # HTTP client with auth
│   │   ├── auth.service.js   # Auth API calls
│   │   ├── workLogs.service.js
│   │   ├── floors.service.js
│   │   ├── tiles.service.js
│   │   └── criticalSectors.service.js
│   └── utils/                # Utility functions
│       ├── date.utils.js
│       └── format.utils.js
├── css/
│   └── dashboard-shared.css  # Shared dashboard styles
├── map/
│   └── marker-manager.js    # OpenSeadragon marker handling
└── components/
    ├── critical-sector-drawer.js
    ├── dashboard-components.js   # StatCard, shared components
    └── sector-integration-methods.js
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.7+** installed
- **Modern web browser** (Chrome, Firefox, Safari, Edge)
- **pip** package manager

### Installation

1. **Clone or download the repository**

2. **Install Python dependencies:**

```bash
cd backend
pip install -r requirements.txt
```

3. **Set up the database and create an admin user:**

```bash
# Run database migrations
python run_migrations.py

# Create admin user (interactive)
python utils/setup_admin.py
```

### Running the Application

1. **Start the backend server:**

```bash
cd backend
python run.py
```

The server will start on `http://localhost:5000`

You should see:

```
============================================================
🏗️  Electrician Log MVP - Refactored Architecture
Environment: development
Database: database.db
============================================================
Available API endpoints:
  Authentication:
    POST /api/auth/login - User login
    POST /api/auth/logout - User logout
    GET  /api/auth/verify - Verify token
    POST /api/auth/refresh - Refresh token
  Work Logs:
    GET  /api/work-logs - Get work logs
    POST /api/work-logs - Create work log
    PUT  /api/work-logs/<id> - Update work log
    DELETE /api/work-logs/<id> - Delete work log
  Critical Sectors:
    GET  /api/critical-sectors - Get critical sectors
    POST /api/critical-sectors - Create critical sector
  Tiles:
    POST /api/tiles/generate/<floor_id> - Generate tiles
    GET  /api/tiles/status/<floor_id> - Check tile status
============================================================
🔐 Authentication enabled!
📊 Modular architecture active!
============================================================
```

2. **Open the frontend:**

   - Open `frontend/login.html` in your web browser
   - Or navigate to: `file:///path/to/electrician-log-mvp/frontend/login.html`
   - Login with your admin credentials
   - You'll be redirected to the main application

### User Management

**Create users via CLI:**

```bash
cd backend
python utils/user_manager.py
```

**Available roles:**

- `worker` - Can create and view work logs
- `supervisor` - Can manage critical sectors and view all logs
- `admin` - Full system access

## 📖 Usage Guide

### Login

1. Open `frontend/login.html`
2. Enter your credentials
3. Click "Sign In"

### Map View (All Users)

1. **Select a Floor** - Choose from available floors in the left panel
2. **View Work Logs** - Markers show work locations (color-coded by work type)
3. **Click Marker** - View work log details
4. **Click Empty Area** - Create new work log at that location
5. **Date Navigation** - Use date controls to filter logs by date
6. **Keyboard Shortcuts:**
   - `1-6` - Jump to floor 1-6
   - `←/→` - Navigate between dates
   - `T` - Go to today
   - `A` - Toggle date filter
   - `R` - Reset view
   - `F` - Toggle fullscreen
   - `ESC` - Show all dates

### Critical Sectors (Supervisor/Admin Only)

1. **Draw Rectangle** - Click "Draw Rectangle" button, click two corners
2. **Draw Polygon** - Click "Draw Polygon" button, click points, double-click to finish
3. **Save Sector** - Enter name and priority, click save
4. **View Sectors** - Toggle visibility with "Show/Hide Sectors"
5. **Delete Sector** - Click sector, view details, click delete

### Dashboard View

Access via the sidebar menu:

- **Worker Dashboard** - View assignments and personal work logs
- **Supervisor Dashboard** - Manage critical sectors, view all work, create assignments
- **Admin Dashboard** - System statistics, tile generation, user management

## 🔌 API Documentation

### Base URL

```
http://localhost:5000/api
```

### Authentication

All API endpoints (except `/api/auth/login`) require a JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Key Endpoints

#### Authentication

```http
POST   /api/auth/login          # Login user
POST   /api/auth/logout         # Logout user
GET    /api/auth/verify         # Verify token
POST   /api/auth/refresh        # Refresh token
```

#### Work Logs

```http
GET    /api/work-logs           # Get work logs (with filters)
POST   /api/work-logs           # Create work log
GET    /api/work-logs/<id>      # Get specific work log
PUT    /api/work-logs/<id>      # Update work log
DELETE /api/work-logs/<id>      # Delete work log
GET    /api/work-logs/dashboard # Get dashboard stats
```

**Query Parameters for GET /api/work-logs:**

- `floor_id` - Filter by floor
- `worker_id` - Filter by worker
- `start_date` - From date (YYYY-MM-DD)
- `end_date` - To date (YYYY-MM-DD)

#### Floors

```http
GET    /api/floors              # Get all floors
GET    /api/floors/<id>         # Get specific floor
POST   /api/floors              # Create floor (admin)
PUT    /api/floors/<id>         # Update floor (admin)
```

#### Critical Sectors

```http
GET    /api/critical-sectors    # Get critical sectors
POST   /api/critical-sectors    # Create critical sector (supervisor/admin)
DELETE /api/critical-sectors/<id> # Delete critical sector (supervisor/admin)
```

#### Tiles

```http
POST   /api/tiles/generate/<floor_id>  # Generate tiles for floor
GET    /api/tiles/status/<floor_id>    # Check tile status
GET    /api/tiles/<floor_id>/<path>    # Serve tile files
POST   /api/tiles/batch-generate       # Generate all tiles (admin)
```

#### Assignments (Supervisor/Admin)

```http
GET    /api/assignments         # Get assignments
POST   /api/assignments         # Create assignment
PUT    /api/assignments/<id>    # Update assignment
```

#### Notifications

```http
GET    /api/notifications       # Get notifications
PUT    /api/notifications/<id>/read  # Mark as read
```

### Example: Create Work Log

```bash
curl -X POST http://localhost:5000/api/work-logs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "floor_id": 1,
    "x_coord": 0.456,
    "y_coord": 0.789,
    "work_date": "2024-11-22",
    "worker_name": "John Doe",
    "work_type": "Electrical",
    "description": "Replaced faulty outlet"
  }'
```

## 🗄️ Database Schema

### Key Tables

#### `users`

- Authentication and role management
- Fields: id, username, password_hash, full_name, role, is_active, created_at, last_login

#### `floors`

- Building floor information
- Fields: id, name, image_path, width, height

#### `work_logs`

- Work log entries with coordinates
- Fields: id, floor_id, worker_id, x_coord, y_coord, work_date, worker_name, work_type, description, created_at, updated_at

#### `critical_sectors`

- Critical areas on floor plans
- Fields: id, floor_id, sector_name, type, x_coord, y_coord, radius, width, height, priority, created_by, created_at

#### `work_assignments`

- Work assignments for workers
- Fields: id, work_log_id, assigned_to, assigned_by, due_date, status, notes, created_at

#### `notifications`

- User notifications
- Fields: id, user_id, type, title, message, related_id, is_read, created_at

## 🎨 Work Type Colors

- 🔴 **Red** - Electrical
- 🔵 **Blue** - Lighting
- 🟢 **Green** - Maintenance
- 🟡 **Yellow** - Installation
- 🟣 **Purple** - Inspection/Other

## 🛠️ Development

### Project Structure Philosophy

The refactored architecture follows these principles:

1. **Separation of Concerns** - Routes, business logic, and data access are separated
2. **Service Layer** - Business logic isolated in service classes
3. **Reusable Components** - Frontend services for API communication
4. **Security First** - JWT authentication, role-based access control
5. **Scalability** - Easy to add new features and endpoints

### Adding a New Feature

1. **Backend:**

   - Create model in `backend/app/models/`
   - Create service in `backend/app/services/`
   - Create routes in `backend/app/api/new_feature/`
   - Register blueprint in `backend/app/__init__.py`

2. **Frontend:**
   - Create service in `frontend/core/api/`
   - Add UI components/pages
   - Wire up with Vue.js

### Running Tests

```bash
cd backend
python -m pytest tests/
```

### Feature Tracking

See [FEATURES.md](FEATURES.md) for implemented features (with how they work), future roadmap, and code simplification opportunities. Last updated: Feb 2025.

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check Python version (need 3.7+)
python --version

# Reinstall dependencies
pip install -r requirements.txt

# Check if port 5000 is in use
# Windows: netstat -ano | findstr :5000
# Mac/Linux: lsof -i :5000
```

### Authentication issues

```bash
# Recreate admin user
cd backend
python utils/setup_admin.py

# Check database
sqlite3 database.db "SELECT * FROM users;"
```

### Tiles not loading

```bash
# Regenerate tiles for a specific floor
cd backend
python utils/regenerate_tiles_safe.py

# Or regenerate all tiles
python utils/regenerate_all_tiles_hd.py
```

### Frontend can't connect

- Verify backend is running on `http://localhost:5000`
- Check browser console for errors (F12)
- Verify CORS is enabled in backend
- Clear browser cache and localStorage

## 📦 Dependencies

### Backend (Python)

- Flask - Web framework
- Flask-CORS - CORS support
- PyJWT - JWT token handling
- Pillow - Image processing
- pdf2image - PDF to image conversion
- pyvips - High-performance image processing

Install all: `pip install -r requirements.txt`

### Frontend (CDN)

- Vue.js 3 - Frontend framework
- Tailwind CSS - Utility-first CSS
- OpenSeadragon - Deep zoom image viewer
- Chart.js - Data visualization

## 🔮 Future Enhancements

See [FEATURES.md](FEATURES.md) for the full roadmap. Planned items:

- [ ] Real-time updates with WebSockets
- [ ] Progressive Web App (PWA) support
- [ ] Offline mode with service workers
- [ ] Export to PDF/Excel
- [ ] Email notifications
- [ ] Mobile native apps
- [ ] PostgreSQL support for production
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Multi-language support

## 📄 License

MIT License - Feel free to use and modify for your needs.

## 🤝 Contributing

This project follows a modular architecture. When contributing:

1. Follow the existing code structure
2. Add services for business logic
3. Use decorators for authentication
4. Write tests for new features
5. Update this README if needed

## 📞 Support

For issues or questions:

1. Check the Troubleshooting section
2. Review the API documentation
3. Create an issue in the project repository

---

**Built with ❤️ using Flask, Vue.js, and OpenSeadragon**
