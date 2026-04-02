"""
Tests for project delete and backup flow.
"""

import io
import zipfile

import pytest

from app.models.project import Project
from app.models.floor import Floor


def test_delete_project_creates_backup(client, supervisor_headers, app):
    """Delete project creates backup and removes project from DB."""
    with app.app_context():
        # Create a project first (supervisor action)
        create_resp = client.post(
            '/api/projects',
            headers=supervisor_headers,
            json={'name': 'Test Project Delete', 'description': 'For delete test'}
        )
        if create_resp.status_code != 201:
            pytest.skip(f"Cannot create project: {create_resp.get_json()}")
        project_id = create_resp.get_json()['project']['id']

        # Delete project (admin or supervisor)
        delete_resp = client.delete(
            f'/api/projects/{project_id}',
            headers=supervisor_headers
        )
        assert delete_resp.status_code == 200
        data = delete_resp.get_json()
        assert 'message' in data
        assert 'backup_path' in data
        assert data['backup_path'].endswith('.zip')

        # Project should be gone from DB
        project = Project.find_by_id(project_id)
        assert project is None


def test_delete_nonexistent_project_returns_error(client, auth_headers):
    """Delete nonexistent project returns 400."""
    response = client.delete(
        '/api/projects/99999',
        headers=auth_headers
    )
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_restore_requires_zip_file(client, auth_headers):
    """Restore endpoint rejects non-ZIP file."""
    data = {'file': (io.BytesIO(b'not a zip'), 'test.txt')}
    response = client.post(
        '/api/projects/restore',
        headers={'Authorization': auth_headers['Authorization']},
        data=data,
        content_type='multipart/form-data'
    )
    # Might get 400 for wrong file type or 400 for no file
    assert response.status_code in (400, 422)


def test_project_backup_service_create_backup(app):
    """ProjectBackupService creates valid ZIP backup."""
    from app.services.project_backup_service import ProjectBackupService
    from app.models.project import Project
    import tempfile
    import os

    with app.app_context():
        # Create a minimal project for backup
        project = Project(name='Backup Test', description='Test')
        project.save()

        backups_dir = tempfile.mkdtemp()
        floor_plans_dir = tempfile.mkdtemp()
        try:
            success, msg, backup_path = ProjectBackupService.create_backup(
                project.id, floor_plans_dir, backups_dir
            )
            assert success is True
            assert backup_path is not None
            full_path = os.path.join(backups_dir, backup_path)
            assert os.path.exists(full_path)

            # ZIP should be valid and contain expected structure
            with zipfile.ZipFile(full_path, 'r') as zf:
                names = zf.namelist()
                assert 'project.json' in names or any('project' in n for n in names)
        finally:
            import shutil
            shutil.rmtree(backups_dir, ignore_errors=True)
            shutil.rmtree(floor_plans_dir, ignore_errors=True)
            project.delete()
