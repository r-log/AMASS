"""
Authentication API tests for Electrician Log MVP.
"""

import jwt as pyjwt
import pytest
from datetime import datetime, timedelta


class TestLogin:
    def test_login_success(self, client, admin_user):
        response = client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'admin_pass'})
        assert response.status_code == 200
        data = response.get_json()
        assert 'token' in data
        assert data['user']['username'] == 'test_admin'
        assert data['user']['role'] == 'admin'

    def test_login_wrong_password(self, client, admin_user):
        response = client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'wrong'})
        assert response.status_code == 401

    def test_login_missing_credentials(self, client):
        response = client.post('/api/auth/login', json={})
        assert response.status_code == 400

    def test_login_nonexistent_user(self, client):
        response = client.post('/api/auth/login', json={'username': 'nobody', 'password': 'x'})
        assert response.status_code == 401


class TestVerifyToken:
    def test_verify_token(self, client, auth_headers):
        response = client.get('/api/auth/verify', headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()['success'] is True

    def test_verify_token_no_auth(self, client):
        response = client.get('/api/auth/verify')
        assert response.status_code == 401

    def test_verify_expired_token(self, client, app):
        payload = {
            'user_id': 1, 'username': 'test_admin', 'full_name': 'Test', 'role': 'admin',
            'exp': datetime.utcnow() - timedelta(hours=1),
            'iat': datetime.utcnow() - timedelta(hours=2),
        }
        expired = pyjwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
        response = client.get('/api/auth/verify', headers={'Authorization': f'Bearer {expired}'})
        assert response.status_code == 401


class TestLogout:
    def test_logout_blacklists_token(self, client, admin_user):
        login = client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'admin_pass'})
        token = login.get_json()['token']
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        assert client.get('/api/auth/verify', headers=headers).status_code == 200
        assert client.post('/api/auth/logout', headers=headers).status_code == 200
        assert client.get('/api/auth/verify', headers=headers).status_code == 401


class TestRefreshToken:
    def test_refresh_token(self, client, admin_user):
        # Use a fresh login token to avoid interference from logout/blacklist tests
        login = client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'admin_pass'})
        token = login.get_json()['token']
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = client.post('/api/auth/refresh', headers=headers)
        assert response.status_code == 200
        assert 'token' in response.get_json()


class TestRegister:
    def test_register_admin_only(self, client, worker_headers):
        response = client.post('/api/auth/register', headers=worker_headers,
                               json={'username': 'x', 'password': 'x12345', 'full_name': 'X', 'role': 'worker'})
        assert response.status_code == 403

    def test_register_success(self, client, auth_headers):
        response = client.post('/api/auth/register', headers=auth_headers,
                               json={'username': 'fresh', 'password': 'securepass', 'full_name': 'Fresh', 'role': 'worker'})
        assert response.status_code == 201
        assert response.get_json()['user']['username'] == 'fresh'

    def test_register_duplicate_username(self, client, auth_headers):
        payload = {'username': 'dup', 'password': 'pass123456', 'full_name': 'Dup', 'role': 'worker'}
        assert client.post('/api/auth/register', headers=auth_headers, json=payload).status_code == 201
        assert client.post('/api/auth/register', headers=auth_headers, json=payload).status_code == 400


class TestRateLimit:
    def test_rate_limit_login(self, client, admin_user, reset_rate_limiter):
        payload = {'username': 'test_admin', 'password': 'wrong'}
        for i in range(10):
            resp = client.post('/api/auth/login', json=payload)
            assert resp.status_code != 429, f"Request {i+1} rate-limited too early"
        assert client.post('/api/auth/login', json=payload).status_code == 429
