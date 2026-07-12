import bpy
import mathutils

def optimize_and_bake_pbr(resolution=2048, extrusion=0.05, margin=16):
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
    low_poly.name = f"{original_name}_PBR_Optimized"
    
    low_poly.scale = (size_x, size_y, size_z)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # --- UV Unwrapping ---
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            with context.temp_override(area=area):
                bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.01)
            break
            
    bpy.ops.object.mode_set(mode='OBJECT')

    # --- PBR Material & Node Setup ---
    mat = bpy.data.materials.new(name=f"{original_name}_Baked_PBR_Mat")
    mat.use_nodes = True
    low_poly.data.materials.append(mat)
    
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    # Create Images
    color_img = bpy.data.images.new(f"{original_name}_Color", width=resolution, height=resolution)
    normal_img = bpy.data.images.new(f"{original_name}_Normal", width=resolution, height=resolution)
    roughness_img = bpy.data.images.new(f"{original_name}_Roughness", width=resolution, height=resolution)
    ao_img = bpy.data.images.new(f"{original_name}_AO", width=resolution, height=resolution)
    
    # Color space settings
    normal_img.colorspace_settings.name = 'Non-Color'
    roughness_img.colorspace_settings.name = 'Non-Color'
    ao_img.colorspace_settings.name = 'Non-Color'

    # Create Image Texture Nodes
    color_node = nodes.new('ShaderNodeTexImage')
    color_node.image = color_img
    color_node.location = (-600, 300)

    ao_node = nodes.new('ShaderNodeTexImage')
    ao_node.image = ao_img
    ao_node.location = (-600, 0)

    roughness_node = nodes.new('ShaderNodeTexImage')
    roughness_node.image = roughness_img
    roughness_node.location = (-600, -300)

    normal_node = nodes.new('ShaderNodeTexImage')
    normal_node.image = normal_img
    normal_node.location = (-600, -600)

    # --- Baking ---
    bpy.ops.object.select_all(action='DESELECT')
    high_poly.select_set(True)
    low_poly.select_set(True)
    context.view_layer.objects.active = low_poly

    # Global Bake Settings
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = extrusion
    scene.render.bake.max_ray_distance = 1.0 
    scene.render.bake.margin = margin # Texture bleed to prevent seams

    print("Baking Diffuse (Color)...")
    nodes.active = color_node
    scene.cycles.bake_type = 'DIFFUSE'
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True
    bpy.ops.object.bake(type='DIFFUSE')

    print("Baking Ambient Occlusion (AO)...")
    nodes.active = ao_node
    scene.cycles.bake_type = 'AO'
    bpy.ops.object.bake(type='AO')

    print("Baking Roughness...")
    nodes.active = roughness_node
    scene.cycles.bake_type = 'ROUGHNESS'
    bpy.ops.object.bake(type='ROUGHNESS')

    print("Baking Normals...")
    nodes.active = normal_node
    scene.cycles.bake_type = 'NORMAL'
    bpy.ops.object.bake(type='NORMAL')

    # --- PBR Wiring ---
    # Wire Roughness
    links.new(roughness_node.outputs['Color'], bsdf.inputs['Roughness'])
    
    # Wire Normal
    normal_map_node = nodes.new('ShaderNodeNormalMap')
    normal_map_node.location = (-300, -600)
    links.new(normal_node.outputs['Color'], normal_map_node.inputs['Color'])
    links.new(normal_map_node.outputs['Normal'], bsdf.inputs['Normal'])

    # Mix AO with Base Color so you can see it in Blender's viewport
    mix_node = nodes.new('ShaderNodeMix')
    mix_node.data_type = 'RGBA'
    mix_node.blend_type = 'MULTIPLY'
    mix_node.inputs[0].default_value = 1.0 # Mix Factor
    mix_node.location = (-300, 200)
    
    links.new(color_node.outputs['Color'], mix_node.inputs[6]) # Input A
    links.new(ao_node.outputs['Color'], mix_node.inputs[7])    # Input B
    links.new(mix_node.outputs[2], bsdf.inputs['Base Color'])  # Result to BSDF

    # Pack all images
    color_img.pack()
    normal_img.pack()
    roughness_img.pack()
    ao_img.pack()

    high_poly.hide_set(True)
    high_poly.select_set(False)

    print(f"PBR Optimization and baking complete! Low-poly generated: {low_poly.name}")

# Run the script
optimize_and_bake_pbr(resolution=2048, extrusion=0.05, margin=16)
