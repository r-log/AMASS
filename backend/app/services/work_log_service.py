"""
Work log service for managing electrical work logs and related operations.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date

from app.models.work_log import WorkLog
from app.utils.result import ServiceResult
from app.models.user import User
from app.models.floor import Floor
from app.models.critical_sector import CriticalSector
from app.models.cable_route import CableRoute
from app.models.notification import Notification

logger = logging.getLogger(__name__)


class WorkLogService:
    """Service for managing work logs and related business logic."""

    @staticmethod
    def create_work_log(data: Dict[str, Any], user_id: int) -> ServiceResult:
        """
        Create a new work log with validation and business logic.
        """
        try:
            # Validate required fields
            required_fields = ['floor_id', 'x_coord',
                               'y_coord', 'work_date', 'work_type']
            for field in required_fields:
                if field not in data or data[field] is None:
                    return ServiceResult.fail(f"Missing required field: {field}")

            # Validate floor exists
            floor = Floor.find_by_id(data['floor_id'])
            if not floor:
                return ServiceResult.fail("Floor not found")

            # Get user info
            user = User.find_by_id(user_id)
            if not user:
                return ServiceResult.fail("User not found")

            # Create work log
            work_log = WorkLog(
                floor_id=data['floor_id'],
                worker_id=user_id,
                x_coord=float(data['x_coord']),
                y_coord=float(data['y_coord']),
                work_date=data['work_date'],
                worker_name=user.full_name,
                work_type=data['work_type'],
                job_type=data.get('job_type'),
                description=data.get('description', ''),
                cable_type=data.get('cable_type'),
                cable_meters=data.get('cable_meters'),
                start_x=data.get('start_x'),
                start_y=data.get('start_y'),
                end_x=data.get('end_x'),
                end_y=data.get('end_y'),
                hours_worked=data.get('hours_worked'),
                status=data.get('status', 'completed'),
                priority=data.get('priority', 'medium')
            )

            work_log.save()

            # Handle cable route if provided
            if data.get('route_points') and work_log.id:
                cable_route = CableRoute(
                    work_log_id=work_log.id,
                    route_points=data['route_points'],
                    cable_type=data.get('cable_type'),
                    cable_cross_section=data.get('cable_cross_section'),
                    total_length=data.get('cable_meters'),
                    installation_method=data.get('installation_method', ''),
                    notes=data.get('route_notes', '')
                )
                cable_route.save()

            # Check for critical sector alerts
            if work_log.id:
                WorkLogService._check_critical_sector_alerts(work_log)

            return ServiceResult.ok(work_log, "Work log created successfully")

        except Exception as e:
            return ServiceResult.fail(f"Failed to create work log: {str(e)}")

    @staticmethod
    def update_work_log(log_id: int, data: Dict[str, Any], user_id: int) -> ServiceResult:
        """Update an existing work log with permission checks."""
        try:
            work_log = WorkLog.find_by_id(log_id)
            if not work_log:
                return ServiceResult.fail("Work log not found")

            user = User.find_by_id(user_id)
            if not user:
                return ServiceResult.fail("User not found")

            # Check permissions
            if not user.can_edit_any_log() and work_log.worker_id != user_id:
                return ServiceResult.fail("Insufficient permissions to edit this work log")

            # Update fields
            updateable_fields = [
                'x_coord', 'y_coord', 'work_date', 'work_type', 'job_type',
                'description', 'cable_type', 'cable_meters', 'start_x', 'start_y',
                'end_x', 'end_y', 'hours_worked', 'status', 'priority'
            ]

            for field in updateable_fields:
                if field in data:
                    if field in ['x_coord', 'y_coord', 'cable_meters', 'start_x', 'start_y', 'end_x', 'end_y', 'hours_worked']:
                        # Handle numeric fields
                        if data[field] is not None:
                            setattr(work_log, field, float(data[field]))
                    else:
                        setattr(work_log, field, data[field])

            work_log.save()

            # Update cable route if needed
            if 'route_points' in data or 'cable_cross_section' in data or 'installation_method' in data:
                cable_route = CableRoute.find_by_work_log_id(work_log.id)
                if cable_route:
                    if 'route_points' in data:
                        cable_route.route_points = data['route_points']
                    if 'cable_cross_section' in data:
                        cable_route.cable_cross_section = data['cable_cross_section']
                    if 'installation_method' in data:
                        cable_route.installation_method = data['installation_method']
                    if 'route_notes' in data:
                        cable_route.notes = data['route_notes']

                    cable_route.save()

            return ServiceResult.ok(work_log, "Work log updated successfully")

        except Exception as e:
            return ServiceResult.fail(f"Failed to update work log: {str(e)}")

    @staticmethod
    def delete_work_log(log_id: int, user_id: int) -> ServiceResult:
        """Delete a work log with permission checks."""
        try:
            work_log = WorkLog.find_by_id(log_id)
            if not work_log:
                return ServiceResult.fail("Work log not found")

            user = User.find_by_id(user_id)
            if not user:
                return ServiceResult.fail("User not found")

            # Check permissions
            if not user.can_delete_any_log() and work_log.worker_id != user_id:
                return ServiceResult.fail("Insufficient permissions to delete this work log")

            # Delete associated cable route first
            cable_route = CableRoute.find_by_work_log_id(work_log.id)
            if cable_route:
                cable_route.delete()

            floor_id = work_log.floor_id
            work_log.delete()

            return ServiceResult.ok(data={'floor_id': floor_id}, message="Work log deleted successfully")

        except Exception as e:
            return ServiceResult.fail(f"Failed to delete work log: {str(e)}")

    @staticmethod
    def get_work_logs(filters: Dict[str, Any] = None, user_id: Optional[int] = None,
                      limit: Optional[int] = None, offset: Optional[int] = None) -> List[WorkLog]:
        """Get work logs with filtering and pagination."""
        try:
            if filters is None:
                filters = {}

            # Apply user-based filtering for workers
            if user_id:
                user = User.find_by_id(user_id)
                if user and user.is_worker():
                    # Workers can only see their own logs by default
                    if 'worker_id' not in filters:
                        filters['worker_id'] = user_id

            # Handle different filter types
            if 'floor_id' in filters:
                return WorkLog.find_by_floor_id(filters['floor_id'], limit)
            elif 'project_id' in filters:
                return WorkLog.find_by_project_id(filters['project_id'], limit, offset)
            elif 'worker_id' in filters:
                return WorkLog.find_by_worker_id(filters['worker_id'], limit)
            elif 'start_date' in filters and 'end_date' in filters:
                return WorkLog.find_by_date_range(
                    filters['start_date'],
                    filters['end_date'],
                    filters.get('floor_id')
                )
            else:
                return WorkLog.find_all(limit, offset)

        except Exception as e:
            logger.error("Error getting work logs: %s", e)
            return []

    @staticmethod
    def get_work_log_with_details(log_id: int, user_id: int) -> ServiceResult:
        """Get detailed work log information including cable routes."""
        try:
            work_log = WorkLog.find_by_id(log_id)
            if not work_log:
                return ServiceResult.fail("Work log not found")

            user = User.find_by_id(user_id)
            if not user:
                return ServiceResult.fail("User not found")

            # Check permissions for workers
            if user.is_worker() and work_log.worker_id != user_id:
                return ServiceResult.fail("Insufficient permissions to view this work log")

            # Get work log data
            log_data = work_log.to_dict()

            # Add cable route information
            cable_route = CableRoute.find_by_work_log_id(work_log.id)
            if cable_route:
                log_data['cable_route'] = cable_route.to_dict()

            # Add floor information
            floor = Floor.find_by_id(work_log.floor_id)
            if floor:
                log_data['floor_name'] = floor.name

            return ServiceResult.ok(log_data, "Work log retrieved successfully")

        except Exception as e:
            return ServiceResult.fail(f"Failed to get work log details: {str(e)}")

    @staticmethod
    def get_dashboard_stats(user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get dashboard statistics for work logs."""
        try:
            stats = {
                'total_logs': 0,
                'recent_logs': 0,
                'work_types': [],
                'floor_stats': [],
                'user_stats': {}
            }

            if user_id:
                user = User.find_by_id(user_id)
                if user and user.is_worker():
                    # Worker-specific stats
                    user_logs = WorkLog.find_by_worker_id(user_id)
                    stats['total_logs'] = len(user_logs)
                    stats['recent_logs'] = len(
                        [log for log in user_logs if log.work_date >= str(date.today().replace(day=1))])
                else:
                    # Supervisor/Admin stats
                    stats['total_logs'] = len(WorkLog.find_all())
                    stats['recent_logs'] = WorkLog.get_recent_logs_count(7)
                    stats['work_types'] = WorkLog.get_work_type_stats()
                    stats['floor_stats'] = WorkLog.get_floor_stats()
            else:
                # Global stats
                stats['total_logs'] = len(WorkLog.find_all())
                stats['recent_logs'] = WorkLog.get_recent_logs_count(7)
                stats['work_types'] = WorkLog.get_work_type_stats()
                stats['floor_stats'] = WorkLog.get_floor_stats()

            return stats

        except Exception as e:
            logger.error("Error getting dashboard stats: %s", e)
            return {}

    @staticmethod
    def validate_work_log_data(data: Dict[str, Any]) -> List[str]:
        """Validate work log data and return list of issues."""
        issues = []

        # Required fields
        required_fields = ['floor_id', 'x_coord',
                           'y_coord', 'work_date', 'work_type']
        for field in required_fields:
            if field not in data or data[field] is None:
                issues.append(f"Missing required field: {field}")

        # Validate coordinates
        try:
            if 'x_coord' in data:
                x_coord = float(data['x_coord'])
                if x_coord < 0 or x_coord > 1:
                    issues.append("X coordinate must be between 0 and 1")
        except (ValueError, TypeError):
            issues.append("X coordinate must be a valid number")

        try:
            if 'y_coord' in data:
                y_coord = float(data['y_coord'])
                if y_coord < 0 or y_coord > 1:
                    issues.append("Y coordinate must be between 0 and 1")
        except (ValueError, TypeError):
            issues.append("Y coordinate must be a valid number")

        # Validate date
        if 'work_date' in data:
            try:
                datetime.fromisoformat(data['work_date'])
            except ValueError:
                issues.append("Invalid work date format")

        # Validate hours worked
        if 'hours_worked' in data and data['hours_worked'] is not None:
            try:
                hours = float(data['hours_worked'])
                if hours < 0 or hours > 24:
                    issues.append("Hours worked must be between 0 and 24")
            except (ValueError, TypeError):
                issues.append("Hours worked must be a valid number")

        # Validate cable meters
        if 'cable_meters' in data and data['cable_meters'] is not None:
            try:
                meters = float(data['cable_meters'])
                if meters < 0:
                    issues.append("Cable meters cannot be negative")
            except (ValueError, TypeError):
                issues.append("Cable meters must be a valid number")

        return issues

    @staticmethod
    def export_work_logs(filters: Dict[str, Any] = None, format: str = 'json') -> ServiceResult:
        """Export work logs in specified format."""
        try:
            work_logs = WorkLogService.get_work_logs(filters)

            if format.lower() == 'json':
                data = [log.to_dict() for log in work_logs]
                return ServiceResult.ok(data, f"Exported {len(data)} work logs")
            elif format.lower() == 'csv':
                import csv
                import io

                output = io.StringIO()
                if work_logs:
                    fieldnames = work_logs[0].to_dict().keys()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    for log in work_logs:
                        writer.writerow(log.to_dict())

                return ServiceResult.ok(output.getvalue(), f"Exported {len(work_logs)} work logs as CSV")
            else:
                return ServiceResult.fail(f"Unsupported export format: {format}")

        except Exception as e:
            return ServiceResult.fail(f"Export failed: {str(e)}")

    @staticmethod
    def _check_critical_sector_alerts(work_log: WorkLog) -> None:
        """Check if work log is in critical sector and send alerts."""
        try:
            # Find critical sectors that contain this work location
            critical_sectors = CriticalSector.find_sectors_containing_point(
                work_log.floor_id, work_log.x_coord, work_log.y_coord
            )

            if critical_sectors:
                # Send alerts to supervisors and admins
                supervisor_users = User.find_by_role('supervisor')
                admin_users = User.find_by_role('admin')
                alert_users = supervisor_users + admin_users

                for sector in critical_sectors:
                    message = f"Work completed in critical sector '{sector.sector_name}' on floor {work_log.floor_id}. Worker: {work_log.worker_name}, Type: {work_log.work_type}"

                    user_ids = [user.id for user in alert_users]
                    if user_ids:
                        Notification.create_critical_alert(
                            user_ids, message, work_log.id)
                        try:
                            from app.realtime import broadcast_to_rooms
                            broadcast_to_rooms('notification_new', {'work_log_id': work_log.id}, rooms=[f'user:{uid}' for uid in user_ids])
                        except Exception:
                            pass

        except Exception as e:
            logger.error("Error checking critical sector alerts: %s", e)

    @staticmethod
    def get_work_logs_near_point(floor_id: int, x: float, y: float, radius: float = 0.05) -> List[WorkLog]:
        """Get work logs near a specific point."""
        try:
            all_logs = WorkLog.find_by_floor_id(floor_id)
            nearby_logs = []

            for log in all_logs:
                distance = log.get_distance_from_point(x, y)
                if distance <= radius:
                    nearby_logs.append(log)

            # Sort by distance
            nearby_logs.sort(key=lambda log: log.get_distance_from_point(x, y))

            return nearby_logs

        except Exception as e:
            logger.error("Error finding nearby work logs: %s", e)
            return []

    @staticmethod
    def bulk_update_work_logs(log_ids: List[int], updates: Dict[str, Any], user_id: int) -> ServiceResult:
        """Bulk update multiple work logs."""
        try:
            user = User.find_by_id(user_id)
            if not user:
                return ServiceResult.fail("User not found")

            if not user.can_edit_any_log():
                return ServiceResult.fail("Insufficient permissions for bulk updates")

            updated_count = 0
            errors = []

            for log_id in log_ids:
                result = WorkLogService.update_work_log(log_id, updates, user_id)
                if result.success:
                    updated_count += 1
                else:
                    errors.append(f"Log {log_id}: {result.message}")

            if errors:
                return ServiceResult.ok(message=f"Updated {updated_count} logs with {len(errors)} errors: {'; '.join(errors[:3])}")
            return ServiceResult.ok(message=f"Successfully updated {updated_count} work logs")

        except Exception as e:
            return ServiceResult.fail(f"Bulk update failed: {str(e)}")
