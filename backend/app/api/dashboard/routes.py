"""
Dashboard API routes for supervisor and admin stats.
"""

from flask import Blueprint, request, jsonify
from app.database.connection import execute_query
from app.utils.decorators import token_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/supervisor', methods=['GET'])
@token_required
def get_supervisor_stats():
    """Get supervisor dashboard stats. Supervisor or admin only."""
    role = request.current_user.get('role')
    if role not in ('supervisor', 'admin'):
        return jsonify({'error': 'Supervisor or admin required'}), 403

    try:
        # Active workers today (distinct workers with work logs today)
        today_result = execute_query(
            "SELECT COUNT(DISTINCT worker_id) as count FROM work_logs "
            "WHERE work_date = date('now') AND worker_id IS NOT NULL",
            fetch_one=True
        )
        active_workers_today = today_result['count'] if today_result else 0

        # Pending assignments
        pending_result = execute_query(
            "SELECT COUNT(*) as count FROM work_assignments WHERE status = 'pending'",
            fetch_one=True
        )
        pending_assignments = pending_result['count'] if pending_result else 0

        # Critical sectors count
        sectors_result = execute_query(
            "SELECT COUNT(*) as count FROM critical_sectors WHERE is_active = 1",
            fetch_one=True
        )
        critical_sectors = sectors_result['count'] if sectors_result else 0

        # Work logs in critical areas (last 24h) - logs whose (floor_id,x,y) is within any sector
        # Using a subquery: for each sector, count logs within radius, with work_date >= yesterday
        critical_work_result = execute_query(
            """SELECT COUNT(DISTINCT wl.id) as count FROM work_logs wl
               INNER JOIN critical_sectors cs ON wl.floor_id = cs.floor_id AND cs.is_active = 1
               WHERE wl.work_date >= date('now', '-1 day')
               AND ((wl.x_coord - cs.x_coord)*(wl.x_coord - cs.x_coord) +
                    (wl.y_coord - cs.y_coord)*(wl.y_coord - cs.y_coord)) <= (cs.radius * cs.radius)""",
            fetch_one=True
        )
        critical_work_24h = critical_work_result['count'] if critical_work_result else 0

        return jsonify({
            'active_workers_today': active_workers_today,
            'pending_assignments': pending_assignments,
            'critical_sectors': critical_sectors,
            'critical_work_24h': critical_work_24h
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get dashboard stats: {str(e)}'}), 500
