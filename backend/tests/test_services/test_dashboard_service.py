"""
Unit tests for DashboardService.

Exercises the SQL aggregates in get_supervisor_stats() directly at the
service level. All queries use SQLite's date('now') so fixtures must
insert work logs with today's date.
"""

from app.services.dashboard_service import DashboardService
from app.database.connection import execute_query
from app.models.work_log import WorkLog
from app.models.assignment import Assignment
from app.models.critical_sector import CriticalSector


def _sqlite_today() -> str:
    """
    Return SQLite's date('now') string.

    Important: SQLite uses UTC for date('now'), which can differ from
    Python's local date.today() by a day around midnight in non-UTC
    timezones. The dashboard service filters on date('now'), so tests
    must use the same reference to avoid flakiness. Must be called
    inside an app context.
    """
    return execute_query("SELECT date('now') as d", fetch_one=True)['d']


YESTERDAY_STR = '2020-01-01'  # anything far in the past for "not today"


# ---------------------------------------------------------------------------
# Empty DB baseline
# ---------------------------------------------------------------------------

class TestEmptyStats:
    def test_all_zeros_on_empty_db(self, app):
        with app.app_context():
            stats = DashboardService.get_supervisor_stats()
            assert stats == {
                'active_workers_today': 0,
                'pending_assignments': 0,
                'critical_sectors': 0,
                'critical_work_24h': 0,
                'workers_in_critical': [],
            }


# ---------------------------------------------------------------------------
# active_workers_today — distinct worker count with work_date = today
# ---------------------------------------------------------------------------

class TestActiveWorkersToday:
    def test_counts_distinct_workers_today(self, app, floor, worker_user):
        with app.app_context():
            today = _sqlite_today()
            # Two logs same worker today → count = 1
            for i in range(2):
                WorkLog(
                    floor_id=floor.id, worker_id=worker_user.id,
                    x_coord=0.1 + i * 0.1, y_coord=0.1, work_date=today,
                    worker_name=worker_user.full_name, work_type='cable_pull',
                    description='Today work',
                ).save()

            stats = DashboardService.get_supervisor_stats()
            assert stats['active_workers_today'] == 1

    def test_excludes_old_work_logs(self, app, floor, worker_user):
        with app.app_context():
            WorkLog(
                floor_id=floor.id, worker_id=worker_user.id,
                x_coord=0.1, y_coord=0.1, work_date=YESTERDAY_STR,
                worker_name=worker_user.full_name, work_type='cable_pull',
                description='Old work',
            ).save()
            stats = DashboardService.get_supervisor_stats()
            assert stats['active_workers_today'] == 0

    def test_ignores_null_worker_id(self, app, floor):
        with app.app_context():
            WorkLog(
                floor_id=floor.id, worker_id=None,
                x_coord=0.1, y_coord=0.1, work_date=_sqlite_today(),
                worker_name='Anonymous', work_type='cable_pull',
                description='No worker',
            ).save()
            stats = DashboardService.get_supervisor_stats()
            assert stats['active_workers_today'] == 0

    def test_multiple_workers_counted_separately(self, app, floor, worker_user, admin_user):
        with app.app_context():
            today = _sqlite_today()
            for user in (worker_user, admin_user):
                WorkLog(
                    floor_id=floor.id, worker_id=user.id,
                    x_coord=0.1, y_coord=0.1, work_date=today,
                    worker_name=user.full_name, work_type='cable_pull',
                    description='x',
                ).save()
            stats = DashboardService.get_supervisor_stats()
            assert stats['active_workers_today'] == 2


# ---------------------------------------------------------------------------
# pending_assignments — rows with status='pending'
# ---------------------------------------------------------------------------

class TestPendingAssignments:
    def test_counts_pending_only(self, app, worker_user, supervisor_user):
        with app.app_context():
            for status in ('pending', 'pending', 'completed', 'in_progress'):
                Assignment(
                    assigned_to=worker_user.id,
                    assigned_by=supervisor_user.id,
                    status=status,
                    notes='test',
                ).save()

            stats = DashboardService.get_supervisor_stats()
            assert stats['pending_assignments'] == 2


# ---------------------------------------------------------------------------
# critical_sectors — active count only
# ---------------------------------------------------------------------------

class TestCriticalSectorsCount:
    def test_counts_active_only(self, app, floor):
        with app.app_context():
            active1 = CriticalSector(floor_id=floor.id, sector_name='A',
                                     x_coord=0.1, y_coord=0.1, is_active=True)
            active1.save()
            active2 = CriticalSector(floor_id=floor.id, sector_name='B',
                                     x_coord=0.3, y_coord=0.3, is_active=True)
            active2.save()
            inactive = CriticalSector(floor_id=floor.id, sector_name='C',
                                      x_coord=0.5, y_coord=0.5, is_active=False)
            inactive.save()

            stats = DashboardService.get_supervisor_stats()
            assert stats['critical_sectors'] == 2


# ---------------------------------------------------------------------------
# critical_work_24h — work logs geometrically inside an active sector
# ---------------------------------------------------------------------------

class TestCriticalWork24h:
    def test_log_inside_sector_counted(self, app, floor, worker_user):
        with app.app_context():
            # Sector at (0.5, 0.5) with radius 0.2
            CriticalSector(floor_id=floor.id, sector_name='Zone',
                           x_coord=0.5, y_coord=0.5, radius=0.2,
                           is_active=True).save()
            # Log inside the circle
            WorkLog(
                floor_id=floor.id, worker_id=worker_user.id,
                x_coord=0.55, y_coord=0.55, work_date=_sqlite_today(),
                worker_name=worker_user.full_name, work_type='cable_pull',
                description='Inside sector',
            ).save()

            stats = DashboardService.get_supervisor_stats()
            assert stats['critical_work_24h'] == 1

    def test_log_outside_sector_ignored(self, app, floor, worker_user):
        with app.app_context():
            CriticalSector(floor_id=floor.id, sector_name='Zone',
                           x_coord=0.5, y_coord=0.5, radius=0.1,
                           is_active=True).save()
            WorkLog(
                floor_id=floor.id, worker_id=worker_user.id,
                x_coord=0.05, y_coord=0.05, work_date=_sqlite_today(),
                worker_name=worker_user.full_name, work_type='cable_pull',
                description='Far away',
            ).save()

            stats = DashboardService.get_supervisor_stats()
            assert stats['critical_work_24h'] == 0

    def test_old_log_ignored(self, app, floor, worker_user):
        with app.app_context():
            CriticalSector(floor_id=floor.id, sector_name='Zone',
                           x_coord=0.5, y_coord=0.5, radius=0.2,
                           is_active=True).save()
            WorkLog(
                floor_id=floor.id, worker_id=worker_user.id,
                x_coord=0.5, y_coord=0.5, work_date=YESTERDAY_STR,
                worker_name=worker_user.full_name, work_type='cable_pull',
                description='Ancient',
            ).save()

            stats = DashboardService.get_supervisor_stats()
            assert stats['critical_work_24h'] == 0

    def test_inactive_sector_ignored(self, app, floor, worker_user):
        with app.app_context():
            CriticalSector(floor_id=floor.id, sector_name='Deactivated',
                           x_coord=0.5, y_coord=0.5, radius=0.2,
                           is_active=False).save()
            WorkLog(
                floor_id=floor.id, worker_id=worker_user.id,
                x_coord=0.5, y_coord=0.5, work_date=_sqlite_today(),
                worker_name=worker_user.full_name, work_type='cable_pull',
                description='In deactivated sector',
            ).save()

            stats = DashboardService.get_supervisor_stats()
            assert stats['critical_work_24h'] == 0


# ---------------------------------------------------------------------------
# workers_in_critical — distinct worker IDs currently in critical zones
# ---------------------------------------------------------------------------

class TestWorkersInCritical:
    def test_returns_worker_ids(self, app, floor, worker_user):
        with app.app_context():
            CriticalSector(floor_id=floor.id, sector_name='Zone',
                           x_coord=0.5, y_coord=0.5, radius=0.2,
                           is_active=True).save()
            WorkLog(
                floor_id=floor.id, worker_id=worker_user.id,
                x_coord=0.5, y_coord=0.5, work_date=_sqlite_today(),
                worker_name=worker_user.full_name, work_type='cable_pull',
                description='In zone',
            ).save()

            stats = DashboardService.get_supervisor_stats()
            assert worker_user.id in stats['workers_in_critical']

    def test_distinct_workers_only(self, app, floor, worker_user):
        with app.app_context():
            CriticalSector(floor_id=floor.id, sector_name='Zone',
                           x_coord=0.5, y_coord=0.5, radius=0.2,
                           is_active=True).save()
            today = _sqlite_today()
            # Same worker, two logs, both inside
            for i in range(2):
                WorkLog(
                    floor_id=floor.id, worker_id=worker_user.id,
                    x_coord=0.5, y_coord=0.5 + i * 0.01, work_date=today,
                    worker_name=worker_user.full_name, work_type='cable_pull',
                    description='In zone',
                ).save()

            stats = DashboardService.get_supervisor_stats()
            # Distinct count — worker listed once
            assert stats['workers_in_critical'].count(worker_user.id) == 1

    def test_empty_when_no_one_in_critical(self, app, floor, worker_user):
        with app.app_context():
            CriticalSector(floor_id=floor.id, sector_name='Zone',
                           x_coord=0.5, y_coord=0.5, radius=0.1,
                           is_active=True).save()
            WorkLog(
                floor_id=floor.id, worker_id=worker_user.id,
                x_coord=0.05, y_coord=0.05, work_date=_sqlite_today(),
                worker_name=worker_user.full_name, work_type='cable_pull',
                description='Far',
            ).save()

            stats = DashboardService.get_supervisor_stats()
            assert stats['workers_in_critical'] == []


# ---------------------------------------------------------------------------
# End-to-end: multiple signals combined
# ---------------------------------------------------------------------------

class TestCombinedStats:
    def test_mixed_scenario(self, app, floor, worker_user, admin_user, supervisor_user):
        with app.app_context():
            today = _sqlite_today()
            CriticalSector(floor_id=floor.id, sector_name='Hot',
                           x_coord=0.5, y_coord=0.5, radius=0.2,
                           is_active=True).save()
            # Worker inside critical zone today
            WorkLog(
                floor_id=floor.id, worker_id=worker_user.id,
                x_coord=0.5, y_coord=0.5, work_date=today,
                worker_name=worker_user.full_name, work_type='cable_pull',
                description='In zone',
            ).save()
            # Admin outside critical zone today
            WorkLog(
                floor_id=floor.id, worker_id=admin_user.id,
                x_coord=0.05, y_coord=0.05, work_date=today,
                worker_name=admin_user.full_name, work_type='cable_pull',
                description='Far',
            ).save()
            # Pending assignment
            Assignment(
                assigned_to=worker_user.id,
                assigned_by=supervisor_user.id,
                status='pending',
                notes='Urgent',
            ).save()

            stats = DashboardService.get_supervisor_stats()
            assert stats['active_workers_today'] == 2
            assert stats['pending_assignments'] == 1
            assert stats['critical_sectors'] == 1
            assert stats['critical_work_24h'] == 1
            assert stats['workers_in_critical'] == [worker_user.id]
