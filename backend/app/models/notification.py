"""
Notification model for system notifications and alerts.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.database.connection import execute_query, insert_and_get_id, update_record, delete_record


@dataclass
class Notification:
    """Notification entity for system alerts and messages."""

    id: Optional[int] = None
    user_id: int = 0
    notification_type: str = "info"
    title: str = ""
    message: str = ""
    related_id: Optional[int] = None
    is_read: bool = False
    created_at: Optional[datetime] = None

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the notifications table."""
        return """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT DEFAULT 'info',
            title TEXT NOT NULL,
            message TEXT,
            related_id INTEGER,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """

    @classmethod
    def find_by_id(cls, notification_id: int) -> Optional['Notification']:
        """Find notification by ID."""
        notification_data = execute_query(
            """SELECT n.*, u.full_name as user_name
               FROM notifications n
               LEFT JOIN users u ON n.user_id = u.id
               WHERE n.id = ?""",
            (notification_id,),
            fetch_one=True
        )

        if notification_data:
            return cls._from_db_row(notification_data)
        return None

    @classmethod
    def find_by_user_id(cls, user_id: int, unread_only: bool = False, limit: Optional[int] = None) -> List['Notification']:
        """Find notifications for a specific user."""
        query = """
            SELECT n.*, u.full_name as user_name
            FROM notifications n
            LEFT JOIN users u ON n.user_id = u.id
            WHERE n.user_id = ?
        """
        params = [user_id]

        if unread_only:
            query += " AND n.is_read = 0"

        query += " ORDER BY n.created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        notifications_data = execute_query(query, tuple(params))
        return [cls._from_db_row(row) for row in notifications_data]

    @classmethod
    def find_by_type(cls, notification_type: str, limit: Optional[int] = None) -> List['Notification']:
        """Find notifications by type."""
        query = """
            SELECT n.*, u.full_name as user_name
            FROM notifications n
            LEFT JOIN users u ON n.user_id = u.id
            WHERE n.type = ?
            ORDER BY n.created_at DESC
        """
        params = (notification_type,)

        if limit:
            query += " LIMIT ?"
            params = (notification_type, limit)

        notifications_data = execute_query(query, params)
        return [cls._from_db_row(row) for row in notifications_data]

    @classmethod
    def find_all_unread(cls, limit: Optional[int] = None) -> List['Notification']:
        """Get all unread notifications across all users."""
        query = """
            SELECT n.*, u.full_name as user_name
            FROM notifications n
            LEFT JOIN users u ON n.user_id = u.id
            WHERE n.is_read = 0
            ORDER BY n.created_at DESC
        """
        params = ()

        if limit:
            query += " LIMIT ?"
            params = (limit,)

        notifications_data = execute_query(query, params)
        return [cls._from_db_row(row) for row in notifications_data]

    @classmethod
    def get_unread_count_by_user(cls, user_id: int) -> int:
        """Get count of unread notifications for a user."""
        result = execute_query(
            "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,),
            fetch_one=True
        )
        return result['count'] if result else 0

    @classmethod
    def get_notification_counts_by_type(cls, user_id: Optional[int] = None) -> Dict[str, int]:
        """Get notification counts by type."""
        query = """
            SELECT type, COUNT(*) as count
            FROM notifications
            WHERE 1=1
        """
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " GROUP BY type"

        counts_data = execute_query(query, tuple(params))
        return {row['type']: row['count'] for row in counts_data}

    @classmethod
    def create_for_user(cls, user_id: int, notification_type: str, title: str,
                        message: str, related_id: Optional[int] = None) -> 'Notification':
        """Create a notification for a specific user."""
        notification = cls(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=related_id
        )
        return notification.save()

    @classmethod
    def create_for_users(cls, user_ids: List[int], notification_type: str,
                         title: str, message: str, related_id: Optional[int] = None) -> List['Notification']:
        """Create notifications for multiple users."""
        notifications = []
        for user_id in user_ids:
            notification = cls.create_for_user(
                user_id, notification_type, title, message, related_id)
            notifications.append(notification)
        return notifications

    @classmethod
    def create_for_all_users(cls, notification_type: str, title: str,
                             message: str, related_id: Optional[int] = None) -> List['Notification']:
        """Create notifications for all active users."""
        users_data = execute_query("SELECT id FROM users WHERE is_active = 1")
        user_ids = [row['id'] for row in users_data]
        return cls.create_for_users(user_ids, notification_type, title, message, related_id)

    @classmethod
    def create_for_role(cls, role: str, notification_type: str, title: str,
                        message: str, related_id: Optional[int] = None) -> List['Notification']:
        """Create notifications for users with a specific role."""
        users_data = execute_query(
            "SELECT id FROM users WHERE role = ? AND is_active = 1",
            (role,)
        )
        user_ids = [row['id'] for row in users_data]
        return cls.create_for_users(user_ids, notification_type, title, message, related_id)

    @classmethod
    def create_critical_alert(cls, user_ids: List[int], message: str,
                              related_id: Optional[int] = None) -> List['Notification']:
        """Create critical alert notifications."""
        return cls.create_for_users(user_ids, 'critical_alert', '⚠️ Critical Alert', message, related_id)

    @classmethod
    def create_assignment_notification(cls, user_id: int, message: str,
                                       assignment_id: Optional[int] = None) -> 'Notification':
        """Create assignment-related notification."""
        return cls.create_for_user(user_id, 'assignment', 'New Assignment', message, assignment_id)

    @classmethod
    def create_work_log_notification(cls, user_ids: List[int], message: str,
                                     work_log_id: Optional[int] = None) -> List['Notification']:
        """Create work log-related notifications."""
        return cls.create_for_users(user_ids, 'work_log', 'Work Log Update', message, work_log_id)

    @classmethod
    def create_critical_sector_notification(cls, user_ids: List[int], message: str,
                                            sector_id: Optional[int] = None) -> List['Notification']:
        """Create critical sector-related notifications."""
        return cls.create_for_users(user_ids, 'critical_sector', 'Critical Sector Alert', message, sector_id)

    @classmethod
    def cleanup_old_notifications(cls, days: int = 30) -> int:
        """Delete notifications older than specified days."""
        return delete_record(
            f"DELETE FROM notifications WHERE created_at < date('now', '-{days} days')"
        )

    def save(self) -> 'Notification':
        """Save notification to database."""
        if self.id is None:
            # Create new notification
            self.id = insert_and_get_id(
                """INSERT INTO notifications 
                   (user_id, type, title, message, related_id, is_read)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (self.user_id, self.notification_type, self.title,
                 self.message, self.related_id, self.is_read)
            )
        else:
            # Update existing notification (mainly for marking as read)
            update_record(
                """UPDATE notifications 
                   SET is_read = ?
                   WHERE id = ?""",
                (self.is_read, self.id)
            )

        return self

    def mark_as_read(self) -> None:
        """Mark notification as read."""
        if self.id:
            self.is_read = True
            update_record(
                "UPDATE notifications SET is_read = 1 WHERE id = ?",
                (self.id,)
            )

    def mark_as_unread(self) -> None:
        """Mark notification as unread."""
        if self.id:
            self.is_read = False
            update_record(
                "UPDATE notifications SET is_read = 0 WHERE id = ?",
                (self.id,)
            )

    def delete(self) -> bool:
        """Delete notification from database."""
        if self.id:
            rows_affected = delete_record(
                "DELETE FROM notifications WHERE id = ?",
                (self.id,)
            )
            return rows_affected > 0
        return False

    def get_age_in_hours(self) -> float:
        """Get the age of the notification in hours."""
        if not self.created_at:
            return 0

        now = datetime.now()
        delta = now - self.created_at
        return delta.total_seconds() / 3600

    def is_recent(self, hours: int = 24) -> bool:
        """Check if notification is recent (within specified hours)."""
        return self.get_age_in_hours() <= hours

    def get_priority_score(self) -> int:
        """Get priority score for sorting notifications."""
        type_priority = {
            'critical_alert': 5,
            'assignment': 4,
            'work_log': 3,
            'critical_sector': 4,
            'system': 2,
            'info': 1
        }

        base_score = type_priority.get(self.notification_type, 1)

        # Boost score for unread notifications
        if not self.is_read:
            base_score += 2

        # Boost score for recent notifications
        if self.is_recent(6):  # Within 6 hours
            base_score += 1

        return base_score

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary representation."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.notification_type,
            'title': self.title,
            'message': self.message,
            'related_id': self.related_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'age_hours': self.get_age_in_hours(),
            'is_recent': self.is_recent(),
            'priority_score': self.get_priority_score()
        }

    @classmethod
    def _from_db_row(cls, row) -> 'Notification':
        """Create Notification instance from database row."""
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            notification_type=row['type'],
            title=row['title'],
            message=row.get('message', ''),
            related_id=row.get('related_id'),
            is_read=bool(row['is_read']),
            created_at=datetime.fromisoformat(
                row['created_at']) if row['created_at'] else None
        )

    def __str__(self) -> str:
        return f"Notification(id={self.id}, user_id={self.user_id}, type={self.notification_type})"

    def __repr__(self) -> str:
        return self.__str__()
