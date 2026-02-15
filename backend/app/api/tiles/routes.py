"""
Tiles API routes.
"""

from flask import Blueprint, request, jsonify, send_from_directory
from app.services.tile_service import TileService
from app.utils.decorators import token_required, supervisor_required
import os

tiles_bp = Blueprint('tiles', __name__)


@tiles_bp.route('/<int:floor_id>', methods=['GET'])
@token_required
def get_tile_configuration(floor_id):
    """Get tile configuration for a specific floor."""
    try:
        config = TileService.get_tile_config(floor_id)

        if config:
            return jsonify(config), 200
        else:
            return jsonify({'error': 'Tile configuration not found'}), 404

    except Exception as e:
        return jsonify({'error': f'Failed to get tile configuration: {str(e)}'}), 500


@tiles_bp.route('/generate/<int:floor_id>', methods=['POST'])
@token_required
@supervisor_required
def generate_tiles(floor_id):
    """Generate tiles for a floor plan. Uses floor_id from URL; image_path from body or Floor model."""
    try:
        data = request.get_json(silent=True) or {}
        image_path = data.get('image_path')

        success, message = TileService.generate_tiles(floor_id, image_path)

        if success:
            return jsonify({'message': message, 'success': True}), 200
        else:
            return jsonify({'error': message, 'success': False}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to generate tiles: {str(e)}', 'success': False}), 500


@tiles_bp.route('/regenerate/<int:floor_id>', methods=['POST'])
@token_required
@supervisor_required
def regenerate_tiles(floor_id):
    """Regenerate tiles for a specific floor."""
    try:
        data = request.get_json() or {}
        image_path = data.get('image_path')

        success, message = TileService.regenerate_tiles(floor_id, image_path)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to regenerate tiles: {str(e)}'}), 500


@tiles_bp.route('/status/<int:floor_id>', methods=['GET'])
@token_required
def get_tile_status(floor_id):
    """Check if tiles exist and get their status."""
    try:
        exists, info = TileService.check_tiles_exist(floor_id)

        return jsonify({
            'tiles_exist': exists,  # Frontend expects 'tiles_exist' not 'exists'
            'floor_id': floor_id,
            'info': info
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get tile status: {str(e)}'}), 500


@tiles_bp.route('/clear/<int:floor_id>', methods=['DELETE'])
@token_required
@supervisor_required
def clear_tiles(floor_id):
    """Clear tile cache for a specific floor."""
    try:
        success, message = TileService.clear_tile_cache(floor_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to clear tile cache: {str(e)}'}), 500


@tiles_bp.route('/clear-all', methods=['DELETE'])
@token_required
@supervisor_required
def clear_all_tiles():
    """Clear all tile caches."""
    try:
        success, message = TileService.clear_all_tile_cache()

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to clear all tiles: {str(e)}'}), 500


@tiles_bp.route('/list', methods=['GET'])
@token_required
def list_available_tiles():
    """List all available floor tiles."""
    try:
        tiles_info = TileService.list_all_tiles()

        return jsonify(tiles_info), 200

    except Exception as e:
        return jsonify({'error': f'Failed to list tiles: {str(e)}'}), 500


@tiles_bp.route('/<int:floor_id>/<path:tile_path>')
@token_required
def serve_tile(floor_id, tile_path):
    """Serve tile files (DZI and tile images)."""
    try:
        from flask import current_app
        import os

        tiles_directory = current_app.config.get('TILES_DIRECTORY', 'tiles')
        # Floor directories are named floor-1, floor-2, etc.
        floor_directory = os.path.join(tiles_directory, f'floor-{floor_id}')

        # Construct full path
        full_path = os.path.abspath(os.path.join(floor_directory, tile_path))
        floor_dir_abs = os.path.abspath(floor_directory)

        # Security check: ensure the path doesn't escape the floor directory
        if not full_path.startswith(floor_dir_abs):
            return jsonify({'error': 'Invalid tile path'}), 400

        # Check if file exists
        if not os.path.exists(full_path):
            return jsonify({'error': f'Tile file not found: {tile_path}'}), 404

        # Get directory and filename
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)

        # Serve the file with appropriate MIME type
        if filename.endswith('.dzi'):
            return send_from_directory(directory, filename, mimetype='application/xml')
        else:
            # Tile images (png, jpg, etc.)
            return send_from_directory(directory, filename)

    except FileNotFoundError:
        return jsonify({'error': f'Tile not found: {tile_path}'}), 404
    except Exception as e:
        print(f"Error serving tile: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to serve tile: {str(e)}'}), 500


@tiles_bp.route('/batch-generate', methods=['POST'])
@token_required
@supervisor_required
def batch_generate_tiles():
    """Generate tiles for multiple floors."""
    try:
        data = request.get_json()

        if not data or 'floors' not in data:
            return jsonify({'error': 'Floors list is required'}), 400

        results = []
        for floor_config in data['floors']:
            floor_id = floor_config.get('floor_id')
            image_path = floor_config.get('image_path')

            if floor_id and image_path:
                success, message = TileService.generate_tiles(
                    floor_id, image_path)
                results.append({
                    'floor_id': floor_id,
                    'success': success,
                    'message': message
                })
            else:
                results.append({
                    'floor_id': floor_id,
                    'success': False,
                    'message': 'Missing floor_id or image_path'
                })

        return jsonify({
            'message': 'Batch tile generation completed',
            'results': results
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to batch generate tiles: {str(e)}'}), 500
