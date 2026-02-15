"""
User model for authentication and authorization.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.database.connection import get_db, execute_query, insert_and_get_id, update_record


@dataclass
class User:
    """User entity representing system users."""

    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    full_name: str = ""
    role: str = "worker"
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the users table."""
        return """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'worker',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
        """

    @classmethod
    def find_by_id(cls, user_id: int) -> Optional['User']:
        """Find user by ID."""
        user_data = execute_query(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )

        if user_data:
            return cls._from_db_row(user_data)
        return None

    @classmethod
    def find_by_username(cls, username: str) -> Optional['User']:
        """Find user by username."""
        user_data = execute_query(
            "SELECT * FROM users WHERE username = ?",
            (username,),
            fetch_one=True
        )

        if user_data:
            return cls._from_db_row(user_data)
        return None

    @classmethod
    def find_all_active(cls) -> List['User']:
        """Get all active users."""
        users_data = execute_query(
            "SELECT * FROM users WHERE is_active = 1 ORDER BY full_name"
        )

        return [cls._from_db_row(row) for row in users_data]

    @classmethod
    def find_by_role(cls, role: str) -> List['User']:
        """Find users by role."""
        users_data = execute_query(
            "SELECT * FROM users WHERE role = ? AND is_active = 1 ORDER BY full_name",
            (role,)
        )

        return [cls._from_db_row(row) for row in users_data]

    def save(self) -> 'User':
        """Save user to database."""
        if self.id is None:
            # Create new user
            self.id = insert_and_get_id(
                """INSERT INTO users 
                   (username, password_hash, full_name, role, is_active)
                   VALUES (?, ?, ?, ?, ?)""",
                (self.username, self.password_hash,
                 self.full_name, self.role, self.is_active)
            )
        else:
            # Update existing user
            update_record(
                """UPDATE users 
                   SET username = ?, password_hash = ?, full_name = ?, role = ?, is_active = ?
                   WHERE id = ?""",
                (self.username, self.password_hash, self.full_name,
                 self.role, self.is_active, self.id)
            )

        return self

    def update_last_login(self) -> None:
        """Update user's last login timestamp."""
        if self.id:
            self.last_login = datetime.now()
            update_record(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (self.id,)
            )

    def deactivate(self) -> None:
        """Deactivate user account."""
        if self.id:
            self.is_active = False
            update_record(
                "UPDATE users SET is_active = 0 WHERE id = ?",
                (self.id,)
            )

    def activate(self) -> None:
        """Activate user account."""
        if self.id:
            self.is_active = True
            update_record(
                "UPDATE users SET is_active = 1 WHERE id = ?",
                (self.id,)
            )

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return self.role == role

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return self.role in roles

    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == 'admin'

    def is_supervisor(self) -> bool:
        """Check if user is a supervisor."""
        return self.role == 'supervisor'

    def is_worker(self) -> bool:
        """Check if user is a worker."""
        return self.role == 'worker'

    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.role == 'admin'

    def can_delete_any_log(self) -> bool:
        """Check if user can delete any work log."""
        return self.role in ['admin', 'supervisor']

    def can_edit_any_log(self) -> bool:
        """Check if user can edit any work log."""
        return self.role in ['admin', 'supervisor']

    def can_manage_critical_sectors(self) -> bool:
        """Check if user can manage critical sectors."""
        return self.role in ['admin', 'supervisor']

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user to dictionary representation."""
        data = {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }

        if include_sensitive:
            data['password_hash'] = self.password_hash

        return data

    @classmethod
    def _from_db_row(cls, row) -> 'User':
        """Create User instance from database row."""
        return cls(
            id=row['id'],
            username=row['username'],
            password_hash=row['password_hash'],
            full_name=row['full_name'],
            role=row['role'],
            created_at=datetime.fromisoformat(
                row['created_at']) if row['created_at'] else None,
            last_login=datetime.fromisoformat(
                row['last_login']) if row['last_login'] else None,
            is_active=bool(row['is_active'])
        )

    def __str__(self) -> str:
        return f"User(id={self.id}, username={self.username}, role={self.role})"

    def __repr__(self) -> str:
        return self.__str__()
