"""
Extended assignment tests — worker access control, statistics, overdue, by-worker, bulk-create.
"""

import pytest
from werkzeug.security import generate_password_hash
from app.models.user import User
from app.services.auth_service import AuthService


class TestAssignmentAccessControl:
    """Workers can only see their own assignments; supervisors see all."""

    def test_worker_sees_own(self, client, supervisor_headers, worker_headers, worker_user, floor):
        # Create assignment for worker
        create = client.post('/api/assignments/', headers=supervisor_headers,
                             json={'title': 'Worker Task', 'assigned_to': worker_user.id, 'floor_id': floor.id})
        aid = create.get_json()['assignment']['id']

        resp = client.get(f'/api/assignments/{aid}', headers=worker_headers)
        assert resp.status_code == 200

    def test_worker_denied_others(self, app, client, supervisor_headers, worker_user, floor):
        # Create another worker
        with app.app_context():
            other = User(username='other_w', password_hash=generate_password_hash('p'),
                         full_name='Other', role='worker', is_active=True)
            other.save()
            other_token = AuthService.generate_token(other)
            other_headers = {'Authorization': f'Bearer {other_token}', 'Content-Type': 'application/json'}

        create = client.post('/api/assignments/', headers=supervisor_headers,
                             json={'title': 'Owned Task', 'assigned_to': worker_user.id, 'floor_id': floor.id})
        aid = create.get_json()['assignment']['id']

        # Other worker cannot view
        resp = client.get(f'/api/assignments/{aid}', headers=other_headers)
        assert resp.status_code == 403

    def test_get_nonexistent(self, client, supervisor_headers):
        resp = client.get('/api/assignments/99999', headers=supervisor_headers)
        assert resp.status_code == 404


class TestAssignmentStatistics:
    def test_supervisor_gets_stats(self, client, supervisor_headers, worker_user, floor):
        client.post('/api/assignments/', headers=supervisor_headers,
                    json={'title': 'Stats', 'assigned_to': worker_user.id, 'floor_id': floor.id})
        resp = client.get('/api/assignments/statistics', headers=supervisor_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)

    def test_worker_denied(self, client, worker_headers):
        resp = client.get('/api/assignments/statistics', headers=worker_headers)
        assert resp.status_code == 403


class TestMyAssignmentStats:
    def test_worker_gets_own_stats(self, client, supervisor_headers, worker_headers, worker_user, floor):
        client.post('/api/assignments/', headers=supervisor_headers,
                    json={'title': 'MyStats', 'assigned_to': worker_user.id, 'floor_id': floor.id})
        resp = client.get('/api/assignments/my-stats', headers=worker_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)


class TestOverdueAssignments:
    def test_supervisor_gets_overdue(self, client, supervisor_headers, worker_user, floor):
        # Create assignment with past due date
        client.post('/api/assignments/', headers=supervisor_headers,
                    json={'title': 'Late', 'assigned_to': worker_user.id,
                          'floor_id': floor.id, 'due_date': '2020-01-01'})
        resp = client.get('/api/assignments/overdue', headers=supervisor_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_worker_denied(self, client, worker_headers):
        resp = client.get('/api/assignments/overdue', headers=worker_headers)
        assert resp.status_code == 403


class TestAssignmentsByWorker:
    def test_supervisor_views(self, client, supervisor_headers, worker_user, floor):
        client.post('/api/assignments/', headers=supervisor_headers,
                    json={'title': 'ByWorker', 'assigned_to': worker_user.id, 'floor_id': floor.id})
        resp = client.get(f'/api/assignments/by-worker/{worker_user.id}', headers=supervisor_headers)
        assert resp.status_code == 200
        assert len(resp.get_json()) >= 1

    def test_worker_denied(self, client, worker_headers, worker_user):
        resp = client.get(f'/api/assignments/by-worker/{worker_user.id}', headers=worker_headers)
        assert resp.status_code == 403


class TestBulkCreateAssignments:
    def test_success(self, client, supervisor_headers, worker_user, floor):
        resp = client.post('/api/assignments/bulk-create', headers=supervisor_headers,
                           json={'assignments': [
                               {'title': 'Bulk 1', 'assigned_to': worker_user.id, 'floor_id': floor.id},
                               {'title': 'Bulk 2', 'assigned_to': worker_user.id, 'floor_id': floor.id},
                           ]})
        assert resp.status_code == 201
        data = resp.get_json()
        assert '2/' in data['message']  # "Created 2/2 assignments"

    def test_missing_body(self, client, supervisor_headers):
        resp = client.post('/api/assignments/bulk-create', headers=supervisor_headers, json={})
        assert resp.status_code == 400

    def test_worker_denied(self, client, worker_headers, worker_user, floor):
        resp = client.post('/api/assignments/bulk-create', headers=worker_headers,
                           json={'assignments': [{'title': 'X', 'assigned_to': worker_user.id, 'floor_id': floor.id}]})
        assert resp.status_code == 403
