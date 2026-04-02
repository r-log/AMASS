"""
Floors and Tiles API tests.
"""

import io
import pytest

# Minimal valid PDF bytes for upload tests
_MINIMAL_PDF = (
    b'%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj '
    b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj '
    b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n'
    b'xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n'
    b'0000000058 00000 n \n0000000115 00000 n \n'
    b'trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF'
)


class TestGetFloors:
    def test_get_floors(self, client, floor, supervisor_headers):
        resp = client.get('/api/floors', headers=supervisor_headers)
        assert resp.status_code == 200
        assert len(resp.get_json()) >= 1

    def test_filter_by_project(self, client, floor, project, supervisor_headers):
        resp = client.get(f'/api/floors?project_id={project.id}', headers=supervisor_headers)
        assert resp.status_code == 200
        assert all(f['project_id'] == project.id for f in resp.get_json())


class TestCreateFloor:
    def test_supervisor_creates(self, client, project, supervisor_headers):
        resp = client.post('/api/floors', headers=supervisor_headers,
                           json={'project_id': project.id, 'name': 'Basement'})
        assert resp.status_code == 201
        assert resp.get_json()['floor']['name'] == 'Basement'

    def test_worker_denied(self, client, project, worker_headers):
        resp = client.post('/api/floors', headers=worker_headers,
                           json={'project_id': project.id, 'name': 'Nope'})
        assert resp.status_code == 403


class TestUploadFloorPlan:
    def test_upload_pdf(self, client, floor, supervisor_headers, sample_pdf):
        headers = {k: v for k, v in supervisor_headers.items() if k != 'Content-Type'}
        resp = client.post(f'/api/floors/{floor.id}/upload',
                           data={'file': (sample_pdf, 'test.pdf')},
                           headers=headers, content_type='multipart/form-data')
        assert resp.status_code == 200
        assert resp.get_json().get('image_path')

    def test_invalid_file_type(self, client, floor, supervisor_headers):
        headers = {k: v for k, v in supervisor_headers.items() if k != 'Content-Type'}
        resp = client.post(f'/api/floors/{floor.id}/upload',
                           data={'file': (io.BytesIO(b'text'), 'notes.txt')},
                           headers=headers, content_type='multipart/form-data')
        assert resp.status_code == 400


class TestBatchImport:
    def test_batch_import(self, client, project, supervisor_headers):
        headers = {k: v for k, v in supervisor_headers.items() if k != 'Content-Type'}
        data = {
            'project_id': str(project.id),
            'files[]': [(io.BytesIO(_MINIMAL_PDF), 'f1.pdf'), (io.BytesIO(_MINIMAL_PDF), 'f2.pdf')],
            'names[]': ['1st Floor', '2nd Floor'],
        }
        resp = client.post('/api/floors/batch-import', data=data, headers=headers,
                           content_type='multipart/form-data')
        assert resp.status_code == 201
        floors = resp.get_json()['floors']
        assert len(floors) == 2
        assert {f['name'] for f in floors} == {'1st Floor', '2nd Floor'}

    def test_batch_import_worker_denied(self, client, project, worker_headers):
        headers = {k: v for k, v in worker_headers.items() if k != 'Content-Type'}
        data = {
            'project_id': str(project.id),
            'files[]': [(io.BytesIO(_MINIMAL_PDF), 'f1.pdf')],
            'names[]': ['Nope'],
        }
        resp = client.post('/api/floors/batch-import', data=data, headers=headers,
                           content_type='multipart/form-data')
        assert resp.status_code == 403


class TestDeleteFloor:
    def test_delete_floor(self, app, client, project, supervisor_headers):
        with app.app_context():
            from app.models.floor import Floor
            f = Floor(project_id=project.id, name='Temp', image_path='placeholder.pdf', is_active=True)
            f.save()
            fid = f.id
        assert client.delete(f'/api/floors/{fid}', headers=supervisor_headers).status_code == 200


class TestTileStatus:
    def test_no_tiles(self, client, floor, supervisor_headers):
        resp = client.get(f'/api/tiles/status/{floor.id}', headers=supervisor_headers)
        assert resp.status_code == 200
        assert resp.get_json()['tiles_exist'] is False


class TestTileProgress:
    def test_idle(self, client, floor, supervisor_headers):
        resp = client.get(f'/api/tiles/progress/{floor.id}', headers=supervisor_headers)
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'idle'
