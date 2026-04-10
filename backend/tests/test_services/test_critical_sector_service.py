"""
Unit tests for CriticalSectorService business logic.

These tests exercise the service layer directly (not through HTTP routes),
covering validation, permissions, CRUD, statistics, overlap detection,
bulk operations, and export. The existing tests in test_critical_sectors.py
hit the API surface — these complement them at the service level.
"""

import pytest

from app.services.critical_sector_service import CriticalSectorService
from app.models.critical_sector import CriticalSector


# ---------------------------------------------------------------------------
# validate_critical_sector_data — pure validation, no DB dependency
# ---------------------------------------------------------------------------

class TestValidateCriticalSectorData:
    def test_valid_minimal_payload(self):
        data = {'floor_id': 1, 'sector_name': 'Zone A', 'x_coord': 0.5, 'y_coord': 0.5}
        assert CriticalSectorService.validate_critical_sector_data(data) == []

    def test_missing_required_fields(self):
        issues = CriticalSectorService.validate_critical_sector_data({})
        assert len(issues) == 4  # floor_id, sector_name, x_coord, y_coord
        assert all('Missing required field' in i for i in issues)

    def test_empty_sector_name(self):
        data = {'floor_id': 1, 'sector_name': '   ', 'x_coord': 0.5, 'y_coord': 0.5}
        issues = CriticalSectorService.validate_critical_sector_data(data)
        assert any('cannot be empty' in i for i in issues)

    def test_coordinate_out_of_range(self):
        data = {'floor_id': 1, 'sector_name': 'X', 'x_coord': 1.5, 'y_coord': -0.1}
        issues = CriticalSectorService.validate_critical_sector_data(data)
        assert any('x_coord must be between 0 and 1' in i for i in issues)
        assert any('y_coord must be between 0 and 1' in i for i in issues)

    def test_non_numeric_coordinate(self):
        data = {'floor_id': 1, 'sector_name': 'X', 'x_coord': 'abc', 'y_coord': 0.5}
        issues = CriticalSectorService.validate_critical_sector_data(data)
        assert any('x_coord must be a valid number' in i for i in issues)

    def test_negative_dimensions(self):
        data = {'floor_id': 1, 'sector_name': 'X', 'x_coord': 0.5, 'y_coord': 0.5,
                'radius': -0.1, 'width': 0, 'height': 2.0}
        issues = CriticalSectorService.validate_critical_sector_data(data)
        assert any('radius must be positive' in i for i in issues)
        assert any('width must be positive' in i for i in issues)
        assert any('height must not exceed 1' in i for i in issues)

    def test_invalid_sector_type(self):
        data = {'floor_id': 1, 'sector_name': 'X', 'x_coord': 0.5, 'y_coord': 0.5,
                'type': 'hexagon'}
        issues = CriticalSectorService.validate_critical_sector_data(data)
        assert any('Invalid sector type' in i for i in issues)

    def test_invalid_priority(self):
        data = {'floor_id': 1, 'sector_name': 'X', 'x_coord': 0.5, 'y_coord': 0.5,
                'priority': 'super-critical'}
        issues = CriticalSectorService.validate_critical_sector_data(data)
        assert any('Invalid priority' in i for i in issues)

    def test_accepts_all_valid_types_and_priorities(self):
        for sector_type in ['rectangle', 'circle', 'polygon']:
            for priority in ['low', 'standard', 'high', 'critical']:
                data = {'floor_id': 1, 'sector_name': 'X',
                        'x_coord': 0.5, 'y_coord': 0.5,
                        'type': sector_type, 'priority': priority}
                assert CriticalSectorService.validate_critical_sector_data(data) == []


# ---------------------------------------------------------------------------
# create_critical_sector — permissions + validation + persistence
# ---------------------------------------------------------------------------

class TestCreateCriticalSector:
    def test_supervisor_creates_successfully(self, app, floor, supervisor_user):
        with app.app_context():
            data = {
                'floor_id': floor.id,
                'sector_name': 'Main Panel',
                'x_coord': 0.5, 'y_coord': 0.5,
                'radius': 0.1, 'priority': 'high',
            }
            success, sector, msg = CriticalSectorService.create_critical_sector(data, supervisor_user.id)
            assert success is True
            assert sector is not None
            assert sector.id is not None
            assert sector.sector_name == 'Main Panel'
            assert sector.priority == 'high'

    def test_admin_creates_successfully(self, app, floor, admin_user):
        with app.app_context():
            data = {'floor_id': floor.id, 'sector_name': 'High Voltage',
                    'x_coord': 0.3, 'y_coord': 0.3}
            success, sector, _ = CriticalSectorService.create_critical_sector(data, admin_user.id)
            assert success is True
            assert sector.sector_name == 'High Voltage'

    def test_worker_denied(self, app, floor, worker_user):
        with app.app_context():
            data = {'floor_id': floor.id, 'sector_name': 'X',
                    'x_coord': 0.5, 'y_coord': 0.5}
            success, sector, msg = CriticalSectorService.create_critical_sector(data, worker_user.id)
            assert success is False
            assert sector is None
            assert 'permissions' in msg.lower()

    def test_nonexistent_user_denied(self, app, floor):
        with app.app_context():
            data = {'floor_id': floor.id, 'sector_name': 'X',
                    'x_coord': 0.5, 'y_coord': 0.5}
            success, _, msg = CriticalSectorService.create_critical_sector(data, 99999)
            assert success is False
            assert 'permissions' in msg.lower()

    def test_missing_required_field(self, app, supervisor_user):
        with app.app_context():
            data = {'sector_name': 'X', 'x_coord': 0.5, 'y_coord': 0.5}  # missing floor_id
            success, _, msg = CriticalSectorService.create_critical_sector(data, supervisor_user.id)
            assert success is False
            assert 'floor_id' in msg

    def test_nonexistent_floor(self, app, supervisor_user):
        with app.app_context():
            data = {'floor_id': 99999, 'sector_name': 'X',
                    'x_coord': 0.5, 'y_coord': 0.5}
            success, _, msg = CriticalSectorService.create_critical_sector(data, supervisor_user.id)
            assert success is False
            assert 'Floor not found' in msg

    def test_coordinate_out_of_range(self, app, floor, supervisor_user):
        with app.app_context():
            data = {'floor_id': floor.id, 'sector_name': 'X',
                    'x_coord': 1.5, 'y_coord': 0.5}
            success, _, msg = CriticalSectorService.create_critical_sector(data, supervisor_user.id)
            assert success is False
            assert 'between 0 and 1' in msg

    def test_non_numeric_coordinate(self, app, floor, supervisor_user):
        with app.app_context():
            data = {'floor_id': floor.id, 'sector_name': 'X',
                    'x_coord': 'bad', 'y_coord': 0.5}
            success, _, msg = CriticalSectorService.create_critical_sector(data, supervisor_user.id)
            assert success is False
            assert 'Invalid coordinate' in msg


# ---------------------------------------------------------------------------
# update_critical_sector — permissions + field validation
# ---------------------------------------------------------------------------

class TestUpdateCriticalSector:
    def test_supervisor_updates(self, app, critical_sector, supervisor_user):
        with app.app_context():
            success, sector, _ = CriticalSectorService.update_critical_sector(
                critical_sector.id, {'sector_name': 'Renamed', 'priority': 'critical'},
                supervisor_user.id)
            assert success is True
            assert sector.sector_name == 'Renamed'
            assert sector.priority == 'critical'

    def test_worker_denied(self, app, critical_sector, worker_user):
        with app.app_context():
            success, _, msg = CriticalSectorService.update_critical_sector(
                critical_sector.id, {'sector_name': 'Hacked'}, worker_user.id)
            assert success is False
            assert 'permissions' in msg.lower()

    def test_nonexistent_sector(self, app, supervisor_user):
        with app.app_context():
            success, _, msg = CriticalSectorService.update_critical_sector(
                99999, {'sector_name': 'X'}, supervisor_user.id)
            assert success is False
            assert 'not found' in msg.lower()

    def test_coord_out_of_range(self, app, critical_sector, supervisor_user):
        with app.app_context():
            success, _, msg = CriticalSectorService.update_critical_sector(
                critical_sector.id, {'x_coord': 2.0}, supervisor_user.id)
            assert success is False
            assert 'x_coord must be between 0 and 1' in msg

    def test_zero_radius_rejected(self, app, critical_sector, supervisor_user):
        with app.app_context():
            success, _, msg = CriticalSectorService.update_critical_sector(
                critical_sector.id, {'radius': 0}, supervisor_user.id)
            assert success is False
            assert 'radius must be positive' in msg

    def test_invalid_numeric_field(self, app, critical_sector, supervisor_user):
        with app.app_context():
            success, _, msg = CriticalSectorService.update_critical_sector(
                critical_sector.id, {'width': 'not-a-number'}, supervisor_user.id)
            assert success is False
            assert 'Invalid value for width' in msg


# ---------------------------------------------------------------------------
# delete_critical_sector — deactivation semantics
# ---------------------------------------------------------------------------

class TestDeleteCriticalSector:
    def test_supervisor_deactivates(self, app, critical_sector, supervisor_user):
        with app.app_context():
            success, _, floor_id = CriticalSectorService.delete_critical_sector(
                critical_sector.id, supervisor_user.id)
            assert success is True
            assert floor_id == critical_sector.floor_id
            # Sector should no longer appear in active listings
            active = CriticalSectorService.get_critical_sectors(floor_id=floor_id)
            assert critical_sector.id not in [s.id for s in active]

    def test_worker_denied(self, app, critical_sector, worker_user):
        with app.app_context():
            success, msg, _ = CriticalSectorService.delete_critical_sector(
                critical_sector.id, worker_user.id)
            assert success is False
            assert 'permissions' in msg.lower()

    def test_nonexistent_user(self, app, critical_sector):
        with app.app_context():
            success, msg, _ = CriticalSectorService.delete_critical_sector(
                critical_sector.id, 99999)
            assert success is False
            assert 'User not found' in msg

    def test_nonexistent_sector(self, app, supervisor_user):
        with app.app_context():
            success, msg, _ = CriticalSectorService.delete_critical_sector(99999, supervisor_user.id)
            assert success is False
            assert 'not found' in msg.lower()


# ---------------------------------------------------------------------------
# check_work_in_critical_areas — geometric point-in-sector check
# ---------------------------------------------------------------------------

class TestCheckWorkInCriticalAreas:
    def test_point_inside_sector(self, app, critical_sector, floor):
        with app.app_context():
            # critical_sector fixture is centered at (0.5, 0.5) with radius 0.2
            is_critical, sectors = CriticalSectorService.check_work_in_critical_areas(
                floor.id, 0.5, 0.5)
            assert is_critical is True
            assert critical_sector.id in [s.id for s in sectors]

    def test_point_outside_sector(self, app, critical_sector, floor):
        with app.app_context():
            is_critical, sectors = CriticalSectorService.check_work_in_critical_areas(
                floor.id, 0.05, 0.05)
            assert is_critical is False
            assert sectors == []

    def test_empty_floor(self, app, floor):
        with app.app_context():
            is_critical, sectors = CriticalSectorService.check_work_in_critical_areas(
                floor.id, 0.5, 0.5)
            assert is_critical is False
            assert sectors == []


# ---------------------------------------------------------------------------
# check_overlapping_sectors — circular overlap detection
# ---------------------------------------------------------------------------

class TestCheckOverlappingSectors:
    def test_overlap_detected(self, app, floor, supervisor_user):
        with app.app_context():
            CriticalSectorService.create_critical_sector({
                'floor_id': floor.id, 'sector_name': 'Base',
                'x_coord': 0.5, 'y_coord': 0.5, 'radius': 0.1,
            }, supervisor_user.id)

            # Point near (0.52, 0.52) with radius 0.1 — overlaps
            overlapping = CriticalSectorService.check_overlapping_sectors(
                floor.id, 0.52, 0.52, 0.1)
            assert len(overlapping) >= 1

    def test_no_overlap_when_far(self, app, floor, supervisor_user):
        with app.app_context():
            CriticalSectorService.create_critical_sector({
                'floor_id': floor.id, 'sector_name': 'Base',
                'x_coord': 0.2, 'y_coord': 0.2, 'radius': 0.05,
            }, supervisor_user.id)

            overlapping = CriticalSectorService.check_overlapping_sectors(
                floor.id, 0.9, 0.9, 0.05)
            assert overlapping == []

    def test_exclude_self_from_overlap(self, app, floor, supervisor_user):
        """When updating a sector, it shouldn't overlap with itself."""
        with app.app_context():
            _, sector, _ = CriticalSectorService.create_critical_sector({
                'floor_id': floor.id, 'sector_name': 'Self',
                'x_coord': 0.5, 'y_coord': 0.5, 'radius': 0.1,
            }, supervisor_user.id)

            overlapping = CriticalSectorService.check_overlapping_sectors(
                floor.id, 0.5, 0.5, 0.1, exclude_sector_id=sector.id)
            assert sector.id not in [s.id for s in overlapping]


# ---------------------------------------------------------------------------
# get_critical_sector_statistics — aggregate counts
# ---------------------------------------------------------------------------

class TestStatistics:
    def test_empty_stats(self, app):
        with app.app_context():
            stats = CriticalSectorService.get_critical_sector_statistics()
            assert stats['total_sectors'] == 0
            assert stats['by_type'] == {}

    def test_counts_by_type_and_priority(self, app, floor, supervisor_user):
        with app.app_context():
            CriticalSectorService.create_critical_sector({
                'floor_id': floor.id, 'sector_name': 'A', 'x_coord': 0.1, 'y_coord': 0.1,
                'type': 'rectangle', 'priority': 'high',
            }, supervisor_user.id)
            CriticalSectorService.create_critical_sector({
                'floor_id': floor.id, 'sector_name': 'B', 'x_coord': 0.3, 'y_coord': 0.3,
                'type': 'circle', 'priority': 'critical',
            }, supervisor_user.id)
            CriticalSectorService.create_critical_sector({
                'floor_id': floor.id, 'sector_name': 'C', 'x_coord': 0.7, 'y_coord': 0.7,
                'type': 'rectangle', 'priority': 'high',
            }, supervisor_user.id)

            stats = CriticalSectorService.get_critical_sector_statistics()
            assert stats['total_sectors'] == 3
            assert stats['by_type'].get('rectangle') == 2
            assert stats['by_type'].get('circle') == 1


# ---------------------------------------------------------------------------
# bulk_update_sectors
# ---------------------------------------------------------------------------

class TestBulkUpdate:
    def test_bulk_update_success(self, app, floor, supervisor_user):
        with app.app_context():
            ids = []
            for i, name in enumerate(['A', 'B', 'C']):
                _, s, _ = CriticalSectorService.create_critical_sector({
                    'floor_id': floor.id, 'sector_name': name,
                    'x_coord': 0.1 + i * 0.2, 'y_coord': 0.5,
                }, supervisor_user.id)
                ids.append(s.id)

            success, msg = CriticalSectorService.bulk_update_sectors(
                ids, {'priority': 'critical'}, supervisor_user.id)
            assert success is True
            assert 'Successfully updated 3' in msg

    def test_worker_denied(self, app, critical_sector, worker_user):
        with app.app_context():
            success, msg = CriticalSectorService.bulk_update_sectors(
                [critical_sector.id], {'priority': 'low'}, worker_user.id)
            assert success is False
            assert 'permissions' in msg.lower()

    def test_partial_failure_reports_errors(self, app, critical_sector, supervisor_user):
        with app.app_context():
            # One valid id, one invalid — bulk reports partial success
            success, msg = CriticalSectorService.bulk_update_sectors(
                [critical_sector.id, 99999], {'priority': 'high'}, supervisor_user.id)
            assert success is True  # partial success still returns True
            assert '1 errors' in msg or 'not found' in msg.lower()


# ---------------------------------------------------------------------------
# export_critical_sectors
# ---------------------------------------------------------------------------

class TestExport:
    def test_json_export(self, app, critical_sector):
        with app.app_context():
            success, data, msg = CriticalSectorService.export_critical_sectors(
                floor_id=critical_sector.floor_id, format='json')
            assert success is True
            assert isinstance(data, list)
            assert any(s.get('id') == critical_sector.id for s in data)

    def test_csv_export(self, app, critical_sector):
        with app.app_context():
            success, data, _ = CriticalSectorService.export_critical_sectors(
                floor_id=critical_sector.floor_id, format='csv')
            assert success is True
            assert isinstance(data, str)
            assert 'sector_name' in data  # header row

    def test_unsupported_format(self, app):
        with app.app_context():
            success, data, msg = CriticalSectorService.export_critical_sectors(format='xml')
            assert success is False
            assert 'Unsupported' in msg

    def test_empty_export(self, app):
        with app.app_context():
            success, data, _ = CriticalSectorService.export_critical_sectors(format='json')
            assert success is True
            assert data == []
