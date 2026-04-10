"""
Extended notification tests — get single, delete, clear-all, by-type, recent, statistics, ownership.
"""

from app.models.notification import Notification


class TestGetSingleNotification:
    def test_own_notification(self, client, worker_headers, app, worker_user):
        with app.app_context():
            n = Notification.create_for_user(worker_user.id, 'system', 'Test', 'Body')
            nid = n.id
        resp = client.get(f'/api/notifications/{nid}', headers=worker_headers)
        assert resp.status_code == 200
        assert resp.get_json()['id'] == nid

    def test_other_users_notification_denied(self, client, worker_headers, app, admin_user):
        with app.app_context():
            n = Notification.create_for_user(admin_user.id, 'system', 'Secret', 'Body')
            nid = n.id
        resp = client.get(f'/api/notifications/{nid}', headers=worker_headers)
        assert resp.status_code == 403

    def test_not_found(self, client, worker_headers):
        resp = client.get('/api/notifications/99999', headers=worker_headers)
        assert resp.status_code == 404


class TestDeleteNotification:
    def test_delete_own(self, client, worker_headers, app, worker_user):
        with app.app_context():
            n = Notification.create_for_user(worker_user.id, 'system', 'Del', 'Body')
            nid = n.id
        resp = client.delete(f'/api/notifications/{nid}', headers=worker_headers)
        assert resp.status_code == 200
        # Verify gone
        assert client.get(f'/api/notifications/{nid}', headers=worker_headers).status_code == 404


class TestClearAllNotifications:
    def test_clears(self, client, worker_headers, app, worker_user):
        with app.app_context():
            Notification.create_for_user(worker_user.id, 'system', 'A', 'a')
            Notification.create_for_user(worker_user.id, 'system', 'B', 'b')
        resp = client.delete('/api/notifications/clear-all', headers=worker_headers)
        assert resp.status_code == 200
        assert 'Cleared' in resp.get_json()['message']
        # Verify empty
        count = client.get('/api/notifications/unread-count', headers=worker_headers)
        assert count.get_json()['count'] == 0


class TestNotificationsByType:
    def test_filter(self, client, worker_headers, app, worker_user):
        with app.app_context():
            Notification.create_for_user(worker_user.id, 'assignment', 'Assign', 'body')
            Notification.create_for_user(worker_user.id, 'system', 'System', 'body')
        resp = client.get('/api/notifications/by-type/assignment', headers=worker_headers)
        assert resp.status_code == 200
        assert all(n['type'] == 'assignment' for n in resp.get_json())


class TestRecentNotifications:
    def test_returns_list(self, client, worker_headers, app, worker_user):
        with app.app_context():
            Notification.create_for_user(worker_user.id, 'system', 'Recent', 'body')
        resp = client.get('/api/notifications/recent?hours=24', headers=worker_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)


class TestNotificationStatistics:
    def test_returns_stats(self, client, worker_headers, app, worker_user):
        with app.app_context():
            Notification.create_for_user(worker_user.id, 'system', 'Stat', 'body')
        resp = client.get('/api/notifications/statistics', headers=worker_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)
