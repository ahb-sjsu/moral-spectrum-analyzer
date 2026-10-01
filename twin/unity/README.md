# Unity renderer for the 3D twin

Plan and the staging of every scenario: `docs/TWIN_3D_PLAN.md`. Staging as data: `scenes.json`.

Only the code is in the repository. `TwinWorld/` becomes a Unity 2022.3.62f3 project when the
editor opens it; third-party assets (Poly Haven CC0 models and textures, Microsoft Rocketbox MIT
avatars) are fetched into it with their checksums:

```
python fetch_assets.py TwinWorld/Assets/ThirdParty --rocketbox <clone of microsoft/Microsoft-Rocketbox>
xvfb-run -a Unity -batchmode -force-vulkan -force-device-index 1 -projectPath TwinWorld \
    -executeMethod TwinBatch.Run -scenes scenes.json -out <dir> [-only id,id]
```

The renderer writes `<dir>/pose_<id>/f000.png .. f023.png` (the robot's head camera, 512x512,
12 frames per second) and `<dir>/shots/<id>.png` (an overview). The suite then reads the clips
unchanged:

```
CLIP_KEY=id POSE_ROOT=<dir> SUITE_REPORT=SUITE-REPORT-3D.txt python twin/suite_run.py
```
