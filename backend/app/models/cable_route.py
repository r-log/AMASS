"""
Cable route model for tracking cable installations and routes.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
from app.database.connection import execute_query, insert_and_get_id, update_record, delete_record


@dataclass
class CableRoute:
    """Cable route entity for tracking cable installation paths."""

    id: Optional[int] = None
    work_log_id: int = 0
    route_points: List[Dict[str, float]] = None
    cable_type: str = ""
    cable_cross_section: Optional[str] = None
    total_length: Optional[float] = None
    installation_method: str = ""
    notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.route_points is None:
            self.route_points = []

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the cable_routes table."""
        return """
        CREATE TABLE IF NOT EXISTS cable_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_log_id INTEGER NOT NULL,
            route_points TEXT NOT NULL,
            cable_type TEXT,
            cable_cross_section TEXT,
            total_length REAL,
            installation_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (work_log_id) REFERENCES work_logs (id)
        )
        """

    @classmethod
    def find_by_id(cls, route_id: int) -> Optional['CableRoute']:
        """Find cable route by ID."""
        route_data = execute_query(
            """SELECT cr.*, wl.work_type, wl.description as work_description,
                      wl.floor_id, f.name as floor_name
               FROM cable_routes cr
               LEFT JOIN work_logs wl ON cr.work_log_id = wl.id
               LEFT JOIN floors f ON wl.floor_id = f.id
               WHERE cr.id = ?""",
            (route_id,),
            fetch_one=True
        )

        if route_data:
            return cls._from_db_row(route_data)
        return None

    @classmethod
    def find_by_work_log_id(cls, work_log_id: int) -> Optional['CableRoute']:
        """Find cable route for a specific work log."""
        route_data = execute_query(
            """SELECT cr.*, wl.work_type, wl.description as work_description,
                      wl.floor_id, f.name as floor_name
               FROM cable_routes cr
               LEFT JOIN work_logs wl ON cr.work_log_id = wl.id
               LEFT JOIN floors f ON wl.floor_id = f.id
               WHERE cr.work_log_id = ?""",
            (work_log_id,),
            fetch_one=True
        )

        if route_data:
            return cls._from_db_row(route_data)
        return None

    @classmethod
    def find_by_floor_id(cls, floor_id: int, limit: Optional[int] = None) -> List['CableRoute']:
        """Find cable routes for a specific floor."""
        query = """
            SELECT cr.*, wl.work_type, wl.description as work_description,
                   wl.floor_id, f.name as floor_name
            FROM cable_routes cr
            LEFT JOIN work_logs wl ON cr.work_log_id = wl.id
            LEFT JOIN floors f ON wl.floor_id = f.id
            WHERE wl.floor_id = ?
            ORDER BY cr.created_at DESC
        """
        params = (floor_id,)

        if limit:
            query += " LIMIT ?"
            params = (floor_id, limit)

        routes_data = execute_query(query, params)
        return [cls._from_db_row(row) for row in routes_data]

    @classmethod
    def find_by_cable_type(cls, cable_type: str, limit: Optional[int] = None) -> List['CableRoute']:
        """Find cable routes by cable type."""
        query = """
            SELECT cr.*, wl.work_type, wl.description as work_description,
                   wl.floor_id, f.name as floor_name
            FROM cable_routes cr
            LEFT JOIN work_logs wl ON cr.work_log_id = wl.id
            LEFT JOIN floors f ON wl.floor_id = f.id
            WHERE cr.cable_type = ?
            ORDER BY cr.created_at DESC
        """
        params = (cable_type,)

        if limit:
            query += " LIMIT ?"
            params = (cable_type, limit)

        routes_data = execute_query(query, params)
        return [cls._from_db_row(row) for row in routes_data]

    @classmethod
    def find_all(cls, limit: Optional[int] = None, offset: Optional[int] = None) -> List['CableRoute']:
        """Get all cable routes with optional pagination."""
        query = """
            SELECT cr.*, wl.work_type, wl.description as work_description,
                   wl.floor_id, f.name as floor_name
            FROM cable_routes cr
            LEFT JOIN work_logs wl ON cr.work_log_id = wl.id
            LEFT JOIN floors f ON wl.floor_id = f.id
            ORDER BY cr.created_at DESC
        """
        params = []

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        if offset and limit:
            query += " OFFSET ?"
            params.append(offset)

        routes_data = execute_query(query, tuple(params) if params else ())
        return [cls._from_db_row(row) for row in routes_data]

    @classmethod
    def get_cable_type_stats(cls) -> List[Dict[str, Any]]:
        """Get statistics by cable type."""
        stats_data = execute_query("""
            SELECT cable_type, COUNT(*) as count, SUM(total_length) as total_length
            FROM cable_routes
            WHERE cable_type IS NOT NULL
            GROUP BY cable_type
            ORDER BY count DESC
        """)
        return [
            {
                'cable_type': row['cable_type'],
                'count': row['count'],
                'total_length': row['total_length'] or 0
            }
            for row in stats_data
        ]

    @classmethod
    def get_total_cable_length(cls, cable_type: Optional[str] = None) -> float:
        """Get total cable length installed."""
        query = "SELECT SUM(total_length) as total FROM cable_routes WHERE total_length IS NOT NULL"
        params = ()

        if cable_type:
            query += " AND cable_type = ?"
            params = (cable_type,)

        result = execute_query(query, params, fetch_one=True)
        return result['total'] or 0 if result else 0

    @classmethod
    def get_installation_method_stats(cls) -> List[Dict[str, Any]]:
        """Get statistics by installation method."""
        stats_data = execute_query("""
            SELECT installation_method, COUNT(*) as count
            FROM cable_routes
            WHERE installation_method IS NOT NULL AND installation_method != ''
            GROUP BY installation_method
            ORDER BY count DESC
        """)
        return [
            {
                'installation_method': row['installation_method'],
                'count': row['count']
            }
            for row in stats_data
        ]

    def save(self) -> 'CableRoute':
        """Save cable route to database."""
        route_points_json = json.dumps(
            self.route_points) if self.route_points else "[]"

        if self.id is None:
            # Create new cable route
            self.id = insert_and_get_id(
                """INSERT INTO cable_routes 
                   (work_log_id, route_points, cable_type, cable_cross_section, 
                    total_length, installation_method, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (self.work_log_id, route_points_json, self.cable_type,
                 self.cable_cross_section, self.total_length,
                 self.installation_method, self.notes)
            )
        else:
            # Update existing cable route
            update_record(
                """UPDATE cable_routes 
                   SET work_log_id = ?, route_points = ?, cable_type = ?, 
                       cable_cross_section = ?, total_length = ?, 
                       installation_method = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (self.work_log_id, route_points_json, self.cable_type,
                 self.cable_cross_section, self.total_length,
                 self.installation_method, self.notes, self.id)
            )

        return self

    def delete(self) -> bool:
        """Delete cable route from database."""
        if self.id:
            rows_affected = delete_record(
                "DELETE FROM cable_routes WHERE id = ?",
                (self.id,)
            )
            return rows_affected > 0
        return False

    @classmethod
    def delete_by_work_log_id(cls, work_log_id: int) -> int:
        """Delete all cable routes for a work log. Returns rows affected."""
        return delete_record(
            "DELETE FROM cable_routes WHERE work_log_id = ?",
            (work_log_id,)
        )

    def add_route_point(self, x: float, y: float, point_type: str = "waypoint") -> None:
        """Add a point to the cable route."""
        point = {
            'x': x,
            'y': y,
            'type': point_type,
            'timestamp': datetime.now().isoformat()
        }

        if not self.route_points:
            self.route_points = []

        self.route_points.append(point)

    def get_start_point(self) -> Optional[Dict[str, float]]:
        """Get the starting point of the cable route."""
        if self.route_points and len(self.route_points) > 0:
            return self.route_points[0]
        return None

    def get_end_point(self) -> Optional[Dict[str, float]]:
        """Get the ending point of the cable route."""
        if self.route_points and len(self.route_points) > 0:
            return self.route_points[-1]
        return None

    def calculate_route_length(self) -> float:
        """Calculate the total length of the route based on points."""
        if not self.route_points or len(self.route_points) < 2:
            return 0.0

        total_length = 0.0
        for i in range(1, len(self.route_points)):
            prev_point = self.route_points[i - 1]
            curr_point = self.route_points[i]

            # Calculate distance between two points
            dx = curr_point['x'] - prev_point['x']
            dy = curr_point['y'] - prev_point['y']
            distance = (dx ** 2 + dy ** 2) ** 0.5
            total_length += distance

        return total_length

    def get_waypoint_count(self) -> int:
        """Get the number of waypoints in the route."""
        return len(self.route_points) if self.route_points else 0

    def validate_route(self) -> List[str]:
        """Validate the cable route and return any issues."""
        issues = []

        if not self.route_points or len(self.route_points) < 2:
            issues.append("Route must have at least 2 points (start and end)")

        if not self.cable_type or self.cable_type.strip() == "":
            issues.append("Cable type is required")

        if self.total_length is not None and self.total_length <= 0:
            issues.append("Total length must be greater than 0")

        # Check for duplicate consecutive points
        if self.route_points and len(self.route_points) > 1:
            for i in range(1, len(self.route_points)):
                prev = self.route_points[i - 1]
                curr = self.route_points[i]
                if prev['x'] == curr['x'] and prev['y'] == curr['y']:
                    issues.append(
                        f"Duplicate consecutive points found at index {i}")

        return issues

    def is_valid(self) -> bool:
        """Check if the cable route is valid."""
        return len(self.validate_route()) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert cable route to dictionary representation."""
        return {
            'id': self.id,
            'work_log_id': self.work_log_id,
            'route_points': self.route_points or [],
            'cable_type': self.cable_type,
            'cable_cross_section': self.cable_cross_section,
            'total_length': self.total_length,
            'installation_method': self.installation_method,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'calculated_length': self.calculate_route_length(),
            'waypoint_count': self.get_waypoint_count(),
            'start_point': self.get_start_point(),
            'end_point': self.get_end_point(),
            'is_valid': self.is_valid(),
            'validation_issues': self.validate_route()
        }

    @classmethod
    def _from_db_row(cls, row) -> 'CableRoute':
        """Create CableRoute instance from database row."""
        route_points = []
        if row.get('route_points'):
            try:
                route_points = json.loads(row['route_points'])
            except (json.JSONDecodeError, TypeError):
                route_points = []

        return cls(
            id=row['id'],
            work_log_id=row['work_log_id'],
            route_points=route_points,
            cable_type=row.get('cable_type', ''),
            cable_cross_section=row.get('cable_cross_section'),
            total_length=row.get('total_length'),
            installation_method=row.get('installation_method', ''),
            notes=row.get('notes', ''),
            created_at=datetime.fromisoformat(
                row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(
                row['updated_at']) if row.get('updated_at') else None
        )

    def __str__(self) -> str:
        return f"CableRoute(id={self.id}, work_log_id={self.work_log_id}, cable_type={self.cable_type})"

    def __repr__(self) -> str:
        return self.__str__()
