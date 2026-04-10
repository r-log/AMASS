"""
Dashboard API tests.
"""

import pytest


class TestSupervisorDashboard:
    def test_supervisor_access(self, client, supervisor_headers):
        resp = client.get('/api/dashboard/supervisor', headers=supervisor_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)

    def test_admin_access(self, client, auth_headers):
        resp = client.get('/api/dashboard/supervisor', headers=auth_headers)
        assert resp.status_code == 200

    def test_worker_denied(self, client, worker_headers):
        resp = client.get('/api/dashboard/supervisor', headers=worker_headers)
        assert resp.status_code == 403

    def test_requires_auth(self, client):
        assert client.get('/api/dashboard/supervisor').status_code == 401
