#!/usr/bin/env python3
"""Convert raw continuous splash framebuffer dump to PNG.

Usage:
  tools/rawfb_to_png.py <raw_fb_bin> <output_png> [width] [height] [format]
Default: width=1080, height=2412, format=BGRA
"""
import sys
from PIL import Image

def main():
    if len(sys.argv) < 3:
        print("Usage: rawfb_to_png.py <raw_fb_bin> <output_png> [width] [height] [format]")
        sys.exit(1)

    raw_path = sys.argv[1]
    out_path = sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 2412
    fmt = sys.argv[5].upper() if len(sys.argv) > 5 else 'BGRA'

    with open(raw_path, 'rb') as f:
        data = f.read(width * height * 4)

    expected = width * height * 4
    if len(data) < expected:
        print(f"Warning: file has {len(data)} bytes, expected {expected}. Padding with zeros.")
        data += b'\x00' * (expected - len(data))

    if fmt == 'BGRA':
        img = Image.frombytes('RGBA', (width, height), data, 'raw', 'BGRA')
    elif fmt == 'RGBA':
        img = Image.frombytes('RGBA', (width, height), data, 'raw', 'RGBA')
    elif fmt == 'ARGB':
        img = Image.frombytes('RGBA', (width, height), data, 'raw', 'ARGB')
    else:
        print(f"Unsupported format: {fmt}")
        sys.exit(1)

    img.save(out_path)
    print(f"Saved {width}x{height} image to {out_path}")

if __name__ == '__main__':
    main()
