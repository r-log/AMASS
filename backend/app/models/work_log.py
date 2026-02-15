"""
Work log model representing electrical work performed.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.database.connection import execute_query, insert_and_get_id, update_record, delete_record


@dataclass
class WorkLog:
    """Work log entity representing electrical work performed on floors."""

    id: Optional[int] = None
    floor_id: int = 0
    worker_id: Optional[int] = None
    x_coord: float = 0.0
    y_coord: float = 0.0
    work_date: str = ""
    worker_name: str = ""
    work_type: str = ""
    job_type: Optional[str] = None
    description: str = ""
    cable_type: Optional[str] = None
    cable_meters: Optional[float] = None
    start_x: Optional[float] = None
    start_y: Optional[float] = None
    end_x: Optional[float] = None
    end_y: Optional[float] = None
    hours_worked: Optional[float] = None
    status: str = "completed"
    priority: str = "medium"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the work_logs table."""
        return """
        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            floor_id INTEGER NOT NULL,
            worker_id INTEGER,
            x_coord REAL NOT NULL,
            y_coord REAL NOT NULL,
            work_date TEXT NOT NULL,
            worker_name TEXT NOT NULL,
            work_type TEXT NOT NULL,
            job_type TEXT,
            description TEXT,
            cable_type TEXT,
            cable_meters REAL,
            start_x REAL,
            start_y REAL,
            end_x REAL,
            end_y REAL,
            hours_worked REAL,
            status TEXT DEFAULT 'completed',
            priority TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (floor_id) REFERENCES floors (id),
            FOREIGN KEY (worker_id) REFERENCES users (id)
        )
        """

    @classmethod
    def find_by_id(cls, log_id: int) -> Optional['WorkLog']:
        """Find work log by ID."""
        log_data = execute_query(
            """SELECT wl.*, f.name as floor_name 
               FROM work_logs wl
               LEFT JOIN floors f ON wl.floor_id = f.id
               WHERE wl.id = ?""",
            (log_id,),
            fetch_one=True
        )

        if log_data:
            return cls._from_db_row(log_data)
        return None

    @classmethod
    def find_by_floor_id(cls, floor_id: int, limit: Optional[int] = None) -> List['WorkLog']:
        """Find work logs for a specific floor."""
        query = """
            SELECT wl.*, f.name as floor_name 
            FROM work_logs wl
            LEFT JOIN floors f ON wl.floor_id = f.id
            WHERE wl.floor_id = ?
            ORDER BY wl.created_at DESC
        """
        params = (floor_id,)

        if limit:
            query += " LIMIT ?"
            params = (floor_id, limit)

        logs_data = execute_query(query, params)
        return [cls._from_db_row(row) for row in logs_data]

    @classmethod
    def find_by_worker_id(cls, worker_id: int, limit: Optional[int] = None) -> List['WorkLog']:
        """Find work logs for a specific worker."""
        query = """
            SELECT wl.*, f.name as floor_name 
            FROM work_logs wl
            LEFT JOIN floors f ON wl.floor_id = f.id
            WHERE wl.worker_id = ?
            ORDER BY wl.created_at DESC
        """
        params = (worker_id,)

        if limit:
            query += " LIMIT ?"
            params = (worker_id, limit)

        logs_data = execute_query(query, params)
        return [cls._from_db_row(row) for row in logs_data]

    @classmethod
    def find_by_date_range(cls, start_date: str, end_date: str, floor_id: Optional[int] = None) -> List['WorkLog']:
        """Find work logs within a date range."""
        query = """
            SELECT wl.*, f.name as floor_name 
            FROM work_logs wl
            LEFT JOIN floors f ON wl.floor_id = f.id
            WHERE wl.work_date >= ? AND wl.work_date <= ?
        """
        params = [start_date, end_date]

        if floor_id:
            query += " AND wl.floor_id = ?"
            params.append(floor_id)

        query += " ORDER BY wl.work_date DESC, wl.created_at DESC"

        logs_data = execute_query(query, tuple(params))
        return [cls._from_db_row(row) for row in logs_data]

    @classmethod
    def find_by_project_id(cls, project_id: int, limit: Optional[int] = None,
                          offset: Optional[int] = None) -> List['WorkLog']:
        """Find work logs for floors in a project."""
        query = """
            SELECT wl.*, f.name as floor_name
            FROM work_logs wl
            LEFT JOIN floors f ON wl.floor_id = f.id
            WHERE f.project_id = ?
            ORDER BY wl.created_at DESC
        """
        params = [project_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        if offset and limit:
            query += " OFFSET ?"
            params.append(offset)
        logs_data = execute_query(query, tuple(params))
        return [cls._from_db_row(row) for row in logs_data]

    @classmethod
    def find_all(cls, limit: Optional[int] = None, offset: Optional[int] = None) -> List['WorkLog']:
        """Get all work logs with optional pagination."""
        query = """
            SELECT wl.*, f.name as floor_name 
            FROM work_logs wl
            LEFT JOIN floors f ON wl.floor_id = f.id
            ORDER BY wl.created_at DESC
        """
        params = []

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        if offset and limit:
            query += " OFFSET ?"
            params.append(offset)

        logs_data = execute_query(query, tuple(params) if params else ())
        return [cls._from_db_row(row) for row in logs_data]

    @classmethod
    def get_work_type_stats(cls) -> List[Dict[str, Any]]:
        """Get statistics by work type."""
        stats_data = execute_query("""
            SELECT work_type, COUNT(*) as count
            FROM work_logs
            GROUP BY work_type
            ORDER BY count DESC
        """)
        return [{'work_type': row['work_type'], 'count': row['count']} for row in stats_data]

    @classmethod
    def get_floor_stats(cls) -> List[Dict[str, Any]]:
        """Get statistics by floor."""
        stats_data = execute_query("""
            SELECT f.name, COUNT(wl.id) as count
            FROM floors f
            LEFT JOIN work_logs wl ON f.id = wl.floor_id
            GROUP BY f.id, f.name
            ORDER BY count DESC
        """)
        return [{'floor_name': row['name'], 'count': row['count']} for row in stats_data]

    @classmethod
    def get_recent_logs_count(cls, days: int = 7) -> int:
        """Get count of recent logs within specified days."""
        result = execute_query(
            "SELECT COUNT(*) as count FROM work_logs WHERE work_date >= date('now', '-{} days')".format(days),
            fetch_one=True
        )
        return result['count'] if result else 0

    def save(self) -> 'WorkLog':
        """Save work log to database."""
        if self.id is None:
            # Create new work log
            self.id = insert_and_get_id(
                """INSERT INTO work_logs 
                   (floor_id, worker_id, x_coord, y_coord, work_date, worker_name, 
                    work_type, job_type, description, cable_type, cable_meters,
                    start_x, start_y, end_x, end_y, hours_worked, status, priority)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.floor_id, self.worker_id, self.x_coord, self.y_coord, self.work_date,
                 self.worker_name, self.work_type, self.job_type, self.description,
                 self.cable_type, self.cable_meters, self.start_x, self.start_y,
                 self.end_x, self.end_y, self.hours_worked, self.status, self.priority)
            )
        else:
            # Update existing work log
            update_record(
                """UPDATE work_logs 
                   SET floor_id = ?, worker_id = ?, x_coord = ?, y_coord = ?, work_date = ?,
                       worker_name = ?, work_type = ?, job_type = ?, description = ?,
                       cable_type = ?, cable_meters = ?, start_x = ?, start_y = ?,
                       end_x = ?, end_y = ?, hours_worked = ?, status = ?, priority = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (self.floor_id, self.worker_id, self.x_coord, self.y_coord, self.work_date,
                 self.worker_name, self.work_type, self.job_type, self.description,
                 self.cable_type, self.cable_meters, self.start_x, self.start_y,
                 self.end_x, self.end_y, self.hours_worked, self.status, self.priority, self.id)
            )

        return self

    def delete(self) -> bool:
        """Delete work log from database."""
        if self.id:
            rows_affected = delete_record(
                "DELETE FROM work_logs WHERE id = ?",
                (self.id,)
            )
            return rows_affected > 0
        return False

    @classmethod
    def delete_by_floor_id(cls, floor_id: int) -> int:
        """Delete all work logs for a floor. Returns rows affected."""
        return delete_record(
            "DELETE FROM work_logs WHERE floor_id = ?",
            (floor_id,)
        )

    def is_in_critical_area(self) -> bool:
        """Check if this work log is within any critical sector."""
        result = execute_query(
            """SELECT COUNT(*) as count
               FROM critical_sectors cs
               WHERE cs.floor_id = ? 
               AND cs.is_active = 1
               AND ((? - cs.x_coord) * (? - cs.x_coord) + (? - cs.y_coord) * (? - cs.y_coord)) <= (cs.radius * cs.radius)""",
            (self.floor_id, self.x_coord, self.x_coord, self.y_coord, self.y_coord),
            fetch_one=True
        )
        return result['count'] > 0 if result else False

    def get_distance_from_point(self, x: float, y: float) -> float:
        """Calculate distance from this work log to a given point."""
        return ((self.x_coord - x) ** 2 + (self.y_coord - y) ** 2) ** 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert work log to dictionary representation."""
        return {
            'id': self.id,
            'floor_id': self.floor_id,
            'worker_id': self.worker_id,
            'x_coord': self.x_coord,
            'y_coord': self.y_coord,
            'work_date': self.work_date,
            'worker_name': self.worker_name,
            'work_type': self.work_type,
            'job_type': self.job_type,
            'description': self.description,
            'cable_type': self.cable_type,
            'cable_meters': self.cable_meters,
            'start_x': self.start_x,
            'start_y': self.start_y,
            'end_x': self.end_x,
            'end_y': self.end_y,
            'hours_worked': self.hours_worked,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_in_critical_area': self.is_in_critical_area()
        }

    @classmethod
    def _from_db_row(cls, row) -> 'WorkLog':
        """Create WorkLog instance from database row."""
        return cls(
            id=row['id'],
            floor_id=row['floor_id'],
            worker_id=row.get('worker_id'),
            x_coord=row['x_coord'],
            y_coord=row['y_coord'],
            work_date=row['work_date'],
            worker_name=row['worker_name'],
            work_type=row['work_type'],
            job_type=row.get('job_type'),
            description=row.get('description', ''),
            cable_type=row.get('cable_type'),
            cable_meters=row.get('cable_meters'),
            start_x=row.get('start_x'),
            start_y=row.get('start_y'),
            end_x=row.get('end_x'),
            end_y=row.get('end_y'),
            hours_worked=row.get('hours_worked'),
            status=row.get('status', 'completed'),
            priority=row.get('priority', 'medium'),
            created_at=datetime.fromisoformat(
                row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(
                row['updated_at']) if row.get('updated_at') else None
        )

    def __str__(self) -> str:
        return f"WorkLog(id={self.id}, floor_id={self.floor_id}, work_type={self.work_type})"

    def __repr__(self) -> str:
        return self.__str__()
