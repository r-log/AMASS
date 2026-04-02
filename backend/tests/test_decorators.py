"""
Decorator tests — token_required, admin_required, supervisor_required, validate_json_request.
"""


class TestTokenRequired:
    def test_missing_token(self, client):
        assert client.get('/api/floors').status_code == 401

    def test_invalid_token(self, client):
        assert client.get('/api/floors', headers={'Authorization': 'Bearer garbage'}).status_code == 401


class TestAdminRequired:
    def test_worker_denied(self, client, worker_headers):
        resp = client.post('/api/auth/register', headers=worker_headers,
                           json={'username': 'x', 'password': 'x12345', 'full_name': 'X', 'role': 'worker'})
        assert resp.status_code == 403

    def test_admin_allowed(self, client, auth_headers):
        resp = client.post('/api/auth/register', headers=auth_headers,
                           json={'username': 'ok_user', 'password': 'x12345', 'full_name': 'OK', 'role': 'worker'})
        assert resp.status_code == 201


class TestSupervisorRequired:
    def test_worker_denied(self, client, worker_headers, project):
        resp = client.post('/api/floors', headers=worker_headers,
                           json={'name': 'X', 'project_id': project.id})
        assert resp.status_code == 403

    def test_supervisor_allowed(self, client, supervisor_headers, project):
        resp = client.post('/api/floors', headers=supervisor_headers,
                           json={'name': 'New Floor', 'project_id': project.id})
        assert resp.status_code == 201


class TestSupervisorOrAdminRequired:
    def test_worker_denied(self, client, worker_headers):
        assert client.delete('/api/tiles/clear/999', headers=worker_headers).status_code == 403


class TestValidateJsonRequest:
    def test_missing_content_type(self, client):
        resp = client.post('/api/auth/login', data='not json', content_type='text/plain')
        assert resp.status_code == 400
