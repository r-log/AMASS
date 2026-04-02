"""
Work Logs API tests.
"""

import pytest
from werkzeug.security import generate_password_hash
from app.models.user import User
from app.services.auth_service import AuthService


class TestCreateWorkLog:
    def test_success(self, client, floor, worker_headers, worker_user):
        payload = {
            'floor_id': floor.id, 'x_coord': 0.3, 'y_coord': 0.7,
            'work_date': '2026-04-02', 'work_type': 'cable_pull',
            'description': 'Pulled 20m NYM 5x2.5',
        }
        resp = client.post('/api/work-logs', json=payload, headers=worker_headers)
        assert resp.status_code == 201
        wl = resp.get_json()['work_log']
        assert wl['floor_id'] == floor.id
        assert wl['worker_id'] == worker_user.id
        assert wl['x_coord'] == pytest.approx(0.3)

    def test_missing_fields(self, client, worker_headers):
        resp = client.post('/api/work-logs', json={'x_coord': 0.5, 'y_coord': 0.5,
                           'work_date': '2026-04-02', 'work_type': 'cable_pull'}, headers=worker_headers)
        assert resp.status_code == 400

    def test_invalid_floor(self, client, worker_headers):
        resp = client.post('/api/work-logs', json={'floor_id': 99999, 'x_coord': 0.5,
                           'y_coord': 0.5, 'work_date': '2026-04-02', 'work_type': 'cable_pull'},
                           headers=worker_headers)
        assert resp.status_code == 400


class TestGetWorkLogs:
    def test_get_all(self, client, work_log, supervisor_headers):
        resp = client.get('/api/work-logs', headers=supervisor_headers)
        assert resp.status_code == 200
        assert len(resp.get_json()) >= 1

    def test_filter_by_floor(self, client, work_log, supervisor_headers, floor):
        resp = client.get(f'/api/work-logs?floor_id={floor.id}', headers=supervisor_headers)
        assert resp.status_code == 200
        assert all(wl['floor_id'] == floor.id for wl in resp.get_json())

    def test_worker_sees_own(self, client, work_log, worker_headers, worker_user):
        resp = client.get('/api/work-logs', headers=worker_headers)
        assert resp.status_code == 200
        assert all(wl['worker_id'] == worker_user.id for wl in resp.get_json())


class TestUpdateWorkLog:
    def test_owner_can_edit(self, client, work_log, worker_headers):
        resp = client.put(f'/api/work-logs/{work_log.id}', json={'description': 'Updated'},
                          headers=worker_headers)
        assert resp.status_code == 200
        assert resp.get_json()['work_log']['description'] == 'Updated'

    def test_non_owner_denied(self, app, client, work_log):
        with app.app_context():
            u2 = User(username='w2', password_hash=generate_password_hash('p'), full_name='W2',
                       role='worker', is_active=True)
            u2.save()
            t2 = AuthService.generate_token(u2)
        resp = client.put(f'/api/work-logs/{work_log.id}', json={'description': 'Hack'},
                          headers={'Authorization': f'Bearer {t2}', 'Content-Type': 'application/json'})
        assert resp.status_code in (400, 403)

    def test_supervisor_can_edit(self, client, work_log, supervisor_headers):
        resp = client.put(f'/api/work-logs/{work_log.id}', json={'description': 'Sup edit'},
                          headers=supervisor_headers)
        assert resp.status_code == 200


class TestDeleteWorkLog:
    def test_owner_can_delete(self, client, work_log, worker_headers):
        assert client.delete(f'/api/work-logs/{work_log.id}', headers=worker_headers).status_code == 200

    def test_non_owner_denied(self, app, client, work_log):
        with app.app_context():
            u2 = User(username='w3', password_hash=generate_password_hash('p'), full_name='W3',
                       role='worker', is_active=True)
            u2.save()
            t2 = AuthService.generate_token(u2)
        resp = client.delete(f'/api/work-logs/{work_log.id}',
                             headers={'Authorization': f'Bearer {t2}', 'Content-Type': 'application/json'})
        assert resp.status_code in (400, 403)
