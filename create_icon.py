# create_icon.py - Creates a pencil icon
from PIL import Image, ImageDraw
import os

def create_pencil_icon():
    """Create a simple pencil icon with multiple sizes"""
    
    # Icon sizes needed for Windows ICO
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # Create the largest size first
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Define colors
    wood_color = (255, 204, 102)  # Light wood/yellow
    lead_color = (64, 64, 64)      # Dark gray for lead
    metal_color = (192, 192, 192)  # Silver for ferrule
    eraser_color = (255, 182, 193) # Pink for eraser
    outline_color = (0, 0, 0)      # Black outline
    
    # Draw pencil at an angle
    # Pencil body (main shaft)
    body_points = [
        (50, 180),   # Bottom left
        (180, 50),   # Top right
        (200, 70),   # Top right edge
        (70, 200),   # Bottom right edge
    ]
    draw.polygon(body_points, fill=wood_color, outline=outline_color, width=2)
    
    # Draw wood texture lines
    for i in range(5):
        offset = i * 15
        draw.line([(60 + offset, 190 - offset), (70 + offset, 200 - offset)], 
                 fill=(230, 180, 80), width=1)
    
    # Draw lead tip
    tip_points = [
        (50, 180),   # Connect to body
        (30, 200),   # Sharp point
        (70, 200),   # Other side
    ]
    draw.polygon(tip_points, fill=lead_color, outline=outline_color, width=2)
    
    # Draw the actual lead point
    lead_points = [
        (42, 188),
        (30, 200),
        (38, 200),
    ]
    draw.polygon(lead_points, fill=(0, 0, 0))
    
    # Draw metal ferrule (the metal band)
    ferrule_points = [
        (180, 50),
        (200, 70),
        (210, 60),
        (190, 40),
    ]
    draw.polygon(ferrule_points, fill=metal_color, outline=outline_color, width=2)
    
    # Draw eraser
    eraser_points = [
        (190, 40),
        (210, 60),
        (226, 44),
        (206, 24),
    ]
    draw.polygon(eraser_points, fill=eraser_color, outline=outline_color, width=2)
    
    # Add some shading to make it look 3D
    # Add highlight on pencil body
    highlight_points = [
        (70, 160),
        (160, 70),
        (170, 80),
        (80, 170),
    ]
    highlight = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight)
    highlight_draw.polygon(highlight_points, fill=(255, 255, 255, 60))
    img = Image.alpha_composite(img, highlight)
    
    # Create ICO file with multiple sizes
    icon_sizes = []
    for s in sizes:
        resized = img.resize(s, Image.Resampling.LANCZOS)
        icon_sizes.append(resized)
    
    # Save as ICO
    icon_sizes[0].save('icon.ico', format='ICO', sizes=[(s[0], s[1]) for s in sizes])
    print("✓ Created icon.ico with a pencil design")
    
    # Also save as PNG for preview
    img.save('icon_preview.png')
    print("✓ Created icon_preview.png for preview")

if __name__ == "__main__":
    create_pencil_icon()