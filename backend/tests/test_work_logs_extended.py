"""
Extended work log tests — single get, enhanced create, dashboard, near-point, export, bulk update.
"""

import pytest


class TestGetSingleWorkLog:
    def test_owner_can_view(self, client, work_log, worker_headers):
        resp = client.get(f'/api/work-logs/{work_log.id}', headers=worker_headers)
        assert resp.status_code == 200

    def test_supervisor_can_view(self, client, work_log, supervisor_headers):
        resp = client.get(f'/api/work-logs/{work_log.id}', headers=supervisor_headers)
        assert resp.status_code == 200

    def test_not_found(self, client, supervisor_headers):
        resp = client.get('/api/work-logs/99999', headers=supervisor_headers)
        assert resp.status_code == 404

    def test_requires_auth(self, client, work_log):
        assert client.get(f'/api/work-logs/{work_log.id}').status_code == 401


class TestEnhancedWorkLog:
    def test_create(self, client, floor, worker_headers):
        payload = {
            'floor_id': floor.id, 'x_coord': 0.4, 'y_coord': 0.6,
            'work_date': '2026-04-05', 'work_type': 'cable_pull',
            'description': 'Enhanced log with cable details',
            'cable_type': 'NYM 5x2.5', 'cable_length': 25,
        }
        resp = client.post('/api/work-logs/enhanced', json=payload, headers=worker_headers)
        assert resp.status_code == 201
        assert 'work_log' in resp.get_json()

    def test_validation_error(self, client, worker_headers):
        resp = client.post('/api/work-logs/enhanced', json={'x_coord': 0.5}, headers=worker_headers)
        assert resp.status_code == 400


class TestDashboardStats:
    def test_worker_gets_stats(self, client, work_log, worker_headers):
        resp = client.get('/api/work-logs/dashboard', headers=worker_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)

    def test_requires_auth(self, client):
        assert client.get('/api/work-logs/dashboard').status_code == 401


class TestNearPoint:
    def test_finds_nearby_log(self, client, work_log, supervisor_headers, floor):
        resp = client.get(
            f'/api/work-logs/near-point?floor_id={floor.id}&x=0.5&y=0.5&radius=0.1',
            headers=supervisor_headers)
        assert resp.status_code == 200
        logs = resp.get_json()
        assert isinstance(logs, list)
        assert any(log['id'] == work_log.id for log in logs)

    def test_empty_far_away(self, client, work_log, supervisor_headers, floor):
        resp = client.get(
            f'/api/work-logs/near-point?floor_id={floor.id}&x=0.01&y=0.01&radius=0.01',
            headers=supervisor_headers)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_missing_params(self, client, supervisor_headers):
        resp = client.get('/api/work-logs/near-point?floor_id=1', headers=supervisor_headers)
        assert resp.status_code == 400


class TestExportWorkLogs:
    def test_json_export(self, client, work_log, supervisor_headers):
        resp = client.get('/api/work-logs/export?format=json', headers=supervisor_headers)
        assert resp.status_code == 200

    def test_csv_export(self, client, work_log, supervisor_headers):
        resp = client.get('/api/work-logs/export?format=csv', headers=supervisor_headers)
        assert resp.status_code == 200
        assert 'text/csv' in resp.content_type

    def test_worker_denied(self, client, worker_headers):
        resp = client.get('/api/work-logs/export', headers=worker_headers)
        assert resp.status_code == 403


class TestBulkUpdateWorkLogs:
    def test_supervisor_bulk_update(self, client, work_log, supervisor_headers):
        resp = client.put('/api/work-logs/bulk-update', headers=supervisor_headers,
                          json={'log_ids': [work_log.id], 'updates': {'status': 'completed'}})
        assert resp.status_code == 200

    def test_missing_fields(self, client, supervisor_headers):
        resp = client.put('/api/work-logs/bulk-update', headers=supervisor_headers,
                          json={'log_ids': [], 'updates': {}})
        assert resp.status_code == 400

    def test_worker_denied(self, client, work_log, worker_headers):
        resp = client.put('/api/work-logs/bulk-update', headers=worker_headers,
                          json={'log_ids': [work_log.id], 'updates': {'status': 'completed'}})
        assert resp.status_code == 403
