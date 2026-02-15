"""
Notification service for managing system notifications and alerts.
"""

from typing import Dict, Any, Optional, List, Tuple

from app.models.notification import Notification
from app.models.user import User


class NotificationService:
    """Service for managing notifications and alerts."""

    @staticmethod
    def create_notification(user_id: int, notification_type: str, title: str,
                            message: str, related_id: Optional[int] = None) -> Tuple[bool, Optional[Notification], str]:
        """
        Create a new notification for a user.

        Returns:
            Tuple of (success, notification_object, message)
        """
        try:
            # Validate user exists
            user = User.find_by_id(user_id)
            if not user:
                return False, None, "User not found"

            # Validate notification type
            valid_types = ['info', 'warning', 'error', 'success', 'assignment',
                           'critical_alert', 'work_log', 'critical_sector', 'system']
            if notification_type not in valid_types:
                return False, None, f"Invalid notification type. Must be one of: {', '.join(valid_types)}"

            # Create notification
            notification = Notification.create_for_user(
                user_id, notification_type, title, message, related_id
            )

            return True, notification, "Notification created successfully"

        except Exception as e:
            return False, None, f"Failed to create notification: {str(e)}"

    @staticmethod
    def get_user_notifications(user_id: int, unread_only: bool = False,
                               limit: Optional[int] = None) -> List[Notification]:
        """Get notifications for a specific user."""
        try:
            return Notification.find_by_user_id(user_id, unread_only, limit)
        except Exception as e:
            print(f"Error getting user notifications: {e}")
            return []

    @staticmethod
    def mark_notification_as_read(notification_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Mark a notification as read.

        Returns:
            Tuple of (success, message)
        """
        try:
            notification = Notification.find_by_id(notification_id)
            if not notification:
                return False, "Notification not found"

            # Check if user owns the notification
            if notification.user_id != user_id:
                return False, "Insufficient permissions to modify this notification"

            notification.mark_as_read()

            return True, "Notification marked as read"

        except Exception as e:
            return False, f"Failed to mark notification as read: {str(e)}"

    @staticmethod
    def mark_all_user_notifications_as_read(user_id: int) -> Tuple[bool, str]:
        """Mark all notifications for a user as read."""
        try:
            from app.database.connection import update_record

            rows_affected = update_record(
                "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
                (user_id,)
            )

            return True, f"Marked {rows_affected} notifications as read"

        except Exception as e:
            return False, f"Failed to mark notifications as read: {str(e)}"

    @staticmethod
    def delete_notification(notification_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Delete a notification.

        Returns:
            Tuple of (success, message)
        """
        try:
            notification = Notification.find_by_id(notification_id)
            if not notification:
                return False, "Notification not found"

            # Check if user owns the notification or is admin
            user = User.find_by_id(user_id)
            if notification.user_id != user_id and (not user or not user.is_admin()):
                return False, "Insufficient permissions to delete this notification"

            notification.delete()

            return True, "Notification deleted successfully"

        except Exception as e:
            return False, f"Failed to delete notification: {str(e)}"

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Get count of unread notifications for a user."""
        try:
            return Notification.get_unread_count_by_user(user_id)
        except Exception as e:
            print(f"Error getting unread count: {e}")
            return 0

    @staticmethod
    def broadcast_notification(notification_type: str, title: str, message: str,
                               target_role: Optional[str] = None, sender_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Broadcast notification to multiple users.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate sender permissions for broadcast
            if sender_id:
                sender = User.find_by_id(sender_id)
                if not sender or not sender.has_any_role(['admin', 'supervisor']):
                    return False, "Insufficient permissions to broadcast notifications"

            # Create notifications based on target
            if target_role:
                notifications = Notification.create_for_role(
                    target_role, notification_type, title, message)
                return True, f"Broadcast sent to {len(notifications)} users with role '{target_role}'"
            else:
                notifications = Notification.create_for_all_users(
                    notification_type, title, message)
                return True, f"Broadcast sent to {len(notifications)} users"

        except Exception as e:
            return False, f"Failed to broadcast notification: {str(e)}"

    @staticmethod
    def create_critical_alert(work_log_id: int, sector_name: str, worker_name: str) -> Tuple[bool, str]:
        """Create critical alert for work in sensitive area."""
        try:
            # Get supervisors and admins
            supervisors = User.find_by_role('supervisor')
            admins = User.find_by_role('admin')
            alert_users = supervisors + admins

            user_ids = [user.id for user in alert_users if user.is_active]

            if user_ids:
                message = f"⚠️ Work completed in critical sector '{sector_name}' by {worker_name}"
                Notification.create_critical_alert(
                    user_ids, message, work_log_id)

                return True, f"Critical alert sent to {len(user_ids)} supervisors and admins"
            else:
                return False, "No supervisors or admins found to alert"

        except Exception as e:
            return False, f"Failed to create critical alert: {str(e)}"

    @staticmethod
    def create_assignment_notification(assignee_id: int, assignment_id: int,
                                       due_date: str, assigner_name: str) -> Tuple[bool, str]:
        """Create notification for new work assignment."""
        try:
            message = f"New work assignment from {assigner_name}. Due: {due_date}"
            notification = Notification.create_assignment_notification(
                assignee_id, message, assignment_id)

            return True, "Assignment notification created"

        except Exception as e:
            return False, f"Failed to create assignment notification: {str(e)}"

    @staticmethod
    def cleanup_old_notifications(days: int = 30, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Clean up old notifications.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check permissions for global cleanup
            if user_id:
                user = User.find_by_id(user_id)
                if not user or not user.is_admin():
                    return False, "Insufficient permissions for notification cleanup"

            deleted_count = Notification.cleanup_old_notifications(days)
            return True, f"Cleaned up {deleted_count} old notifications"

        except Exception as e:
            return False, f"Failed to cleanup notifications: {str(e)}"

    @staticmethod
    def get_notification_statistics(user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get notification statistics."""
        try:
            if user_id:
                # User-specific statistics
                user_notifications = Notification.find_by_user_id(
                    user_id, limit=100)
                unread_count = Notification.get_unread_count_by_user(user_id)
                type_counts = Notification.get_notification_counts_by_type(
                    user_id)

                # Calculate age statistics
                total_age_hours = 0
                recent_count = 0
                for notif in user_notifications:
                    age = notif.get_age_in_hours()
                    total_age_hours += age
                    if notif.is_recent(24):
                        recent_count += 1

                return {
                    'user_id': user_id,
                    'total_notifications': len(user_notifications),
                    'unread_count': unread_count,
                    'recent_count': recent_count,
                    'avg_age_hours': total_age_hours / len(user_notifications) if user_notifications else 0,
                    'by_type': type_counts
                }
            else:
                # Global statistics
                all_unread = Notification.find_all_unread(limit=1000)
                type_counts = Notification.get_notification_counts_by_type()

                return {
                    'global_unread_count': len(all_unread),
                    'by_type': type_counts
                }

        except Exception as e:
            print(f"Error getting notification statistics: {e}")
            return {}

    @staticmethod
    def get_priority_notifications(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get highest priority notifications for a user."""
        try:
            notifications = Notification.find_by_user_id(user_id, limit=50)

            # Sort by priority score
            notifications.sort(
                key=lambda n: n.get_priority_score(), reverse=True)

            # Return top notifications with additional context
            priority_notifications = []
            for notif in notifications[:limit]:
                notif_dict = notif.to_dict()
                priority_notifications.append(notif_dict)

            return priority_notifications

        except Exception as e:
            print(f"Error getting priority notifications: {e}")
            return []

    @staticmethod
    def bulk_mark_as_read(notification_ids: List[int], user_id: int) -> Tuple[bool, str]:
        """Mark multiple notifications as read."""
        try:
            marked_count = 0
            errors = []

            for notif_id in notification_ids:
                success, message = NotificationService.mark_notification_as_read(
                    notif_id, user_id)
                if success:
                    marked_count += 1
                else:
                    errors.append(f"Notification {notif_id}: {message}")

            if errors:
                return True, f"Marked {marked_count} notifications as read with {len(errors)} errors"
            else:
                return True, f"Successfully marked {marked_count} notifications as read"

        except Exception as e:
            return False, f"Bulk operation failed: {str(e)}"

    @staticmethod
    def validate_notification_data(data: Dict[str, Any]) -> List[str]:
        """Validate notification data and return list of issues."""
        issues = []

        # Required fields
        required_fields = ['user_id', 'type', 'title']
        for field in required_fields:
            if field not in data or not data[field]:
                issues.append(f"Missing required field: {field}")

        # Validate type
        if 'type' in data:
            valid_types = ['info', 'warning', 'error', 'success', 'assignment',
                           'critical_alert', 'work_log', 'critical_sector', 'system']
            if data['type'] not in valid_types:
                issues.append(
                    f"Invalid type. Must be one of: {', '.join(valid_types)}")

        # Validate title length
        if 'title' in data and len(data['title'].strip()) > 100:
            issues.append("Title must be 100 characters or less")

        # Validate message length
        if 'message' in data and len(data['message']) > 1000:
            issues.append("Message must be 1000 characters or less")

        return issues
