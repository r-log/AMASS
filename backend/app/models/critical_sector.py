"""
Critical sector model representing sensitive areas on floors.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.database.connection import execute_query, insert_and_get_id, update_record, delete_record


@dataclass
class CriticalSector:
    """Critical sector entity representing sensitive areas that require special attention."""

    id: Optional[int] = None
    floor_id: int = 0
    sector_name: str = ""
    x_coord: float = 0.0
    y_coord: float = 0.0
    radius: float = 0.1
    width: float = 0.1
    height: float = 0.1
    sector_type: str = "rectangle"
    priority: str = "standard"
    points: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the critical_sectors table."""
        return """
        CREATE TABLE IF NOT EXISTS critical_sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            floor_id INTEGER NOT NULL,
            sector_name TEXT NOT NULL,
            x_coord REAL NOT NULL,
            y_coord REAL NOT NULL,
            radius REAL DEFAULT 0.1,
            width REAL DEFAULT 0.1,
            height REAL DEFAULT 0.1,
            type TEXT DEFAULT 'rectangle',
            priority TEXT DEFAULT 'standard',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (floor_id) REFERENCES floors (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
        """

    @classmethod
    def find_by_id(cls, sector_id: int) -> Optional['CriticalSector']:
        """Find critical sector by ID."""
        sector_data = execute_query(
            """SELECT cs.*, f.name as floor_name, u.full_name as created_by_name
               FROM critical_sectors cs
               LEFT JOIN floors f ON cs.floor_id = f.id
               LEFT JOIN users u ON cs.created_by = u.id
               WHERE cs.id = ?""",
            (sector_id,),
            fetch_one=True
        )

        if sector_data:
            return cls._from_db_row(sector_data)
        return None

    @classmethod
    def find_by_floor_id(cls, floor_id: int, active_only: bool = True) -> List['CriticalSector']:
        """Find critical sectors for a specific floor."""
        query = """
            SELECT cs.*, f.name as floor_name, u.full_name as created_by_name
            FROM critical_sectors cs
            LEFT JOIN floors f ON cs.floor_id = f.id
            LEFT JOIN users u ON cs.created_by = u.id
            WHERE cs.floor_id = ?
        """
        params = [floor_id]

        if active_only:
            query += " AND cs.is_active = 1"

        query += " ORDER BY cs.created_at DESC"

        sectors_data = execute_query(query, tuple(params))
        return [cls._from_db_row(row) for row in sectors_data]

    @classmethod
    def find_by_project_id(cls, project_id: int, active_only: bool = True) -> List['CriticalSector']:
        """Find critical sectors for floors in a project."""
        query = """
            SELECT cs.*, f.name as floor_name, u.full_name as created_by_name
            FROM critical_sectors cs
            LEFT JOIN floors f ON cs.floor_id = f.id
            LEFT JOIN users u ON cs.created_by = u.id
            WHERE f.project_id = ?
        """
        params = [project_id]
        if active_only:
            query += " AND cs.is_active = 1"
        query += " ORDER BY cs.floor_id, cs.created_at DESC"
        sectors_data = execute_query(query, tuple(params))
        return [cls._from_db_row(row) for row in sectors_data]

    @classmethod
    def find_all_active(cls) -> List['CriticalSector']:
        """Get all active critical sectors."""
        sectors_data = execute_query(
            """SELECT cs.*, f.name as floor_name, u.full_name as created_by_name
               FROM critical_sectors cs
               LEFT JOIN floors f ON cs.floor_id = f.id
               LEFT JOIN users u ON cs.created_by = u.id
               WHERE cs.is_active = 1
               ORDER BY cs.floor_id, cs.created_at DESC"""
        )

        return [cls._from_db_row(row) for row in sectors_data]

    @classmethod
    def find_by_priority(cls, priority: str, floor_id: Optional[int] = None) -> List['CriticalSector']:
        """Find critical sectors by priority level."""
        query = """
            SELECT cs.*, f.name as floor_name, u.full_name as created_by_name
            FROM critical_sectors cs
            LEFT JOIN floors f ON cs.floor_id = f.id
            LEFT JOIN users u ON cs.created_by = u.id
            WHERE cs.priority = ? AND cs.is_active = 1
        """
        params = [priority]

        if floor_id:
            query += " AND cs.floor_id = ?"
            params.append(floor_id)

        query += " ORDER BY cs.created_at DESC"

        sectors_data = execute_query(query, tuple(params))
        return [cls._from_db_row(row) for row in sectors_data]

    @classmethod
    def find_sectors_containing_point(cls, floor_id: int, x: float, y: float) -> List['CriticalSector']:
        """Find critical sectors that contain a specific point."""
        sectors_data = execute_query(
            """SELECT cs.*, f.name as floor_name, u.full_name as created_by_name
               FROM critical_sectors cs
               LEFT JOIN floors f ON cs.floor_id = f.id
               LEFT JOIN users u ON cs.created_by = u.id
               WHERE cs.floor_id = ? AND cs.is_active = 1
               AND ((? - cs.x_coord) * (? - cs.x_coord) + (? - cs.y_coord) * (? - cs.y_coord)) <= (cs.radius * cs.radius)""",
            (floor_id, x, x, y, y)
        )

        return [cls._from_db_row(row) for row in sectors_data]

    @classmethod
    def get_count_by_floor(cls) -> List[Dict[str, Any]]:
        """Get count of critical sectors by floor."""
        stats_data = execute_query("""
            SELECT f.name as floor_name, COUNT(cs.id) as count
            FROM floors f
            LEFT JOIN critical_sectors cs ON f.id = cs.floor_id AND cs.is_active = 1
            GROUP BY f.id, f.name
            ORDER BY count DESC
        """)
        return [{'floor_name': row['floor_name'], 'count': row['count']} for row in stats_data]

    @classmethod
    def get_count_by_priority(cls) -> List[Dict[str, Any]]:
        """Get count of critical sectors by priority."""
        stats_data = execute_query("""
            SELECT priority, COUNT(*) as count
            FROM critical_sectors
            WHERE is_active = 1
            GROUP BY priority
            ORDER BY 
                CASE priority 
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'standard' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END
        """)
        return [{'priority': row['priority'], 'count': row['count']} for row in stats_data]

    def save(self) -> 'CriticalSector':
        """Save critical sector to database."""
        if self.id is None:
            # Create new critical sector
            self.id = insert_and_get_id(
                """INSERT INTO critical_sectors 
                   (floor_id, sector_name, x_coord, y_coord, radius, width, height, 
                    type, priority, points, created_by, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.floor_id, self.sector_name, self.x_coord, self.y_coord,
                 self.radius, self.width, self.height, self.sector_type,
                 self.priority, self.points, self.created_by, self.is_active)
            )
        else:
            # Update existing critical sector
            update_record(
                """UPDATE critical_sectors 
                   SET floor_id = ?, sector_name = ?, x_coord = ?, y_coord = ?,
                       radius = ?, width = ?, height = ?, type = ?, priority = ?,
                       points = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (self.floor_id, self.sector_name, self.x_coord, self.y_coord,
                 self.radius, self.width, self.height, self.sector_type,
                 self.priority, self.points, self.id)
            )

        return self

    def deactivate(self) -> None:
        """Deactivate critical sector."""
        if self.id:
            self.is_active = False
            update_record(
                "UPDATE critical_sectors SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (self.id,)
            )

    def activate(self) -> None:
        """Activate critical sector."""
        if self.id:
            self.is_active = True
            update_record(
                "UPDATE critical_sectors SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (self.id,)
            )

    def delete_permanently(self) -> bool:
        """Permanently delete critical sector from database."""
        if self.id:
            rows_affected = delete_record(
                "DELETE FROM critical_sectors WHERE id = ?",
                (self.id,)
            )
            return rows_affected > 0
        return False

    @classmethod
    def delete_by_floor_id(cls, floor_id: int) -> int:
        """Delete all critical sectors for a floor. Returns rows affected."""
        return delete_record(
            "DELETE FROM critical_sectors WHERE floor_id = ?",
            (floor_id,)
        )

    def contains_point(self, x: float, y: float) -> bool:
        """Check if this critical sector contains the given point."""
        if self.sector_type == "circle":
            # Use radius for circular sectors
            distance = ((x - self.x_coord) ** 2 +
                        (y - self.y_coord) ** 2) ** 0.5
            return distance <= self.radius
        else:
            # Use width/height for rectangular sectors
            return (abs(x - self.x_coord) <= self.width / 2 and
                    abs(y - self.y_coord) <= self.height / 2)

    def get_work_logs_in_sector(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get work logs that fall within this critical sector."""
        query = """
            SELECT wl.*, f.name as floor_name
            FROM work_logs wl
            LEFT JOIN floors f ON wl.floor_id = f.id
            WHERE wl.floor_id = ?
            AND ((wl.x_coord - ?) * (wl.x_coord - ?) + (wl.y_coord - ?) * (wl.y_coord - ?)) <= (? * ?)
            ORDER BY wl.created_at DESC
        """
        params = (self.floor_id, self.x_coord, self.x_coord,
                  self.y_coord, self.y_coord, self.radius, self.radius)

        if limit:
            query += " LIMIT ?"
            params = params + (limit,)

        return execute_query(query, params)

    def get_work_logs_count_in_sector(self) -> int:
        """Get count of work logs within this critical sector."""
        result = execute_query(
            """SELECT COUNT(*) as count
               FROM work_logs
               WHERE floor_id = ?
               AND ((x_coord - ?) * (x_coord - ?) + (y_coord - ?) * (y_coord - ?)) <= (? * ?)""",
            (self.floor_id, self.x_coord, self.x_coord,
             self.y_coord, self.y_coord, self.radius, self.radius),
            fetch_one=True
        )
        return result['count'] if result else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert critical sector to dictionary representation."""
        return {
            'id': self.id,
            'floor_id': self.floor_id,
            'sector_name': self.sector_name,
            'x_coord': self.x_coord,
            'y_coord': self.y_coord,
            'radius': self.radius,
            'width': self.width,
            'height': self.height,
            'type': self.sector_type,
            'priority': self.priority,
            'points': self.points,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'work_logs_count': self.get_work_logs_count_in_sector()
        }

    @classmethod
    def _from_db_row(cls, row) -> 'CriticalSector':
        """Create CriticalSector instance from database row."""
        return cls(
            id=row['id'],
            floor_id=row['floor_id'],
            sector_name=row['sector_name'],
            x_coord=row['x_coord'],
            y_coord=row['y_coord'],
            radius=row.get('radius', 0.1),
            width=row.get('width', 0.1),
            height=row.get('height', 0.1),
            sector_type=row.get('type', 'rectangle'),
            priority=row.get('priority', 'standard'),
            points=row.get('points'),
            created_by=row.get('created_by'),
            created_at=datetime.fromisoformat(
                row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(
                row['updated_at']) if row.get('updated_at') else None,
            is_active=bool(row.get('is_active', True))
        )

    def __str__(self) -> str:
        return f"CriticalSector(id={self.id}, name={self.sector_name}, floor_id={self.floor_id})"

    def __repr__(self) -> str:
        return self.__str__()
