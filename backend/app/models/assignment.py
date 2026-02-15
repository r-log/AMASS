"""
Assignment model for work assignments and task management.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.database.connection import execute_query, insert_and_get_id, update_record, delete_record


@dataclass
class Assignment:
    """Assignment entity for managing work tasks assigned to workers."""

    id: Optional[int] = None
    work_log_id: Optional[int] = None
    assigned_to: int = 0
    assigned_by: int = 0
    due_date: Optional[str] = None
    status: str = "pending"
    notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Enriched fields from work_log/floors join (for map navigation)
    floor_id: Optional[int] = None
    project_id: Optional[int] = None
    x_coord: Optional[float] = None
    y_coord: Optional[float] = None
    floor_name: Optional[str] = None
    work_type: Optional[str] = None
    work_description: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_by_name: Optional[str] = None

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the work_assignments table."""
        return """
        CREATE TABLE IF NOT EXISTS work_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_log_id INTEGER,
            assigned_to INTEGER NOT NULL,
            assigned_by INTEGER NOT NULL,
            due_date TEXT,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (work_log_id) REFERENCES work_logs (id),
            FOREIGN KEY (assigned_to) REFERENCES users (id),
            FOREIGN KEY (assigned_by) REFERENCES users (id)
        )
        """

    @classmethod
    def find_by_id(cls, assignment_id: int) -> Optional['Assignment']:
        """Find assignment by ID."""
        assignment_data = execute_query(
            """SELECT wa.*, 
                      wl.work_type, wl.description as work_description, wl.floor_id,
                      wl.x_coord, wl.y_coord,
                      f.name as floor_name, f.project_id,
                      u1.full_name as assigned_to_name,
                      u2.full_name as assigned_by_name
               FROM work_assignments wa
               LEFT JOIN work_logs wl ON wa.work_log_id = wl.id
               LEFT JOIN floors f ON wl.floor_id = f.id
               LEFT JOIN users u1 ON wa.assigned_to = u1.id
               LEFT JOIN users u2 ON wa.assigned_by = u2.id
               WHERE wa.id = ?""",
            (assignment_id,),
            fetch_one=True
        )

        if assignment_data:
            return cls._from_db_row(assignment_data)
        return None

    @classmethod
    def find_by_user_id(cls, user_id: int, status_filter: Optional[str] = None) -> List['Assignment']:
        """Find assignments for a specific user."""
        query = """
            SELECT wa.*, 
                   wl.work_type, wl.description as work_description, wl.floor_id,
                   wl.x_coord, wl.y_coord,
                   f.name as floor_name, f.project_id,
                   u1.full_name as assigned_to_name,
                   u2.full_name as assigned_by_name
            FROM work_assignments wa
            LEFT JOIN work_logs wl ON wa.work_log_id = wl.id
            LEFT JOIN floors f ON wl.floor_id = f.id
            LEFT JOIN users u1 ON wa.assigned_to = u1.id
            LEFT JOIN users u2 ON wa.assigned_by = u2.id
            WHERE wa.assigned_to = ?
        """
        params = [user_id]

        if status_filter:
            query += " AND wa.status = ?"
            params.append(status_filter)

        query += " ORDER BY wa.due_date ASC, wa.created_at DESC"

        assignments_data = execute_query(query, tuple(params))
        return [cls._from_db_row(row) for row in assignments_data]

    @classmethod
    def find_by_assigned_by(cls, assigned_by_id: int) -> List['Assignment']:
        """Find assignments created by a specific user."""
        assignments_data = execute_query(
            """SELECT wa.*, 
                      wl.work_type, wl.description as work_description, wl.floor_id,
                      wl.x_coord, wl.y_coord,
                      f.name as floor_name, f.project_id,
                      u1.full_name as assigned_to_name,
                      u2.full_name as assigned_by_name
               FROM work_assignments wa
               LEFT JOIN work_logs wl ON wa.work_log_id = wl.id
               LEFT JOIN floors f ON wl.floor_id = f.id
               LEFT JOIN users u1 ON wa.assigned_to = u1.id
               LEFT JOIN users u2 ON wa.assigned_by = u2.id
               WHERE wa.assigned_by = ?
               ORDER BY wa.due_date ASC, wa.created_at DESC""",
            (assigned_by_id,)
        )

        return [cls._from_db_row(row) for row in assignments_data]

    @classmethod
    def find_by_status(cls, status: str) -> List['Assignment']:
        """Find assignments by status."""
        assignments_data = execute_query(
            """SELECT wa.*, 
                      wl.work_type, wl.description as work_description, wl.floor_id,
                      wl.x_coord, wl.y_coord,
                      f.name as floor_name, f.project_id,
                      u1.full_name as assigned_to_name,
                      u2.full_name as assigned_by_name
               FROM work_assignments wa
               LEFT JOIN work_logs wl ON wa.work_log_id = wl.id
               LEFT JOIN floors f ON wl.floor_id = f.id
               LEFT JOIN users u1 ON wa.assigned_to = u1.id
               LEFT JOIN users u2 ON wa.assigned_by = u2.id
               WHERE wa.status = ?
               ORDER BY wa.due_date ASC, wa.created_at DESC""",
            (status,)
        )

        return [cls._from_db_row(row) for row in assignments_data]

    @classmethod
    def find_by_project_id(cls, project_id: int, limit: Optional[int] = None) -> List['Assignment']:
        """Find assignments for work logs on floors in a project (excludes assignments without work_log)."""
        query = """
            SELECT wa.*,
                   wl.work_type, wl.description as work_description, wl.floor_id,
                   wl.x_coord, wl.y_coord,
                   f.name as floor_name, f.project_id,
                   u1.full_name as assigned_to_name,
                   u2.full_name as assigned_by_name
            FROM work_assignments wa
            INNER JOIN work_logs wl ON wa.work_log_id = wl.id
            INNER JOIN floors f ON wl.floor_id = f.id
            LEFT JOIN users u1 ON wa.assigned_to = u1.id
            LEFT JOIN users u2 ON wa.assigned_by = u2.id
            WHERE f.project_id = ?
            ORDER BY wa.due_date ASC, wa.created_at DESC
        """
        params = (project_id,)
        if limit:
            query += " LIMIT ?"
            params = (project_id, limit)
        assignments_data = execute_query(query, params)
        return [cls._from_db_row(row) for row in assignments_data]

    @classmethod
    def find_all(cls, limit: Optional[int] = None) -> List['Assignment']:
        """Get all assignments with optional limit."""
        query = """
            SELECT wa.*, 
                   wl.work_type, wl.description as work_description, wl.floor_id,
                   wl.x_coord, wl.y_coord,
                   f.name as floor_name, f.project_id,
                   u1.full_name as assigned_to_name,
                   u2.full_name as assigned_by_name
            FROM work_assignments wa
            LEFT JOIN work_logs wl ON wa.work_log_id = wl.id
            LEFT JOIN floors f ON wl.floor_id = f.id
            LEFT JOIN users u1 ON wa.assigned_to = u1.id
            LEFT JOIN users u2 ON wa.assigned_by = u2.id
            ORDER BY wa.due_date ASC, wa.created_at DESC
        """
        params = ()

        if limit:
            query += " LIMIT ?"
            params = (limit,)

        assignments_data = execute_query(query, params)
        return [cls._from_db_row(row) for row in assignments_data]

    @classmethod
    def get_overdue_assignments(cls) -> List['Assignment']:
        """Get assignments that are past due date."""
        assignments_data = execute_query(
            """SELECT wa.*, 
                      wl.work_type, wl.description as work_description, wl.floor_id,
                      wl.x_coord, wl.y_coord,
                      f.name as floor_name, f.project_id,
                      u1.full_name as assigned_to_name,
                      u2.full_name as assigned_by_name
               FROM work_assignments wa
               LEFT JOIN work_logs wl ON wa.work_log_id = wl.id
               LEFT JOIN floors f ON wl.floor_id = f.id
               LEFT JOIN users u1 ON wa.assigned_to = u1.id
               LEFT JOIN users u2 ON wa.assigned_by = u2.id
               WHERE wa.due_date < date('now') AND wa.status != 'completed'
               ORDER BY wa.due_date ASC""")

        return [cls._from_db_row(row) for row in assignments_data]

    @classmethod
    def get_assignments_due_soon(cls, days: int = 3) -> List['Assignment']:
        """Get assignments due within specified number of days."""
        assignments_data = execute_query(
            f"""SELECT wa.*, 
                       wl.work_type, wl.description as work_description, wl.floor_id,
                       wl.x_coord, wl.y_coord,
                       f.name as floor_name, f.project_id,
                       u1.full_name as assigned_to_name,
                       u2.full_name as assigned_by_name
                FROM work_assignments wa
                LEFT JOIN work_logs wl ON wa.work_log_id = wl.id
                LEFT JOIN floors f ON wl.floor_id = f.id
                LEFT JOIN users u1 ON wa.assigned_to = u1.id
                LEFT JOIN users u2 ON wa.assigned_by = u2.id
                WHERE wa.due_date <= date('now', '+{days} days') 
                AND wa.status != 'completed'
                ORDER BY wa.due_date ASC""")

        return [cls._from_db_row(row) for row in assignments_data]

    @classmethod
    def get_status_counts(cls) -> Dict[str, int]:
        """Get count of assignments by status."""
        counts_data = execute_query("""
            SELECT status, COUNT(*) as count
            FROM work_assignments
            GROUP BY status
        """)

        return {row['status']: row['count'] for row in counts_data}

    def save(self) -> 'Assignment':
        """Save assignment to database."""
        if self.id is None:
            # Create new assignment
            self.id = insert_and_get_id(
                """INSERT INTO work_assignments 
                   (work_log_id, assigned_to, assigned_by, due_date, status, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (self.work_log_id, self.assigned_to, self.assigned_by,
                 self.due_date, self.status, self.notes)
            )
        else:
            # Update existing assignment
            update_record(
                """UPDATE work_assignments 
                   SET work_log_id = ?, assigned_to = ?, assigned_by = ?, 
                       due_date = ?, status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (self.work_log_id, self.assigned_to, self.assigned_by,
                 self.due_date, self.status, self.notes, self.id)
            )

        return self

    def update_status(self, new_status: str) -> None:
        """Update assignment status."""
        if self.id:
            self.status = new_status
            update_record(
                "UPDATE work_assignments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, self.id)
            )

    def complete(self) -> None:
        """Mark assignment as completed."""
        self.update_status('completed')

    def cancel(self) -> None:
        """Mark assignment as cancelled."""
        self.update_status('cancelled')

    def is_overdue(self) -> bool:
        """Check if assignment is overdue."""
        if not self.due_date or self.status == 'completed':
            return False

        from datetime import date
        try:
            due = date.fromisoformat(self.due_date)
            return due < date.today()
        except:
            return False

    def is_due_soon(self, days: int = 3) -> bool:
        """Check if assignment is due within specified days."""
        if not self.due_date or self.status == 'completed':
            return False

        from datetime import date, timedelta
        try:
            due = date.fromisoformat(self.due_date)
            return due <= date.today() + timedelta(days=days)
        except:
            return False

    def delete(self) -> bool:
        """Delete assignment from database."""
        if self.id:
            rows_affected = delete_record(
                "DELETE FROM work_assignments WHERE id = ?",
                (self.id,)
            )
            return rows_affected > 0
        return False

    @classmethod
    def delete_by_work_log_id(cls, work_log_id: int) -> int:
        """Delete all assignments for a work log. Returns rows affected."""
        return delete_record(
            "DELETE FROM work_assignments WHERE work_log_id = ?",
            (work_log_id,)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert assignment to dictionary representation."""
        result = {
            'id': self.id,
            'work_log_id': self.work_log_id,
            'assigned_to': self.assigned_to,
            'assigned_by': self.assigned_by,
            'due_date': self.due_date,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_overdue': self.is_overdue(),
            'is_due_soon': self.is_due_soon()
        }
        # Enriched fields for map navigation and display
        if self.floor_id is not None:
            result['floor_id'] = self.floor_id
        if self.project_id is not None:
            result['project_id'] = self.project_id
        if self.x_coord is not None:
            result['x_coord'] = self.x_coord
        if self.y_coord is not None:
            result['y_coord'] = self.y_coord
        if self.floor_name is not None:
            result['floor_name'] = self.floor_name
        if self.work_type is not None:
            result['work_type'] = self.work_type
        if self.work_description is not None:
            result['work_description'] = self.work_description
            result['description'] = self.work_description  # Alias for frontend
        if self.assigned_to_name is not None:
            result['assigned_to_name'] = self.assigned_to_name
        if self.assigned_by_name is not None:
            result['assigned_by_name'] = self.assigned_by_name
        return result

    @classmethod
    def _from_db_row(cls, row) -> 'Assignment':
        """Create Assignment instance from database row."""
        return cls(
            id=row['id'],
            work_log_id=row.get('work_log_id'),
            assigned_to=row['assigned_to'],
            assigned_by=row['assigned_by'],
            due_date=row.get('due_date'),
            status=row['status'],
            notes=row.get('notes', ''),
            created_at=datetime.fromisoformat(
                row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(
                row['updated_at']) if row.get('updated_at') else None,
            floor_id=row.get('floor_id'),
            project_id=row.get('project_id'),
            x_coord=row.get('x_coord'),
            y_coord=row.get('y_coord'),
            floor_name=row.get('floor_name'),
            work_type=row.get('work_type'),
            work_description=row.get('work_description'),
            assigned_to_name=row.get('assigned_to_name'),
            assigned_by_name=row.get('assigned_by_name')
        )

    def __str__(self) -> str:
        return f"Assignment(id={self.id}, assigned_to={self.assigned_to}, status={self.status})"

    def __repr__(self) -> str:
        return self.__str__()
