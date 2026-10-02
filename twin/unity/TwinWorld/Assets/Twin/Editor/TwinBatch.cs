using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Batch renderer for the 3D twin (docs/TWIN_3D_PLAN.md).
//
//   Unity -batchmode -force-vulkan -force-device-index 1 -projectPath TwinWorld \
//         -executeMethod TwinBatch.Run -scenes <scenes.json> -out <dir> [-only id,id]
//
// For every scenario it builds the room, places the avatar in its posture or runs its ragdoll
// fall, and renders 24 frames (12 per second) from the robot's head camera into
// <out>/pose_<id>/f000.png..f023.png, the layout twin/suite_run.py reads, plus one overview
// still <out>/shots/<id>.png. Nothing here decides anything: the clips go to the unchanged
// vision witness and governor.
public static class TwinBatch
{
    const int W = 512, H = 512, NFR = 24, FPS = 12, STEPS_PER_FRAME = 20;
    const string TP = "Assets/ThirdParty/";

    [Serializable] public class Scene { public string id, set, room, avatar, posture, fall, anchor; public float yaw; public bool seizure, tv, empty, walk; }
    [Serializable] public class SceneList { public Scene[] scenes; }

    public static void Run()
    {
        string scenesPath = Arg("-scenes"), outDir = Arg("-out"), only = Arg("-only");
        var list = JsonUtility.FromJson<SceneList>(File.ReadAllText(scenesPath)).scenes;
        if (!string.IsNullOrEmpty(only)) { var keep = new HashSet<string>(only.Split(',')); list = list.Where(s => keep.Contains(s.id)).ToArray(); }
        Physics.simulationMode = SimulationMode.Script;
        int ok = 0;
        foreach (var sc in list)
        {
            try { RenderScene(sc, outDir); ok++; Debug.Log($"TWIN_SCENE_OK {sc.id}"); }
            catch (Exception e) { Debug.LogError($"TWIN_SCENE_FAIL {sc.id}: {e}"); }
        }
        Debug.Log($"TWIN_BATCH_DONE ok={ok} of {list.Length} device={SystemInfo.graphicsDeviceName}");
        EditorApplication.Exit(ok == list.Length ? 0 : 1);
    }

    static string Arg(string name)
    {
        var a = Environment.GetCommandLineArgs();
        int i = Array.IndexOf(a, name);
        return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
    }

    // ------------------------------------------------------------------ scene
    static void RenderScene(Scene sc, string outDir)
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var room = Rooms.Build(sc.room, sc.tv);
        Vector3 anchor = room.Anchor(sc.anchor);
        if (anchor.y > 0.05f)
        {
            // a seat or bed: find its real surface under the anchor
            Physics.SyncTransforms();
            if (Physics.Raycast(anchor + Vector3.up * 0.35f, Vector3.down, out var hit, 1.0f)) anchor.y = hit.point.y;
            Debug.Log($"TWIN_SURFACE {sc.id} {sc.anchor} y={anchor.y:F3}");
        }

        GameObject person = null; Ragdoll rag = null;
        if (!sc.empty)
        {
            person = Avatars.Spawn(sc.avatar);
            Posture.Apply(person, sc.posture);
            Avatars.PlaceAt(person, anchor, sc.yaw, sc.posture);
            if (!string.IsNullOrEmpty(sc.fall) && sc.fall != "none") rag = Ragdoll.Build(person);
        }

        bool upright = sc.posture == "stand" || sc.posture == "chest" || sc.posture == "bend";
        var cam = MakeCamera("robot_cam", room.RobotCam(anchor), anchor + Vector3.up * (upright ? 0.9f : 0.45f), 62f);
        var shot = sc.tv && room.TvShotFrom.HasValue
            ? MakeCamera("shot_cam", room.TvShotFrom.Value, (room.TvAt.Value + anchor) / 2f + Vector3.up * 0.3f, 65f)
            : MakeCamera("shot_cam", room.ShotCam, anchor + Vector3.up * 0.6f, 55f);

        string clip = Path.Combine(outDir, "pose_" + sc.id);
        Directory.CreateDirectory(clip);
        Directory.CreateDirectory(Path.Combine(outDir, "shots"));
        int trigger = NFR / 4;  // the fall starts after six frames of the starting posture
        for (int f = 0; f < NFR; f++)
        {
            if (rag != null && f == trigger) rag.Release(sc.fall, person.transform.forward);
            if (rag != null && f >= trigger)
            {
                for (int k = 0; k < STEPS_PER_FRAME; k++)
                {
                    if (sc.seizure && f >= trigger + 8) rag.Convulse(f * STEPS_PER_FRAME + k);
                    Physics.Simulate(1f / (FPS * STEPS_PER_FRAME));
                }
            }
            if (sc.walk && person != null) Posture.WalkStep(person, f);
            Save(cam, Path.Combine(clip, $"f{f:000}.png"));
            if (f == NFR - 1) Save(shot, Path.Combine(outDir, "shots", sc.id + ".png"));
        }
    }

    static Camera MakeCamera(string name, Vector3 pos, Vector3 look, float fov)
    {
        var c = new GameObject(name).AddComponent<Camera>();
        c.transform.position = pos; c.transform.LookAt(look);
        c.fieldOfView = fov; c.nearClipPlane = 0.05f; c.allowHDR = false;
        return c;
    }

    static void Save(Camera c, string path)
    {
        var rt = RenderTexture.GetTemporary(W, H, 24, RenderTextureFormat.ARGB32);
        rt.antiAliasing = 4;
        c.targetTexture = rt; c.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(W, H, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, W, H), 0, 0); tex.Apply();
        File.WriteAllBytes(path, tex.EncodeToPNG());
        RenderTexture.active = null; c.targetTexture = null;
        RenderTexture.ReleaseTemporary(rt); UnityEngine.Object.DestroyImmediate(tex);
    }

    // ------------------------------------------------------------------ assets
    public static GameObject Model(string name)
    {
        string dir = TP + "PolyHaven/Models/" + name + "/";
        var guid = AssetDatabase.FindAssets("t:Model", new[] { dir.TrimEnd('/') }).FirstOrDefault();
        if (guid == null) throw new Exception("model not found: " + name);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(guid)));
        foreach (var r in go.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
        return go;
    }

    public static Material Surface(string tex, float tiling)
    {
        string dir = TP + "PolyHaven/Textures/" + tex + "/";
        var m = new Material(Shader.Find("Standard"));
        foreach (var p in Directory.GetFiles(dir))
        {
            string n = Path.GetFileName(p).ToLowerInvariant();
            if (n.EndsWith(".meta")) continue;
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(p.Replace('\\', '/'));
            if (t == null) continue;
            if (n.Contains("_diff_")) m.mainTexture = t;
            else if (n.Contains("_nor_gl_")) { m.SetTexture("_BumpMap", t); m.EnableKeyword("_NORMALMAP"); }
        }
        m.mainTextureScale = new Vector2(tiling, tiling);
        m.SetTextureScale("_BumpMap", new Vector2(tiling, tiling));
        m.SetFloat("_Glossiness", 0.25f);
        return m;
    }

    public static Material Flat(Color c, float gloss = 0.2f)
    {
        var m = new Material(Shader.Find("Standard")); m.color = c; m.SetFloat("_Glossiness", gloss); return m;
    }

    // world-space bounds of every renderer under a transform (skinned meshes baked in their pose)
    public static Bounds WorldBounds(GameObject go)
    {
        bool any = false; var b = new Bounds();
        foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>())
        {
            var mesh = new Mesh(); smr.BakeMesh(mesh, true);
            var m = Matrix4x4.TRS(smr.transform.position, smr.transform.rotation, Vector3.one);
            foreach (var v in mesh.vertices) { var w = m.MultiplyPoint3x4(v); if (!any) { b = new Bounds(w, Vector3.zero); any = true; } else b.Encapsulate(w); }
            UnityEngine.Object.DestroyImmediate(mesh);
        }
        foreach (var r in go.GetComponentsInChildren<MeshRenderer>()) { if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds); }
        return b;
    }
}

// ---------------------------------------------------------------------- rooms
public class Room
{
    public Vector3 ShotCam;
    public Vector3? TvShotFrom, TvAt;  // a second overview that shows the television, when it is on
    public Dictionary<string, Vector3> Anchors = new Dictionary<string, Vector3>();
    public float CamBack = 3.0f, HalfW = 2.5f, HalfD = 2.5f;
    public Vector3 Anchor(string name)
    {
        if (string.IsNullOrEmpty(name)) name = "floor";
        if (!Anchors.TryGetValue(name, out var a)) throw new Exception("no anchor '" + name + "' in this room");
        return a;
    }
    // the robot stands CamBack metres in front of the scene (toward -z), head camera at 1.35 m
    public Vector3 RobotCam(Vector3 anchor) =>
        new Vector3(Mathf.Clamp(anchor.x * 0.4f, -HalfW + 0.3f, HalfW - 0.3f), 1.35f, Mathf.Max(anchor.z - CamBack, -HalfD + 0.3f));
}

public static class Rooms
{
    public static Room Build(string kind, bool tvOn)
    {
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.78f, 0.78f, 0.82f);
        RenderSettings.ambientEquatorColor = new Color(0.62f, 0.60f, 0.56f);
        RenderSettings.ambientGroundColor = new Color(0.36f, 0.33f, 0.30f);
        var r = new Room();
        void Size(float w, float d) { r.HalfW = w / 2f; r.HalfD = d / 2f; }
        switch (kind)
        {
            case "living": Size(6f, 5.5f); Shell(6f, 5.5f, "laminate_floor_02", "beige_wall_001"); Living(r, tvOn); break;
            case "kitchen": Size(4.5f, 4.5f); Shell(4.5f, 4.5f, "floor_tiles_06", "beige_wall_001"); Kitchen(r); break;
            case "dining": Size(5f, 4.5f); Shell(5f, 4.5f, "laminate_floor_02", "beige_wall_001"); Dining(r); break;
            case "bathroom": Size(3.2f, 3.4f); Shell(3.2f, 3.4f, "floor_tiles_06", "long_white_tiles"); Bathroom(r); break;
            case "bedroom": Size(5f, 5f); Shell(5f, 5f, "laminate_floor_02", "beige_wall_001"); Bedroom(r); break;
            case "hallway": Size(2.4f, 6f); Shell(2.4f, 6f, "herringbone_parquet", "beige_wall_001"); Hallway(r); break;
            case "sunroom": Size(4.5f, 4.5f); Shell(4.5f, 4.5f, "floor_tiles_06", "beige_wall_001", bright: true); Sunroom(r); break;
            default: throw new Exception("unknown room " + kind);
        }
        return r;
    }

    public static void Shell(float w, float d, string floor, string wall, bool bright = false)
    {
        Box("floor", new Vector3(0, -0.05f, 0), new Vector3(w, 0.1f, d), TwinBatch.Surface(floor, w / 1.2f), collide: true);
        Box("ceiling", new Vector3(0, 2.65f, 0), new Vector3(w, 0.1f, d), TwinBatch.Flat(new Color(0.93f, 0.92f, 0.9f)));
        var wm = TwinBatch.Surface(wall, 2.5f);
        Box("wall_n", new Vector3(0, 1.3f, d / 2), new Vector3(w, 2.6f, 0.1f), wm, collide: true);
        Box("wall_s", new Vector3(0, 1.3f, -d / 2), new Vector3(w, 2.6f, 0.1f), wm, collide: true);
        Box("wall_e", new Vector3(w / 2, 1.3f, 0), new Vector3(0.1f, 2.6f, d), wm, collide: true);
        Box("wall_w", new Vector3(-w / 2, 1.3f, 0), new Vector3(0.1f, 2.6f, d), wm, collide: true);
        var sun = new GameObject("window_light").AddComponent<Light>();
        sun.type = LightType.Directional; sun.intensity = bright ? 1.1f : 0.75f; sun.shadows = LightShadows.Soft;
        sun.color = new Color(1f, 0.96f, 0.9f); sun.transform.rotation = Quaternion.Euler(48, -35, 0);
        var lamp = new GameObject("ceiling_light").AddComponent<Light>();
        lamp.type = LightType.Point; lamp.range = 8f; lamp.intensity = 0.9f; lamp.shadows = LightShadows.Soft;
        lamp.color = new Color(1f, 0.92f, 0.82f); lamp.transform.position = new Vector3(0, 2.3f, 0.3f);
        var fill = new GameObject("fill_light").AddComponent<Light>();
        fill.type = LightType.Point; fill.range = 8f; fill.intensity = 0.6f; fill.shadows = LightShadows.None;
        fill.color = new Color(0.9f, 0.93f, 1f); fill.transform.position = new Vector3(0.5f, 1.9f, -d / 2 + 0.6f);
    }

    public static GameObject Box(string name, Vector3 pos, Vector3 size, Material m, bool collide = false)
    {
        var g = GameObject.CreatePrimitive(PrimitiveType.Cube);
        g.name = name; g.transform.position = pos; g.transform.localScale = size;
        g.GetComponent<Renderer>().sharedMaterial = m;
        if (!collide) UnityEngine.Object.DestroyImmediate(g.GetComponent<Collider>());
        return g;
    }

    // place a model so its footprint centre sits at (x, z) on the floor, facing yaw degrees
    public static GameObject Put(string model, float x, float z, float yaw, bool collide = true, float y = 0f, float scale = 1f)
    {
        var g = TwinBatch.Model(model);
        g.transform.localScale *= scale;
        g.transform.rotation = Quaternion.Euler(0, yaw, 0) * g.transform.rotation;  // keep the importer's axis conversion
        var b = TwinBatch.WorldBounds(g);
        g.transform.position += new Vector3(x - b.center.x, y - b.min.y, z - b.center.z);
        if (collide)
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
                mf.gameObject.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh;
        return g;
    }

    static void Living(Room r, bool tvOn)
    {
        Put("Sofa_01", 0f, 2.25f, 0f);
        Put("CoffeeTable_01", 0f, 1.2f, 0f, scale: 0.6f);
        Put("ArmChair_01", 2.1f, 0.9f, 240f);
        Put("side_table_01", -2.55f, 0.6f, 90f);
        var tv = Put("Television_01", -2.55f, 0.6f, 90f, y: 0.62f);
        if (tvOn) Screen(tv);
        var tb = TwinBatch.WorldBounds(tv);
        r.TvShotFrom = new Vector3(2.7f, 1.7f, 1.9f); r.TvAt = tb.center;
        Put("Shelf_01", -2.6f, -1.7f, 90f);
        Put("potted_plant_01", -2.5f, 2.2f, 0f);
        Put("potted_plant_02", 2.6f, 2.3f, 0f);
        Box("rug", new Vector3(0, 0.005f, 0.6f), new Vector3(2.6f, 0.01f, 1.8f), TwinBatch.Flat(new Color(0.42f, 0.30f, 0.26f), 0.05f));
        Box("yoga_mat", new Vector3(-1.1f, 0.012f, -0.1f), new Vector3(0.65f, 0.012f, 1.85f), TwinBatch.Flat(new Color(0.27f, 0.48f, 0.55f), 0.1f));
        r.Anchors["floor"] = new Vector3(0.3f, 0, 0.2f);
        r.Anchors["mat"] = new Vector3(-1.1f, 0.02f, -0.1f);
        r.Anchors["sofa"] = new Vector3(0f, 0.47f, 2.05f);
        r.Anchors["sofa_edge"] = new Vector3(0.85f, 0.45f, 1.9f);  // the sofa end, clear of the coffee table
        r.Anchors["armchair"] = new Vector3(2.0f, 0.45f, 0.85f);
        r.ShotCam = new Vector3(2.6f, 2.2f, -2.4f);
    }

    public static void Screen(GameObject tv)
    {
        var b = TwinBatch.WorldBounds(tv);
        var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
        q.name = "tv_screen";
        UnityEngine.Object.DestroyImmediate(q.GetComponent<Collider>());
        q.transform.position = new Vector3(b.max.x + 0.01f, b.center.y + 0.03f, b.center.z);
        q.transform.rotation = Quaternion.Euler(0, -90, 0);  // quad faces -z by default, turn it to face +x
        q.transform.localScale = new Vector3(b.size.z * 0.8f, b.size.y * 0.62f, 1);
        var m = new Material(Shader.Find("Standard"));
        m.color = Color.black; m.EnableKeyword("_EMISSION");
        m.SetColor("_EmissionColor", new Color(0.55f, 0.75f, 0.95f) * 1.6f);  // a lit hospital-drama frame
        q.GetComponent<Renderer>().sharedMaterial = m;
    }

    static void Kitchen(Room r)
    {
        var wood = TwinBatch.Surface("kitchen_wood", 1.5f); var top = TwinBatch.Surface("marble_01", 1f);
        Box("counter", new Vector3(0, 0.45f, 1.95f), new Vector3(3.6f, 0.9f, 0.6f), wood, collide: true);
        Box("counter_top", new Vector3(0, 0.92f, 1.95f), new Vector3(3.7f, 0.04f, 0.64f), top);
        Box("upper_cabinets", new Vector3(0, 1.85f, 2.05f), new Vector3(3.6f, 0.7f, 0.35f), wood);
        Put("WoodenTable_01", 1.3f, -0.2f, 0f);
        Put("WoodenChair_01", 0.6f, -0.2f, 90f);
        Put("potted_plant_02", -1.9f, -1.8f, 0f);
        r.Anchors["floor"] = new Vector3(-0.4f, 0, 0.6f);
        r.ShotCam = new Vector3(1.9f, 2.1f, -1.9f); r.CamBack = 2.7f;
    }

    static void Dining(Room r)
    {
        Put("dining_table", 0.2f, 1.0f, 0f);
        Put("dining_chair_02", -0.65f, 1.0f, 90f);
        Put("dining_chair_02", 1.05f, 1.0f, 270f);
        Put("vintage_cabinet_01", -2.2f, 1.6f, 90f);
        Put("ceramic_vase_01", 0.2f, 1.0f, 0f, collide: false, y: 0.76f);
        r.Anchors["chair"] = new Vector3(-0.65f, 0.47f, 0.25f);
        Put("dining_chair_02", -0.65f, 0.25f, 180f);
        r.Anchors["floor"] = new Vector3(-0.3f, 0, 0.2f);
        r.ShotCam = new Vector3(2.2f, 2.1f, -1.9f);
    }

    static void Bathroom(Room r)
    {
        var top = TwinBatch.Surface("marble_01", 1f); var white = TwinBatch.Flat(new Color(0.95f, 0.95f, 0.95f), 0.6f);
        Box("vanity", new Vector3(-0.6f, 0.42f, 1.45f), new Vector3(1.1f, 0.84f, 0.5f), TwinBatch.Surface("kitchen_wood", 1f), collide: true);
        Box("vanity_top", new Vector3(-0.6f, 0.86f, 1.45f), new Vector3(1.15f, 0.04f, 0.54f), top);
        Box("basin", new Vector3(-0.6f, 0.9f, 1.45f), new Vector3(0.45f, 0.06f, 0.34f), white);
        Box("mirror", new Vector3(-0.6f, 1.55f, 1.64f), new Vector3(0.9f, 0.7f, 0.02f), TwinBatch.Flat(new Color(0.8f, 0.85f, 0.9f), 0.95f));
        Box("toilet", new Vector3(0.9f, 0.22f, 1.35f), new Vector3(0.4f, 0.44f, 0.6f), white, collide: true);
        Box("bathtub", new Vector3(1.05f, 0.28f, -0.6f), new Vector3(0.9f, 0.56f, 1.7f), white, collide: true);
        r.Anchors["floor"] = new Vector3(-0.35f, 0, 0.6f);
        r.ShotCam = new Vector3(1.3f, 2.1f, -1.4f); r.CamBack = 2.0f;
    }

    static void Bedroom(Room r)
    {
        Put("old_bed_frame", 0.4f, 1.3f, 180f);
        Box("mattress", new Vector3(0.4f, 0.52f, 1.3f), new Vector3(1.45f, 0.22f, 1.95f), TwinBatch.Flat(new Color(0.86f, 0.84f, 0.8f), 0.05f), collide: true);
        Box("blanket", new Vector3(0.4f, 0.64f, 1.0f), new Vector3(1.5f, 0.04f, 1.2f), TwinBatch.Flat(new Color(0.36f, 0.42f, 0.55f), 0.05f));
        Put("side_table_01", -0.7f, 2.0f, 180f);
        Put("wooden_bookshelf_worn", -2.2f, 0.4f, 90f);
        Put("potted_plant_01", 2.1f, -1.9f, 0f);
        r.Anchors["bed"] = new Vector3(0.4f, 0.67f, 1.3f);
        r.Anchors["floor"] = new Vector3(-0.6f, 0, 0.1f);
        r.ShotCam = new Vector3(2.2f, 2.2f, -2.1f);
    }

    static void Hallway(Room r)
    {
        Put("wooden_bookshelf_worn", -0.95f, 1.6f, 90f);
        Put("ceramic_vase_01", 0.9f, 2.4f, 0f);
        Put("Ottoman_01", 0.8f, -1.2f, 0f);
        r.Anchors["floor"] = new Vector3(0.1f, 0, 0.7f);
        r.ShotCam = new Vector3(0.9f, 2.2f, -2.6f); r.CamBack = 3.2f;
    }

    static void Sunroom(Room r)
    {
        Put("planter_box_01", 0.5f, 1.6f, 0f);
        Put("potted_plant_01", -1.5f, 1.8f, 0f);
        Put("potted_plant_02", 1.8f, 1.7f, 0f);
        Put("potted_plant_01", -1.8f, -1.6f, 0f);
        Put("modern_arm_chair_01", 1.7f, -0.9f, 300f);
        r.Anchors["floor"] = new Vector3(0.5f, 0, 0.9f);
        r.ShotCam = new Vector3(1.9f, 2.1f, -1.9f);
    }
}

// --------------------------------------------------------------------- avatars
public static class Avatars
{
    public static GameObject Spawn(string name)
    {
        string dir = "Assets/ThirdParty/Rocketbox/" + name + "/Export/" + name + ".fbx";
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(dir);
        if (prefab == null) throw new Exception("avatar not found: " + dir);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        var an = go.GetComponent<Animator>();
        if (an == null || an.avatar == null || !an.avatar.isHuman) throw new Exception("avatar is not a valid humanoid: " + name);
        an.enabled = false;
        foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>()) { smr.updateWhenOffscreen = true; Skin(smr, name); }
        // normalise height: adults 1.74 m, children 1.20 m
        float target = name.Contains("Child") ? 1.2f : 1.74f;
        Posture.Apply(go, "stand");
        var b = TwinBatch.WorldBounds(go);
        go.transform.localScale *= target / Mathf.Max(b.size.y, 0.1f);
        return go;
    }

    // Rocketbox ships body, head and opacity (hair, lashes) textures per avatar; the imported
    // materials do not pick them up, so each slot is rebuilt from the avatar's Textures folder
    static void Skin(SkinnedMeshRenderer smr, string name)
    {
        string dir = "Assets/ThirdParty/Rocketbox/" + name + "/Textures/";
        Texture2D T(string part, string kind)
        {
            foreach (var p in System.IO.Directory.GetFiles(dir))
            {
                string n = System.IO.Path.GetFileName(p).ToLowerInvariant();
                if (!n.EndsWith(".meta") && n.Contains("_" + part + "_" + kind)) return AssetDatabase.LoadAssetAtPath<Texture2D>(p.Replace('\\', '/'));
            }
            return null;
        }
        var mats = smr.sharedMaterials;
        for (int i = 0; i < mats.Length; i++)
        {
            string mn = (mats[i] != null ? mats[i].name : "").ToLowerInvariant();
            string part = mn.Contains("head") ? "head" : (mn.Contains("opacity") || mn.Contains("hair") || mn.Contains("lash") || mn.Contains("eye")) ? "opacity" : "body";
            var m = new Material(Shader.Find("Standard"));
            m.mainTexture = T(part, "color");
            var nrm = T(part, "normal");
            if (nrm != null) { m.SetTexture("_BumpMap", nrm); m.EnableKeyword("_NORMALMAP"); }
            m.SetFloat("_Glossiness", part == "head" ? 0.35f : 0.2f);
            if (part == "opacity")
            {
                m.SetFloat("_Mode", 1f); m.SetFloat("_Cutoff", 0.4f);
                m.EnableKeyword("_ALPHATEST_ON"); m.SetOverrideTag("RenderType", "TransparentCutout");
                m.renderQueue = 2450;
            }
            Debug.Log($"TWIN_SKIN {name} slot {i} '{mn}' -> {part} tex={(m.mainTexture != null ? m.mainTexture.name : "none")}");
            mats[i] = m;
        }
        smr.sharedMaterials = mats;
    }

    public static Vector3 Facing(GameObject go) => Body.Facing(go);

    // make the body axis vertical: feet-to-head for standing and lying postures, feet-to-hips for
    // bending (the torso is meant to lean), hips-to-head for seated and kneeling ones
    static void Straighten(GameObject go, string posture)
    {
        var an = go.GetComponent<Animator>();
        Vector3 P(HumanBodyBones b) => an.GetBoneTransform(b).position;
        Vector3 feet = (P(HumanBodyBones.LeftFoot) + P(HumanBodyBones.RightFoot)) / 2f;
        Vector3 from, to;
        if (posture == "bend") { from = feet; to = P(HumanBodyBones.Hips); }
        else if (posture.StartsWith("sit") || posture == "kneel" || posture == "play") { from = P(HumanBodyBones.Hips); to = P(HumanBodyBones.Head); }
        else { from = feet; to = P(HumanBodyBones.Head); }
        var q = Quaternion.FromToRotation((to - from).normalized, Vector3.up);
        q.ToAngleAxis(out float ang, out Vector3 axis);
        if (ang > 0.01f) go.transform.RotateAround(P(HumanBodyBones.Hips), axis, ang);
    }

    public static void PlaceAt(GameObject go, Vector3 anchor, float yaw, string posture)
    {
        Straighten(go, posture);
        // turn so the character faces yaw (0 = toward the robot camera at -z)
        var f = Facing(go);
        float cur = Mathf.Atan2(f.x, f.z) * Mathf.Rad2Deg;
        go.transform.RotateAround(go.transform.position, Vector3.up, (180f + yaw) - cur);
        var an = go.GetComponent<Animator>();
        Vector3 right = an.GetBoneTransform(HumanBodyBones.RightUpperLeg).position - an.GetBoneTransform(HumanBodyBones.LeftUpperLeg).position;
        right.y = 0; right.Normalize();
        var hips = an.GetBoneTransform(HumanBodyBones.Hips).position;
        // lying and plank postures: tip the whole body about its own left-right axis
        if (posture == "supine" || posture == "yoga") go.transform.RotateAround(hips, right, -90f);
        else if (posture == "prone" || posture == "stretch" || posture == "pushup" || posture == "play") go.transform.RotateAround(hips, right, 90f);
        // put the lowest point on the anchor's surface; seated postures put the hips on it
        var b = TwinBatch.WorldBounds(go);
        Vector3 shift;
        if (posture == "sit" || posture == "sit_edge" || posture == "sit_chest")
        {
            hips = an.GetBoneTransform(HumanBodyBones.Hips).position;
            shift = new Vector3(anchor.x - hips.x, anchor.y + 0.08f - hips.y, anchor.z - hips.z);
        }
        else shift = new Vector3(anchor.x - b.center.x, anchor.y - b.min.y, anchor.z - b.center.z);
        go.transform.position += shift;
    }
}

