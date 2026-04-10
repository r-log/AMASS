"""
Extended authentication tests — change-password, reset-password, users list, profile.
"""

import pytest


class TestChangePassword:
    def test_success(self, client, admin_user):
        login = client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'admin_pass'})
        token = login.get_json()['token']
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        resp = client.post('/api/auth/change-password', headers=headers,
                           json={'old_password': 'admin_pass', 'new_password': 'new_secure_pass'})
        assert resp.status_code == 200

        # Old password no longer works
        assert client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'admin_pass'}).status_code == 401
        # New one does
        assert client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'new_secure_pass'}).status_code == 200

    def test_wrong_old_password(self, client, auth_headers):
        resp = client.post('/api/auth/change-password', headers=auth_headers,
                           json={'old_password': 'totally_wrong', 'new_password': 'x'})
        assert resp.status_code == 400

    def test_missing_fields(self, client, auth_headers):
        resp = client.post('/api/auth/change-password', headers=auth_headers, json={})
        assert resp.status_code == 400

    def test_requires_auth(self, client):
        resp = client.post('/api/auth/change-password', json={'old_password': 'a', 'new_password': 'b'})
        assert resp.status_code == 401


class TestResetPassword:
    def test_admin_resets_worker(self, client, auth_headers, worker_user):
        resp = client.post('/api/auth/reset-password', headers=auth_headers,
                           json={'user_id': worker_user.id, 'new_password': 'reset123'})
        assert resp.status_code == 200
        # Worker can log in with new password
        assert client.post('/api/auth/login', json={'username': 'test_worker', 'password': 'reset123'}).status_code == 200

    def test_worker_cannot_reset(self, client, worker_headers, admin_user):
        resp = client.post('/api/auth/reset-password', headers=worker_headers,
                           json={'user_id': admin_user.id, 'new_password': 'hacked'})
        assert resp.status_code == 403

    def test_missing_fields(self, client, auth_headers):
        resp = client.post('/api/auth/reset-password', headers=auth_headers, json={'user_id': 1})
        assert resp.status_code == 400


class TestListUsers:
    def test_admin_lists_all(self, client, auth_headers, admin_user, worker_user, supervisor_user):
        resp = client.get('/api/auth/users', headers=auth_headers)
        assert resp.status_code == 200
        usernames = {u['username'] for u in resp.get_json()}
        assert 'test_admin' in usernames
        assert 'test_worker' in usernames

    def test_admin_filter_by_role(self, client, auth_headers, worker_user):
        resp = client.get('/api/auth/users?role=worker', headers=auth_headers)
        assert resp.status_code == 200
        assert all(u['role'] == 'worker' for u in resp.get_json())

    def test_supervisor_sees_workers_only(self, client, supervisor_headers, worker_user, admin_user):
        resp = client.get('/api/auth/users?role=worker', headers=supervisor_headers)
        assert resp.status_code == 200
        assert all(u['role'] == 'worker' for u in resp.get_json())

    def test_supervisor_cannot_list_admins(self, client, supervisor_headers, admin_user):
        resp = client.get('/api/auth/users?role=admin', headers=supervisor_headers)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_worker_forbidden(self, client, worker_headers):
        resp = client.get('/api/auth/users', headers=worker_headers)
        assert resp.status_code == 403


class TestProfile:
    def test_get_own_profile(self, client, auth_headers, admin_user):
        resp = client.get('/api/auth/profile', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['user']['username'] == 'test_admin'
        assert 'permissions' in data

    def test_update_own_profile(self, client, worker_headers):
        resp = client.put('/api/auth/profile', headers=worker_headers,
                          json={'full_name': 'Updated Name'})
        assert resp.status_code == 200

    def test_worker_cannot_update_others(self, client, worker_headers, admin_user):
        resp = client.put('/api/auth/profile', headers=worker_headers,
                          json={'user_id': admin_user.id, 'full_name': 'Hacked'})
        assert resp.status_code == 403

    def test_admin_can_update_others(self, client, auth_headers, worker_user):
        resp = client.put('/api/auth/profile', headers=auth_headers,
                          json={'user_id': worker_user.id, 'full_name': 'Admin Changed'})
        assert resp.status_code == 200

    def test_requires_auth(self, client):
        assert client.get('/api/auth/profile').status_code == 401
