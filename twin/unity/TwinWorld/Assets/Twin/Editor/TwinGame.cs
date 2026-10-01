using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Builds the real-time twin: the living room, a patient, the G1 robot with its head camera, the
// game director and the ruling panel, saved as a scene and built as a player.
//
//   Unity -batchmode ... -executeMethod TwinGame.Build -out <player path> [-target linux|windows]
public static class TwinGame
{
    const string SCENE = "Assets/Twin/Scenes/Game.unity";
    const string GEN = "Assets/Twin/Generated";

    public static void Build()
    {
        try
        {
            MakeScene();
            string outPath = Arg("-out") ?? "/archive/unity/builds/linux/TwinGame.x86_64";
            bool win = (Arg("-target") ?? "linux") == "windows";
            PlayerSettings.productName = "Embodied Governance Twin";
            PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
            PlayerSettings.defaultScreenWidth = 1600; PlayerSettings.defaultScreenHeight = 900;
            PlayerSettings.runInBackground = true;
            var rep = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { SCENE }, locationPathName = outPath,
                target = win ? BuildTarget.StandaloneWindows64 : BuildTarget.StandaloneLinux64, options = BuildOptions.None,
            });
            Debug.Log($"TWIN_GAME_BUILD {rep.summary.result} {rep.summary.totalSize / 1e6:F1} MB -> {outPath}");
            EditorApplication.Exit(rep.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded ? 0 : 1);
        }
        catch (Exception e) { Debug.LogError("TWIN_GAME_FAIL " + e); EditorApplication.Exit(1); }
    }

    static string Arg(string name)
    {
        var a = Environment.GetCommandLineArgs();
        int i = Array.IndexOf(a, name);
        return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
    }

    static void MakeScene()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var room = Rooms.Build("living", true);
        var screen = GameObject.Find("tv_screen");

        // the patient stands in the open floor; every event starts from here
        Vector3 spot = room.Anchor("floor");
        var patient = Avatars.Spawn("Female_Adult_09");
        Posture.Apply(patient, "stand");
        Avatars.PlaceAt(patient, spot, 90f, "stand");

        // the robot waits at its standby spot by the door, facing into the room
        var robotGo = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(RobotImport.PREFAB));
        var rig = robotGo.GetComponent<RobotRig>();
        rig.Pose("stand");
        var rb = TwinBatch.WorldBounds(robotGo);
        robotGo.transform.position += new Vector3(-1.3f - rb.center.x, -rb.min.y, -1.4f - rb.center.z);
        var robotCam = new GameObject("robot_head_camera").AddComponent<Camera>();
        robotCam.transform.SetParent(robotGo.transform, false);
        robotCam.transform.localPosition = new Vector3(0f, 1.15f - robotGo.transform.position.y, 0.12f);  // head height above the floor
        robotCam.transform.localRotation = Quaternion.Euler(12f, 0f, 0f);
        robotCam.fieldOfView = 70f; robotCam.enabled = false;  // rendered on demand by the director

        var view = new GameObject("view_camera").AddComponent<Camera>();
        view.transform.position = new Vector3(2.7f, 2.3f, -2.5f); view.transform.LookAt(new Vector3(-0.3f, 0.5f, 0.6f));
        view.fieldOfView = 70f;  // wide enough to keep the robot's standby spot in view

        var dir = new GameObject("director");
        var gd = dir.AddComponent<GameDirector>();
        gd.patient = patient; gd.robot = rig; gd.viewCam = view; gd.robotCam = robotCam;
        gd.tvScreen = screen != null ? screen.transform : null;
        gd.patientSpot = spot; gd.robotHome = robotGo.transform.position;
        dir.AddComponent<RulingPanel>().director = gd;
        dir.AddComponent<Autoplay>();

        PersistMaterials();
        Directory.CreateDirectory(Path.GetDirectoryName(SCENE));
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(), SCENE);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(SCENE, true) };
        Debug.Log("TWIN_GAME_SCENE " + SCENE);
    }

    // materials made in code are not assets; a saved scene keeps only references to assets
    static void PersistMaterials()
    {
        Directory.CreateDirectory(GEN);
        var done = new Dictionary<Material, Material>();
        int k = 0;
        foreach (var r in UnityEngine.Object.FindObjectsOfType<Renderer>(true))
        {
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++)
            {
                var m = mats[i];
                if (m == null || AssetDatabase.Contains(m)) continue;
                if (!done.TryGetValue(m, out var saved))
                {
                    string path = $"{GEN}/mat_{k++:000}_{San(m.name)}.mat";
                    AssetDatabase.CreateAsset(m, path);
                    saved = m; done[m] = m;
                }
                mats[i] = saved;
            }
            r.sharedMaterials = mats;
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"TWIN_GAME_MATERIALS {done.Count}");
    }

    static string San(string s) => new string((s ?? "m").Select(c => char.IsLetterOrDigit(c) ? c : '_').ToArray());
}
