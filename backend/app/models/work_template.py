"""
Work template model for predefined work types and templates.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
from app.database.connection import execute_query, insert_and_get_id, update_record, delete_record


@dataclass
class WorkTemplate:
    """Work template entity for predefined work configurations."""

    id: Optional[int] = None
    name: str = ""
    work_type: str = ""
    description: str = ""
    estimated_hours: Optional[float] = None
    required_materials: List[Dict[str, Any]] = None
    instructions: str = ""
    safety_notes: str = ""
    is_active: bool = True
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.required_materials is None:
            self.required_materials = []

    @classmethod
    def create_table(cls) -> str:
        """Get SQL for creating the work_templates table."""
        return """
        CREATE TABLE IF NOT EXISTS work_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            work_type TEXT NOT NULL,
            description TEXT,
            estimated_hours REAL,
            required_materials TEXT,
            instructions TEXT,
            safety_notes TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
        """

    @classmethod
    def find_by_id(cls, template_id: int) -> Optional['WorkTemplate']:
        """Find work template by ID."""
        template_data = execute_query(
            """SELECT wt.*, u.full_name as created_by_name
               FROM work_templates wt
               LEFT JOIN users u ON wt.created_by = u.id
               WHERE wt.id = ?""",
            (template_id,),
            fetch_one=True
        )

        if template_data:
            return cls._from_db_row(template_data)
        return None

    @classmethod
    def find_by_work_type(cls, work_type: str, active_only: bool = True) -> List['WorkTemplate']:
        """Find work templates by work type."""
        query = """
            SELECT wt.*, u.full_name as created_by_name
            FROM work_templates wt
            LEFT JOIN users u ON wt.created_by = u.id
            WHERE wt.work_type = ?
        """
        params = [work_type]

        if active_only:
            query += " AND wt.is_active = 1"

        query += " ORDER BY wt.name"

        templates_data = execute_query(query, tuple(params))
        return [cls._from_db_row(row) for row in templates_data]

    @classmethod
    def find_all_active(cls) -> List['WorkTemplate']:
        """Get all active work templates."""
        templates_data = execute_query(
            """SELECT wt.*, u.full_name as created_by_name
               FROM work_templates wt
               LEFT JOIN users u ON wt.created_by = u.id
               WHERE wt.is_active = 1
               ORDER BY wt.work_type, wt.name"""
        )

        return [cls._from_db_row(row) for row in templates_data]

    @classmethod
    def find_all(cls) -> List['WorkTemplate']:
        """Get all work templates."""
        templates_data = execute_query(
            """SELECT wt.*, u.full_name as created_by_name
               FROM work_templates wt
               LEFT JOIN users u ON wt.created_by = u.id
               ORDER BY wt.work_type, wt.name"""
        )

        return [cls._from_db_row(row) for row in templates_data]

    @classmethod
    def search_templates(cls, search_term: str, active_only: bool = True) -> List['WorkTemplate']:
        """Search work templates by name, work type, or description."""
        query = """
            SELECT wt.*, u.full_name as created_by_name
            FROM work_templates wt
            LEFT JOIN users u ON wt.created_by = u.id
            WHERE (wt.name LIKE ? OR wt.work_type LIKE ? OR wt.description LIKE ?)
        """
        search_pattern = f"%{search_term}%"
        params = [search_pattern, search_pattern, search_pattern]

        if active_only:
            query += " AND wt.is_active = 1"

        query += " ORDER BY wt.name"

        templates_data = execute_query(query, tuple(params))
        return [cls._from_db_row(row) for row in templates_data]

    @classmethod
    def get_work_type_stats(cls) -> List[Dict[str, Any]]:
        """Get statistics by work type."""
        stats_data = execute_query("""
            SELECT work_type, COUNT(*) as count
            FROM work_templates
            WHERE is_active = 1
            GROUP BY work_type
            ORDER BY count DESC
        """)
        return [
            {
                'work_type': row['work_type'],
                'count': row['count']
            }
            for row in stats_data
        ]

    @classmethod
    def get_most_used_templates(cls, limit: int = 10) -> List['WorkTemplate']:
        """Get most frequently used templates based on work log usage."""
        query = """
            SELECT wt.*, u.full_name as created_by_name, COUNT(wl.id) as usage_count
            FROM work_templates wt
            LEFT JOIN users u ON wt.created_by = u.id
            LEFT JOIN work_logs wl ON wt.work_type = wl.work_type
            WHERE wt.is_active = 1
            GROUP BY wt.id
            ORDER BY usage_count DESC, wt.name
            LIMIT ?
        """

        templates_data = execute_query(query, (limit,))
        return [cls._from_db_row(row) for row in templates_data]

    @classmethod
    def create_default_templates(cls) -> List['WorkTemplate']:
        """Create default work templates for common electrical work."""
        default_templates = [
            {
                'name': 'Outlet Installation',
                'work_type': 'Installation',
                'description': 'Install standard electrical outlet',
                'estimated_hours': 1.0,
                'required_materials': [
                    {'item': 'Outlet receptacle', 'quantity': 1, 'unit': 'piece'},
                    {'item': 'Wire nuts', 'quantity': 3, 'unit': 'pieces'},
                    {'item': 'Electrical wire', 'quantity': 10, 'unit': 'feet'}
                ],
                'instructions': '1. Turn off power at circuit breaker\n2. Run cable to location\n3. Install outlet box\n4. Connect wires\n5. Install outlet\n6. Test operation',
                'safety_notes': 'Always verify power is off before working. Use proper PPE.'
            },
            {
                'name': 'Light Switch Installation',
                'work_type': 'Installation',
                'description': 'Install single pole light switch',
                'estimated_hours': 0.75,
                'required_materials': [
                    {'item': 'Light switch', 'quantity': 1, 'unit': 'piece'},
                    {'item': 'Wire nuts', 'quantity': 2, 'unit': 'pieces'},
                    {'item': 'Switch plate', 'quantity': 1, 'unit': 'piece'}
                ],
                'instructions': '1. Turn off power\n2. Remove old switch if replacing\n3. Connect hot wire to switch\n4. Connect neutral and ground\n5. Install switch and plate\n6. Test operation',
                'safety_notes': 'Verify power is off with voltage tester.'
            },
            {
                'name': 'Circuit Breaker Replacement',
                'work_type': 'Repair',
                'description': 'Replace faulty circuit breaker',
                'estimated_hours': 1.5,
                'required_materials': [
                    {'item': 'Circuit breaker', 'quantity': 1, 'unit': 'piece'}
                ],
                'instructions': '1. Turn off main breaker\n2. Remove panel cover\n3. Disconnect wires from old breaker\n4. Remove old breaker\n5. Install new breaker\n6. Reconnect wires\n7. Test circuit',
                'safety_notes': 'Work with main power off. Check for proper breaker amperage rating.'
            },
            {
                'name': 'Cable Pull',
                'work_type': 'Installation',
                'description': 'Pull cable through conduit or walls',
                'estimated_hours': 2.0,
                'required_materials': [
                    {'item': 'Electrical cable', 'quantity': 100, 'unit': 'feet'},
                    {'item': 'Fish tape', 'quantity': 1, 'unit': 'piece'},
                    {'item': 'Cable lubricant', 'quantity': 1, 'unit': 'bottle'}
                ],
                'instructions': '1. Measure cable run\n2. Set up pull boxes\n3. Feed fish tape\n4. Attach cable to tape\n5. Pull cable through\n6. Secure cable at ends',
                'safety_notes': 'Be careful with fish tape around electrical equipment.'
            }
        ]

        created_templates = []
        for template_data in default_templates:
            template = cls(
                name=template_data['name'],
                work_type=template_data['work_type'],
                description=template_data['description'],
                estimated_hours=template_data['estimated_hours'],
                required_materials=template_data['required_materials'],
                instructions=template_data['instructions'],
                safety_notes=template_data['safety_notes']
            )
            created_templates.append(template.save())

        return created_templates

    def save(self) -> 'WorkTemplate':
        """Save work template to database."""
        materials_json = json.dumps(
            self.required_materials) if self.required_materials else "[]"

        if self.id is None:
            # Create new work template
            self.id = insert_and_get_id(
                """INSERT INTO work_templates 
                   (name, work_type, description, estimated_hours, required_materials,
                    instructions, safety_notes, is_active, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.name, self.work_type, self.description, self.estimated_hours,
                 materials_json, self.instructions, self.safety_notes,
                 self.is_active, self.created_by)
            )
        else:
            # Update existing work template
            update_record(
                """UPDATE work_templates 
                   SET name = ?, work_type = ?, description = ?, estimated_hours = ?,
                       required_materials = ?, instructions = ?, safety_notes = ?,
                       is_active = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (self.name, self.work_type, self.description, self.estimated_hours,
                 materials_json, self.instructions, self.safety_notes,
                 self.is_active, self.id)
            )

        return self

    def deactivate(self) -> None:
        """Deactivate work template."""
        if self.id:
            self.is_active = False
            update_record(
                "UPDATE work_templates SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (self.id,)
            )

    def activate(self) -> None:
        """Activate work template."""
        if self.id:
            self.is_active = True
            update_record(
                "UPDATE work_templates SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (self.id,)
            )

    def delete_permanently(self) -> bool:
        """Permanently delete work template from database."""
        if self.id:
            rows_affected = delete_record(
                "DELETE FROM work_templates WHERE id = ?",
                (self.id,)
            )
            return rows_affected > 0
        return False

    def add_material(self, item: str, quantity: float, unit: str, notes: str = "") -> None:
        """Add a required material to the template."""
        material = {
            'item': item,
            'quantity': quantity,
            'unit': unit,
            'notes': notes
        }

        if not self.required_materials:
            self.required_materials = []

        self.required_materials.append(material)

    def remove_material(self, item: str) -> bool:
        """Remove a material from the required materials list."""
        if not self.required_materials:
            return False

        original_count = len(self.required_materials)
        self.required_materials = [
            m for m in self.required_materials if m.get('item') != item]
        return len(self.required_materials) < original_count

    def get_total_estimated_cost(self, material_costs: Dict[str, float] = None) -> float:
        """Calculate estimated total material cost if costs are provided."""
        if not self.required_materials or not material_costs:
            return 0.0

        total_cost = 0.0
        for material in self.required_materials:
            item = material.get('item', '')
            quantity = material.get('quantity', 0)
            unit_cost = material_costs.get(item, 0)
            total_cost += quantity * unit_cost

        return total_cost

    def get_material_list_text(self) -> str:
        """Get formatted text list of required materials."""
        if not self.required_materials:
            return "No materials specified"

        lines = []
        for material in self.required_materials:
            item = material.get('item', 'Unknown item')
            quantity = material.get('quantity', 0)
            unit = material.get('unit', 'units')
            notes = material.get('notes', '')

            line = f"• {quantity} {unit} of {item}"
            if notes:
                line += f" ({notes})"
            lines.append(line)

        return '\n'.join(lines)

    def validate_template(self) -> List[str]:
        """Validate the work template and return any issues."""
        issues = []

        if not self.name or self.name.strip() == "":
            issues.append("Template name is required")

        if not self.work_type or self.work_type.strip() == "":
            issues.append("Work type is required")

        if self.estimated_hours is not None and self.estimated_hours <= 0:
            issues.append("Estimated hours must be greater than 0")

        if self.required_materials:
            for i, material in enumerate(self.required_materials):
                if not material.get('item'):
                    issues.append(f"Material {i+1} is missing item name")
                if not isinstance(material.get('quantity'), (int, float)) or material.get('quantity', 0) <= 0:
                    issues.append(
                        f"Material {i+1} must have a valid quantity greater than 0")
                if not material.get('unit'):
                    issues.append(
                        f"Material {i+1} is missing unit specification")

        return issues

    def is_valid(self) -> bool:
        """Check if the work template is valid."""
        return len(self.validate_template()) == 0

    def duplicate(self, new_name: str, created_by: Optional[int] = None) -> 'WorkTemplate':
        """Create a duplicate of this template with a new name."""
        duplicate_template = WorkTemplate(
            name=new_name,
            work_type=self.work_type,
            description=self.description,
            estimated_hours=self.estimated_hours,
            required_materials=self.required_materials.copy() if self.required_materials else [],
            instructions=self.instructions,
            safety_notes=self.safety_notes,
            is_active=True,
            created_by=created_by or self.created_by
        )

        return duplicate_template.save()

    def to_dict(self) -> Dict[str, Any]:
        """Convert work template to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'work_type': self.work_type,
            'description': self.description,
            'estimated_hours': self.estimated_hours,
            'required_materials': self.required_materials or [],
            'instructions': self.instructions,
            'safety_notes': self.safety_notes,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'material_list_text': self.get_material_list_text(),
            'is_valid': self.is_valid(),
            'validation_issues': self.validate_template()
        }

    @classmethod
    def _from_db_row(cls, row) -> 'WorkTemplate':
        """Create WorkTemplate instance from database row."""
        required_materials = []
        if row.get('required_materials'):
            try:
                required_materials = json.loads(row['required_materials'])
            except (json.JSONDecodeError, TypeError):
                required_materials = []

        return cls(
            id=row['id'],
            name=row['name'],
            work_type=row['work_type'],
            description=row.get('description', ''),
            estimated_hours=row.get('estimated_hours'),
            required_materials=required_materials,
            instructions=row.get('instructions', ''),
            safety_notes=row.get('safety_notes', ''),
            is_active=bool(row.get('is_active', True)),
            created_by=row.get('created_by'),
            created_at=datetime.fromisoformat(
                row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(
                row['updated_at']) if row.get('updated_at') else None
        )

    def __str__(self) -> str:
        return f"WorkTemplate(id={self.id}, name={self.name}, work_type={self.work_type})"

    def __repr__(self) -> str:
        return self.__str__()
