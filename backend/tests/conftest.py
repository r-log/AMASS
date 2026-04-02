"""
Pytest fixtures for Electrician Log MVP tests.
"""

import io
import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.database.migrations import initialize_database
from app.models.user import User
from app.models.project import Project
from app.models.floor import Floor
from app.models.work_log import WorkLog
from app.models.critical_sector import CriticalSector
from app.models.notification import Notification
from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# App & client
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Create application for testing with isolated temp database."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    try:
        test_app = create_app('testing')
        test_app.config['DATABASE_PATH'] = path
        test_app.config['DEBUG'] = False
        test_app.config['TESTING'] = True
        # Use a fixed secret so tokens are valid across the test session
        test_app.config['SECRET_KEY'] = 'test-secret-key-for-tests'

        with test_app.app_context():
            initialize_database()

        # Clear singletons so tests don't leak state
        from app.services.auth_service import _token_blacklist
        _token_blacklist._blacklisted.clear()

        yield test_app
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Users & tokens
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user(app):
    """Create and return an admin user."""
    with app.app_context():
        user = User.find_by_username('test_admin')
        if not user:
            user = User(
                username='test_admin',
                password_hash=generate_password_hash('admin_pass'),
                full_name='Test Admin',
                role='admin',
                is_active=True,
            )
            user.save()
        return user


@pytest.fixture
def admin_token(app, admin_user):
    """Get JWT token for admin user."""
    with app.app_context():
        return AuthService.generate_token(admin_user)


@pytest.fixture
def auth_headers(admin_token):
    """Authorization headers for admin API requests."""
    return {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}


@pytest.fixture
def supervisor_user(app):
    """Create and return a supervisor user."""
    with app.app_context():
        user = User.find_by_username('test_supervisor')
        if not user:
            user = User(
                username='test_supervisor',
                password_hash=generate_password_hash('super_pass'),
                full_name='Test Supervisor',
                role='supervisor',
                is_active=True,
            )
            user.save()
        return user


@pytest.fixture
def supervisor_token(app, supervisor_user):
    """Get JWT token for supervisor user."""
    with app.app_context():
        return AuthService.generate_token(supervisor_user)


@pytest.fixture
def supervisor_headers(supervisor_token):
    """Authorization headers for supervisor API requests."""
    return {'Authorization': f'Bearer {supervisor_token}', 'Content-Type': 'application/json'}


@pytest.fixture
def worker_user(app):
    """Create and return a worker user."""
    with app.app_context():
        user = User.find_by_username('test_worker')
        if not user:
            user = User(
                username='test_worker',
                password_hash=generate_password_hash('worker_pass'),
                full_name='Test Worker',
                role='worker',
                is_active=True,
            )
            user.save()
        return user


@pytest.fixture
def worker_token(app, worker_user):
    """Get JWT token for worker user."""
    with app.app_context():
        return AuthService.generate_token(worker_user)


@pytest.fixture
def worker_headers(worker_token):
    """Authorization headers for worker API requests."""
    return {'Authorization': f'Bearer {worker_token}', 'Content-Type': 'application/json'}


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------

@pytest.fixture
def project(app, supervisor_user):
    """Create a test project."""
    with app.app_context():
        p = Project(name='Test Project', description='For testing', is_active=True, created_by=supervisor_user.id)
        p.save()
        return p


@pytest.fixture
def floor(app, project):
    """Create a test floor in the test project."""
    with app.app_context():
        f = Floor(project_id=project.id, name='Ground Floor', image_path='placeholder.pdf',
                  width=1920, height=1080, sort_order=0)
        f.save()
        return f


@pytest.fixture
def work_log(app, floor, worker_user):
    """Create a test work log on the test floor by the worker."""
    with app.app_context():
        wl = WorkLog(
            floor_id=floor.id,
            worker_id=worker_user.id,
            x_coord=0.5,
            y_coord=0.5,
            work_date='2026-04-01',
            worker_name=worker_user.full_name,
            work_type='cable_pull',
            description='Test work log',
            status='completed',
            priority='medium',
        )
        wl.save()
        return wl


@pytest.fixture
def critical_sector(app, floor):
    """Create a test critical sector on the test floor."""
    with app.app_context():
        cs = CriticalSector(
            floor_id=floor.id,
            sector_name='High Voltage Zone',
            x_coord=0.5,
            y_coord=0.5,
            radius=0.2,
            priority='high',
            is_active=True,
        )
        cs.save()
        return cs


# ---------------------------------------------------------------------------
# File upload helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_pdf():
    """Create a minimal valid PDF in memory for upload tests."""
    # Minimal PDF (valid per spec, ~70 bytes)
    pdf_bytes = (
        b'%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj '
        b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj '
        b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n'
        b'xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n'
        b'0000000058 00000 n \n0000000115 00000 n \n'
        b'trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF'
    )
    return io.BytesIO(pdf_bytes)


@pytest.fixture
def reset_rate_limiter():
    """Reset the global rate limiter between tests."""
    from app.utils.decorators import _rate_limit_store
    _rate_limit_store._requests.clear()
    yield
    _rate_limit_store._requests.clear()
