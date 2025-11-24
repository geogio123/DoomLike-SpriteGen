# DOOM-like Sprite Generator

![pixil-frame-0 (8) (1)](https://github.com/user-attachments/assets/d294e4f3-f3eb-4cf0-b7c4-f85ffb28d808)


A Python tool with a PyQt5 GUI that automates the process of converting 3D models into 8-directional, retro-style pixel art sprites (similar to *Doom*, *Duke Nukem 3D*, or *Daggerfall*).

It utilizes **Blender** in the background to render the model and **Pillow (PIL)** to handle pixelation, downscaling, and alignment.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![Blender](https://img.shields.io/badge/Blender-3.0+-orange)

##  Features

*   **8-Directional Rendering:** Automatically renders the model from Front, Front-Right, Right, Back-Right, Back, Back-Left, Left, and Front-Left.
*   **Format Support:** Supports `.obj(recommended)`, `.fbx`, `.gltf`, and `.glb` 3D models.
*   **Automatic Pixelation:** Renders at high resolution and downscales using Nearest Neighbor interpolation for a crisp, retro look.
*   **Smart Alignment:** Calculates the maximum bounding box across all 8 frames and crops them uniformly to ensure the sprite doesn't "jitter" when animating or rotating in-game.
*   **Texture Support:** Optional ability to override the model's texture with an external image file.
*   **Correction Controls:** Built-in inputs to adjust pitch/roll/yaw and camera angle to fix orientation issues common with downloaded assets.

##  Prerequisites

To use this tool, you need the following installed on your system:

1.  **Python 3.x**
2.  **Blender** (Version 3.0 or higher recommended).
    *   *Note: The tool needs to know the location of your `blender.exe`.*

##  Installation

1.  Clone this repository or download the source code.
2.  Ensure both `generate_sprites.py` and `blender_render_helper.py` are in the same directory.
3.  Install the required Python dependencies:

```bash
pip install PyQt5 Pillow
```

##  Usage

1.  Run the main script:
    ```bash
    python generate_sprites.py
    ```
2.  **Blender Configuration**: Click "Browse" to locate your local `blender.exe` (e.g., `C:\Program Files\Blender Foundation\Blender 3.6\blender.exe`).
3.  **Input Files**:
    *   Load your 3D Model (`.obj`, `.fbx`, etc.).
    *   (Optional) Load a specific Texture image.
4.  **Render Settings**:
    *   **Sprite name**: The prefix for your output files (e.g., `imp` becomes `imp_front.png`).
    *   **Render size**: The raw resolution Blender renders at (e.g., `512`). Higher is better for anti-aliasing before downscaling.
    *   **Final pixel size**: The target height/width of the pixelated output (e.g., `64` for a 64x64 retro look).
5.  **Orientation & Camera**:
    *   Adjust **Rotate X/Y/Z** if your model imports lying on its side or facing the wrong way.
    *   **Camera Angle**: `90` is a straight-on side view. Lower values (e.g., `45`) create a top-down isometric view.
6.  Click **GENERATE SPRITES**.

The tool will create a folder named `output_sprites` in the same directory containing your 8 `.png` files.

##  How It Works

1.  **The GUI** constructs a command-line argument list based on your settings.
2.  **Blender** is launched in "Background Mode" (headless) using the helper script `blender_render_helper.py`.
    *   It imports the mesh.
    *   Sets up an Orthographic camera and Sun lighting.
    *   Rotates the model 8 times, rendering a transparent PNG for each angle.
3.  **Post-Processing** (Python):
    *   Images are opened via Pillow.
    *   They are downscaled to the **Final Pixel Size** using `Image.NEAREST` filter to preserve hard edges.
    *   The script calculates the "Maximum Bounding Box" (the largest width and height occupied by non-transparent pixels across *all* 8 images).
    *   All images are cropped and centered onto a canvas of that maximum size. This ensures that if the monster raises its arms in one frame, the sprite size remains consistent across the set.

##  Troubleshooting

*   **"Blender executable not found":** Make sure the path in the top text box points directly to the `.exe` file, not just the folder.
*   **Model is black/untextured:** Some model formats (like OBJ) rely on an `.mtl` file being in the same folder, or absolute paths. Try loading the texture manually via the "Load Texture" button.
*   **Model is facing the floor:** Use the **Rotate X** setting (try 90 or -90) to fix the pitch.
*   **Sprites are tiny or cut off:** Ensure your **Final pixel size** isn't too small relative to the model's complexity.


---
