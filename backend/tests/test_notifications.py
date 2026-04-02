"""
Notifications API tests.
"""

from app.models.notification import Notification


def test_get_notifications(client, worker_headers):
    resp = client.get('/api/notifications/', headers=worker_headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_unread_count(client, worker_headers):
    resp = client.get('/api/notifications/unread-count', headers=worker_headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json()['count'], int)


def test_mark_read(client, worker_headers, app, worker_user):
    with app.app_context():
        n = Notification.create_for_user(worker_user.id, 'system', 'Test', 'Msg')
        nid = n.id
    resp = client.put(f'/api/notifications/{nid}/read', headers=worker_headers)
    assert resp.status_code == 200


def test_mark_all_read(client, worker_headers, app, worker_user):
    with app.app_context():
        Notification.create_for_user(worker_user.id, 'system', 'A', 'Msg A')
        Notification.create_for_user(worker_user.id, 'system', 'B', 'Msg B')
    resp = client.put('/api/notifications/read-all', headers=worker_headers)
    assert resp.status_code == 200
