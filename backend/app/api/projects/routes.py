"""
Projects API routes.
"""

from flask import Blueprint, request, jsonify
from app.services.project_service import ProjectService
from app.utils.decorators import token_required, supervisor_required, supervisor_or_admin_required

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('', methods=['GET'])
@token_required
def get_projects():
    """Get projects (workers: assigned only; supervisors: all)."""
    try:
        user_id = request.current_user.get('user_id')
        role = request.current_user.get('role')

        projects = ProjectService.get_projects_for_user(user_id, role)
        return jsonify([p.to_dict() for p in projects]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>', methods=['GET'])
@token_required
def get_project(project_id):
    """Get project by ID (if user has access)."""
    try:
        user_id = request.current_user.get('user_id')
        role = request.current_user.get('role')

        project = ProjectService.get_project_by_id(project_id, user_id, role)
        if not project:
            return jsonify({'error': 'Project not found or access denied'}), 404

        return jsonify(project.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('', methods=['POST'])
@supervisor_required
def create_project():
    """Create new project (supervisor only)."""
    try:
        data = request.get_json() or {}
        user_id = request.current_user.get('user_id')

        success, project, message = ProjectService.create_project(data, user_id)
        if success:
            return jsonify({'message': message, 'project': project.to_dict()}), 201
        return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@supervisor_required
def update_project(project_id):
    """Update project (supervisor only)."""
    try:
        data = request.get_json() or {}
        user_id = request.current_user.get('user_id')

        success, project, message = ProjectService.update_project(project_id, data, user_id)
        if success:
            return jsonify({'message': message, 'project': project.to_dict()}), 200
        return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>/assign', methods=['POST'])
@supervisor_required
def assign_worker(project_id):
    """Assign worker to project (supervisor only)."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        assigned_by = request.current_user.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        success, message = ProjectService.assign_worker(project_id, user_id, assigned_by)
        if success:
            return jsonify({'message': message}), 200
        return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>/assign/<int:user_id>', methods=['DELETE'])
@supervisor_required
def unassign_worker(project_id, user_id):
    """Unassign worker from project (supervisor only)."""
    try:
        success, message = ProjectService.unassign_worker(project_id, user_id)
        if success:
            return jsonify({'message': message}), 200
        return jsonify({'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>/workers', methods=['GET'])
@supervisor_required
def get_project_workers(project_id):
    """Get workers assigned to project (supervisor only)."""
    try:
        workers = ProjectService.get_workers_for_project(project_id)
        return jsonify(workers), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@token_required
@supervisor_or_admin_required
def delete_project(project_id):
    """Delete project with full cascade. Creates compressed backup first."""
    try:
        user_id = request.current_user.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not found'}), 401
        success, message, backup_name = ProjectService.delete_project(
            project_id, user_id
        )
        if success:
            return jsonify({
                'message': message,
                'backup_path': backup_name,
            }), 200
        return jsonify({'error': message}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to delete project: {str(e)}'}), 500
