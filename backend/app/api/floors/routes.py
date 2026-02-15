"""
Floors API routes.
"""

import threading
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.services.floor_service import FloorService
from app.models.floor import Floor
from app.utils.decorators import token_required, supervisor_required

floors_bp = Blueprint('floors', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
PLACEHOLDER_IMAGE = 'placeholder.pdf'


@floors_bp.route('', methods=['GET'])
@token_required
def get_floors():
    """Get floors, optionally filtered by project_id."""
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        project_id = request.args.get('project_id', type=int)
        user_id = request.current_user.get('user_id')
        role = request.current_user.get('role')

        floors = FloorService.get_all_floors(
            active_only=active_only,
            project_id=project_id,
            user_id=user_id,
            role=role
        )

        return jsonify([floor.to_dict() for floor in floors]), 200

    except Exception as e:
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


def _trigger_async_tile_generation(floor_id: int, app) -> None:
    """Run tile generation in background thread."""
    def _run():
        with app.app_context():
            try:
                from app.services.tile_service import TileService
                TileService.generate_tiles(floor_id)
                print(f"[FLOORS] ✓ Async tile generation completed for floor {floor_id}")
            except Exception as e:
                print(f"[FLOORS] ✗ Async tile generation failed for floor {floor_id}: {e}")

    thread = threading.Thread(target=_run)
    thread.daemon = True
    thread.start()


@floors_bp.route('', methods=['POST'])
@supervisor_required
def create_floor():
    """
    Create new floor (supervisor only).
    Accepts:
    - multipart/form-data: name, project_id, file (required preferred; fallback to placeholder)
    - application/json: name, project_id, image_path (optional, defaults to placeholder)
    """
    try:
        user_id = request.current_user.get('user_id')
        data = {}
        had_file = False

        if request.content_type and 'multipart/form-data' in request.content_type:
            data['project_id'] = request.form.get('project_id', type=int)
            data['name'] = request.form.get('name', '').strip()  # optional, auto-generated if empty
            file = request.files.get('file')
            if file and file.filename and _allowed_file(file.filename):
                had_file = True
                data['_uploaded_file'] = file
                data['_file_ext'] = file.filename.rsplit('.', 1)[1].lower()
            else:
                data['image_path'] = PLACEHOLDER_IMAGE
            data['width'] = request.form.get('width', type=int) or 1920
            data['height'] = request.form.get('height', type=int) or 1080
            data['sort_order'] = request.form.get('sort_order', type=int) or 0
        else:
            req_data = request.get_json() or {}
            data = {
                'name': req_data.get('name', '').strip() or None,
                'project_id': req_data.get('project_id'),
                'image_path': req_data.get('image_path') or PLACEHOLDER_IMAGE,
                'width': req_data.get('width', 1920),
                'height': req_data.get('height', 1080),
                'sort_order': req_data.get('sort_order', 0),
            }

        if not data.get('project_id'):
            return jsonify({'error': 'project_id is required'}), 400

        if '_uploaded_file' in data:
            data['image_path'] = PLACEHOLDER_IMAGE

        create_data = {k: v for k, v in data.items() if not k.startswith('_')}
        if create_data.get('name') is None:
            create_data.pop('name', None)
        success, floor, message = FloorService.create_floor(create_data, user_id)

        if success and floor:
            floor_id = floor.id
            if had_file and '_uploaded_file' in data:
                file = data['_uploaded_file']
                ext = data['_file_ext']
                floor_plans_dir = Path(current_app.config.get('FLOOR_PLANS_DIR', 'floor-plans'))
                floor_plans_dir.mkdir(parents=True, exist_ok=True)
                safe_name = secure_filename(f"floor-{floor_id}.{ext}")
                save_path = floor_plans_dir / safe_name
                file.save(str(save_path))
                floor.image_path = safe_name
                floor.save()
                _trigger_async_tile_generation(floor_id, current_app._get_current_object())

            return jsonify({
                'message': message,
                'floor': floor.to_dict(),
                'tiles_generating': had_file
            }), 201
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create floor: {str(e)}'}), 500


@floors_bp.route('/<int:floor_id>', methods=['PUT'])
@supervisor_required
def update_floor(floor_id):
    """Update floor (supervisor only)."""
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
@supervisor_required
def delete_floor(floor_id):
    """Delete (deactivate) floor (supervisor only)."""
    try:
        user_id = request.current_user.get('user_id')

        success, message = FloorService.delete_floor(floor_id, user_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to delete floor: {str(e)}'}), 500


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@floors_bp.route('/<int:floor_id>/upload', methods=['POST'])
@supervisor_required
def upload_floor_plan(floor_id):
    """Upload floor plan file (PDF/PNG/JPG) for a floor. Supervisor only."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not _allowed_file(file.filename):
            return jsonify({'error': 'File must be PDF, PNG, or JPEG'}), 400

        floor = Floor.find_by_id(floor_id)
        if not floor:
            return jsonify({'error': 'Floor not found'}), 404

        floor_plans_dir = current_app.config.get('FLOOR_PLANS_DIR', 'floor-plans')
        Path(floor_plans_dir).mkdir(parents=True, exist_ok=True)

        ext = file.filename.rsplit('.', 1)[1].lower()
        safe_name = secure_filename(f"floor-{floor_id}.{ext}")
        save_path = Path(floor_plans_dir) / safe_name
        file.save(str(save_path))

        floor.image_path = safe_name
        floor.save()

        _trigger_async_tile_generation(floor_id, current_app._get_current_object())

        return jsonify({
            'message': 'Floor plan uploaded successfully. Tiles are generating.',
            'image_path': safe_name,
            'tiles_generating': True
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to upload: {str(e)}'}), 500


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
