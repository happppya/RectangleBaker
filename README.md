# Rectangle Baker
Blender Auto PBR Optimizer & Baker

This Python script for Blender automates the creation of an optimized low-poly proxy from a high-poly mesh. It generates a scaled bounding-box mesh, unwraps it, and bakes a complete set of PBR textures (Color, Ambient Occlusion, Roughness, and Normal) from your high-poly object directly onto the new low-poly proxy. This is highly useful for optimizing complex background assets or generating quick LODs (Level of Detail) for game engines.

## Features
- Automatic Retopology (Proxy): Calculates the exact bounding box of your selected high-poly mesh and generates a low-poly cube to match.
- Auto UV Unwrapping: Automatically applies a Smart UV Project to the generated low-poly mesh.
- Automated Node Setup: Creates a new material with a Principled BSDF and all necessary Image Texture nodes configured with the correct color spaces.
- One-Click Baking: Uses Cycles' "Selected to Active" to bake Diffuse, AO, Roughness, and Normal maps.
- Auto-Wiring: Connects the baked maps into the Principled BSDF, automatically multiplying the AO into the Base Color for a better viewport preview.
- Auto-Packing: Packs all newly baked textures directly into your .blend file so you don't lose them upon closing.

## Usage
- Open your project in Blender.
- Navigate to the Scripting workspace.
- Click New to create a new text block and paste the provided script into the editor.
- In the 3D Viewport, select the high-poly mesh you want to optimize. (Ensure only one active mesh is selected).
- Click the Run Script button (the play icon) in the top right of the text editor.
- Wait for the baking process to finish. Check the system console or Blender's info bar for progress.
- Once complete, your high-poly mesh will be hidden, and a new object named [OriginalName]_PBR_Optimized will take its place, fully textured.
