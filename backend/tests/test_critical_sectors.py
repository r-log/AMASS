"""
Critical Sectors API tests.
"""


def test_create_sector(client, supervisor_headers, floor):
    resp = client.post('/api/critical-sectors/', headers=supervisor_headers,
                       json={'floor_id': floor.id, 'sector_name': 'Danger Zone',
                             'x_coord': 0.3, 'y_coord': 0.3, 'radius': 0.1, 'priority': 'high'})
    assert resp.status_code == 201
    assert resp.get_json()['sector']['sector_name'] == 'Danger Zone'


def test_get_sectors(client, supervisor_headers, floor, critical_sector):
    resp = client.get(f'/api/critical-sectors/?floor_id={floor.id}', headers=supervisor_headers)
    assert resp.status_code == 200
    assert any(s['id'] == critical_sector.id for s in resp.get_json())


def test_get_sector_detail(client, supervisor_headers, critical_sector):
    resp = client.get(f'/api/critical-sectors/{critical_sector.id}', headers=supervisor_headers)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == critical_sector.id


def test_update_sector(client, supervisor_headers, critical_sector):
    resp = client.put(f'/api/critical-sectors/{critical_sector.id}', headers=supervisor_headers,
                      json={'sector_name': 'Updated Zone'})
    assert resp.status_code == 200
    assert resp.get_json()['sector']['sector_name'] == 'Updated Zone'


def test_delete_sector(client, supervisor_headers, critical_sector):
    assert client.delete(f'/api/critical-sectors/{critical_sector.id}',
                         headers=supervisor_headers).status_code == 200


def test_check_point_in_sector(client, supervisor_headers, floor, critical_sector):
    resp = client.post('/api/critical-sectors/check-point', headers=supervisor_headers,
                       json={'floor_id': floor.id, 'x': 0.5, 'y': 0.5})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['is_critical'] is True
    assert critical_sector.id in [s['id'] for s in data['sectors']]


def test_check_point_outside_sector(client, supervisor_headers, floor, critical_sector):
    resp = client.post('/api/critical-sectors/check-point', headers=supervisor_headers,
                       json={'floor_id': floor.id, 'x': 0.1, 'y': 0.1})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['is_critical'] is False
    assert len(data['sectors']) == 0
