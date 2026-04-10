"""
Extended critical sector tests — work logs in sector, statistics, priority filter, export, bulk update.
"""

import pytest


class TestSectorWorkLogs:
    def test_get_logs(self, client, critical_sector, work_log, supervisor_headers):
        resp = client.get(f'/api/critical-sectors/{critical_sector.id}/work-logs',
                          headers=supervisor_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'sector' in data
        assert 'work_logs' in data

    def test_not_found(self, client, supervisor_headers):
        resp = client.get('/api/critical-sectors/99999/work-logs', headers=supervisor_headers)
        assert resp.status_code == 404


class TestCriticalSectorStatistics:
    def test_supervisor(self, client, critical_sector, supervisor_headers):
        resp = client.get('/api/critical-sectors/statistics', headers=supervisor_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)

    def test_worker_denied(self, client, worker_headers):
        resp = client.get('/api/critical-sectors/statistics', headers=worker_headers)
        assert resp.status_code == 403


class TestSectorsByPriority:
    def test_high_priority(self, client, critical_sector, supervisor_headers):
        resp = client.get('/api/critical-sectors/priority/high', headers=supervisor_headers)
        assert resp.status_code == 200
        sectors = resp.get_json()
        assert all(s['priority'] == 'high' for s in sectors)

    def test_empty_for_unknown_priority(self, client, supervisor_headers):
        resp = client.get('/api/critical-sectors/priority/nonexistent', headers=supervisor_headers)
        assert resp.status_code == 200
        assert resp.get_json() == []


class TestRecentWorkInSectors:
    def test_supervisor(self, client, critical_sector, work_log, supervisor_headers):
        resp = client.get('/api/critical-sectors/recent-work?days=365', headers=supervisor_headers)
        assert resp.status_code == 200

    def test_worker_denied(self, client, worker_headers):
        resp = client.get('/api/critical-sectors/recent-work', headers=worker_headers)
        assert resp.status_code == 403


class TestBulkUpdateSectors:
    def test_success(self, client, critical_sector, supervisor_headers):
        resp = client.put('/api/critical-sectors/bulk-update', headers=supervisor_headers,
                          json={'sector_ids': [critical_sector.id], 'updates': {'priority': 'medium'}})
        assert resp.status_code == 200

    def test_missing_fields(self, client, supervisor_headers):
        resp = client.put('/api/critical-sectors/bulk-update', headers=supervisor_headers,
                          json={'sector_ids': [], 'updates': {}})
        assert resp.status_code == 400

    def test_worker_denied(self, client, critical_sector, worker_headers):
        resp = client.put('/api/critical-sectors/bulk-update', headers=worker_headers,
                          json={'sector_ids': [critical_sector.id], 'updates': {'priority': 'low'}})
        assert resp.status_code == 403


class TestExportSectors:
    def test_json_export(self, client, critical_sector, supervisor_headers):
        resp = client.get('/api/critical-sectors/export?format=json', headers=supervisor_headers)
        assert resp.status_code == 200

    def test_csv_export(self, client, critical_sector, supervisor_headers):
        resp = client.get('/api/critical-sectors/export?format=csv', headers=supervisor_headers)
        assert resp.status_code == 200
        assert 'text/csv' in resp.content_type

    def test_worker_denied(self, client, worker_headers):
        resp = client.get('/api/critical-sectors/export', headers=worker_headers)
        assert resp.status_code == 403
