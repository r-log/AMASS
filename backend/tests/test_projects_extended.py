"""
Extended project tests — unassign worker, 404s, worker access restrictions.
"""

import pytest


class TestProjectAccessControl:
    def test_worker_cannot_update(self, client, worker_headers, project):
        resp = client.put(f'/api/projects/{project.id}', headers=worker_headers,
                          json={'name': 'Hacked'})
        assert resp.status_code == 403

    def test_get_nonexistent(self, client, supervisor_headers):
        resp = client.get('/api/projects/99999', headers=supervisor_headers)
        assert resp.status_code == 404

    def test_delete_nonexistent(self, client, supervisor_headers):
        resp = client.delete('/api/projects/99999', headers=supervisor_headers)
        assert resp.status_code == 400  # service returns error, not 404


class TestUnassignWorker:
    def test_supervisor_unassigns(self, client, supervisor_headers, project, worker_user):
        # Assign first
        client.post(f'/api/projects/{project.id}/assign', headers=supervisor_headers,
                    json={'user_id': worker_user.id})
        # Unassign
        resp = client.delete(f'/api/projects/{project.id}/assign/{worker_user.id}',
                             headers=supervisor_headers)
        assert resp.status_code == 200

    def test_worker_cannot_unassign(self, client, worker_headers, project, worker_user):
        resp = client.delete(f'/api/projects/{project.id}/assign/{worker_user.id}',
                             headers=worker_headers)
        assert resp.status_code == 403


class TestRestoreProject:
    def test_requires_zip(self, client, supervisor_headers):
        headers = {k: v for k, v in supervisor_headers.items() if k != 'Content-Type'}
        import io
        resp = client.post('/api/projects/restore',
                           data={'file': (io.BytesIO(b'not a zip'), 'backup.txt')},
                           headers=headers, content_type='multipart/form-data')
        assert resp.status_code == 400

    def test_no_file_provided(self, client, supervisor_headers):
        headers = {k: v for k, v in supervisor_headers.items() if k != 'Content-Type'}
        resp = client.post('/api/projects/restore', headers=headers,
                           content_type='multipart/form-data')
        assert resp.status_code == 400

    def test_worker_denied(self, client, worker_headers):
        headers = {k: v for k, v in worker_headers.items() if k != 'Content-Type'}
        import io
        resp = client.post('/api/projects/restore',
                           data={'file': (io.BytesIO(b'PK'), 'backup.zip')},
                           headers=headers, content_type='multipart/form-data')
        assert resp.status_code == 403
