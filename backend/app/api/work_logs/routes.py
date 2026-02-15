"""
Work logs API routes.
"""

from flask import Blueprint, request, jsonify
from app.services.work_log_service import WorkLogService
from app.utils.decorators import token_required, supervisor_or_admin_required, validate_json_request

work_logs_bp = Blueprint('work_logs', __name__)


@work_logs_bp.route('', methods=['GET'])
@token_required
def get_work_logs():
    """Get work logs with filtering."""
    try:
        print(f"\n{'@'*60}")
        print(f"[WORK LOGS] GET work logs request")

        # Extract filters from query parameters
        filters = {}
        if request.args.get('floor_id'):
            filters['floor_id'] = int(request.args.get('floor_id'))
        if request.args.get('worker_id'):
            filters['worker_id'] = int(request.args.get('worker_id'))
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')

        print(f"[WORK LOGS] Filters applied: {filters}")

        # Pagination
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', type=int)
        print(f"[WORK LOGS] Pagination: limit={limit}, offset={offset}")

        user_id = request.current_user.get('user_id')
        print(f"[WORK LOGS] Requesting user ID: {user_id}")

        work_logs = WorkLogService.get_work_logs(
            filters, user_id, limit, offset)

        print(f"[WORK LOGS] ✓ Retrieved {len(work_logs)} work logs")

        # Log coordinate summary for map rendering
        if work_logs and filters.get('floor_id'):
            coords_summary = []
            for log in work_logs[:5]:  # Show first 5
                coords_summary.append(
                    f"Log {log.id}: ({log.x_coord:.3f}, {log.y_coord:.3f})")
            print(f"[WORK LOGS] Sample coordinates for map rendering:")
            for coord in coords_summary:
                print(f"[WORK LOGS]   {coord}")
            if len(work_logs) > 5:
                print(f"[WORK LOGS]   ... and {len(work_logs) - 5} more")

        print(f"[WORK LOGS] ✓ Sending response with {len(work_logs)} logs")
        print(f"{'@'*60}\n")

        return jsonify([log.to_dict() for log in work_logs]), 200

    except Exception as e:
        print(f"[WORK LOGS] ❌ Error getting work logs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to get work logs: {str(e)}'}), 500


@work_logs_bp.route('', methods=['POST'])
@token_required
@validate_json_request
def create_work_log():
    """Create new work log."""
    try:
        data = request.get_json()
        user_id = request.current_user.get('user_id')

        # Validate data
        validation_errors = WorkLogService.validate_work_log_data(data)
        if validation_errors:
            return jsonify({'error': 'Validation failed', 'details': validation_errors}), 400

        success, work_log, message = WorkLogService.create_work_log(
            data, user_id)

        if success:
            return jsonify({
                'message': message,
                'work_log': work_log.to_dict() if work_log else None
            }), 201
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to create work log: {str(e)}'}), 500


@work_logs_bp.route('/<int:log_id>', methods=['GET'])
@token_required
def get_work_log(log_id):
    """Get specific work log with details."""
    try:
        user_id = request.current_user.get('user_id')
        success, log_data, message = WorkLogService.get_work_log_with_details(
            log_id, user_id)

        if success:
            return jsonify(log_data), 200
        else:
            return jsonify({'error': message}), 404 if 'not found' in message.lower() else 403

    except Exception as e:
        return jsonify({'error': f'Failed to get work log: {str(e)}'}), 500


@work_logs_bp.route('/<int:log_id>', methods=['PUT'])
@token_required
@validate_json_request
def update_work_log(log_id):
    """Update work log."""
    try:
        data = request.get_json()
        user_id = request.current_user.get('user_id')

        success, work_log, message = WorkLogService.update_work_log(
            log_id, data, user_id)

        if success:
            return jsonify({
                'message': message,
                'work_log': work_log.to_dict() if work_log else None
            }), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to update work log: {str(e)}'}), 500


@work_logs_bp.route('/<int:log_id>', methods=['DELETE'])
@token_required
def delete_work_log(log_id):
    """Delete work log."""
    try:
        user_id = request.current_user.get('user_id')

        success, message = WorkLogService.delete_work_log(log_id, user_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 403 if 'permission' in message.lower() else 400

    except Exception as e:
        return jsonify({'error': f'Failed to delete work log: {str(e)}'}), 500


@work_logs_bp.route('/enhanced', methods=['POST'])
@token_required
@validate_json_request
def create_enhanced_work_log():
    """Create enhanced work log with cable details."""
    try:
        data = request.get_json()
        user_id = request.current_user.get('user_id')

        # Enhanced validation
        validation_errors = WorkLogService.validate_work_log_data(data)
        if validation_errors:
            return jsonify({'error': 'Validation failed', 'details': validation_errors}), 400

        success, work_log, message = WorkLogService.create_work_log(
            data, user_id)

        if success:
            return jsonify({
                'message': message,
                'work_log': work_log.to_dict() if work_log else None
            }), 201
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to create enhanced work log: {str(e)}'}), 500


@work_logs_bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard_stats():
    """Get dashboard statistics for work logs."""
    try:
        user_id = request.current_user.get('user_id')
        stats = WorkLogService.get_dashboard_stats(user_id)

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get dashboard stats: {str(e)}'}), 500


@work_logs_bp.route('/export', methods=['GET'])
@supervisor_or_admin_required
def export_work_logs():
    """Export work logs in specified format."""
    try:
        # Extract filters
        filters = {}
        if request.args.get('floor_id'):
            filters['floor_id'] = int(request.args.get('floor_id'))
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')

        export_format = request.args.get('format', 'json')

        success, data, message = WorkLogService.export_work_logs(
            filters, export_format)

        if success:
            if export_format.lower() == 'csv':
                from flask import Response
                return Response(
                    data,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': 'attachment;filename=work_logs.csv'}
                )
            else:
                return jsonify({'message': message, 'data': data}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to export work logs: {str(e)}'}), 500


@work_logs_bp.route('/near-point', methods=['GET'])
@token_required
def get_work_logs_near_point():
    """Get work logs near a specific point."""
    try:
        floor_id = request.args.get('floor_id', type=int)
        x = request.args.get('x', type=float)
        y = request.args.get('y', type=float)
        radius = request.args.get('radius', 0.05, type=float)

        if floor_id is None or x is None or y is None:
            return jsonify({'error': 'floor_id, x, and y parameters are required'}), 400

        nearby_logs = WorkLogService.get_work_logs_near_point(
            floor_id, x, y, radius)

        return jsonify([log.to_dict() for log in nearby_logs]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get nearby work logs: {str(e)}'}), 500


@work_logs_bp.route('/bulk-update', methods=['PUT'])
@supervisor_or_admin_required
@validate_json_request
def bulk_update_work_logs():
    """Bulk update multiple work logs."""
    try:
        data = request.get_json()

        log_ids = data.get('log_ids', [])
        updates = data.get('updates', {})

        if not log_ids or not updates:
            return jsonify({'error': 'log_ids and updates are required'}), 400

        user_id = request.current_user.get('user_id')
        success, message = WorkLogService.bulk_update_work_logs(
            log_ids, updates, user_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to bulk update work logs: {str(e)}'}), 500
