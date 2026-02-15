"""
Project model representing building/construction projects.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.database.connection import execute_query, insert_and_get_id, update_record, delete_record


@dataclass
class Project:
    """Project entity representing a building or construction project."""

    id: Optional[int] = None
    name: str = ""
    description: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the projects table."""
        return """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
        """

    @classmethod
    def find_by_id(cls, project_id: int) -> Optional['Project']:
        """Find project by ID."""
        project_data = execute_query(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
            fetch_one=True
        )
        if project_data:
            return cls._from_db_row(project_data)
        return None

    @classmethod
    def find_all_active(cls) -> List['Project']:
        """Get all active projects."""
        data = execute_query(
            "SELECT * FROM projects WHERE is_active = 1 ORDER BY name"
        )
        return [cls._from_db_row(row) for row in data]

    @classmethod
    def find_all(cls) -> List['Project']:
        """Get all projects."""
        data = execute_query(
            "SELECT * FROM projects ORDER BY name"
        )
        return [cls._from_db_row(row) for row in data]

    def save(self) -> 'Project':
        """Save project to database."""
        if self.id is None:
            self.id = insert_and_get_id(
                """INSERT INTO projects (name, description, is_active, created_by)
                   VALUES (?, ?, ?, ?)""",
                (self.name, self.description, self.is_active, self.created_by)
            )
        else:
            update_record(
                """UPDATE projects SET name = ?, description = ?, is_active = ?
                   WHERE id = ?""",
                (self.name, self.description, self.is_active, self.id)
            )
        return self

    def delete(self) -> bool:
        """Permanently delete project from database."""
        if self.id:
            rows_affected = delete_record(
                "DELETE FROM projects WHERE id = ?",
                (self.id,)
            )
            return rows_affected > 0
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
        }

    @classmethod
    def _from_db_row(cls, row) -> 'Project':
        """Create Project instance from database row."""
        return cls(
            id=row['id'],
            name=row['name'],
            description=row.get('description') or '',
            is_active=bool(row.get('is_active', True)),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
            created_by=row.get('created_by'),
        )
