"""
Project service for managing projects and worker assignments.
"""

from typing import Dict, Any, Optional, List, Tuple
from app.models.project import Project
from app.models.project_user_assignment import ProjectUserAssignment
from app.models.floor import Floor
from app.models.user import User
from app.models.work_log import WorkLog
from app.models.cable_route import CableRoute
from app.models.assignment import Assignment
from app.models.critical_sector import CriticalSector


class ProjectService:
    """Service for project and worker assignment operations."""

    @staticmethod
    def get_projects_for_user(user_id: int, role: str) -> List[Project]:
        """Get projects for user. Workers get only assigned projects; supervisors get all."""
        if role == 'supervisor':
            return Project.find_all_active()
        if role == 'admin':
            return []  # Admin has no project access - system oversight only
        # Workers: only assigned projects
        project_ids = ProjectUserAssignment.find_projects_for_user(user_id)
        if not project_ids:
            return []
        projects = []
        for pid in project_ids:
            p = Project.find_by_id(pid)
            if p and p.is_active:
                projects.append(p)
        return sorted(projects, key=lambda x: x.name)

    @staticmethod
    def get_project_by_id(project_id: int, user_id: int, role: str) -> Optional[Project]:
        """Get project by ID if user has access."""
        project = Project.find_by_id(project_id)
        if not project:
            return None
        if role == 'supervisor':
            return project
        if ProjectUserAssignment.is_user_assigned(project_id, user_id):
            return project
        return None

    @staticmethod
    def create_project(data: Dict[str, Any], user_id: int) -> Tuple[bool, Optional[Project], str]:
        """Create a new project."""
        name = data.get('name', '').strip()
        if not name:
            return False, None, "Project name is required"
        project = Project(
            name=name,
            description=data.get('description', ''),
            is_active=True,
            created_by=user_id
        )
        project.save()
        return True, project, "Project created successfully"

    @staticmethod
    def update_project(project_id: int, data: Dict[str, Any], user_id: int) -> Tuple[bool, Optional[Project], str]:
        """Update a project."""
        project = Project.find_by_id(project_id)
        if not project:
            return False, None, "Project not found"
        if 'name' in data and data['name']:
            project.name = data['name'].strip()
        if 'description' in data:
            project.description = data.get('description', '')
        if 'is_active' in data:
            project.is_active = bool(data['is_active'])
        project.save()
        return True, project, "Project updated successfully"

    @staticmethod
    def assign_worker(project_id: int, user_id: int, assigned_by: int) -> Tuple[bool, str]:
        """Assign a worker to a project."""
        project = Project.find_by_id(project_id)
        if not project:
            return False, "Project not found"
        user = User.find_by_id(user_id)
        if not user:
            return False, "User not found"
        if user.role != 'worker':
            return False, "Can only assign workers to projects"
        ProjectUserAssignment.assign(project_id, user_id, assigned_by)
        return True, "Worker assigned to project"

    @staticmethod
    def unassign_worker(project_id: int, user_id: int) -> Tuple[bool, str]:
        """Unassign a worker from a project."""
        project = Project.find_by_id(project_id)
        if not project:
            return False, "Project not found"
        ProjectUserAssignment.unassign(project_id, user_id)
        return True, "Worker unassigned from project"

    @staticmethod
    def get_workers_for_project(project_id: int) -> List[Dict[str, Any]]:
        """Get workers assigned to a project."""
        return ProjectUserAssignment.find_workers_for_project(project_id)

    @staticmethod
    def delete_project(
        project_id: int, user_id: int
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Delete project with full cascade. Creates compressed backup first.
        Supervisor only.

        Returns:
            Tuple of (success, message, backup_filename or None)
        """
        try:
            from flask import current_app
            from app.services.project_backup_service import ProjectBackupService
            from app.services.tile_service import TileService

            user = User.find_by_id(user_id)
            if not user or user.role not in ("supervisor", "admin"):
                return False, "Supervisor or admin permissions required to delete projects", None

            project = Project.find_by_id(project_id)
            if not project:
                return False, "Project not found", None

            floor_plans_dir = current_app.config.get(
                "FLOOR_PLANS_DIR", "floor-plans"
            )
            backups_dir = current_app.config.get(
                "PROJECT_BACKUPS_DIR", "project-backups"
            )

            success, msg, backup_name = ProjectBackupService.create_backup(
                project_id, floor_plans_dir, backups_dir
            )
            if not success:
                return False, msg, None

            # Cascade delete (reverse dependency order)
            floors = Floor.find_all(project_id=project_id)
            for floor in floors:
                work_logs = WorkLog.find_by_floor_id(floor.id)
                for wl in work_logs:
                    CableRoute.delete_by_work_log_id(wl.id)
                    Assignment.delete_by_work_log_id(wl.id)
                WorkLog.delete_by_floor_id(floor.id)
                CriticalSector.delete_by_floor_id(floor.id)
                try:
                    TileService.clear_tile_cache(floor.id)
                except Exception as te:
                    print(f"Warning: could not clear tiles for floor {floor.id}: {te}")
            Floor.delete_by_project_id(project_id)
            ProjectUserAssignment.delete_by_project_id(project_id)
            project.delete()

            return True, f"Project deleted. Backup: {backup_name}", backup_name
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Failed to delete project: {str(e)}", None
