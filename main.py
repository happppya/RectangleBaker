import bpy
import mathutils

def optimize_and_bake(resolution=2048, extrusion=0.05):
    context = bpy.context
    scene = context.scene
    
    if not context.active_object or context.active_object.type != 'MESH':
        print("ERROR: Please select a mesh object before running.")
        return

    high_poly = context.active_object
    original_name = high_poly.name
    
    # Ensure high-poly is actually visible to the Cycles render engine
    high_poly.hide_render = False 
    
    scene.render.engine = 'CYCLES'
    
    if context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # --- Bounding Box Calculation ---
    bbox_corners = [high_poly.matrix_world @ mathutils.Vector(corner) for corner in high_poly.bound_box]
    
    min_x = min([c.x for c in bbox_corners])
    max_x = max([c.x for c in bbox_corners])
    min_y = min([c.y for c in bbox_corners])
    max_y = max([c.y for c in bbox_corners])
    min_z = min([c.z for c in bbox_corners])
    max_z = max([c.z for c in bbox_corners])

    size_x = max_x - min_x
    size_y = max_y - min_y
    size_z = max_z - min_z

    center_x = (max_x + min_x) / 2.0
    center_y = (max_y + min_y) / 2.0
    center_z = (max_z + min_z) / 2.0

    bpy.ops.mesh.primitive_cube_add(size=1, location=(center_x, center_y, center_z))
    low_poly = context.active_object
    low_poly.name = f"{original_name}_Optimized"
    
    low_poly.scale = (size_x, size_y, size_z)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # --- FIX: Context Override for UV Unwrapping ---
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Find a 3D Viewport to trick Blender into running the UV unwrap correctly
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            with context.temp_override(area=area):
                bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.01)
            break
            
    bpy.ops.object.mode_set(mode='OBJECT')

    # --- Material Setup ---
    mat = bpy.data.materials.new(name=f"{original_name}_Baked_Mat")
    mat.use_nodes = True
    low_poly.data.materials.append(mat)
    
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    color_img = bpy.data.images.new(f"{original_name}_Color", width=resolution, height=resolution)
    normal_img = bpy.data.images.new(f"{original_name}_Normal", width=resolution, height=resolution)
    normal_img.colorspace_settings.name = 'Non-Color'

    color_node = nodes.new('ShaderNodeTexImage')
    color_node.image = color_img
    color_node.location = (-400, 200)

    normal_node = nodes.new('ShaderNodeTexImage')
    normal_node.image = normal_img
    normal_node.location = (-400, -200)

    # --- FIX: Aggressive Ray Distance Baking ---
    bpy.ops.object.select_all(action='DESELECT')
    high_poly.select_set(True)
    low_poly.select_set(True)
    context.view_layer.objects.active = low_poly

    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = extrusion
    scene.render.bake.max_ray_distance = 1.0 # Force rays to search up to 1 meter inwards
    
    print("Baking Diffuse (Color)...")
    nodes.active = color_node
    scene.cycles.bake_type = 'DIFFUSE'
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True
    bpy.ops.object.bake(type='DIFFUSE')

    print("Baking Normals...")
    nodes.active = normal_node
    scene.cycles.bake_type = 'NORMAL'
    bpy.ops.object.bake(type='NORMAL')

    # --- Wiring ---
    links.new(color_node.outputs['Color'], bsdf.inputs['Base Color'])
    
    normal_map_node = nodes.new('ShaderNodeNormalMap')
    normal_map_node.location = (-200, -200)
    links.new(normal_node.outputs['Color'], normal_map_node.inputs['Color'])
    links.new(normal_map_node.outputs['Normal'], bsdf.inputs['Normal'])

    color_img.pack()
    normal_img.pack()

    high_poly.hide_set(True)
    high_poly.select_set(False)

    print(f"Optimization and baking complete! Low-poly generated: {low_poly.name}")

optimize_and_bake(resolution=2048, extrusion=0.05)
