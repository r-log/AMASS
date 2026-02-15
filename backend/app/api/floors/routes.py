"""
Floors API routes.
"""

from flask import Blueprint, request, jsonify
from app.services.floor_service import FloorService
from app.utils.decorators import token_required, admin_required

floors_bp = Blueprint('floors', __name__)


@floors_bp.route('', methods=['GET'])
@token_required
def get_floors():
    """Get all floors."""
    try:
        print(f"\n{'='*60}")
        print(f"[FLOORS API] GET all floors request")

        active_only = request.args.get('active_only', 'true').lower() == 'true'
        print(f"[FLOORS API] Filter: active_only={active_only}")

        floors = FloorService.get_all_floors(active_only)
        print(f"[FLOORS API] ✓ Retrieved {len(floors)} floors")

        for floor in floors:
            print(
                f"[FLOORS API]   - Floor {floor.id}: {floor.name} (Image: {floor.image_path})")

        print(f"[FLOORS API] ✓ Sending response with {len(floors)} floors")
        print(f"{'='*60}\n")

        return jsonify([floor.to_dict() for floor in floors]), 200

    except Exception as e:
        print(f"[FLOORS API] ❌ Error getting floors: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to get floors: {str(e)}'}), 500


@floors_bp.route('/', methods=['GET'])
@token_required
def get_floors_with_slash():
    """Get all floors (alternative endpoint with trailing slash)."""
    return get_floors()


@floors_bp.route('/<int:floor_id>', methods=['GET'])
@token_required
def get_floor(floor_id):
    """Get specific floor by ID."""
    try:
        print(f"\n{'#'*60}")
        print(f"[FLOOR DETAIL] GET floor ID: {floor_id}")

        floor = FloorService.get_floor_by_id(floor_id)

        if not floor:
            print(f"[FLOOR DETAIL] ❌ Floor {floor_id} not found")
            return jsonify({'error': 'Floor not found'}), 404

        print(f"[FLOOR DETAIL] ✓ Floor found: {floor.name}")
        print(f"[FLOOR DETAIL]   Image: {floor.image_path}")
        print(f"[FLOOR DETAIL]   Active: {floor.is_active}")
        print(f"[FLOOR DETAIL] ✓ Sending floor data")
        print(f"{'#'*60}\n")

        return jsonify(floor.to_dict()), 200

    except Exception as e:
        print(f"[FLOOR DETAIL] ❌ Error getting floor {floor_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to get floor: {str(e)}'}), 500


@floors_bp.route('', methods=['POST'])
@admin_required
def create_floor():
    """Create new floor (admin only)."""
    try:
        data = request.get_json()
        user_id = request.current_user.get('user_id')

        success, floor, message = FloorService.create_floor(data, user_id)

        if success:
            return jsonify({
                'message': message,
                'floor': floor.to_dict() if floor else None
            }), 201
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to create floor: {str(e)}'}), 500


@floors_bp.route('/<int:floor_id>', methods=['PUT'])
@admin_required
def update_floor(floor_id):
    """Update floor (admin only)."""
    try:
        data = request.get_json()
        user_id = request.current_user.get('user_id')

        success, floor, message = FloorService.update_floor(
            floor_id, data, user_id)

        if success:
            return jsonify({
                'message': message,
                'floor': floor.to_dict() if floor else None
            }), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to update floor: {str(e)}'}), 500


@floors_bp.route('/<int:floor_id>', methods=['DELETE'])
@admin_required
def delete_floor(floor_id):
    """Delete (deactivate) floor (admin only)."""
    try:
        user_id = request.current_user.get('user_id')

        success, message = FloorService.delete_floor(floor_id, user_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to delete floor: {str(e)}'}), 500


@floors_bp.route('/statistics', methods=['GET'])
@token_required
def get_floor_statistics():
    """Get floor statistics."""
    try:
        floor_id = request.args.get('floor_id', type=int)
        stats = FloorService.get_floor_statistics(floor_id)

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 500


@floors_bp.route('/<int:floor_id>/summary', methods=['GET'])
@token_required
def get_floor_work_summary(floor_id):
    """Get work summary for a specific floor."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        date_range = None
        if start_date and end_date:
            date_range = (start_date, end_date)

        summary = FloorService.get_floor_work_summary(floor_id, date_range)

        return jsonify(summary), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get floor summary: {str(e)}'}), 500


@floors_bp.route('/activity', methods=['GET'])
@token_required
def get_floors_with_activity():
    """Get floors with recent activity."""
    try:
        days = request.args.get('days', 30, type=int)
        active_floors = FloorService.get_floors_with_activity(days)

        return jsonify(active_floors), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get floor activity: {str(e)}'}), 500
