"""
Extended floor tests — get single, update, statistics, summary, activity.
"""

import pytest


class TestGetSingleFloor:
    def test_found(self, client, floor, supervisor_headers):
        resp = client.get(f'/api/floors/{floor.id}', headers=supervisor_headers)
        assert resp.status_code == 200
        assert resp.get_json()['id'] == floor.id

    def test_not_found(self, client, supervisor_headers):
        resp = client.get('/api/floors/99999', headers=supervisor_headers)
        assert resp.status_code == 404

    def test_requires_auth(self, client, floor):
        assert client.get(f'/api/floors/{floor.id}').status_code == 401


class TestUpdateFloor:
    def test_supervisor_updates(self, client, floor, supervisor_headers):
        resp = client.put(f'/api/floors/{floor.id}', headers=supervisor_headers,
                          json={'name': 'Renamed Floor'})
        assert resp.status_code == 200
        assert resp.get_json()['floor']['name'] == 'Renamed Floor'

    def test_worker_denied(self, client, floor, worker_headers):
        resp = client.put(f'/api/floors/{floor.id}', headers=worker_headers,
                          json={'name': 'Nope'})
        assert resp.status_code == 403


class TestFloorStatistics:
    def test_all_floors(self, client, floor, supervisor_headers):
        resp = client.get('/api/floors/statistics', headers=supervisor_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)

    def test_specific_floor(self, client, floor, supervisor_headers):
        resp = client.get(f'/api/floors/statistics?floor_id={floor.id}', headers=supervisor_headers)
        assert resp.status_code == 200


class TestFloorWorkSummary:
    def test_summary(self, client, floor, work_log, supervisor_headers):
        resp = client.get(f'/api/floors/{floor.id}/summary', headers=supervisor_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)

    def test_with_date_range(self, client, floor, work_log, supervisor_headers):
        resp = client.get(
            f'/api/floors/{floor.id}/summary?start_date=2026-01-01&end_date=2026-12-31',
            headers=supervisor_headers)
        assert resp.status_code == 200


class TestFloorsWithActivity:
    def test_returns_list(self, client, floor, work_log, supervisor_headers):
        resp = client.get('/api/floors/activity?days=365', headers=supervisor_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)
