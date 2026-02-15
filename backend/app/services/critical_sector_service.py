"""
Critical sector service for managing critical areas and safety zones.
"""

from typing import Dict, Any, Optional, List, Tuple

from app.models.critical_sector import CriticalSector
from app.models.user import User
from app.models.floor import Floor
from app.models.work_log import WorkLog
from app.models.notification import Notification


class CriticalSectorService:
    """Service for managing critical sectors and related operations."""

    @staticmethod
    def create_critical_sector(data: Dict[str, Any], user_id: int) -> Tuple[bool, Optional[CriticalSector], str]:
        """
        Create a new critical sector with validation.

        Returns:
            Tuple of (success, sector_object, message)
        """
        try:
            # Check permissions
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_critical_sectors():
                return False, None, "Insufficient permissions to create critical sectors"

            # Validate required fields
            required_fields = ['floor_id', 'sector_name', 'x_coord', 'y_coord']
            for field in required_fields:
                if field not in data or data[field] is None:
                    return False, None, f"Missing required field: {field}"

            # Validate floor exists
            floor = Floor.find_by_id(data['floor_id'])
            if not floor:
                return False, None, "Floor not found"

            # Validate coordinates
            try:
                x_coord = float(data['x_coord'])
                y_coord = float(data['y_coord'])
                if x_coord < 0 or x_coord > 1 or y_coord < 0 or y_coord > 1:
                    return False, None, "Coordinates must be between 0 and 1"
            except (ValueError, TypeError):
                return False, None, "Invalid coordinate values"

            # Create critical sector
            sector = CriticalSector(
                floor_id=data['floor_id'],
                sector_name=data['sector_name'],
                x_coord=x_coord,
                y_coord=y_coord,
                radius=data.get('radius', 0.1),
                width=data.get('width', 0.1),
                height=data.get('height', 0.1),
                sector_type=data.get('type', 'rectangle'),
                priority=data.get('priority', 'standard'),
                points=data.get('points'),
                created_by=user_id,
                is_active=True
            )

            sector.save()

            # Notify relevant users
            CriticalSectorService._notify_sector_creation(sector, user)

            return True, sector, "Critical sector created successfully"

        except Exception as e:
            return False, None, f"Failed to create critical sector: {str(e)}"

    @staticmethod
    def update_critical_sector(sector_id: int, data: Dict[str, Any], user_id: int) -> Tuple[bool, Optional[CriticalSector], str]:
        """
        Update an existing critical sector.

        Returns:
            Tuple of (success, sector_object, message)
        """
        try:
            # Check permissions
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_critical_sectors():
                return False, None, "Insufficient permissions to update critical sectors"

            sector = CriticalSector.find_by_id(sector_id)
            if not sector:
                return False, None, "Critical sector not found"

            # Update fields
            updateable_fields = [
                'sector_name', 'floor_id', 'x_coord', 'y_coord', 'radius', 'width', 'height',
                'sector_type', 'priority'
            ]

            for field in updateable_fields:
                if field in data:
                    if field == 'floor_id':
                        try:
                            sector.floor_id = int(data[field])
                        except (ValueError, TypeError):
                            return False, None, "Invalid floor_id"
                    elif field in ['x_coord', 'y_coord', 'radius', 'width', 'height']:
                        # Handle numeric fields with validation
                        try:
                            value = float(data[field])
                            if field in ['x_coord', 'y_coord'] and (value < 0 or value > 1):
                                return False, None, f"{field} must be between 0 and 1"
                            if field in ['radius', 'width', 'height'] and value <= 0:
                                return False, None, f"{field} must be positive"
                            setattr(sector, field, value)
                        except (ValueError, TypeError):
                            return False, None, f"Invalid value for {field}"
                    else:
                        setattr(sector, field, data[field])

            sector.save()

            return True, sector, "Critical sector updated successfully"

        except Exception as e:
            return False, None, f"Failed to update critical sector: {str(e)}"

    @staticmethod
    def delete_critical_sector(sector_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Delete (deactivate) a critical sector.

        Returns:
            Tuple of (success, message)
        """
        try:
            print(
                f"\n[DELETE DEBUG] Starting delete for sector_id={sector_id}, user_id={user_id}")

            # Check permissions
            user = User.find_by_id(user_id)
            print(
                f"[DELETE DEBUG] User.find_by_id({user_id}) returned: {user}")

            if not user:
                print(f"[DELETE DEBUG] ❌ User not found")
                return False, "User not found"

            if not user.can_manage_critical_sectors():
                print(
                    f"[DELETE DEBUG] ❌ User {user.username} (role={user.role}) lacks permissions")
                return False, "Insufficient permissions to delete critical sectors"

            print(f"[DELETE DEBUG] ✓ User {user.username} has permissions")

            sector = CriticalSector.find_by_id(sector_id)
            print(
                f"[DELETE DEBUG] CriticalSector.find_by_id({sector_id}) returned: {sector}")

            if not sector:
                print(f"[DELETE DEBUG] ❌ Sector not found")
                return False, "Critical sector not found"

            print(f"[DELETE DEBUG] ✓ Sector found: {sector.sector_name}")
            print(f"[DELETE DEBUG] Calling sector.deactivate()...")

            # Deactivate sector
            sector.deactivate()

            print(f"[DELETE DEBUG] ✓ Deactivate completed")
            print(f"[DELETE DEBUG] ✓ Delete successful!\n")

            return True, "Critical sector deleted successfully"

        except Exception as e:
            print(f"[DELETE DEBUG] ❌ Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Failed to delete critical sector: {str(e)}"

    @staticmethod
    def get_critical_sectors(floor_id: Optional[int] = None, project_id: Optional[int] = None,
                            active_only: bool = True) -> List[CriticalSector]:
        """Get critical sectors with optional filtering."""
        try:
            if floor_id:
                return CriticalSector.find_by_floor_id(floor_id, active_only)
            if project_id:
                return CriticalSector.find_by_project_id(project_id, active_only)
            if active_only:
                return CriticalSector.find_all_active()
            return CriticalSector.find_all_active()

        except Exception as e:
            print(f"Error getting critical sectors: {e}")
            return []

    @staticmethod
    def get_sectors_by_priority(priority: str, floor_id: Optional[int] = None) -> List[CriticalSector]:
        """Get critical sectors by priority level."""
        try:
            return CriticalSector.find_by_priority(priority, floor_id)
        except Exception as e:
            print(f"Error getting sectors by priority: {e}")
            return []

    @staticmethod
    def check_work_in_critical_areas(floor_id: int, x: float, y: float) -> Tuple[bool, List[CriticalSector]]:
        """
        Check if coordinates fall within any critical sectors.

        Returns:
            Tuple of (is_in_critical_area, list_of_sectors)
        """
        try:
            sectors = CriticalSector.find_sectors_containing_point(
                floor_id, x, y)
            return len(sectors) > 0, sectors

        except Exception as e:
            print(f"Error checking critical areas: {e}")
            return False, []

    @staticmethod
    def get_critical_sector_statistics() -> Dict[str, Any]:
        """Get statistics for critical sectors."""
        try:
            all_sectors = CriticalSector.find_all_active()

            stats = {
                'total_sectors': len(all_sectors),
                'by_floor': CriticalSector.get_count_by_floor(),
                'by_priority': CriticalSector.get_count_by_priority(),
                'by_type': {},
                'recent_activity': []
            }

            # Count by type
            type_counts = {}
            for sector in all_sectors:
                sector_type = sector.sector_type
                type_counts[sector_type] = type_counts.get(sector_type, 0) + 1
            stats['by_type'] = type_counts

            # Recent critical area work (last 30 days)
            from datetime import date, timedelta
            recent_date = date.today() - timedelta(days=30)

            recent_activity = []
            for sector in all_sectors[:10]:  # Limit to top 10 for performance
                work_logs = sector.get_work_logs_in_sector(limit=5)
                recent_work = [log for log in work_logs if log.get(
                    'work_date', '') >= str(recent_date)]
                if recent_work:
                    recent_activity.append({
                        'sector_id': sector.id,
                        'sector_name': sector.sector_name,
                        'floor_id': sector.floor_id,
                        'recent_work_count': len(recent_work)
                    })

            stats['recent_activity'] = recent_activity

            return stats

        except Exception as e:
            print(f"Error getting critical sector statistics: {e}")
            return {}

    @staticmethod
    def validate_critical_sector_data(data: Dict[str, Any]) -> List[str]:
        """Validate critical sector data and return list of issues."""
        issues = []

        # Required fields
        required_fields = ['floor_id', 'sector_name', 'x_coord', 'y_coord']
        for field in required_fields:
            if field not in data or data[field] is None:
                issues.append(f"Missing required field: {field}")

        # Validate sector name
        if 'sector_name' in data and len(data['sector_name'].strip()) < 1:
            issues.append("Sector name cannot be empty")

        # Validate coordinates
        for coord_field in ['x_coord', 'y_coord']:
            if coord_field in data:
                try:
                    coord = float(data[coord_field])
                    if coord < 0 or coord > 1:
                        issues.append(f"{coord_field} must be between 0 and 1")
                except (ValueError, TypeError):
                    issues.append(f"{coord_field} must be a valid number")

        # Validate dimensions
        for dim_field in ['radius', 'width', 'height']:
            if dim_field in data and data[dim_field] is not None:
                try:
                    dim = float(data[dim_field])
                    if dim <= 0:
                        issues.append(f"{dim_field} must be positive")
                    if dim > 1:
                        issues.append(f"{dim_field} must not exceed 1")
                except (ValueError, TypeError):
                    issues.append(f"{dim_field} must be a valid number")

        # Validate type
        if 'type' in data:
            valid_types = ['rectangle', 'circle', 'polygon']
            if data['type'] not in valid_types:
                issues.append(
                    f"Invalid sector type. Must be one of: {', '.join(valid_types)}")

        # Validate priority
        if 'priority' in data:
            valid_priorities = ['low', 'standard', 'high', 'critical']
            if data['priority'] not in valid_priorities:
                issues.append(
                    f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")

        return issues

    @staticmethod
    def get_work_in_critical_sectors(days: int = 7) -> List[Dict[str, Any]]:
        """Get recent work that occurred in critical sectors."""
        try:
            from datetime import date, timedelta

            recent_date = date.today() - timedelta(days=days)
            critical_sectors = CriticalSector.find_all_active()
            critical_work = []

            for sector in critical_sectors:
                work_logs = sector.get_work_logs_in_sector(limit=10)
                recent_logs = [log for log in work_logs if log.get(
                    'work_date', '') >= str(recent_date)]

                if recent_logs:
                    critical_work.append({
                        'sector_id': sector.id,
                        'sector_name': sector.sector_name,
                        'floor_id': sector.floor_id,
                        'priority': sector.priority,
                        'work_count': len(recent_logs),
                        # Limit to 5 most recent
                        'recent_work': recent_logs[:5]
                    })

            # Sort by priority and work count
            priority_order = {'critical': 0,
                              'high': 1, 'standard': 2, 'low': 3}
            critical_work.sort(key=lambda x: (
                priority_order.get(x['priority'], 4), -x['work_count']))

            return critical_work

        except Exception as e:
            print(f"Error getting work in critical sectors: {e}")
            return []

    @staticmethod
    def create_sector_alert(sector: CriticalSector, message: str, work_log_id: Optional[int] = None) -> None:
        """Create alert notifications for critical sector activity."""
        try:
            # Get supervisors and admins
            supervisors = User.find_by_role('supervisor')
            admins = User.find_by_role('admin')
            alert_users = supervisors + admins

            user_ids = [user.id for user in alert_users if user.is_active]

            if user_ids:
                Notification.create_critical_alert(
                    user_ids, message, work_log_id)

        except Exception as e:
            print(f"Error creating sector alert: {e}")

    @staticmethod
    def check_overlapping_sectors(floor_id: int, x: float, y: float, radius: float,
                                  exclude_sector_id: Optional[int] = None) -> List[CriticalSector]:
        """Check for overlapping critical sectors."""
        try:
            sectors = CriticalSector.find_by_floor_id(floor_id)
            overlapping = []

            for sector in sectors:
                if exclude_sector_id and sector.id == exclude_sector_id:
                    continue

                # Simple circular overlap check
                distance = ((x - sector.x_coord) ** 2 +
                            (y - sector.y_coord) ** 2) ** 0.5
                if distance < (radius + sector.radius):
                    overlapping.append(sector)

            return overlapping

        except Exception as e:
            print(f"Error checking overlapping sectors: {e}")
            return []

    @staticmethod
    def bulk_update_sectors(sector_ids: List[int], updates: Dict[str, Any], user_id: int) -> Tuple[bool, str]:
        """
        Bulk update multiple critical sectors.

        Returns:
            Tuple of (success, message)
        """
        try:
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_critical_sectors():
                return False, "Insufficient permissions for bulk updates"

            updated_count = 0
            errors = []

            for sector_id in sector_ids:
                success, _, message = CriticalSectorService.update_critical_sector(
                    sector_id, updates, user_id)
                if success:
                    updated_count += 1
                else:
                    errors.append(f"Sector {sector_id}: {message}")

            if errors:
                return True, f"Updated {updated_count} sectors with {len(errors)} errors: {'; '.join(errors[:3])}"
            else:
                return True, f"Successfully updated {updated_count} critical sectors"

        except Exception as e:
            return False, f"Bulk update failed: {str(e)}"

    @staticmethod
    def export_critical_sectors(floor_id: Optional[int] = None, format: str = 'json') -> Tuple[bool, Any, str]:
        """
        Export critical sectors in specified format.

        Returns:
            Tuple of (success, data, message)
        """
        try:
            if floor_id:
                sectors = CriticalSectorService.get_critical_sectors(floor_id)
            else:
                sectors = CriticalSectorService.get_critical_sectors()

            if format.lower() == 'json':
                data = [sector.to_dict() for sector in sectors]
                return True, data, f"Exported {len(data)} critical sectors"
            elif format.lower() == 'csv':
                # Convert to CSV format
                import csv
                import io

                output = io.StringIO()
                if sectors:
                    fieldnames = sectors[0].to_dict().keys()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    for sector in sectors:
                        writer.writerow(sector.to_dict())

                return True, output.getvalue(), f"Exported {len(sectors)} critical sectors as CSV"
            else:
                return False, None, f"Unsupported export format: {format}"

        except Exception as e:
            return False, None, f"Export failed: {str(e)}"

    @staticmethod
    def _notify_sector_creation(sector: CriticalSector, creator: User) -> None:
        """Send notifications about new critical sector creation."""
        try:
            # Notify users who work on this floor
            floor_workers = []
            recent_logs = WorkLog.find_by_floor_id(sector.floor_id, limit=50)
            worker_ids = set()

            for log in recent_logs:
                if log.worker_id and log.worker_id not in worker_ids:
                    worker_ids.add(log.worker_id)

            # Also notify supervisors and admins
            supervisors = User.find_by_role('supervisor')
            admins = User.find_by_role('admin')

            all_notify_ids = list(worker_ids) + \
                [user.id for user in supervisors + admins]
            all_notify_ids = list(set(all_notify_ids))  # Remove duplicates

            # Remove the creator from notifications
            if creator.id in all_notify_ids:
                all_notify_ids.remove(creator.id)

            if all_notify_ids:
                message = f"New critical sector '{sector.sector_name}' created by {creator.full_name}"
                Notification.create_for_users(
                    all_notify_ids,
                    'critical_sector',
                    'New Critical Sector',
                    message,
                    sector.id
                )

        except Exception as e:
            print(f"Error sending sector creation notifications: {e}")
