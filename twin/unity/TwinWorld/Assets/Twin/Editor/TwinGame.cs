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

    // the signed capability manifest's SHA-256 (twin/manifest.py), checked against its canonical text
    // and pinned into the build; without one there is no build
    static string PinnedManifest()
    {
        string p = Arg("-manifest");
        if (string.IsNullOrEmpty(p) || !File.Exists(p))
            throw new Exception("TwinGame.Build needs -manifest <signed manifest>: the actuator executes only a pinned manifest");
        var m = MiniJson.Obj(MiniJson.Parse(File.ReadAllText(p)));
        string text = MiniJson.S(m["canonical"]), sha = MiniJson.S(m["sha256"]);
        using (var s = System.Security.Cryptography.SHA256.Create())
            if (string.Concat(s.ComputeHash(System.Text.Encoding.UTF8.GetBytes(text)).Select(b => b.ToString("x2"))) != sha)
                throw new Exception("the manifest's canonical text does not match its sha256");
        Debug.Log("TWIN_GAME_MANIFEST " + sha);
        return sha;
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
        // the cone emits along the object's forward axis: point it up, or the smoke blows into the wall
        var go = new GameObject("smoke"); go.transform.SetPositionAndRotation(at, Quaternion.Euler(-90f, 0f, 0f));
        var ps = go.AddComponent<ParticleSystem>();
        var main = ps.main; main.startLifetime = 7f; main.startSpeed = 0.45f; main.startSize = 0.6f; main.maxParticles = 500;
        main.startColor = new Color(0.75f, 0.75f, 0.75f, 0.7f);
        var size = ps.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0f, 1f, 1f, 3.5f));
        var em = ps.emission; em.rateOverTime = 45f;
        var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 35f; sh.radius = 0.3f;
        var r = go.GetComponent<ParticleSystemRenderer>();
        r.sharedMaterial = SmokeMaterial();
        return go.transform;
    }

    // a soft, see-through puff: the shader's defaults are opaque and untextured, which drew every
    // particle as a dark square and the cloud as a black block
    static Material SmokeMaterial()
    {
        Directory.CreateDirectory(GEN);
        const int N = 64;
        var tex = new Texture2D(N, N, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "smoke_puff" };
        for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float d = new Vector2(x - (N - 1) / 2f, y - (N - 1) / 2f).magnitude / (N / 2f);
                float a = Mathf.Clamp01(1f - d); a *= a;
                tex.SetPixel(x, y, new Color(1f, 1f, 1f, a));
            }
        tex.Apply();
        string tp = GEN + "/smoke_puff.asset";
        AssetDatabase.DeleteAsset(tp);
        AssetDatabase.CreateAsset(tex, tp);
        var m = new Material(Shader.Find("Particles/Standard Unlit")) { name = "smoke", mainTexture = tex, color = new Color(0.62f, 0.62f, 0.62f, 0.7f) };
        m.SetFloat("_Mode", 2f);   // fade
        m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        m.SetInt("_ZWrite", 0);
        m.EnableKeyword("_ALPHABLEND_ON");
        m.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
        return m;
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
        view.gameObject.AddComponent<Cutaway>();   // looks into the room from outside: drop the near shell

        var sys = new GameObject("twin");
        var world = sys.AddComponent<World>();
        world.margaret = margaret; world.dog = dog; world.stranger = stranger; world.wildAnimal = coyote; world.dogBed = dogBed;
        world.tvScreen = GameObject.Find("tv_screen")?.transform;
        world.smoke = Smoke(new Vector3(3.6f, 0.6f, 2.5f)); world.smoke.gameObject.SetActive(false);
        foreach (var kv in L.spots) { world.spotIds.Add(kv.Key); world.spotAt.Add(kv.Value); world.spotFace.Add(L.faces[kv.Key]); }

        var per = sys.AddComponent<Perception>(); per.world = world; per.robot = robotGo.transform;
        // the agent lives on the robot: its transform is the robot's body
        world.robotBody = robotGo.transform; world.robotDock = L.dock;
        var agent = robotGo.AddComponent<RobotAgent>();
        agent.world = world; agent.perception = per; agent.rig = rig; agent.roomCam = roomCam; agent.headCam = head; agent.dock = L.dock;
        agent.pinnedManifest = PinnedManifest();   // the actuation boundary: this build executes only this manifest
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
