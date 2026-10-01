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

## The real-time game

```
python twin/unity/fetch_assets.py TwinWorld/Assets/ThirdParty --rocketbox <rocketbox clone> --unitree <unitree_ros clone>
Unity -batchmode -force-vulkan -projectPath TwinWorld -executeMethod RobotImport.Run        # G1 prefab, once
Unity -batchmode -force-vulkan -projectPath TwinWorld -executeMethod TwinGame.Build -out <player> [-target windows]
python twin/service.py --port 8765 --log session.jsonl [--frames-dir frames]                # governor, localhost only
<player> [-service http://127.0.0.1:8765]                                                   # play
<player> -autoplay -shots <dir>                                                             # scripted session
```

The service needs the repository's `src/` (the cached analyzer scores) and, for the live camera
witness, torch and torchvision; without them the camera abstains and says so in the ruling.
