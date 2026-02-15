"""
Critical Sectors API routes.
"""

from flask import Blueprint, request, jsonify
from app.services.critical_sector_service import CriticalSectorService
from app.utils.decorators import token_required, supervisor_or_admin_required

critical_sectors_bp = Blueprint('critical_sectors', __name__, url_prefix='')
critical_sectors_bp.strict_slashes = False


@critical_sectors_bp.route('/', methods=['GET'])
@token_required
def get_critical_sectors():
    """Get all critical sectors with optional floor filtering."""
    try:
        floor_id = request.args.get('floor_id', type=int)
        active_only = request.args.get('active_only', 'true').lower() == 'true'

        sectors = CriticalSectorService.get_critical_sectors(
            floor_id, active_only)

        return jsonify([sector.to_dict() for sector in sectors]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get critical sectors: {str(e)}'}), 500


@critical_sectors_bp.route('/', methods=['POST'])
@supervisor_or_admin_required
def create_critical_sector():
    """Create a new critical sector."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate data
        validation_errors = CriticalSectorService.validate_critical_sector_data(
            data)
        if validation_errors:
            return jsonify({'error': 'Validation failed', 'issues': validation_errors}), 400

        user_id = request.current_user.get('user_id')
        success, sector, message = CriticalSectorService.create_critical_sector(
            data, user_id)

        if success:
            return jsonify({
                'message': message,
                'sector': sector.to_dict() if sector else None
            }), 201
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to create critical sector: {str(e)}'}), 500


@critical_sectors_bp.route('/<int:sector_id>', methods=['GET'])
@token_required
def get_critical_sector(sector_id):
    """Get a specific critical sector by ID."""
    try:
        from app.models.critical_sector import CriticalSector

        sector = CriticalSector.find_by_id(sector_id)

        if not sector:
            return jsonify({'error': 'Critical sector not found'}), 404

        return jsonify(sector.to_dict()), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get critical sector: {str(e)}'}), 500


@critical_sectors_bp.route('/<int:sector_id>', methods=['PUT'])
@supervisor_or_admin_required
def update_critical_sector(sector_id):
    """Update an existing critical sector."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        user_id = request.current_user.get('user_id')
        success, sector, message = CriticalSectorService.update_critical_sector(
            sector_id, data, user_id
        )

        if success:
            return jsonify({
                'message': message,
                'sector': sector.to_dict() if sector else None
            }), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to update critical sector: {str(e)}'}), 500


@critical_sectors_bp.route('/<int:sector_id>', methods=['DELETE'])
@supervisor_or_admin_required
def delete_critical_sector(sector_id):
    """Delete (deactivate) a critical sector."""
    try:
        user_id = request.current_user.get('user_id')
        success, message = CriticalSectorService.delete_critical_sector(
            sector_id, user_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to delete critical sector: {str(e)}'}), 500


@critical_sectors_bp.route('/<int:sector_id>/work-logs', methods=['GET'])
@token_required
def get_sector_work_logs(sector_id):
    """Get work logs within a specific critical sector."""
    try:
        from app.models.critical_sector import CriticalSector

        sector = CriticalSector.find_by_id(sector_id)

        if not sector:
            return jsonify({'error': 'Critical sector not found'}), 404

        limit = request.args.get('limit', 50, type=int)
        work_logs = sector.get_work_logs_in_sector(limit)

        return jsonify({
            'sector': sector.to_dict(),
            'work_logs': work_logs
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get sector work logs: {str(e)}'}), 500


@critical_sectors_bp.route('/statistics', methods=['GET'])
@supervisor_or_admin_required
def get_critical_sector_statistics():
    """Get statistics for critical sectors."""
    try:
        stats = CriticalSectorService.get_critical_sector_statistics()

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 500


@critical_sectors_bp.route('/check-point', methods=['POST'])
@token_required
def check_point_in_critical_areas():
    """Check if a point falls within any critical sectors."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        floor_id = data.get('floor_id')
        x = data.get('x')
        y = data.get('y')

        if floor_id is None or x is None or y is None:
            return jsonify({'error': 'floor_id, x, and y are required'}), 400

        is_critical, sectors = CriticalSectorService.check_work_in_critical_areas(
            floor_id, float(x), float(y)
        )

        return jsonify({
            'is_critical': is_critical,
            'sectors': [sector.to_dict() for sector in sectors]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to check critical areas: {str(e)}'}), 500


@critical_sectors_bp.route('/priority/<priority>', methods=['GET'])
@token_required
def get_sectors_by_priority(priority):
    """Get critical sectors by priority level."""
    try:
        floor_id = request.args.get('floor_id', type=int)

        sectors = CriticalSectorService.get_sectors_by_priority(
            priority, floor_id)

        return jsonify([sector.to_dict() for sector in sectors]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get sectors by priority: {str(e)}'}), 500


@critical_sectors_bp.route('/recent-work', methods=['GET'])
@supervisor_or_admin_required
def get_recent_work_in_critical_sectors():
    """Get recent work that occurred in critical sectors."""
    try:
        days = request.args.get('days', 7, type=int)

        critical_work = CriticalSectorService.get_work_in_critical_sectors(
            days)

        return jsonify(critical_work), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get recent work: {str(e)}'}), 500


@critical_sectors_bp.route('/bulk-update', methods=['PUT'])
@supervisor_or_admin_required
def bulk_update_sectors():
    """Bulk update multiple critical sectors."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        sector_ids = data.get('sector_ids', [])
        updates = data.get('updates', {})

        if not sector_ids or not updates:
            return jsonify({'error': 'sector_ids and updates are required'}), 400

        user_id = request.current_user.get('user_id')
        success, message = CriticalSectorService.bulk_update_sectors(
            sector_ids, updates, user_id
        )

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to bulk update sectors: {str(e)}'}), 500


@critical_sectors_bp.route('/export', methods=['GET'])
@supervisor_or_admin_required
def export_critical_sectors():
    """Export critical sectors in specified format."""
    try:
        floor_id = request.args.get('floor_id', type=int)
        export_format = request.args.get('format', 'json')

        success, data, message = CriticalSectorService.export_critical_sectors(
            floor_id, export_format
        )

        if success:
            if export_format.lower() == 'csv':
                from flask import Response
                return Response(
                    data,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': 'attachment; filename=critical_sectors.csv'}
                )
            else:
                return jsonify(data), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to export sectors: {str(e)}'}), 500
