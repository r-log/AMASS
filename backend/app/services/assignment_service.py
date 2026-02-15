"""
Assignment service for managing work assignments and task allocation.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import date, timedelta

from app.models.assignment import Assignment
from app.models.user import User
from app.models.work_log import WorkLog
from app.models.notification import Notification


class AssignmentService:
    """Service for managing work assignments and related operations."""

    @staticmethod
    def create_assignment(data: Dict[str, Any], assigned_by_id: int) -> Tuple[bool, Optional[Assignment], str]:
        """
        Create a new work assignment.

        Returns:
            Tuple of (success, assignment_object, message)
        """
        try:
            # Check permissions
            assigner = User.find_by_id(assigned_by_id)
            if not assigner or not assigner.has_any_role(['admin', 'supervisor']):
                return False, None, "Insufficient permissions to create assignments"

            # Validate required fields
            required_fields = ['assigned_to']
            for field in required_fields:
                if field not in data or data[field] is None:
                    return False, None, f"Missing required field: {field}"

            # Validate assignee exists
            assignee = User.find_by_id(data['assigned_to'])
            if not assignee or not assignee.is_active:
                return False, None, "Assignee not found or inactive"

            # Validate work log if provided
            work_log = None
            if data.get('work_log_id'):
                work_log = WorkLog.find_by_id(data['work_log_id'])
                if not work_log:
                    return False, None, "Work log not found"

            # Create assignment
            assignment = Assignment(
                work_log_id=data.get('work_log_id'),
                assigned_to=data['assigned_to'],
                assigned_by=assigned_by_id,
                due_date=data.get('due_date'),
                status='pending',
                notes=data.get('notes', '')
            )

            assignment.save()

            # Create notification for assignee
            if assignment.id:
                AssignmentService._notify_assignment_creation(
                    assignment, assigner, assignee)

            return True, assignment, "Assignment created successfully"

        except Exception as e:
            return False, None, f"Failed to create assignment: {str(e)}"

    @staticmethod
    def update_assignment_status(assignment_id: int, new_status: str, user_id: int) -> Tuple[bool, str]:
        """
        Update assignment status.

        Returns:
            Tuple of (success, message)
        """
        try:
            assignment = Assignment.find_by_id(assignment_id)
            if not assignment:
                return False, "Assignment not found"

            user = User.find_by_id(user_id)
            if not user:
                return False, "User not found"

            # Check permissions
            can_update = (
                user.id == assignment.assigned_to or  # Assignee can update
                user.id == assignment.assigned_by or  # Assigner can update
                # Supervisors/admins can update
                user.has_any_role(['admin', 'supervisor'])
            )

            if not can_update:
                return False, "Insufficient permissions to update this assignment"

            # Validate status
            valid_statuses = ['pending', 'in_progress',
                              'completed', 'cancelled']
            if new_status not in valid_statuses:
                return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"

            old_status = assignment.status
            assignment.update_status(new_status)

            # Notify relevant users about status change
            AssignmentService._notify_status_change(
                assignment, old_status, new_status, user)

            return True, "Assignment status updated successfully"

        except Exception as e:
            return False, f"Failed to update assignment status: {str(e)}"

    @staticmethod
    def get_user_assignments(user_id: int, status_filter: Optional[str] = None,
                             include_assigned_by: bool = False) -> List[Assignment]:
        """Get assignments for a user (assigned to them or by them)."""
        try:
            assignments = []

            # Get assignments assigned TO the user
            user_assignments = Assignment.find_by_user_id(
                user_id, status_filter)
            assignments.extend(user_assignments)

            # Get assignments assigned BY the user (for supervisors/admins)
            if include_assigned_by:
                user = User.find_by_id(user_id)
                if user and user.has_any_role(['admin', 'supervisor']):
                    assigned_by_user = Assignment.find_by_assigned_by(user_id)
                    assignments.extend(assigned_by_user)

            # Remove duplicates
            seen_ids = set()
            unique_assignments = []
            for assignment in assignments:
                if assignment.id not in seen_ids:
                    unique_assignments.append(assignment)
                    seen_ids.add(assignment.id)

            return unique_assignments

        except Exception as e:
            print(f"Error getting user assignments: {e}")
            return []

    @staticmethod
    def get_assignments_by_status(status: str, user_id: Optional[int] = None) -> List[Assignment]:
        """Get assignments by status with optional user filtering."""
        try:
            assignments = Assignment.find_by_status(status)

            # Filter by user if provided (for workers to see only their assignments)
            if user_id:
                user = User.find_by_id(user_id)
                if user and user.is_worker():
                    assignments = [
                        a for a in assignments if a.assigned_to == user_id]

            return assignments

        except Exception as e:
            print(f"Error getting assignments by status: {e}")
            return []

    @staticmethod
    def get_overdue_assignments(user_id: Optional[int] = None) -> List[Assignment]:
        """Get overdue assignments with optional user filtering."""
        try:
            overdue_assignments = Assignment.get_overdue_assignments()

            # Filter by user if provided
            if user_id:
                user = User.find_by_id(user_id)
                if user and user.is_worker():
                    overdue_assignments = [
                        a for a in overdue_assignments if a.assigned_to == user_id]

            return overdue_assignments

        except Exception as e:
            print(f"Error getting overdue assignments: {e}")
            return []

    @staticmethod
    def get_assignments_due_soon(days: int = 3, user_id: Optional[int] = None) -> List[Assignment]:
        """Get assignments due within specified days."""
        try:
            due_soon = Assignment.get_assignments_due_soon(days)

            # Filter by user if provided
            if user_id:
                user = User.find_by_id(user_id)
                if user and user.is_worker():
                    due_soon = [
                        a for a in due_soon if a.assigned_to == user_id]

            return due_soon

        except Exception as e:
            print(f"Error getting assignments due soon: {e}")
            return []

    @staticmethod
    def delete_assignment(assignment_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Delete an assignment.

        Returns:
            Tuple of (success, message)
        """
        try:
            assignment = Assignment.find_by_id(assignment_id)
            if not assignment:
                return False, "Assignment not found"

            user = User.find_by_id(user_id)
            if not user:
                return False, "User not found"

            # Check permissions (only creator or admins can delete)
            can_delete = (
                user.id == assignment.assigned_by or
                user.is_admin()
            )

            if not can_delete:
                return False, "Insufficient permissions to delete this assignment"

            assignment.delete()

            # Notify assignee about deletion
            assignee = User.find_by_id(assignment.assigned_to)
            if assignee:
                Notification.create_for_user(
                    assignee.id,
                    'assignment',
                    'Assignment Cancelled',
                    f'Your assignment has been cancelled by {user.full_name}'
                )

            return True, "Assignment deleted successfully"

        except Exception as e:
            return False, f"Failed to delete assignment: {str(e)}"

    @staticmethod
    def get_assignment_statistics(user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get assignment statistics."""
        try:
            if user_id:
                user = User.find_by_id(user_id)
                if user and user.is_worker():
                    # Worker-specific stats
                    user_assignments = Assignment.find_by_user_id(user_id)
                    status_counts = {}
                    overdue_count = 0
                    due_soon_count = 0

                    for assignment in user_assignments:
                        status = assignment.status
                        status_counts[status] = status_counts.get(
                            status, 0) + 1

                        if assignment.is_overdue():
                            overdue_count += 1
                        elif assignment.is_due_soon():
                            due_soon_count += 1

                    return {
                        'user_id': user_id,
                        'total_assignments': len(user_assignments),
                        'by_status': status_counts,
                        'overdue_count': overdue_count,
                        'due_soon_count': due_soon_count
                    }
                else:
                    # Supervisor/Admin stats
                    all_assignments = Assignment.find_all()
                    status_counts = Assignment.get_status_counts()
                    overdue_assignments = Assignment.get_overdue_assignments()
                    due_soon_assignments = Assignment.get_assignments_due_soon()

                    return {
                        'total_assignments': len(all_assignments),
                        'by_status': status_counts,
                        'overdue_count': len(overdue_assignments),
                        'due_soon_count': len(due_soon_assignments)
                    }
            else:
                # Global stats
                all_assignments = Assignment.find_all()
                status_counts = Assignment.get_status_counts()
                overdue_assignments = Assignment.get_overdue_assignments()

                return {
                    'total_assignments': len(all_assignments),
                    'by_status': status_counts,
                    'overdue_count': len(overdue_assignments)
                }

        except Exception as e:
            print(f"Error getting assignment statistics: {e}")
            return {}

    @staticmethod
    def validate_assignment_data(data: Dict[str, Any]) -> List[str]:
        """Validate assignment data and return list of issues."""
        issues = []

        # Required fields
        required_fields = ['assigned_to']
        for field in required_fields:
            if field not in data or data[field] is None:
                issues.append(f"Missing required field: {field}")

        # Validate due date format
        if 'due_date' in data and data['due_date']:
            try:
                date.fromisoformat(data['due_date'])
            except ValueError:
                issues.append("Invalid due date format. Use YYYY-MM-DD")

        # Validate due date is not in the past
        if 'due_date' in data and data['due_date']:
            try:
                due_date_obj = date.fromisoformat(data['due_date'])
                if due_date_obj < date.today():
                    issues.append("Due date cannot be in the past")
            except ValueError:
                pass  # Already caught above

        return issues

    @staticmethod
    def _notify_assignment_creation(assignment: Assignment, assigner: User, assignee: User) -> None:
        """Send notification about new assignment creation."""
        try:
            due_text = f" Due: {assignment.due_date}" if assignment.due_date else ""
            message = f"New work assignment from {assigner.full_name}.{due_text}"

            Notification.create_assignment_notification(
                assignee.id, message, assignment.id)

        except Exception as e:
            print(f"Error sending assignment creation notification: {e}")

    @staticmethod
    def _notify_status_change(assignment: Assignment, old_status: str, new_status: str, changed_by: User) -> None:
        """Send notification about assignment status change."""
        try:
            # Notify the assigner if status changed by assignee
            if changed_by.id == assignment.assigned_to and assignment.assigned_by != changed_by.id:
                message = f"Assignment status changed from '{old_status}' to '{new_status}' by {changed_by.full_name}"

                Notification.create_for_user(
                    assignment.assigned_by,
                    'assignment',
                    'Assignment Status Update',
                    message,
                    assignment.id
                )

            # Notify the assignee if status changed by someone else
            elif changed_by.id != assignment.assigned_to:
                message = f"Your assignment status was changed from '{old_status}' to '{new_status}' by {changed_by.full_name}"

                Notification.create_for_user(
                    assignment.assigned_to,
                    'assignment',
                    'Assignment Status Update',
                    message,
                    assignment.id
                )

        except Exception as e:
            print(f"Error sending status change notification: {e}")

    @staticmethod
    def send_due_date_reminders() -> Tuple[bool, str]:
        """Send reminders for assignments due soon (automated task)."""
        try:
            due_soon_assignments = Assignment.get_assignments_due_soon(days=3)
            reminder_count = 0

            for assignment in due_soon_assignments:
                assignee = User.find_by_id(assignment.assigned_to)
                if assignee and assignee.is_active:
                    days_until_due = (date.fromisoformat(
                        assignment.due_date) - date.today()).days

                    if days_until_due <= 1:
                        urgency = "⚠️ URGENT"
                    else:
                        urgency = "📅 Reminder"

                    message = f"{urgency}: Assignment due in {days_until_due} day(s). {assignment.notes if assignment.notes else ''}"

                    Notification.create_for_user(
                        assignee.id,
                        'assignment',
                        'Assignment Due Soon',
                        message,
                        assignment.id
                    )

                    reminder_count += 1

            return True, f"Sent {reminder_count} due date reminders"

        except Exception as e:
            return False, f"Failed to send reminders: {str(e)}"

    @staticmethod
    def escalate_overdue_assignments() -> Tuple[bool, str]:
        """Escalate overdue assignments to supervisors (automated task)."""
        try:
            overdue_assignments = Assignment.get_overdue_assignments()
            escalated_count = 0

            supervisors = User.find_by_role('supervisor')
            admins = User.find_by_role('admin')
            escalation_users = supervisors + admins

            for assignment in overdue_assignments:
                assignee = User.find_by_id(assignment.assigned_to)
                if assignee:
                    days_overdue = (
                        date.today() - date.fromisoformat(assignment.due_date)).days

                    message = f"🚨 Assignment overdue by {days_overdue} day(s). Assignee: {assignee.full_name}"

                    for supervisor in escalation_users:
                        if supervisor.is_active:
                            Notification.create_for_user(
                                supervisor.id,
                                'critical_alert',
                                'Overdue Assignment',
                                message,
                                assignment.id
                            )

                    escalated_count += 1

            return True, f"Escalated {escalated_count} overdue assignments"

        except Exception as e:
            return False, f"Failed to escalate assignments: {str(e)}"
