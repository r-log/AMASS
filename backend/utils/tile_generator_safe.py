"""
Safe & Fast Tile Generator
Conservative approach that balances speed with system stability
Prevents resource exhaustion and system crashes
"""

import os
import math
import io
import time
import sys
from pathlib import Path
from typing import Dict, Any, List
from PIL import Image, ImageFilter
import fitz  # PyMuPDF
import xml.etree.ElementTree as ET
import gc  # Garbage collection


class SafeTileGenerator:
    """Safe tile generator with conservative resource usage"""

    def __init__(self, tiles_dir: str = 'tiles', tile_size: int = 256,
                 overlap: int = 1, dpi: int = 300):
        """
        Initialize safe generator with conservative settings

        Args:
            tiles_dir: Output directory
            tile_size: Tile size (256 for faster processing)
            overlap: Tile overlap (1 for speed)
            dpi: DPI setting (300 for good quality without overwhelming system)
        """
        self.tiles_dir = Path(tiles_dir)
        self.tile_size = tile_size
        self.overlap = overlap
        self.dpi = dpi
        self.tiles_dir.mkdir(exist_ok=True)

        print(f"🛡️  Safe Tile Generator Initialized")
        print(
            f"   📐 Tile size: {self.tile_size}x{self.tile_size} (conservative)")
        print(f"   🎯 DPI: {self.dpi} (optimized for stability)")
        print(f"   ⚡ Processing: Sequential with memory management")
        print(f"   🛡️  Resource limits: Built-in safety controls")

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

        try:
            print(f"\n🏢 Processing {floor_name}...")
            print(f"   📄 PDF: {pdf_path}")
            print(f"   ⚙️  Settings: {self.dpi} DPI, {self.tile_size}px tiles")

            start_time = time.time()

            # Step 1: Convert PDF to image with memory management
            print("   📄 Step 1/3: Converting PDF...")
            pdf_document = fitz.open(pdf_path)
            page = pdf_document.load_page(0)

            # Conservative zoom factor
            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)

            # Render page
            pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))

            # Clean up PDF resources immediately
            pdf_document.close()
            del pix, img_data
            gc.collect()  # Force garbage collection

            print(f"   ✓ Image: {image.width}x{image.height} pixels")

            # Step 2: Setup directories
            print("   📁 Step 2/3: Setting up directories...")
            floor_dir = self.tiles_dir / f"floor-{floor_id}"
            floor_dir.mkdir(exist_ok=True)

            tiles_subdir = floor_dir / f"floor-{floor_id}_files"
            tiles_subdir.mkdir(exist_ok=True)

            # Step 3: Generate tiles with progress
            print("   🔨 Step 3/3: Generating tiles...")
            levels, total_tiles = self.generate_tiles_safely(
                image, tiles_subdir, floor_id)

            # Create DZI file
            dzi_path = self.create_dzi_file(
                image.width, image.height, floor_dir, floor_id)

            # Clean up main image
            image.close()
            gc.collect()

            generation_time = time.time() - start_time
            tiles_per_sec = total_tiles / generation_time if generation_time > 0 else 0

            print(
                f"   ✅ Completed: {total_tiles} tiles in {generation_time:.1f}s ({tiles_per_sec:.1f} tiles/sec)")

            return {
                'success': True,
                'floor_id': floor_id,
                'floor_name': floor_name,
                'dzi_path': str(dzi_path),
                'original_width': image.width if hasattr(image, 'width') else 0,
                'original_height': image.height if hasattr(image, 'height') else 0,
                'levels': levels,
                'total_tiles': total_tiles,
                'generation_time': generation_time,
                'tiles_per_second': tiles_per_sec
            }

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'floor_id': floor_id,
                'floor_name': floor_name
            }

    def generate_tiles_safely(self, image: Image.Image, tiles_subdir: Path, floor_id: int) -> tuple:
        """Generate tiles with safe resource management"""

        max_dimension = max(image.width, image.height)
        max_level = math.ceil(math.log(max_dimension, 2))

        total_tiles = 0

        print(f"     📊 Pyramid: {max_level + 1} levels")

        # Process each level sequentially to avoid overwhelming system
        for level in range(max_level + 1):
            level_dir = tiles_subdir / str(level)
            level_dir.mkdir(exist_ok=True)

            # Calculate level dimensions
            scale = 2 ** (max_level - level)
            level_width = max(1, image.width // scale)
            level_height = max(1, image.height // scale)

            # Create level image
            if scale > 1:
                level_image = image.resize(
                    (level_width, level_height),
                    Image.Resampling.LANCZOS
                )
                # Light sharpening only for detail levels
                if scale <= 2:
                    level_image = level_image.filter(
                        ImageFilter.UnsharpMask(
                            radius=1, percent=100, threshold=2)
                    )
            else:
                level_image = image

            # Calculate tiles for this level
            cols = math.ceil(level_width / self.tile_size)
            rows = math.ceil(level_height / self.tile_size)
            level_tiles = cols * rows

            print(
                f"     Level {level}: {cols}x{rows} = {level_tiles} tiles", end="")

            # Generate tiles with periodic progress updates
            tiles_created = 0
            for col in range(cols):
                for row in range(rows):
                    x = col * self.tile_size
                    y = row * self.tile_size
                    x2 = min(x + self.tile_size, level_width)
                    y2 = min(y + self.tile_size, level_height)

                    # Extract and save tile
                    tile = level_image.crop((x, y, x2, y2))
                    tile_path = level_dir / f"{col}_{row}.png"
                    tile.save(tile_path, "PNG",
                              optimize=True, compress_level=6)
                    tile.close()  # Close tile immediately

                    tiles_created += 1

                    # Show progress every 50 tiles
                    if tiles_created % 50 == 0 or tiles_created == level_tiles:
                        progress = (tiles_created / level_tiles) * 100
                        print(
                            f"\r     Level {level}: {tiles_created}/{level_tiles} ({progress:.0f}%)", end="")

            print("  ✓")
            total_tiles += level_tiles

            # Clean up level image if it's not the original
            if scale > 1:
                level_image.close()

            # Force garbage collection every level to keep memory usage low
            gc.collect()

        return max_level + 1, total_tiles

    def create_dzi_file(self, width: int, height: int, floor_dir: Path, floor_id: int) -> Path:
        """Create DZI metadata file"""

        root = ET.Element("Image", {
            "TileSize": str(self.tile_size),
            "Overlap": str(self.overlap),
            "Format": "png",
            "xmlns": "http://schemas.microsoft.com/deepzoom/2008"
        })

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
            print("🗑️  Cleaning up existing tiles...")

            # Remove directories one by one to avoid overwhelming system
            removed_count = 0
            for item in self.tiles_dir.iterdir():
                if item.is_dir():
                    print(f"   - Removing {item.name}...")
                    shutil.rmtree(item)
                    removed_count += 1
                    # Small delay to prevent overwhelming system
                    time.sleep(0.1)

            print(f"✅ Cleaned up {removed_count} floor directories")
        else:
            print("ℹ️  No existing tiles found")

    def process_all_floors_safely(self, floor_configs: List[Dict]) -> List[Dict]:
        """Process all floors sequentially with memory management"""

        print(f"\n🛡️  Starting SAFE processing of {len(floor_configs)} floors")
        print("=" * 60)
        print("🛡️  SAFETY FEATURES:")
        print(f"   • Sequential processing (no parallel overload)")
        print(f"   • Conservative {self.dpi} DPI")
        print(f"   • Active memory management")
        print(f"   • Regular garbage collection")
        print(f"   • Progress tracking")
        print("=" * 60)

        results = []
        total_start_time = time.time()

        for i, config in enumerate(floor_configs, 1):
            pdf_path = f"../floor-plans/{config['file']}"

            if not Path(pdf_path).exists():
                print(
                    f"\n⚠️  Floor {i}/{len(floor_configs)}: Skipping {config['name']} - PDF not found")
                continue

            print(
                f"\n📊 Progress: Floor {i}/{len(floor_configs)} ({(i/len(floor_configs)*100):.0f}%)")

            result = self.process_pdf_safely(
                pdf_path=pdf_path,
                floor_id=config['id'],
                floor_name=config['name']
            )

            results.append(result)

            # Force cleanup between floors to keep memory usage stable
            gc.collect()
            time.sleep(0.5)  # Brief pause to let system stabilize

        total_time = time.time() - total_start_time
        successful = [r for r in results if r['success']]
        total_tiles = sum(r.get('total_tiles', 0) for r in successful)

        print(f"\n🎯 SAFE PROCESSING SUMMARY")
        print("=" * 50)
        print(f"✅ Processed: {len(successful)}/{len(results)} floors")
        print(f"📊 Total tiles: {total_tiles:,}")
        print(f"⏱️  Total time: {total_time:.1f}s")
        print(f"🛡️  Method: Safe sequential processing")
        print(f"📈 Average: {total_tiles/total_time:.1f} tiles/second")

        return results
