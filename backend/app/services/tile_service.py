"""
Tile service for managing floor plan tiles and tile generation.
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import os
import shutil

from app.models.floor import Floor
from app.models.user import User


class TileService:
    """Service for managing tile generation and serving."""

    @staticmethod
    def get_tile_status(floor_id: int, tiles_dir: str) -> Dict[str, Any]:
        """
        Check if tiles exist for a floor.

        Returns:
            Dictionary with tile status information
        """
        try:
            floor = Floor.find_by_id(floor_id)
            if not floor:
                return {
                    'floor_id': floor_id,
                    'tiles_exist': False,
                    'error': 'Floor not found'
                }

            tiles_path = Path(tiles_dir) / f'floor-{floor_id}'
            dzi_file = tiles_path / f'floor-{floor_id}.dzi'

            if dzi_file.exists():
                # Get tile information
                tile_info = TileService._get_tile_info(tiles_path)
                return {
                    'floor_id': floor_id,
                    'floor_name': floor.name,
                    'tiles_exist': True,
                    'dzi_path': f'/api/tiles/{floor_id}/floor-{floor_id}.dzi',
                    'tiles_path': str(tiles_path),
                    'tile_info': tile_info
                }
            else:
                return {
                    'floor_id': floor_id,
                    'floor_name': floor.name,
                    'tiles_exist': False,
                    'dzi_path': None
                }

        except Exception as e:
            return {
                'floor_id': floor_id,
                'tiles_exist': False,
                'error': str(e)
            }

    @staticmethod
    def generate_tiles_for_floor(floor_id: int, floor_plans_dir: str, tiles_dir: str,
                                 tile_generator, force_regenerate: bool = False) -> Tuple[bool, Dict[str, Any], str]:
        """
        Generate tiles for a specific floor.

        Returns:
            Tuple of (success, result_data, message)
        """
        try:
            print(f"\n{'*'*60}")
            print(
                f"[TILE GEN] Starting tile generation for floor ID: {floor_id}")
            print(f"[TILE GEN] Force regenerate: {force_regenerate}")

            floor = Floor.find_by_id(floor_id)
            if not floor:
                print(f"[TILE GEN] ❌ Floor {floor_id} not found")
                return False, {}, "Floor not found"

            print(f"[TILE GEN] Floor found: {floor.name}")
            print(f"[TILE GEN] PDF path: {floor.image_path}")

            # Check if tiles already exist and not forcing regeneration
            if not force_regenerate:
                print(f"[TILE GEN] Checking for existing tiles...")
                status = TileService.get_tile_status(floor_id, tiles_dir)
                if status['tiles_exist']:
                    print(f"[TILE GEN] ✓ Tiles already exist (using cache)")
                    print(f"[TILE GEN]   DZI path: {status['dzi_path']}")
                    print(f"{'*'*60}\n")
                    return True, {
                        'success': True,
                        'message': 'Tiles already exist for this floor',
                        'cached': True,
                        'dzi_path': status['dzi_path'],
                        'tile_info': status.get('tile_info', {})
                    }, "Tiles already exist"

            # Get PDF path
            pdf_path = Path(floor_plans_dir) / floor.image_path
            print(f"[TILE GEN] Full PDF path: {pdf_path}")

            if not pdf_path.exists():
                print(f"[TILE GEN] ❌ PDF file not found: {pdf_path}")
                return False, {}, f"PDF file not found: {floor.image_path}"

            print(f"[TILE GEN] ✓ PDF file exists, starting generation...")
            print(f"[TILE GEN] Output directory: {tiles_dir}/floor-{floor_id}")

            # Generate tiles using the tile generator
            result = tile_generator.process_pdf_safely(
                str(pdf_path),
                floor_id,
                floor.name
            )

            if result['success']:
                print(f"[TILE GEN] ✓ Tile generation successful!")
                print(f"[TILE GEN]   Total tiles: {result.get('total_tiles')}")
                print(f"[TILE GEN]   Zoom levels: {result.get('levels')}")
                print(
                    f"[TILE GEN]   Original size: {result.get('original_width')}x{result.get('original_height')}")
                print(
                    f"[TILE GEN]   DZI path: /api/tiles/{floor_id}/floor-{floor_id}.dzi")
                print(f"{'*'*60}\n")

                return True, {
                    'success': True,
                    'message': f'Tiles generated for {floor.name}',
                    'dzi_path': f'/api/tiles/{floor_id}/floor-{floor_id}.dzi',
                    'stats': {
                        'total_tiles': result.get('total_tiles'),
                        'levels': result.get('levels'),
                        'original_size': f"{result.get('original_width')}x{result.get('original_height')}"
                    }
                }, "Tiles generated successfully"
            else:
                print(
                    f"[TILE GEN] ❌ Tile generation failed: {result.get('error')}")
                print(f"{'*'*60}\n")
                return False, {
                    'error': result.get('error'),
                    'success': False
                }, result.get('error', 'Unknown error during tile generation')

        except Exception as e:
            print(f"[TILE GEN] ❌ Exception during tile generation: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"{'*'*60}\n")
            return False, {}, f"Failed to generate tiles: {str(e)}"

    @staticmethod
    def generate_all_tiles(floor_plans_dir: str, tiles_dir: str, tile_generator,
                           force_regenerate: bool = False) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Generate tiles for all floors.

        Returns:
            Tuple of (success, results_list, message)
        """
        try:
            floors = Floor.find_all_active()
            if not floors:
                return True, [], "No floors found"

            results = []
            success_count = 0
            error_count = 0

            for floor in floors:
                success, result_data, message = TileService.generate_tiles_for_floor(
                    floor.id, floor_plans_dir, tiles_dir, tile_generator, force_regenerate
                )

                floor_result = {
                    'floor_id': floor.id,
                    'floor_name': floor.name,
                    'status': 'success' if success else 'failed',
                    'message': message,
                    'data': result_data
                }

                results.append(floor_result)

                if success:
                    success_count += 1
                else:
                    error_count += 1

            overall_message = f"Generated tiles for {success_count} floors"
            if error_count > 0:
                overall_message += f" with {error_count} errors"

            return True, results, overall_message

        except Exception as e:
            return False, [], f"Failed to generate tiles: {str(e)}"

    @staticmethod
    def cleanup_tiles_for_floor(floor_id: int, tiles_dir: str, user_id: int) -> Tuple[bool, str]:
        """
        Remove tiles for a specific floor.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check permissions
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_users():
                return False, "Insufficient permissions to cleanup tiles"

            tiles_path = Path(tiles_dir) / f'floor-{floor_id}'

            if tiles_path.exists():
                shutil.rmtree(tiles_path)
                return True, f"Tiles cleaned up for floor {floor_id}"
            else:
                return True, "No tiles found to cleanup"

        except Exception as e:
            return False, f"Failed to cleanup tiles: {str(e)}"

    @staticmethod
    def get_tile_file_path(floor_id: int, filename: str, tiles_dir: str) -> Optional[str]:
        """
        Get the full path to a tile file.

        Returns:
            Full path to file if it exists, None otherwise
        """
        try:
            tiles_path = Path(tiles_dir) / f'floor-{floor_id}'

            # Handle DZI file
            if filename.endswith('.dzi'):
                dzi_path = tiles_path / filename
                if dzi_path.exists():
                    return str(dzi_path)
            else:
                # Handle tile images (in subdirectories)
                file_path = tiles_path / filename
                if file_path.exists():
                    return str(file_path)

            return None

        except Exception as e:
            print(f"Error getting tile file path: {e}")
            return None

    @staticmethod
    def get_all_tile_statuses(tiles_dir: str) -> List[Dict[str, Any]]:
        """Get tile status for all floors."""
        try:
            floors = Floor.find_all_active()
            statuses = []

            for floor in floors:
                status = TileService.get_tile_status(floor.id, tiles_dir)
                statuses.append(status)

            return statuses

        except Exception as e:
            print(f"Error getting tile statuses: {e}")
            return []

    @staticmethod
    def validate_tile_generation_request(floor_id: int, floor_plans_dir: str) -> List[str]:
        """Validate tile generation request and return list of issues."""
        issues = []

        # Check if floor exists
        floor = Floor.find_by_id(floor_id)
        if not floor:
            issues.append("Floor not found")
            return issues

        # Check if PDF file exists
        pdf_path = Path(floor_plans_dir) / floor.image_path
        if not pdf_path.exists():
            issues.append(f"PDF file not found: {floor.image_path}")

        # Validate file extension
        if not floor.image_path.lower().endswith('.pdf'):
            issues.append("Floor plan must be a PDF file")

        return issues

    @staticmethod
    def get_tile_generation_statistics(tiles_dir: str) -> Dict[str, Any]:
        """Get statistics about tile generation."""
        try:
            floors = Floor.find_all_active()
            total_floors = len(floors)
            tiled_floors = 0
            total_disk_usage = 0

            for floor in floors:
                status = TileService.get_tile_status(floor.id, tiles_dir)
                if status['tiles_exist']:
                    tiled_floors += 1

                    # Calculate disk usage
                    tiles_path = Path(tiles_dir) / f'floor-{floor.id}'
                    if tiles_path.exists():
                        total_disk_usage += TileService._calculate_directory_size(
                            tiles_path)

            return {
                'total_floors': total_floors,
                'tiled_floors': tiled_floors,
                'untiled_floors': total_floors - tiled_floors,
                'coverage_percentage': (tiled_floors / total_floors * 100) if total_floors > 0 else 0,
                'total_disk_usage_mb': total_disk_usage / (1024 * 1024),
                'avg_size_per_floor_mb': (total_disk_usage / tiled_floors / (1024 * 1024)) if tiled_floors > 0 else 0
            }

        except Exception as e:
            print(f"Error getting tile statistics: {e}")
            return {}

    @staticmethod
    def optimize_tiles(tiles_dir: str, user_id: int) -> Tuple[bool, str]:
        """
        Optimize tiles by removing unused zoom levels or compressing.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check permissions
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_users():
                return False, "Insufficient permissions to optimize tiles"

            # This is a placeholder for tile optimization logic
            # In a real implementation, you might:
            # 1. Analyze tile usage statistics
            # 2. Remove unused deep zoom levels
            # 3. Compress tile images
            # 4. Remove duplicate tiles

            tiles_path = Path(tiles_dir)
            if not tiles_path.exists():
                return False, "Tiles directory not found"

            # Simple optimization: remove empty directories
            removed_count = 0
            for floor_dir in tiles_path.iterdir():
                if floor_dir.is_dir():
                    for root, dirs, files in os.walk(floor_dir, topdown=False):
                        for dir_name in dirs:
                            dir_path = Path(root) / dir_name
                            if dir_path.is_dir() and not any(dir_path.iterdir()):
                                dir_path.rmdir()
                                removed_count += 1

            return True, f"Optimization completed. Removed {removed_count} empty directories."

        except Exception as e:
            return False, f"Optimization failed: {str(e)}"

    @staticmethod
    def _get_tile_info(tiles_path: Path) -> Dict[str, Any]:
        """Get information about generated tiles."""
        try:
            info = {
                'levels': 0,
                'total_tiles': 0,
                'disk_size_mb': 0
            }

            if tiles_path.exists():
                # Count levels (subdirectories in _files directory)
                files_dir = None
                for item in tiles_path.iterdir():
                    if item.is_dir() and item.name.endswith('_files'):
                        files_dir = item
                        break

                if files_dir:
                    levels = [item for item in files_dir.iterdir(
                    ) if item.is_dir() and item.name.isdigit()]
                    info['levels'] = len(levels)

                    # Count total tiles
                    for level_dir in levels:
                        tiles_in_level = sum(
                            1 for item in level_dir.iterdir() if item.is_file())
                        info['total_tiles'] += tiles_in_level

                # Calculate disk usage
                info['disk_size_mb'] = TileService._calculate_directory_size(
                    tiles_path) / (1024 * 1024)

            return info

        except Exception as e:
            print(f"Error getting tile info: {e}")
            return {}

    @staticmethod
    def _calculate_directory_size(path: Path) -> int:
        """Calculate total size of directory in bytes."""
        try:
            total_size = 0
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.exists():
                        total_size += file_path.stat().st_size
            return total_size
        except Exception as e:
            print(f"Error calculating directory size: {e}")
            return 0

    @staticmethod
    def backup_tiles(floor_id: int, tiles_dir: str, backup_dir: str, user_id: int) -> Tuple[bool, str]:
        """
        Create backup of tiles for a specific floor.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check permissions
            user = User.find_by_id(user_id)
            if not user or not user.can_manage_users():
                return False, "Insufficient permissions to backup tiles"

            source_path = Path(tiles_dir) / f'floor-{floor_id}'
            if not source_path.exists():
                return False, f"No tiles found for floor {floor_id}"

            # Create backup directory
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)

            # Create timestamped backup
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_floor_path = backup_path / \
                f'floor-{floor_id}_backup_{timestamp}'

            # Copy tiles
            shutil.copytree(source_path, backup_floor_path)

            return True, f"Tiles backed up to {backup_floor_path}"

        except Exception as e:
            return False, f"Backup failed: {str(e)}"

    # ==================== WRAPPER METHODS FOR API COMPATIBILITY ====================
    # These methods provide compatibility with the routes API expectations
    # They wrap the core functionality methods above

    @staticmethod
    def check_tiles_exist(floor_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if tiles exist for a floor (API wrapper).

        Returns:
            Tuple of (exists: bool, info: dict)
        """
        try:
            from flask import current_app
            tiles_dir = current_app.config.get('TILES_DIRECTORY', 'tiles')

            status = TileService.get_tile_status(floor_id, tiles_dir)
            exists = status.get('tiles_exist', False)

            # Return formatted info
            info = {
                'floor_id': floor_id,
                'floor_name': status.get('floor_name', ''),
                'dzi_path': status.get('dzi_path'),
                'tile_info': status.get('tile_info', {})
            }

            return exists, info

        except Exception as e:
            print(f"Error checking tiles exist: {e}")
            return False, {'error': str(e)}

    @staticmethod
    def get_tile_config(floor_id: int) -> Optional[Dict[str, Any]]:
        """
        Get tile configuration for a floor (API wrapper).

        Returns:
            Configuration dict or None if not found
        """
        try:
            from flask import current_app
            tiles_dir = current_app.config.get('TILES_DIRECTORY', 'tiles')

            status = TileService.get_tile_status(floor_id, tiles_dir)

            if status.get('tiles_exist'):
                return {
                    'floor_id': floor_id,
                    'floor_name': status.get('floor_name'),
                    'dzi_path': status.get('dzi_path'),
                    'tiles_path': status.get('tiles_path'),
                    'tile_info': status.get('tile_info', {}),
                    'exists': True
                }
            else:
                return None

        except Exception as e:
            print(f"Error getting tile config: {e}")
            return None

    @staticmethod
    def generate_tiles(floor_id: int, image_path: str = None) -> Tuple[bool, str]:
        """
        Generate tiles for a floor (API wrapper).

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from flask import current_app

            floor_plans_dir = current_app.config.get(
                'FLOOR_PLANS_DIRECTORY', 'floor-plans')
            tiles_dir = current_app.config.get('TILES_DIRECTORY', 'tiles')

            # Get tile generator from app context
            tile_generator = current_app.config.get('TILE_GENERATOR')
            if not tile_generator:
                return False, "Tile generator not available"

            # Use provided image_path or get from floor
            if not image_path:
                floor = Floor.find_by_id(floor_id)
                if not floor:
                    return False, "Floor not found"
                image_path = floor.image_path

            success, result_data, message = TileService.generate_tiles_for_floor(
                floor_id, floor_plans_dir, tiles_dir, tile_generator, force_regenerate=False
            )

            return success, message

        except Exception as e:
            print(f"Error generating tiles: {e}")
            return False, f"Failed to generate tiles: {str(e)}"

    @staticmethod
    def regenerate_tiles(floor_id: int, image_path: str = None) -> Tuple[bool, str]:
        """
        Regenerate tiles for a floor (API wrapper).

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from flask import current_app

            floor_plans_dir = current_app.config.get(
                'FLOOR_PLANS_DIRECTORY', 'floor-plans')
            tiles_dir = current_app.config.get('TILES_DIRECTORY', 'tiles')

            # Get tile generator from app context
            tile_generator = current_app.config.get('TILE_GENERATOR')
            if not tile_generator:
                return False, "Tile generator not available"

            # Use provided image_path or get from floor
            if not image_path:
                floor = Floor.find_by_id(floor_id)
                if not floor:
                    return False, "Floor not found"
                image_path = floor.image_path

            success, result_data, message = TileService.generate_tiles_for_floor(
                floor_id, floor_plans_dir, tiles_dir, tile_generator, force_regenerate=True
            )

            return success, message

        except Exception as e:
            print(f"Error regenerating tiles: {e}")
            return False, f"Failed to regenerate tiles: {str(e)}"

    @staticmethod
    def clear_tile_cache(floor_id: int) -> Tuple[bool, str]:
        """
        Clear tile cache for a specific floor (API wrapper).

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from flask import current_app
            tiles_dir = current_app.config.get('TILES_DIRECTORY', 'tiles')

            tiles_path = Path(tiles_dir) / f'floor-{floor_id}'

            if tiles_path.exists():
                shutil.rmtree(tiles_path)
                return True, f"Tile cache cleared for floor {floor_id}"
            else:
                return True, "No tiles found to clear"

        except Exception as e:
            print(f"Error clearing tile cache: {e}")
            return False, f"Failed to clear tile cache: {str(e)}"

    @staticmethod
    def clear_all_tile_cache() -> Tuple[bool, str]:
        """
        Clear all tile caches (API wrapper).

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from flask import current_app
            tiles_dir = current_app.config.get('TILES_DIRECTORY', 'tiles')

            tiles_path = Path(tiles_dir)

            if not tiles_path.exists():
                return True, "No tiles directory found"

            cleared_count = 0
            for floor_dir in tiles_path.iterdir():
                if floor_dir.is_dir() and floor_dir.name.startswith('floor-'):
                    try:
                        shutil.rmtree(floor_dir)
                        cleared_count += 1
                    except Exception as e:
                        print(f"Error clearing {floor_dir}: {e}")

            return True, f"Cleared tile cache for {cleared_count} floor(s)"

        except Exception as e:
            print(f"Error clearing all tile caches: {e}")
            return False, f"Failed to clear tile caches: {str(e)}"

    @staticmethod
    def list_all_tiles() -> List[Dict[str, Any]]:
        """
        List all available tiles (API wrapper).

        Returns:
            List of tile status dictionaries
        """
        try:
            from flask import current_app
            tiles_dir = current_app.config.get('TILES_DIRECTORY', 'tiles')

            return TileService.get_all_tile_statuses(tiles_dir)

        except Exception as e:
            print(f"Error listing tiles: {e}")
            return []
