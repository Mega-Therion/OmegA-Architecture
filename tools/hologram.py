#!/usr/bin/env python3
"""
OmegA Holographic Terminal Symbol
A reference implementation of a simulated holographic display in a CLI.
Uses Braille characters for high-resolution ASCII-style animation.
"""

import math
import time
import sys

# Stylized Omega symbol as a 3D-ish surface or just a rotating glyph
def get_omega_point(u, v):
    # u in [0, 2*pi], v in [-1, 1]
    # Simple torus-like omega
    r = 1.0 + 0.3 * math.cos(v * math.pi)
    x = r * math.cos(u)
    y = r * math.sin(u)
    z = 0.5 * math.sin(v * math.pi)
    
    # Clip to form omega shape (break the bottom)
    if u > 0.5 and u < 2 * math.pi - 0.5:
        return x, y, z
    return None

def rotate(x, y, z, angle):
    # Rotate around Y and Z
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    
    # Y rotation
    nx = x * cos_a + z * sin_a
    nz = -x * sin_a + z * cos_a
    x, z = nx, nz
    
    # Z rotation
    nx = x * cos_a - y * sin_a
    ny = x * sin_a + y * cos_a
    x, y = nx, ny
    
    return x, y, z

def render_frame(angle, width=80, height=40):
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Sample points on the omega
    for u_idx in range(100):
        u = u_idx * 2 * math.pi / 100
        for v_idx in range(20):
            v = v_idx * 2.0 / 20 - 1.0
            
            p = get_omega_point(u, v)
            if p:
                x, y, z = p
                x, y, z = rotate(x, y, z, angle)
                
                # Projection
                # Center is at (width/2, height/2)
                # Scale to fit
                scale = min(width, height) * 0.4
                px = int(width / 2 + x * scale * 2) # X is wider in terminal
                py = int(height / 2 - y * scale)
                
                if 0 <= px < width and 0 <= py < height:
                    # Shading based on Z (depth)
                    chars = ".: -=+*#%@"
                    shade = int((z + 1.3) * (len(chars) - 1) / 2.6)
                    shade = max(0, min(len(chars) - 1, shade))
                    grid[py][px] = chars[shade]
                    
    return "\n".join("".join(row) for row in grid)

def main():
    print("\033[?25l") # Hide cursor
    try:
        angle = 0
        while True:
            frame = render_frame(angle)
            sys.stdout.write("\033[H") # Move cursor to home
            sys.stdout.write("\033[1;36m") # Cyan color
            sys.stdout.write(frame)
            sys.stdout.flush()
            angle += 0.1
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\033[?25h") # Show cursor
        print("\nAnimation stopped.")

if __name__ == "__main__":
    main()
