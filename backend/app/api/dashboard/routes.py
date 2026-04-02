"""
Dashboard API routes for supervisor and admin stats.
"""

from flask import Blueprint, request, jsonify

from app.services.dashboard_service import DashboardService
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
        stats = DashboardService.get_supervisor_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get dashboard stats: {str(e)}'}), 500
