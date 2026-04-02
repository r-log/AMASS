"""
Safe & Fast Tile Generator
Conservative approach that balances speed with system stability
Prevents resource exhaustion and system crashes
Supports WebP, PNG, and JPEG output formats.
"""

import os
import math
import io
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageFilter

# Electrical blueprints at 300 DPI easily exceed PIL's default 89M pixel limit.
# Raise it to 500M to avoid DecompressionBombWarning crashing the server.
Image.MAX_IMAGE_PIXELS = 500_000_000
import fitz  # PyMuPDF
import xml.etree.ElementTree as ET
import gc  # Garbage collection

logger = logging.getLogger(__name__)

# Format-specific save kwargs
# WebP uses lossless mode — blueprints have text/lines that lossy destroys.
# Lossless WebP is ~30% smaller than PNG with zero quality loss.
_SAVE_KWARGS: Dict[str, Dict[str, Any]] = {
    'webp': lambda _q, _cl: {'format': 'WEBP', 'lossless': True, 'method': 4},
    'jpeg': lambda q, _cl: {'format': 'JPEG', 'quality': q, 'optimize': True},
    'png':  lambda _q, cl: {'format': 'PNG', 'optimize': True, 'compress_level': cl},
}


class SafeTileGenerator:
    """Safe tile generator with conservative resource usage"""

    # Class-level progress dict — shared across the process so the
    # HTTP progress endpoint can read it while generation runs in a thread.
    _progress: Dict[int, Dict[str, Any]] = {}

    def __init__(self, tiles_dir: str = 'tiles', tile_size: int = 256,
                 overlap: int = 1, dpi: int = 300,
                 compress_level: int = 9, max_level: Optional[int] = None,
                 tile_format: str = 'webp', quality: int = 85):
        """
        Initialize safe generator with conservative settings

        Args:
            tiles_dir: Output directory
            tile_size: Tile size (256 for faster processing)
            overlap: Tile overlap (1 for speed)
            dpi: DPI setting (300 for good quality without overwhelming system)
            compress_level: PNG compression level (0-9, 9 = max)
            max_level: Cap zoom levels at generation (None = no cap)
            tile_format: Output format — 'webp', 'png', or 'jpeg'
            quality: Quality for lossy formats (1-100, default 85)
        """
        self.tiles_dir = Path(tiles_dir)
        self.tile_size = tile_size
        self.overlap = overlap
        self.dpi = dpi
        self.compress_level = compress_level
        self.max_level = max_level
        self.tile_format = tile_format.lower() if tile_format.lower() in _SAVE_KWARGS else 'webp'
        self.quality = max(1, min(100, quality))
        self.tiles_dir.mkdir(exist_ok=True)

        # File extension for tiles
        self._ext = 'jpg' if self.tile_format == 'jpeg' else self.tile_format

        logger.info("Tile Generator: %dpx tiles, %d DPI, format=%s (q=%d)",
                     self.tile_size, self.dpi, self.tile_format, self.quality)

    # ------------------------------------------------------------------
    # Progress helpers
    # ------------------------------------------------------------------
    @classmethod
    def get_progress(cls, floor_id: int) -> Optional[Dict[str, Any]]:
        """Get current generation progress for a floor (thread-safe read)."""
        return cls._progress.get(floor_id)

    @classmethod
    def get_batch_progress(cls, floor_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get progress for multiple floors at once."""
        return {fid: cls._progress[fid] for fid in floor_ids if fid in cls._progress}

    def _set_progress(self, floor_id: int, **kwargs: Any) -> None:
        SafeTileGenerator._progress[floor_id] = kwargs

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------
    def process_pdf_safely(self, pdf_path: str, floor_id: int, floor_name: str) -> Dict[str, Any]:
        """
        Process a PDF with safe resource management

        Args:
            pdf_path: Path to PDF file
            floor_id: Floor ID
            floor_name: Floor name

        Returns:
            Processing result dictionary
        """
        self._set_progress(floor_id, status='starting', percent=0,
                           floor_name=floor_name)
        try:
            logger.info("Processing %s (floor %d) from %s", floor_name, floor_id, pdf_path)
            start_time = time.time()

            # Step 1: Convert PDF to image with memory management
            self._set_progress(floor_id, status='converting_pdf', percent=5,
                               floor_name=floor_name)
            pdf_document = fitz.open(pdf_path)
            page = pdf_document.load_page(0)

            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)

            pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))

            pdf_document.close()
            del pix, img_data
            gc.collect()

            img_w, img_h = image.width, image.height
            logger.info("  Image: %dx%d pixels", img_w, img_h)

            # Step 2: Setup directories
            floor_dir = self.tiles_dir / f"floor-{floor_id}"
            floor_dir.mkdir(exist_ok=True)
            tiles_subdir = floor_dir / f"floor-{floor_id}_files"
            tiles_subdir.mkdir(exist_ok=True)

            # Step 3: Generate tiles with progress
            self._set_progress(floor_id, status='generating', percent=10,
                               floor_name=floor_name, current_level=0, total_levels=0)
            levels, total_tiles = self.generate_tiles_safely(
                image, tiles_subdir, floor_id, floor_name)

            # Create DZI file
            dzi_path = self.create_dzi_file(
                img_w, img_h, floor_dir, floor_id,
                max_level=levels - 1)

            image.close()
            gc.collect()

            generation_time = time.time() - start_time
            tiles_per_sec = total_tiles / generation_time if generation_time > 0 else 0

            logger.info("  Completed: %d tiles in %.1fs (%.1f t/s)",
                         total_tiles, generation_time, tiles_per_sec)

            self._set_progress(floor_id, status='complete', percent=100,
                               floor_name=floor_name, total_tiles=total_tiles,
                               generation_time=round(generation_time, 1))

            return {
                'success': True,
                'floor_id': floor_id,
                'floor_name': floor_name,
                'dzi_path': str(dzi_path),
                'original_width': img_w,
                'original_height': img_h,
                'levels': levels,
                'total_tiles': total_tiles,
                'generation_time': generation_time,
                'tiles_per_second': tiles_per_sec
            }

        except Exception as e:
            logger.error("Tile generation failed for floor %d: %s", floor_id, e, exc_info=True)
            self._set_progress(floor_id, status='error', percent=0,
                               floor_name=floor_name, error=str(e))
            return {
                'success': False,
                'error': str(e),
                'floor_id': floor_id,
                'floor_name': floor_name
            }

    def generate_tiles_safely(self, image: Image.Image, tiles_subdir: Path,
                              floor_id: int, floor_name: str = '') -> tuple:
        """Generate tiles with safe resource management"""

        max_dimension = max(image.width, image.height)
        computed_max_level = math.ceil(math.log(max_dimension, 2))
        effective_max_level = computed_max_level
        if self.max_level is not None:
            effective_max_level = min(computed_max_level, self.max_level)

        total_tiles = 0
        save_kwargs_fn = _SAVE_KWARGS[self.tile_format]

        logger.info("  Pyramid: %d levels (format=%s)", effective_max_level + 1, self.tile_format)

        for level in range(effective_max_level + 1):
            level_dir = tiles_subdir / str(level)
            level_dir.mkdir(exist_ok=True)

            # Calculate level dimensions
            scale = 2 ** (effective_max_level - level)
            level_width = max(1, image.width // scale)
            level_height = max(1, image.height // scale)

            # Create level image
            if scale > 1:
                level_image = image.resize(
                    (level_width, level_height),
                    Image.Resampling.LANCZOS
                )
                if scale <= 2:
                    level_image = level_image.filter(
                        ImageFilter.UnsharpMask(radius=1, percent=100, threshold=2)
                    )
            else:
                level_image = image

            # For JPEG/WebP: ensure RGB (no alpha)
            if self.tile_format in ('jpeg', 'webp') and level_image.mode == 'RGBA':
                level_image = level_image.convert('RGB')

            cols = math.ceil(level_width / self.tile_size)
            rows = math.ceil(level_height / self.tile_size)
            level_tiles = cols * rows
            ovl = self.overlap

            # Generate tiles with DZI-standard overlap:
            # Each tile extends `overlap` pixels beyond its nominal boundary
            # so OpenSeadragon can blend edges seamlessly.
            for col in range(cols):
                for row in range(rows):
                    x1 = col * self.tile_size - (ovl if col > 0 else 0)
                    y1 = row * self.tile_size - (ovl if row > 0 else 0)
                    x2 = min((col + 1) * self.tile_size + ovl, level_width)
                    y2 = min((row + 1) * self.tile_size + ovl, level_height)

                    tile = level_image.crop((x1, y1, x2, y2))
                    tile_path = level_dir / f"{col}_{row}.{self._ext}"
                    tile.save(tile_path, **save_kwargs_fn(self.quality, self.compress_level))
                    tile.close()

            total_tiles += level_tiles

            # Update progress (10-95% range, proportional to levels done)
            pct = 10 + int(85 * (level + 1) / (effective_max_level + 1))
            self._set_progress(floor_id, status='generating', percent=pct,
                               floor_name=floor_name,
                               current_level=level + 1,
                               total_levels=effective_max_level + 1)

            if scale > 1:
                level_image.close()
            gc.collect()

        return effective_max_level + 1, total_tiles

    def create_dzi_file(self, width: int, height: int, floor_dir: Path, floor_id: int,
                        max_level: Optional[int] = None) -> Path:
        """Create DZI metadata file"""

        attrs = {
            "TileSize": str(self.tile_size),
            "Overlap": str(self.overlap),
            "Format": self._ext,
            "xmlns": "http://schemas.microsoft.com/deepzoom/2008",
        }
        if max_level is not None:
            attrs["MaxLevel"] = str(max_level)

        root = ET.Element("Image", attrs)
        ET.SubElement(root, "Size", {
            "Width": str(width),
            "Height": str(height)
        })

        dzi_path = floor_dir / f"floor-{floor_id}.dzi"
        tree = ET.ElementTree(root)
        tree.write(dzi_path, encoding='utf-8', xml_declaration=True)
        return dzi_path

    def cleanup_tiles(self):
        """Safely remove existing tiles"""
        if self.tiles_dir.exists():
            import shutil
            removed_count = 0
            for item in self.tiles_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    removed_count += 1
            logger.info("Cleaned up %d floor directories", removed_count)

    def process_all_floors_safely(self, floor_configs: List[Dict]) -> List[Dict]:
        """Process all floors sequentially with memory management"""
        results = []
        for i, config in enumerate(floor_configs, 1):
            pdf_path = f"../floor-plans/{config['file']}"
            if not Path(pdf_path).exists():
                logger.warning("Skipping %s — PDF not found", config['name'])
                continue
            result = self.process_pdf_safely(
                pdf_path=pdf_path,
                floor_id=config['id'],
                floor_name=config['name']
            )
            results.append(result)
            gc.collect()
        return results
