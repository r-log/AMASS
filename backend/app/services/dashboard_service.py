"""
Dashboard service for supervisor and admin statistics.
"""

from typing import Dict, Any

from app.database.connection import execute_query


class DashboardService:
    """Service for dashboard statistics and aggregates."""

    @staticmethod
    def get_supervisor_stats() -> Dict[str, Any]:
        """
        Get supervisor dashboard stats:
        - active_workers_today: distinct workers with work logs today
        - pending_assignments: count of pending work assignments
        - critical_sectors: count of active critical sectors
        - critical_work_24h: work logs in critical areas (last 24h)
        - workers_in_critical: worker IDs currently in critical zones
        """
        today_result = execute_query(
            "SELECT COUNT(DISTINCT worker_id) as count FROM work_logs "
            "WHERE work_date = date('now') AND worker_id IS NOT NULL",
            fetch_one=True
        )
        active_workers_today = today_result['count'] if today_result else 0

        pending_result = execute_query(
            "SELECT COUNT(*) as count FROM work_assignments WHERE status = 'pending'",
            fetch_one=True
        )
        pending_assignments = pending_result['count'] if pending_result else 0

        sectors_result = execute_query(
            "SELECT COUNT(*) as count FROM critical_sectors WHERE is_active = 1",
            fetch_one=True
        )
        critical_sectors = sectors_result['count'] if sectors_result else 0

        critical_work_result = execute_query(
            """SELECT COUNT(DISTINCT wl.id) as count FROM work_logs wl
               INNER JOIN critical_sectors cs ON wl.floor_id = cs.floor_id AND cs.is_active = 1
               WHERE wl.work_date >= date('now', '-1 day')
               AND ((wl.x_coord - cs.x_coord)*(wl.x_coord - cs.x_coord) +
                    (wl.y_coord - cs.y_coord)*(wl.y_coord - cs.y_coord)) <= (cs.radius * cs.radius)""",
            fetch_one=True
        )
        critical_work_24h = critical_work_result['count'] if critical_work_result else 0

        workers_in_critical_result = execute_query(
            """SELECT DISTINCT wl.worker_id FROM work_logs wl
               INNER JOIN critical_sectors cs ON wl.floor_id = cs.floor_id AND cs.is_active = 1
               WHERE wl.work_date = date('now') AND wl.worker_id IS NOT NULL
               AND ((wl.x_coord - cs.x_coord)*(wl.x_coord - cs.x_coord) +
                    (wl.y_coord - cs.y_coord)*(wl.y_coord - cs.y_coord)) <= (cs.radius * cs.radius)"""
        )
        workers_in_critical = (
            [r['worker_id'] for r in workers_in_critical_result]
            if workers_in_critical_result else []
        )

        return {
            'active_workers_today': active_workers_today,
            'pending_assignments': pending_assignments,
            'critical_sectors': critical_sectors,
            'critical_work_24h': critical_work_24h,
            'workers_in_critical': workers_in_critical
        }
