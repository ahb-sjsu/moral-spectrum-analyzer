using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Builds the autonomous twin: Margaret's home (HomeRoom), Margaret, her dog, a stranger kept out
// of sight until a scenario brings him in, the G1 robot with its head camera, the attested room
// camera, and the World / Perception / RobotAgent / TwinUI / ScenarioRunner components. None of
// them holds robot behaviour: the robot's actions come from the brain (twin/service.py).
//
//   Unity -batchmode ... -executeMethod TwinGame.Build -out <player path> [-target linux|windows]
public static class TwinGame
{
    const string SCENE = "Assets/Twin/Scenes/Home.unity";
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

    static GameObject Dog() => Animal("Dog_Beagle_01", "beagle_color.tga", "dog", 0.42f, Color.white);   // a beagle stands about 40 cm

    // the wild animal: Rocketbox has no coyote, so a German Shepherd model at coyote size (about
    // 60 cm) with a grey-brown tint stands in for one
    static GameObject Coyote() => Animal("Dog_GermanShepard_01", "shepherd_dog_color.tga", "coyote", 0.6f, new Color(0.78f, 0.7f, 0.6f));

    static GameObject Animal(string id, string texture, string name, float height, Color tint)
    {
        string P = "Assets/ThirdParty/RocketboxAnimals/" + id + "/";
        var g = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(P + "Export/" + id + ".fbx"));
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(P + "Textures/" + texture);
        var m = new Material(Shader.Find("Standard")) { mainTexture = tex, color = tint }; m.SetFloat("_Glossiness", 0.2f);
        foreach (var r in g.GetComponentsInChildren<Renderer>()) r.sharedMaterials = r.sharedMaterials.Select(_ => m).ToArray();
        foreach (var an in g.GetComponentsInChildren<Animator>()) an.enabled = false;
        var b = TwinBatch.WorldBounds(g);
        g.transform.localScale *= height / Mathf.Max(b.size.y, 0.05f);
        b = TwinBatch.WorldBounds(g);
        g.transform.position += Vector3.up * -b.min.y;
        g.name = name;
        return g;
    }

    static Transform Smoke(Vector3 at)
    {
        var go = new GameObject("smoke"); go.transform.position = at;
        var ps = go.AddComponent<ParticleSystem>();
        var main = ps.main; main.startLifetime = 6f; main.startSpeed = 0.35f; main.startSize = 0.8f; main.maxParticles = 400;
        main.startColor = new Color(0.35f, 0.35f, 0.35f, 0.55f);
        var em = ps.emission; em.rateOverTime = 40f;
        var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 25f;
        var r = go.GetComponent<ParticleSystemRenderer>();
        r.sharedMaterial = new Material(Shader.Find("Particles/Standard Unlit")) { color = new Color(0.4f, 0.4f, 0.4f, 0.5f) };
        return go.transform;
    }

    static void MakeScene()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var L = HomeRoom.Build();

        var margaret = Avatars.Spawn("Female_Adult_09"); margaret.name = "margaret";
        Posture.Apply(margaret, "stand");
        var dog = Dog();
        var stranger = Avatars.Spawn("Male_Adult_12"); stranger.name = "stranger";
        Avatars.PlaceAt(stranger, new Vector3(-0.6f, 0f, -2.3f), 0f, "stand");
        stranger.SetActive(false);
        var coyote = Coyote(); coyote.SetActive(false);
        var dogBed = new GameObject("dog_bed_spot").transform; dogBed.position = L.dogSpot;

        var robotGo = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(RobotImport.PREFAB));
        var rig = robotGo.GetComponent<RobotRig>(); rig.Pose("stand");
        var rb = TwinBatch.WorldBounds(robotGo);
        robotGo.transform.position += new Vector3(L.dock.x - rb.center.x, -rb.min.y, L.dock.z - rb.center.z);
        var head = new GameObject("robot_head_camera").AddComponent<Camera>();
        head.transform.SetParent(robotGo.transform, false);
        head.transform.localPosition = new Vector3(0f, 1.18f - robotGo.transform.position.y, 0.14f);
        head.transform.localRotation = Quaternion.Euler(10f, 0f, 0f); head.fieldOfView = 75f; head.nearClipPlane = 0.12f;

        var roomCam = new GameObject("room_camera").AddComponent<Camera>();
        roomCam.transform.position = L.roomCam; roomCam.transform.LookAt(L.roomCamLook); roomCam.fieldOfView = 62f;  // vertical; 16:9 frames
        var view = new GameObject("view_camera").AddComponent<Camera>(); view.fieldOfView = 55f;

        var sys = new GameObject("twin");
        var world = sys.AddComponent<World>();
        world.margaret = margaret; world.dog = dog; world.stranger = stranger; world.wildAnimal = coyote; world.dogBed = dogBed;
        world.tvScreen = GameObject.Find("tv_screen")?.transform;
        world.smoke = Smoke(new Vector3(3.6f, 0.6f, 2.5f)); world.smoke.gameObject.SetActive(false);
        foreach (var kv in L.spots) { world.spotIds.Add(kv.Key); world.spotAt.Add(kv.Value); world.spotFace.Add(L.faces[kv.Key]); }

        var per = sys.AddComponent<Perception>(); per.world = world; per.robot = robotGo.transform;
        // the agent lives on the robot: its transform is the robot's body
        world.robotBody = robotGo.transform;
        var agent = robotGo.AddComponent<RobotAgent>();
        agent.world = world; agent.perception = per; agent.rig = rig; agent.roomCam = roomCam; agent.headCam = head; agent.dock = L.dock;
        foreach (var c in L.chores) { agent.choreNames.Add(c.task); agent.choreAt.Add(c.at); agent.choreLook.Add(c.look); }
        var resp = sys.AddComponent<Responders>(); resp.world = world; resp.robot = agent; resp.perception = per;
        agent.responders = resp;
        var ui = sys.AddComponent<TwinUI>(); ui.world = world; ui.robot = agent; ui.view = view; ui.responders = resp;
        var runner = sys.AddComponent<ScenarioRunner>(); runner.world = world; runner.robot = agent; runner.responders = resp;

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
        foreach (var f in Directory.GetFiles(GEN, "*.mat")) AssetDatabase.DeleteAsset(f.Replace('\\', '/'));
        var done = new HashSet<Material>();
        int k = 0;
        foreach (var r in UnityEngine.Object.FindObjectsOfType<Renderer>(true))
            foreach (var m in r.sharedMaterials)
                if (m != null && !AssetDatabase.Contains(m) && done.Add(m))
                    AssetDatabase.CreateAsset(m, $"{GEN}/mat_{k++:000}_{new string((m.name ?? "m").Select(c => char.IsLetterOrDigit(c) ? c : '_').ToArray())}.mat");
        AssetDatabase.SaveAssets();
        Debug.Log($"TWIN_GAME_MATERIALS {done.Count}");
    }
}
