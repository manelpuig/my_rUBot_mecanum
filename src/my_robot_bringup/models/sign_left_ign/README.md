# sign_left_ign (Ignition Gazebo Fortress)

This is an optimized Gazebo Sim version of the original `sign_left` model:

- Removes Gazebo Classic Ogre material scripts (`*.material`).
- Uses PBR material with `left.png`.
- Replaces mesh collisions with simple box collisions (faster + more stable).

## Folder
Place the folder `sign_left_ign/` inside a directory configured in `IGN_GAZEBO_RESOURCE_PATH` or `GZ_SIM_RESOURCE_PATH`.

Example (Linux):
```bash
export GZ_SIM_RESOURCE_PATH=/path/to/models:$GZ_SIM_RESOURCE_PATH
gz sim
```

Example (Windows PowerShell):
```powershell
$env:GZ_SIM_RESOURCE_PATH="C:\path\to\models;$env:GZ_SIM_RESOURCE_PATH"
gz sim
```

## Include in a world
```xml
<include>
  <uri>model://sign_left_ign</uri>
  <pose>0 0 0 0 0 0</pose>
</include>
```
