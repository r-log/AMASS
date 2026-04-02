"""
Projects API tests.
"""


def test_create_project(client, supervisor_headers):
    resp = client.post('/api/projects', headers=supervisor_headers,
                       json={'name': 'New Project', 'description': 'Test'})
    assert resp.status_code == 201
    assert resp.get_json()['project']['name'] == 'New Project'


def test_create_project_worker_denied(client, worker_headers):
    resp = client.post('/api/projects', headers=worker_headers,
                       json={'name': 'Nope', 'description': 'No'})
    assert resp.status_code == 403


def test_get_projects(client, supervisor_headers, project):
    resp = client.get('/api/projects', headers=supervisor_headers)
    assert resp.status_code == 200
    assert any(p['id'] == project.id for p in resp.get_json())


def test_get_project_detail(client, supervisor_headers, project):
    resp = client.get(f'/api/projects/{project.id}', headers=supervisor_headers)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == project.id


def test_update_project(client, supervisor_headers, project):
    resp = client.put(f'/api/projects/{project.id}', headers=supervisor_headers,
                      json={'name': 'Renamed'})
    assert resp.status_code == 200
    assert resp.get_json()['project']['name'] == 'Renamed'


def test_assign_worker(client, supervisor_headers, project, worker_user):
    resp = client.post(f'/api/projects/{project.id}/assign', headers=supervisor_headers,
                       json={'user_id': worker_user.id})
    assert resp.status_code == 200


def test_get_project_workers(client, supervisor_headers, project, worker_user):
    client.post(f'/api/projects/{project.id}/assign', headers=supervisor_headers,
                json={'user_id': worker_user.id})
    resp = client.get(f'/api/projects/{project.id}/workers', headers=supervisor_headers)
    assert resp.status_code == 200
    workers = resp.get_json()
    assert any(w.get('id') == worker_user.id or w.get('user_id') == worker_user.id for w in workers)


def test_delete_project(client, supervisor_headers):
    create = client.post('/api/projects', headers=supervisor_headers,
                         json={'name': 'Delete Me', 'description': 'X'})
    pid = create.get_json()['project']['id']
    resp = client.delete(f'/api/projects/{pid}', headers=supervisor_headers)
    assert resp.status_code == 200
