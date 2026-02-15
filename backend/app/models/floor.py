"""
Floor model representing building floors.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.database.connection import execute_query, insert_and_get_id, update_record


@dataclass
class Floor:
    """Floor entity representing building floors with floor plans."""

    id: Optional[int] = None
    name: str = ""
    image_path: str = ""
    width: int = 1920
    height: int = 1080
    created_at: Optional[datetime] = None
    is_active: bool = True

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the floors table."""
        return """
        CREATE TABLE IF NOT EXISTS floors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image_path TEXT NOT NULL,
            width INTEGER DEFAULT 1920,
            height INTEGER DEFAULT 1080,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
        """

    @classmethod
    def find_by_id(cls, floor_id: int) -> Optional['Floor']:
        """Find floor by ID."""
        floor_data = execute_query(
            "SELECT * FROM floors WHERE id = ?",
            (floor_id,),
            fetch_one=True
        )

        if floor_data:
            return cls._from_db_row(floor_data)
        return None

    @classmethod
    def find_all_active(cls) -> List['Floor']:
        """Get all active floors."""
        floors_data = execute_query(
            "SELECT * FROM floors WHERE is_active = 1 ORDER BY name"
        )

        return [cls._from_db_row(row) for row in floors_data]

    @classmethod
    def find_all(cls) -> List['Floor']:
        """Get all floors."""
        floors_data = execute_query(
            "SELECT * FROM floors ORDER BY name"
        )

        return [cls._from_db_row(row) for row in floors_data]

    def save(self) -> 'Floor':
        """Save floor to database."""
        if self.id is None:
            # Create new floor
            self.id = insert_and_get_id(
                """INSERT INTO floors (name, image_path, width, height, is_active)
                   VALUES (?, ?, ?, ?, ?)""",
                (self.name, self.image_path, self.width, self.height, self.is_active)
            )
        else:
            # Update existing floor
            update_record(
                """UPDATE floors 
                   SET name = ?, image_path = ?, width = ?, height = ?, is_active = ?
                   WHERE id = ?""",
                (self.name, self.image_path, self.width,
                 self.height, self.is_active, self.id)
            )

        return self

    def deactivate(self) -> None:
        """Deactivate floor."""
        if self.id:
            self.is_active = False
            update_record(
                "UPDATE floors SET is_active = 0 WHERE id = ?",
                (self.id,)
            )

    def activate(self) -> None:
        """Activate floor."""
        if self.id:
            self.is_active = True
            update_record(
                "UPDATE floors SET is_active = 1 WHERE id = ?",
                (self.id,)
            )

    def get_work_logs_count(self) -> int:
        """Get count of work logs for this floor."""
        result = execute_query(
            "SELECT COUNT(*) as count FROM work_logs WHERE floor_id = ?",
            (self.id,),
            fetch_one=True
        )
        return result['count'] if result else 0

    def get_critical_sectors_count(self) -> int:
        """Get count of critical sectors for this floor."""
        result = execute_query(
            "SELECT COUNT(*) as count FROM critical_sectors WHERE floor_id = ? AND is_active = 1",
            (self.id,),
            fetch_one=True
        )
        return result['count'] if result else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert floor to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'image_path': self.image_path,
            'width': self.width,
            'height': self.height,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'work_logs_count': self.get_work_logs_count() if self.id else 0,
            'critical_sectors_count': self.get_critical_sectors_count() if self.id else 0
        }

    @classmethod
    def _from_db_row(cls, row) -> 'Floor':
        """Create Floor instance from database row."""
        return cls(
            id=row['id'],
            name=row['name'],
            image_path=row['image_path'],
            width=row['width'],
            height=row['height'],
            created_at=datetime.fromisoformat(
                row['created_at']) if row.get('created_at') else None,
            is_active=bool(row.get('is_active', True))
        )

    def __str__(self) -> str:
        return f"Floor(id={self.id}, name={self.name})"

    def __repr__(self) -> str:
        return self.__str__()
