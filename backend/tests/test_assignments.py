"""
Assignments API tests.
"""


def test_create_assignment(client, supervisor_headers, worker_user, floor):
    resp = client.post('/api/assignments/', headers=supervisor_headers,
                       json={'title': 'Install Panel', 'description': 'Main panel',
                             'assigned_to': worker_user.id, 'floor_id': floor.id, 'due_date': '2026-12-31'})
    assert resp.status_code == 201
    assert resp.get_json()['assignment']['assigned_to'] == worker_user.id


def test_get_assignments(client, supervisor_headers, worker_user, floor):
    client.post('/api/assignments/', headers=supervisor_headers,
                json={'title': 'Wire', 'assigned_to': worker_user.id, 'floor_id': floor.id})
    resp = client.get('/api/assignments/', headers=supervisor_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) >= 1


def test_get_assignment_detail(client, supervisor_headers, worker_user, floor):
    create = client.post('/api/assignments/', headers=supervisor_headers,
                         json={'title': 'Detail', 'assigned_to': worker_user.id, 'floor_id': floor.id})
    aid = create.get_json()['assignment']['id']
    resp = client.get(f'/api/assignments/{aid}', headers=supervisor_headers)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == aid


def test_update_assignment(client, supervisor_headers, worker_user, floor):
    create = client.post('/api/assignments/', headers=supervisor_headers,
                         json={'title': 'Upd', 'assigned_to': worker_user.id, 'floor_id': floor.id})
    aid = create.get_json()['assignment']['id']
    resp = client.put(f'/api/assignments/{aid}', headers=supervisor_headers,
                      json={'status': 'completed'})
    assert resp.status_code == 200


def test_update_assignment_status(client, supervisor_headers, worker_user, floor):
    create = client.post('/api/assignments/', headers=supervisor_headers,
                         json={'title': 'Status', 'assigned_to': worker_user.id, 'floor_id': floor.id})
    aid = create.get_json()['assignment']['id']
    resp = client.put(f'/api/assignments/{aid}/status', headers=supervisor_headers,
                      json={'status': 'in_progress'})
    assert resp.status_code == 200
    assert resp.get_json()['assignment']['status'] == 'in_progress'


def test_delete_assignment(client, supervisor_headers, worker_user, floor):
    create = client.post('/api/assignments/', headers=supervisor_headers,
                         json={'title': 'Del', 'assigned_to': worker_user.id, 'floor_id': floor.id})
    aid = create.get_json()['assignment']['id']
    assert client.delete(f'/api/assignments/{aid}', headers=supervisor_headers).status_code == 200
