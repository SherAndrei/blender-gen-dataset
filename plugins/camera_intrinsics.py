"""
Intrinsics plugin
=================
Writes *camera_intrinsics.txt* (11 numbers) once per render batch.

Why store only 11 values?
-------------------------
For a pin-hole camera with square pixels, zero skew and no lens distortion
the 4x4 intrinsic matrix

       ┌ fx  0   cx  0 ┐
  K4 = │ 0   fx  cy  0 │
       │ 0   0   1   0 │
       └ 0   0   0   1 ┘

contains many constant zeros and ones. We therefore save only what can vary:

1 - 3 l**fx,lcx, cy**   (focal length in pixels and principal point)
4      zero (unused z-shift)
5 - 7  zeros for distortion coefficients *(k1, k2, p1)*
8      zero (reserved)
9      **1.0** (K4[2, 2])
10-11  **H, W** - image height and width in pixels

The file layout is thus:

```

fx cx cy 0
0 0 0
0
1
H W

````

Re-creating the full 4x4 K4
-----------------------------

```python
import numpy as np

vals = np.loadtxt("camera_intrinsics.txt").flatten()
fx, cx, cy = vals[:3]
H, W       = vals[-2:]

K = np.array([[fx, 0,  cx],
              [0,  fx, cy],
              [0,  0,   1]], dtype=np.float32)

K4 = np.eye(4, dtype=np.float32)
K4[:3, :3] = K
```

"""

import os
from plugins import IPlugin

class CameraIntrinsics(IPlugin):
    """Generate camera_intrinsics.txt once - after the first camera appears."""

    def __init__(self, cfg, plugin_cfg):
        self._written = False

    def on_camera_created(self, scene, camera_obj, index, output_path):
        if self._written:
            return

        cam   = camera_obj.data
        rend  = scene.render

        # Actual render resolution (takes percentage slider into account)
        W = rend.resolution_x * rend.resolution_percentage / 100.0
        H = rend.resolution_y * rend.resolution_percentage / 100.0

        # focal length in pixels (square‑pixel assumption ⇒ fx = fy)
        fx = cam.lens * (W / cam.sensor_width)

        cx = W / 2.0
        cy = H / 2.0

        lines = [
            f"{fx:.10f} {cx:.0f} {cy:.0f} 0.",
            "0. 0. 0.",
            "0.",
            "1.",
            f"{int(H)} {int(W)}"
        ]

        out_path = os.path.join(output_path, "camera_intrinsics.txt")
        with open(out_path, "w") as f:
            f.write("\n".join(lines))

        print(f"[CameraIntrinsics] camera_intrinsics.txt saved to {out_path}")
        self._written = True
