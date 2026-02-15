"""
Project backup service - creates compressed backups before project deletion.
"""

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.database.connection import execute_query
from app.models.project import Project
from app.models.project_user_assignment import ProjectUserAssignment
from app.models.floor import Floor
from app.models.work_log import WorkLog
from app.models.cable_route import CableRoute
from app.models.critical_sector import CriticalSector
from app.models.assignment import Assignment


def _serialize_obj(obj: Any) -> Any:
    """Convert object to JSON-serializable form."""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_obj(x) for x in obj]
    return obj


def _row_to_dict(row, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convert DB row to dict, excluding certain keys."""
    exclude = exclude or []
    try:
        d = dict(row) if not isinstance(row, dict) else row.copy()
    except (TypeError, ValueError):
        d = {k: row[k] for k in row.keys()} if hasattr(row, "keys") else {}
    for k in exclude:
        d.pop(k, None)
    return _serialize_obj(d)


class ProjectBackupService:
    """Service for creating project backups before cascade delete."""

    @staticmethod
    def create_backup(
        project_id: int,
        floor_plans_dir: str,
        backups_dir: str,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a compressed backup of project and all related data.

        Returns:
            Tuple of (success, message, backup_filename or None)
        """
        try:
            project = Project.find_by_id(project_id)
            if not project:
                return False, "Project not found", None

            # Collect all data (include inactive for full backup)
            floors = Floor.find_all(project_id=project_id)
            floor_ids = [f.id for f in floors]
            work_logs = WorkLog.find_by_project_id(project_id) if floor_ids else []
            cable_routes = []
            for wl in work_logs:
                cr = CableRoute.find_by_work_log_id(wl.id)
                if cr:
                    cable_routes.append(cr)
            critical_sectors = CriticalSector.find_by_project_id(
                project_id, active_only=False
            )
            assignments = Assignment.find_by_project_id(project_id)
            pua_data = []
            for row in (
                execute_query(
                    "SELECT * FROM project_user_assignments WHERE project_id = ?",
                    (project_id,),
                )
                or []
            ):
                pua_data.append(_row_to_dict(row))

            # Build backup payload
            payload = {
                "project": _serialize_obj(project.to_dict()),
                "project_user_assignments": pua_data,
                "floors": [_serialize_obj(f.to_dict()) for f in floors],
                "work_logs": [_serialize_obj(wl.to_dict()) for wl in work_logs],
                "cable_routes": [
                    _serialize_obj(
                        {
                            "id": cr.id,
                            "work_log_id": cr.work_log_id,
                            "route_points": cr.route_points,
                            "cable_type": cr.cable_type,
                            "cable_cross_section": cr.cable_cross_section,
                            "total_length": cr.total_length,
                            "installation_method": cr.installation_method,
                            "notes": cr.notes,
                            "created_at": cr.created_at.isoformat()
                            if cr.created_at
                            else None,
                            "updated_at": cr.updated_at.isoformat()
                            if cr.updated_at
                            else None,
                        }
                    )
                    for cr in cable_routes
                ],
                "critical_sectors": [
                    _serialize_obj(s.to_dict()) for s in critical_sectors
                ],
                "assignments": [
                    _serialize_obj(a.to_dict()) for a in assignments
                ],
            }

            # Manifest
            sanitized_name = "".join(
                c if c.isalnum() or c in " -_" else "_"
                for c in project.name
            ).strip()[:50]
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            manifest = {
                "version": 1,
                "backup_type": "project",
                "created_at": datetime.now().isoformat(),
                "project_id": project_id,
                "project_name": project.name,
                "tables": [
                    "project",
                    "project_user_assignments",
                    "floors",
                    "work_logs",
                    "cable_routes",
                    "critical_sectors",
                    "assignments",
                ],
                "floor_plan_files": [
                    f.image_path for f in floors if f.image_path
                ],
            }

            # Ensure backups directory exists
            backups_path = Path(backups_dir)
            backups_path.mkdir(parents=True, exist_ok=True)

            zip_filename = f"project-{project_id}-{sanitized_name}-{ts}.zip"
            zip_path = backups_path / zip_filename

            floor_plans_path = Path(floor_plans_dir)

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))
                zf.writestr("project.json", json.dumps(payload["project"]))
                zf.writestr(
                    "project_user_assignments.json",
                    json.dumps(payload["project_user_assignments"], indent=2),
                )
                zf.writestr(
                    "floors.json",
                    json.dumps(payload["floors"], indent=2),
                )
                zf.writestr(
                    "work_logs.json",
                    json.dumps(payload["work_logs"], indent=2),
                )
                zf.writestr(
                    "cable_routes.json",
                    json.dumps(payload["cable_routes"], indent=2),
                )
                zf.writestr(
                    "critical_sectors.json",
                    json.dumps(payload["critical_sectors"], indent=2),
                )
                zf.writestr(
                    "assignments.json",
                    json.dumps(payload["assignments"], indent=2),
                )
                # Add floor plan files (one per floor: prefer image_path, else floor-{id}.ext)
                for f in floors:
                    if f.image_path and f.image_path != "placeholder.pdf":
                        src = floor_plans_path / f.image_path
                        if src.exists():
                            zf.write(src, f"floor-plans/{f.image_path}")
                            continue
                    for ext in ["pdf", "png", "jpg", "jpeg"]:
                        alt = floor_plans_path / f"floor-{f.id}.{ext}"
                        if alt.exists():
                            zf.write(alt, f"floor-plans/floor-{f.id}.{ext}")
                            break

            return True, f"Backup created: {zip_filename}", zip_filename

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Failed to create backup: {str(e)}", None
