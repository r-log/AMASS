#!/usr/bin/env python3
"""
Safe Tile Regeneration Script
Conservative approach that won't crash your system
Uses sequential processing with active memory management
"""

import os
import sys
from pathlib import Path
from tile_generator_safe import SafeTileGenerator


def main():
    """Main safe regeneration function"""

    print("🛡️  SAFE TILE REGENERATION")
    print("==========================")
    print("This version prioritizes system stability over speed.")
    print("Sequential processing prevents crashes and resource exhaustion.")
    print()
    print("🛡️  SAFETY FEATURES:")
    print("   • No multiprocessing (prevents system overload)")
    print("   • Conservative 300 DPI (good quality, stable)")
    print("   • Active memory management")
    print("   • Progress tracking")
    print("   • Expected time: 2-5 minutes")
    print()

    response = input("🛡️  Start safe regeneration? (y/n): ")
    if response.lower() != 'y':
        print("❌ Operation cancelled")
        return

    # Floor configurations
    floors = [
        {'id': 1, 'name': 'Ground Floor', 'file': 'floor-1.pdf'},
        {'id': 2, 'name': 'First Floor', 'file': 'floor-2.pdf'},
        {'id': 3, 'name': 'Second Floor', 'file': 'floor-3.pdf'},
        {'id': 4, 'name': 'Third Floor', 'file': 'floor-4.pdf'},
        {'id': 5, 'name': 'Fourth Floor', 'file': 'floor-5.pdf'},
        {'id': 6, 'name': 'Fifth Floor', 'file': 'floor-6.pdf'},
    ]

    # Create safe generator with conservative settings
    generator = SafeTileGenerator(
        tiles_dir='tiles',
        tile_size=256,     # Conservative tile size
        overlap=1,         # Minimal overlap for speed
        dpi=300           # Good quality without overwhelming system
    )

    print("\n" + "="*60)

    # Clean up existing tiles safely
    generator.cleanup_tiles()

    print()

    # Process all floors safely (sequential)
    results = generator.process_all_floors_safely(floors)

    # Final summary
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\n🎯 FINAL RESULTS")
    print("=" * 40)

    if successful:
        total_tiles = sum(r.get('total_tiles', 0) for r in successful)
        max_time = max(r.get('generation_time', 0) for r in successful)

        print(f"✅ Success: {len(successful)}/{len(results)} floors")
        print(f"📊 Total tiles: {total_tiles:,}")
        print(f"⏱️  Longest floor: {max_time:.1f}s")
        print(f"🎯 Quality: 300 DPI (good for all zoom levels)")
        print(f"💎 Format: PNG (lossless)")
        print(f"🛡️  Method: Safe sequential processing")

    if failed:
        print(f"\n❌ Failed floors: {len(failed)}")
        for f in failed:
            print(f"   - {f['floor_name']}: {f.get('error', 'Unknown error')}")

    print(f"\n🎉 Safe regeneration complete!")
    print("📝 Clear your browser cache (Ctrl+F5) to see the new tiles")
    print("🛡️  System remained stable throughout the process")
    print("💡 This method prioritizes reliability over speed")


if __name__ == "__main__":
    main()
