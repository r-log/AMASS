"""
Tests for global error handlers and edge cases.
"""

import pytest


class TestErrorHandlers:
    def test_404_on_missing_api_route(self, client, auth_headers):
        resp = client.get('/api/nonexistent', headers=auth_headers)
        assert resp.status_code == 404

    def test_401_without_token(self, client):
        resp = client.get('/api/floors')
        assert resp.status_code == 401

    def test_malformed_bearer(self, client):
        resp = client.get('/api/floors', headers={'Authorization': 'Bearer'})
        assert resp.status_code == 401

    def test_empty_auth_header(self, client):
        resp = client.get('/api/floors', headers={'Authorization': ''})
        assert resp.status_code == 401


class TestInputValidation:
    def test_invalid_json_body(self, client, auth_headers):
        resp = client.post('/api/auth/login', data='not json', content_type='text/plain')
        assert resp.status_code == 400

    def test_empty_json_login(self, client):
        resp = client.post('/api/auth/login', json={})
        assert resp.status_code == 400

    def test_non_integer_query_param(self, client, supervisor_headers):
        # floor_id should be int — make sure it doesn't crash
        resp = client.get('/api/work-logs?floor_id=abc', headers=supervisor_headers)
        # Should either ignore the bad param or return 400, not 500
        assert resp.status_code in (200, 400)
