#!/usr/bin/env python3
# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import argparse
from PIL import Image


def slice_spritesheet(spritesheet_path, output_dir, tile_width, tile_height):
    """
    Slices a spritesheet into individual tiles.

    :param spritesheet_path: Path to the input spritesheet image.
    :param output_dir: Directory to save the output tiles.
    :param tile_width: Width of a single tile.
    :param tile_height: Height of a single tile.
    """
    try:
        img = Image.open(spritesheet_path)
    except FileNotFoundError:
        print(f"Error: Spritesheet file not found at '{spritesheet_path}'")
        return
    except Exception as e:
        print(f"Error: Could not open image file. Make sure it's a valid image. Details: {e}")
        return

    img_width, img_height = img.size
    os.makedirs(output_dir, exist_ok=True)

    print(f"Image size: {img_width}x{img_height}")
    print(f"Tile size: {tile_width}x{tile_height}")

    tile_count = 0
    for y in range(0, img_height, tile_height):
        for x in range(0, img_width, tile_width):
            # Define the box for the current tile
            box = (x, y, x + tile_width, y + tile_height)

            # Ensure the box is within the image boundaries
            if box[2] > img_width or box[3] > img_height:
                print(f"Skipping tile at ({x},{y}) as it extends beyond image boundaries.")
                continue

            # Crop the tile
            tile = img.crop(box)

            # Check if the tile is not completely transparent or empty (optional)
            if tile.getbbox():
                tile_count += 1
                output_filename = f"tile_{tile_count:03d}.png"
                output_path = os.path.join(output_dir, output_filename)

                # Save the tile as PNG to preserve transparency
                tile.save(output_path, "PNG")
                print(f"Saved {output_path}")
            else:
                print(f"Skipping empty tile at ({x},{y})")

    print(f"\nSlicing complete. Saved {tile_count} tiles to '{output_dir}'.")


def main():
    parser = argparse.ArgumentParser(description="Slice a spritesheet into individual tiles.")
    parser.add_argument("spritesheet_path", help="Path to the input spritesheet image.")
    parser.add_argument("output_dir", help="Directory to save the output tiles.")
    parser.add_argument("--tile_width", type=int, required=True, help="Width of a single tile in pixels.")
    parser.add_argument("--tile_height", type=int, required=True, help="Height of a single tile in pixels.")

    args = parser.parse_args()

    slice_spritesheet(args.spritesheet_path, args.output_dir, args.tile_width, args.tile_height)


if __name__ == "__main__":
    main()
