#!/usr/bin/env python3
"""
Regenerate All Tiles with High-Quality Settings
This script will regenerate tiles for floors 2-6 to match the quality of floor-1
"""

import sys
import os
from pathlib import Path
from tile_generator_pure import PurePythonTileGenerator


def main():
    print("🔧 High-Quality Tile Regeneration Script")
    print("=" * 50)
    print("This will regenerate tiles for floors 2-6 with 1200 DPI")
    print("to match the quality of floor-1.")
    print("=" * 50)

    # Floor configurations (skip floor-1 as it's already high quality)
    floors_to_regenerate = [
        {'id': 2, 'name': 'First Floor', 'file': 'floor-2.pdf'},
        {'id': 3, 'name': 'Second Floor', 'file': 'floor-3.pdf'},
        {'id': 4, 'name': 'Third Floor', 'file': 'floor-4.pdf'},
        {'id': 5, 'name': 'Fourth Floor', 'file': 'floor-5.pdf'},
        {'id': 6, 'name': 'Fifth Floor', 'file': 'floor-6.pdf'},
    ]

    # Initialize high-quality tile generator
    tile_generator = PurePythonTileGenerator(
        tiles_dir='tiles',
        tile_size=512,  # Match floor-1 settings
        quality=95,
        high_zoom_quality=100
    )

    print(f"📋 Floors to regenerate: {len(floors_to_regenerate)}")
    print(f"⚙️  Settings: 1200 DPI, 512px tiles, PNG format")

    response = input("\nProceed with regeneration? (y/n): ")
    if response.lower() != 'y':
        print("❌ Regeneration cancelled")
        return

    print("\n🚀 Starting regeneration...")

    successful = 0
    failed = 0

    for floor in floors_to_regenerate:
        print(f"\n📐 Processing {floor['name']} (Floor {floor['id']})...")

        # Check if PDF exists
        pdf_path = Path(f"../floor-plans/{floor['file']}")
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            failed += 1
            continue

        # Clean up existing tiles first
        print(f"🗑️  Cleaning up existing tiles for floor {floor['id']}...")
        tile_generator.cleanup_tiles(floor['id'])

        # Generate new high-quality tiles
        print(f"🔨 Generating high-quality tiles (1200 DPI)...")
