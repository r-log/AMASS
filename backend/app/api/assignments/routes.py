"""
Assignments API routes.
"""

from flask import Blueprint, request, jsonify
from app.services.assignment_service import AssignmentService
from app.utils.decorators import token_required, supervisor_or_admin_required

assignments_bp = Blueprint('assignments', __name__)


@assignments_bp.route('/', methods=['GET'])
@token_required
def get_assignments():
    """Get work assignments with role-based filtering."""
    try:
        user_id = request.current_user.get('user_id')
        user_role = request.current_user.get('role')

        # Query parameters
        status = request.args.get('status')
        assigned_to = request.args.get('assigned_to', type=int)
        floor_id = request.args.get('floor_id', type=int)

        # Workers only see their own assignments unless they specify otherwise (admin)
        if user_role == 'worker' and not assigned_to:
            assigned_to = user_id

        # Get assignments based on role
        if status:
            assignments = AssignmentService.get_assignments_by_status(
                status, assigned_to or user_id)
        elif assigned_to:
            assignments = AssignmentService.get_user_assignments(
                assigned_to, status)
        else:
            assignments = AssignmentService.get_user_assignments(
                user_id, status, include_assigned_by=(user_role in ['admin', 'supervisor']))

        return jsonify([assignment.to_dict() for assignment in assignments]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get assignments: {str(e)}'}), 500


@assignments_bp.route('/<int:assignment_id>', methods=['GET'])
@token_required
def get_assignment(assignment_id):
    """Get a specific assignment by ID."""
    try:
        from app.models.assignment import Assignment

        assignment = Assignment.find_by_id(assignment_id)

        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404

        # Check permissions: workers can only view their own assignments
        user_id = request.current_user.get('user_id')
        user_role = request.current_user.get('role')

        if user_role == 'worker' and assignment.assigned_to != user_id:
            return jsonify({'error': 'Access denied'}), 403

        return jsonify(assignment.to_dict()), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get assignment: {str(e)}'}), 500


@assignments_bp.route('/', methods=['POST'])
@supervisor_or_admin_required
def create_assignment():
    """Create a new work assignment."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate required fields
        required_fields = ['assigned_to']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        user_id = request.current_user.get('user_id')
        success, assignment, message = AssignmentService.create_assignment(
            data, user_id
        )

        if success:
            return jsonify({
                'message': message,
                'assignment': assignment.to_dict() if assignment else None
            }), 201
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to create assignment: {str(e)}'}), 500


@assignments_bp.route('/<int:assignment_id>', methods=['PUT'])
@token_required
def update_assignment(assignment_id):
    """Update an assignment."""
    try:
        from app.models.assignment import Assignment

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Check if assignment exists
        assignment = Assignment.find_by_id(assignment_id)
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404

        # Check permissions
        user_id = request.current_user.get('user_id')
        user_role = request.current_user.get('role')

        # Workers can only update their own assignments (typically just status)
        if user_role == 'worker' and assignment.assigned_to != user_id:
            return jsonify({'error': 'Access denied'}), 403

        # For now, only support status updates through this endpoint
        # Full updates would need a more complex service method
        if 'status' in data:
            success, message = AssignmentService.update_assignment_status(
                assignment_id, data['status'], user_id
            )
            if success:
                updated_assignment = Assignment.find_by_id(assignment_id)
                return jsonify({
                    'message': message,
                    'assignment': updated_assignment.to_dict() if updated_assignment else None
                }), 200
            else:
                return jsonify({'error': message}), 400
        else:
            return jsonify({'error': 'Only status updates are currently supported'}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to update assignment: {str(e)}'}), 500


@assignments_bp.route('/<int:assignment_id>', methods=['DELETE'])
@supervisor_or_admin_required
def delete_assignment(assignment_id):
    """Delete an assignment."""
    try:
        user_id = request.current_user.get('user_id')
        success, message = AssignmentService.delete_assignment(
            assignment_id, user_id)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to delete assignment: {str(e)}'}), 500


@assignments_bp.route('/<int:assignment_id>/status', methods=['PUT'])
@token_required
def update_assignment_status(assignment_id):
    """Update assignment status (workers can update their own assignments)."""
    try:
        from app.models.assignment import Assignment

        data = request.get_json()

        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400

        # Check if assignment exists
        assignment = Assignment.find_by_id(assignment_id)
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404

        # Check permissions
        user_id = request.current_user.get('user_id')
        user_role = request.current_user.get('role')

        # Workers can only update their own assignments
        if user_role == 'worker' and assignment.assigned_to != user_id:
            return jsonify({'error': 'Access denied'}), 403

        success, message = AssignmentService.update_assignment_status(
            assignment_id, data['status'], user_id
        )

        if success:
            updated_assignment = Assignment.find_by_id(assignment_id)
            return jsonify({
                'message': message,
                'assignment': updated_assignment.to_dict() if updated_assignment else None
            }), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to update assignment status: {str(e)}'}), 500


@assignments_bp.route('/statistics', methods=['GET'])
@supervisor_or_admin_required
def get_assignment_statistics():
    """Get assignment statistics."""
    try:
        stats = AssignmentService.get_assignment_statistics(None)

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 500


@assignments_bp.route('/my-stats', methods=['GET'])
@token_required
def get_my_assignment_stats():
    """Get assignment statistics for the current user."""
    try:
        user_id = request.current_user.get('user_id')
        stats = AssignmentService.get_assignment_statistics(user_id)

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get user statistics: {str(e)}'}), 500


@assignments_bp.route('/overdue', methods=['GET'])
@supervisor_or_admin_required
def get_overdue_assignments():
    """Get overdue assignments."""
    try:
        overdue = AssignmentService.get_overdue_assignments(None)

        return jsonify([assignment.to_dict() for assignment in overdue]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get overdue assignments: {str(e)}'}), 500


@assignments_bp.route('/by-worker/<int:worker_id>', methods=['GET'])
@supervisor_or_admin_required
def get_assignments_by_worker(worker_id):
    """Get all assignments for a specific worker."""
    try:
        status = request.args.get('status')
        assignments = AssignmentService.get_user_assignments(
            worker_id, status)

        return jsonify([assignment.to_dict() for assignment in assignments]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get worker assignments: {str(e)}'}), 500


@assignments_bp.route('/bulk-create', methods=['POST'])
@supervisor_or_admin_required
def bulk_create_assignments():
    """Create multiple assignments at once."""
    try:
        data = request.get_json()

        if not data or 'assignments' not in data:
            return jsonify({'error': 'Assignments list is required'}), 400

        user_id = request.current_user.get('user_id')
        # Bulk create assignments one by one
        results = []
        success_count = 0

        for assignment_data in data['assignments']:
            success, assignment, message = AssignmentService.create_assignment(
                assignment_data, user_id
            )
            results.append({
                'success': success,
                'message': message,
                'assignment': assignment.to_dict() if assignment else None
            })
            if success:
                success_count += 1

        return jsonify({
            'message': f'Created {success_count}/{len(data["assignments"])} assignments',
            'results': results
        }), 201

    except Exception as e:
        return jsonify({'error': f'Failed to bulk create assignments: {str(e)}'}), 500
