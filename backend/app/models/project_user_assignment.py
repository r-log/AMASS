"""
Project user assignment model for assigning workers to projects.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.database.connection import execute_query, insert_and_get_id, delete_record


@dataclass
class ProjectUserAssignment:
    """Assignment of a user (worker) to a project."""

    id: Optional[int] = None
    project_id: int = 0
    user_id: int = 0
    assigned_by: Optional[int] = None
    assigned_at: Optional[datetime] = None

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the project_user_assignments table."""
        return """
        CREATE TABLE IF NOT EXISTS project_user_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            assigned_by INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (assigned_by) REFERENCES users (id),
            UNIQUE(project_id, user_id)
        )
        """

    @classmethod
    def assign(cls, project_id: int, user_id: int, assigned_by: Optional[int] = None) -> 'ProjectUserAssignment':
        """Assign a user to a project."""
        assignment = cls(
            project_id=project_id,
            user_id=user_id,
            assigned_by=assigned_by
        )
        assignment.id = insert_and_get_id(
            """INSERT OR IGNORE INTO project_user_assignments (project_id, user_id, assigned_by)
               VALUES (?, ?, ?)""",
            (project_id, user_id, assigned_by)
        )
        return assignment

    @classmethod
    def unassign(cls, project_id: int, user_id: int) -> bool:
        """Unassign a user from a project."""
        delete_record(
            "DELETE FROM project_user_assignments WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        )
        return True

    @classmethod
    def delete_by_project_id(cls, project_id: int) -> int:
        """Delete all project user assignments for a project. Returns rows affected."""
        return delete_record(
            "DELETE FROM project_user_assignments WHERE project_id = ?",
            (project_id,)
        )

    @classmethod
    def find_projects_for_user(cls, user_id: int) -> List[int]:
        """Get list of project IDs the user is assigned to."""
        data = execute_query(
            "SELECT project_id FROM project_user_assignments WHERE user_id = ?",
            (user_id,)
        )
        return [row['project_id'] for row in data] if data else []

    @classmethod
    def find_workers_for_project(cls, project_id: int) -> List[Dict[str, Any]]:
        """Get list of users assigned to the project."""
        data = execute_query(
            """SELECT pua.*, u.full_name, u.username, u.role
               FROM project_user_assignments pua
               JOIN users u ON pua.user_id = u.id
               WHERE pua.project_id = ? AND u.is_active = 1""",
            (project_id,)
        )
        return [
            {
                'user_id': row['user_id'],
                'full_name': row['full_name'],
                'username': row['username'],
                'role': row['role'],
                'assigned_at': row['assigned_at'],
            }
            for row in (data or [])
        ]

    @classmethod
    def is_user_assigned(cls, project_id: int, user_id: int) -> bool:
        """Check if user is assigned to project."""
        result = execute_query(
            "SELECT 1 FROM project_user_assignments WHERE project_id = ? AND user_id = ?",
            (project_id, user_id),
            fetch_one=True
        )
        return result is not None
