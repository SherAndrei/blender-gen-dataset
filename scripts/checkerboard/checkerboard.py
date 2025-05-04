#!/usr/bin/env python3
"""
Create a plane at the origin and give it a Diffuse BSDF material whose color
comes from a Checker Texture.  Roughness = 1.0, Checker scale = 10.
"""

import bpy

# ─────────────────────────────────────────────────────────────────────────────
# 1. Add a plane at the default position (origin, lying on the XY‑plane)
# ─────────────────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(location=(0.0, 0.0, 0.0))
plane = bpy.context.active_object

# ─────────────────────────────────────────────────────────────────────────────
# 2. Build the material node tree
# ─────────────────────────────────────────────────────────────────────────────
mat = bpy.data.materials.new(name="CheckerDiffuse")
mat.use_nodes = True

nodes  = mat.node_tree.nodes
links  = mat.node_tree.links
nodes.clear()                         # nuke default Principled setup

# Output node
out_node = nodes.new("ShaderNodeOutputMaterial")

# Diffuse BSDF
diff_node = nodes.new("ShaderNodeBsdfDiffuse")
diff_node.inputs["Roughness"].default_value = 1.0  # Full diffuse scatter

# Checker Texture
check_node = nodes.new("ShaderNodeTexChecker")
check_node.inputs["Scale"].default_value = 10.0     # 10× frequency

# Texture Coordinates (use UV for predictable mapping)
coord_node = nodes.new("ShaderNodeTexCoord")

# Wire it up
links.new(coord_node.outputs["UV"], check_node.inputs["Vector"])
links.new(check_node.outputs["Color"], diff_node.inputs["Color"])
links.new(diff_node.outputs["BSDF"], out_node.inputs["Surface"])

# ─────────────────────────────────────────────────────────────────────────────
# 3. Assign material to the plane
# ─────────────────────────────────────────────────────────────────────────────
plane.data.materials.clear()
plane.data.materials.append(mat)
