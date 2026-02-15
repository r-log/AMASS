"""
Floor service for managing building floors and floor plans.
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from app.models.floor import Floor
from app.models.work_log import WorkLog
from app.models.critical_sector import CriticalSector
from app.models.user import User


class FloorService:
    """Service for managing floors and floor-related operations."""

    @staticmethod
    def get_all_floors(active_only: bool = True) -> List[Floor]:
        """Get all floors with optional active filtering."""
        try:
            if active_only:
                return Floor.find_all_active()
            else:
                return Floor.find_all()
        except Exception as e:
            print(f"Error getting floors: {e}")
            return []

    @staticmethod
    def get_floor_by_id(floor_id: int) -> Optional[Floor]:
        """Get floor by ID."""
        try:
            return Floor.find_by_id(floor_id)
        except Exception as e:
            print(f"Error getting floor {floor_id}: {e}")
            return None

    @staticmethod
    def create_floor(data: Dict[str, Any], user_id: int) -> Tuple[bool, Optional[Floor], str]:
        """
        Create a new floor with validation.

        Returns:
            Tuple of (success, floor_object, message)
        """
        try:
            # Check permissions
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_users():  # Only admins can create floors
                return False, None, "Insufficient permissions to create floors"

            # Validate required fields
            required_fields = ['name', 'image_path']
            for field in required_fields:
                if field not in data or not data[field]:
                    return False, None, f"Missing required field: {field}"

            # Create floor
            floor = Floor(
                name=data['name'],
                image_path=data['image_path'],
                width=data.get('width', 1920),
                height=data.get('height', 1080),
                is_active=True
            )

            floor.save()

            return True, floor, "Floor created successfully"

        except Exception as e:
            return False, None, f"Failed to create floor: {str(e)}"

    @staticmethod
    def update_floor(floor_id: int, data: Dict[str, Any], user_id: int) -> Tuple[bool, Optional[Floor], str]:
        """
        Update an existing floor.

        Returns:
            Tuple of (success, floor_object, message)
        """
        try:
            # Check permissions
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_users():
                return False, None, "Insufficient permissions to update floors"

            floor = Floor.find_by_id(floor_id)
            if not floor:
                return False, None, "Floor not found"

            # Update fields
            updateable_fields = ['name', 'image_path',
                                 'width', 'height', 'is_active']
            for field in updateable_fields:
                if field in data:
                    if field in ['width', 'height']:
                        # Handle numeric fields
                        if data[field] is not None:
                            setattr(floor, field, int(data[field]))
                    else:
                        setattr(floor, field, data[field])

            floor.save()

            return True, floor, "Floor updated successfully"

        except Exception as e:
            return False, None, f"Failed to update floor: {str(e)}"

    @staticmethod
    def delete_floor(floor_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Deactivate a floor (soft delete).

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check permissions
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_users():
                return False, "Insufficient permissions to delete floors"

            floor = Floor.find_by_id(floor_id)
            if not floor:
                return False, "Floor not found"

            # Check if floor has associated work logs
            work_logs_count = floor.get_work_logs_count()
            if work_logs_count > 0:
                return False, f"Cannot delete floor with {work_logs_count} work logs. Please remove work logs first."

            # Check if floor has critical sectors
            sectors_count = floor.get_critical_sectors_count()
            if sectors_count > 0:
                return False, f"Cannot delete floor with {sectors_count} critical sectors. Please remove sectors first."

            # Deactivate floor
            floor.deactivate()

            return True, "Floor deactivated successfully"

        except Exception as e:
            return False, f"Failed to delete floor: {str(e)}"

    @staticmethod
    def get_floor_statistics(floor_id: Optional[int] = None) -> Dict[str, Any]:
        """Get statistics for floors."""
        try:
            if floor_id:
                # Statistics for a specific floor
                floor = Floor.find_by_id(floor_id)
                if not floor:
                    return {}

                work_logs = WorkLog.find_by_floor_id(floor_id)
                critical_sectors = CriticalSector.find_by_floor_id(floor_id)

                # Work type distribution
                work_type_stats = {}
                for log in work_logs:
                    work_type = log.work_type
                    work_type_stats[work_type] = work_type_stats.get(
                        work_type, 0) + 1

                # Recent activity
                from datetime import date, timedelta
                recent_date = date.today() - timedelta(days=30)
                recent_logs = [
                    log for log in work_logs if log.work_date >= str(recent_date)]

                return {
                    'floor_info': floor.to_dict(),
                    'total_work_logs': len(work_logs),
                    'recent_work_logs': len(recent_logs),
                    'critical_sectors': len(critical_sectors),
                    'work_type_distribution': work_type_stats,
                    'avg_logs_per_day': len(recent_logs) / 30 if recent_logs else 0
                }
            else:
                # Global floor statistics
                floors = Floor.find_all_active()
                total_logs = 0
                total_sectors = 0
                floor_stats = []

                for floor in floors:
                    logs_count = floor.get_work_logs_count()
                    sectors_count = floor.get_critical_sectors_count()
                    total_logs += logs_count
                    total_sectors += sectors_count

                    floor_stats.append({
                        'floor_id': floor.id,
                        'floor_name': floor.name,
                        'work_logs_count': logs_count,
                        'critical_sectors_count': sectors_count
                    })

                return {
                    'total_floors': len(floors),
                    'total_work_logs': total_logs,
                    'total_critical_sectors': total_sectors,
                    'floor_stats': floor_stats,
                    'avg_logs_per_floor': total_logs / len(floors) if floors else 0
                }

        except Exception as e:
            print(f"Error getting floor statistics: {e}")
            return {}

    @staticmethod
    def validate_floor_data(data: Dict[str, Any]) -> List[str]:
        """Validate floor data and return list of issues."""
        issues = []

        # Required fields
        required_fields = ['name', 'image_path']
        for field in required_fields:
            if field not in data or not data[field]:
                issues.append(f"Missing required field: {field}")

        # Validate name
        if 'name' in data and len(data['name'].strip()) < 1:
            issues.append("Floor name cannot be empty")

        # Validate dimensions
        if 'width' in data:
            try:
                width = int(data['width'])
                if width <= 0:
                    issues.append("Width must be positive")
            except (ValueError, TypeError):
                issues.append("Width must be a valid number")

        if 'height' in data:
            try:
                height = int(data['height'])
                if height <= 0:
                    issues.append("Height must be positive")
            except (ValueError, TypeError):
                issues.append("Height must be a valid number")

        # Validate image path
        if 'image_path' in data:
            image_path = data['image_path']
            if not image_path.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                issues.append("Image path must be a PDF, PNG, or JPEG file")

        return issues

    @staticmethod
    def check_floor_plan_file_exists(floor: Floor, floor_plans_dir: str) -> Tuple[bool, str]:
        """
        Check if the floor plan file exists on disk.

        Returns:
            Tuple of (exists, full_path)
        """
        try:
            floor_plan_path = Path(floor_plans_dir) / floor.image_path
            return floor_plan_path.exists(), str(floor_plan_path)
        except Exception as e:
            print(f"Error checking floor plan file: {e}")
            return False, ""

    @staticmethod
    def get_floor_work_summary(floor_id: int, date_range: Optional[Tuple[str, str]] = None) -> Dict[str, Any]:
        """Get work summary for a specific floor."""
        try:
            floor = Floor.find_by_id(floor_id)
            if not floor:
                return {}

            # Get work logs
            if date_range:
                start_date, end_date = date_range
                work_logs = WorkLog.find_by_date_range(
                    start_date, end_date, floor_id)
            else:
                work_logs = WorkLog.find_by_floor_id(floor_id)

            # Calculate summary statistics
            total_hours = 0
            total_cable_meters = 0
            work_type_counts = {}
            worker_counts = {}
            status_counts = {}

            for log in work_logs:
                # Hours worked
                if log.hours_worked:
                    total_hours += log.hours_worked

                # Cable meters
                if log.cable_meters:
                    total_cable_meters += log.cable_meters

                # Work type counts
                work_type = log.work_type
                work_type_counts[work_type] = work_type_counts.get(
                    work_type, 0) + 1

                # Worker counts
                worker = log.worker_name
                worker_counts[worker] = worker_counts.get(worker, 0) + 1

                # Status counts
                status = log.status
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                'floor_id': floor_id,
                'floor_name': floor.name,
                'period': {
                    'start_date': date_range[0] if date_range else None,
                    'end_date': date_range[1] if date_range else None
                },
                'totals': {
                    'work_logs': len(work_logs),
                    'hours_worked': total_hours,
                    'cable_meters_installed': total_cable_meters
                },
                'breakdowns': {
                    'by_work_type': work_type_counts,
                    'by_worker': worker_counts,
                    'by_status': status_counts
                },
                'averages': {
                    'hours_per_log': total_hours / len(work_logs) if work_logs else 0,
                    'cable_per_log': total_cable_meters / len(work_logs) if work_logs else 0
                }
            }

        except Exception as e:
            print(f"Error getting floor work summary: {e}")
            return {}

    @staticmethod
    def get_floors_with_activity(days: int = 30) -> List[Dict[str, Any]]:
        """Get floors with recent activity."""
        try:
            from datetime import date, timedelta

            recent_date = date.today() - timedelta(days=days)
            floors = Floor.find_all_active()
            active_floors = []

            for floor in floors:
                recent_logs = WorkLog.find_by_date_range(
                    str(recent_date), str(date.today()), floor.id)

                if recent_logs:
                    active_floors.append({
                        'floor_id': floor.id,
                        'floor_name': floor.name,
                        'recent_activity': len(recent_logs),
                        'last_activity': max(log.work_date for log in recent_logs) if recent_logs else None
                    })

            # Sort by recent activity
            active_floors.sort(
                key=lambda x: x['recent_activity'], reverse=True)

            return active_floors

        except Exception as e:
            print(f"Error getting floors with activity: {e}")
            return []

    @staticmethod
    def bulk_update_floors(floor_ids: List[int], updates: Dict[str, Any], user_id: int) -> Tuple[bool, str]:
        """
        Bulk update multiple floors.

        Returns:
            Tuple of (success, message)
        """
        try:
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_users():
                return False, "Insufficient permissions for bulk updates"

            updated_count = 0
            errors = []

            for floor_id in floor_ids:
                success, _, message = FloorService.update_floor(
                    floor_id, updates, user_id)
                if success:
                    updated_count += 1
                else:
                    errors.append(f"Floor {floor_id}: {message}")

            if errors:
                return True, f"Updated {updated_count} floors with {len(errors)} errors: {'; '.join(errors[:3])}"
            else:
                return True, f"Successfully updated {updated_count} floors"

        except Exception as e:
            return False, f"Bulk update failed: {str(e)}"
