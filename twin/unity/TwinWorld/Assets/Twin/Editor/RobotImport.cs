using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using Unity.Robotics.UrdfImporter;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Imports the Unitree G1 description (BSD-3-Clause) once and saves it as a kinematic prefab:
// the URDF importer builds articulation bodies and colliders, which are removed, and a RobotRig
// records each revolute joint's link, axis and limits from the URDF itself.
//
//   Unity -batchmode ... -executeMethod RobotImport.Run -out <dir>
public static class RobotImport
{
    const string URDF = "Assets/ThirdParty/Robots/g1_description/g1_29dof_rev_1_0.urdf";
    public const string PREFAB = "Assets/Twin/Robots/G1.prefab";

    public static void Run()
    {
        try
        {
            Build();
            Preview(Arg("-out"));
            EditorApplication.Exit(0);
        }
        catch (Exception e) { Debug.LogError("ROBOT_IMPORT_FAIL " + e); EditorApplication.Exit(1); }
    }

    static string Arg(string name)
    {
        var a = Environment.GetCommandLineArgs();
        int i = Array.IndexOf(a, name);
        return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
    }

    public static GameObject Build()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var settings = new ImportSettings { chosenAxis = ImportSettings.axisType.yAxis, convexMethod = ImportSettings.convexDecomposer.unity };
        var it = UrdfRobotExtensions.Create(Path.GetFullPath(URDF), settings, false, false);
        GameObject robot = null;
        while (it.MoveNext()) if (it.Current != null) robot = it.Current;
        if (robot == null) throw new Exception("URDF import returned nothing");
        robot.name = "G1";

        // strip physics and importer components, deepest first (joints depend on their parents)
        foreach (var t in robot.GetComponentsInChildren<Transform>(true).Where(t => t.name == "Collisions").ToList())
            UnityEngine.Object.DestroyImmediate(t.gameObject);
        // a component another one requires cannot be removed first, so repeat until none is left
        for (int pass = 0; pass < 10; pass++)
        {
            var left = robot.GetComponentsInChildren<Component>(true)
                .Where(c => c != null && !(c is Transform) && !(c is MeshFilter) && !(c is MeshRenderer))
                .OrderBy(c => c is ArticulationBody ? 1 : 0).ThenByDescending(c => Depth(c.transform)).ToList();
            if (left.Count == 0) break;
            foreach (var c in left) if (c != null) UnityEngine.Object.DestroyImmediate(c);
        }
        int remaining = robot.GetComponentsInChildren<Component>(true).Count(c => !(c is Transform) && !(c is MeshFilter) && !(c is MeshRenderer));
        if (remaining > 0) throw new Exception($"{remaining} physics or importer components could not be removed from the robot");

        var rig = robot.AddComponent<RobotRig>();
        var links = robot.GetComponentsInChildren<Transform>(true).GroupBy(t => t.name).ToDictionary(g => g.Key, g => g.First());
        var doc = XDocument.Load(URDF);
        foreach (var j in doc.Root.Elements("joint").Where(j => (string)j.Attribute("type") == "revolute"))
        {
            string child = (string)j.Element("child").Attribute("link");
            if (!links.TryGetValue(child, out var link)) { Debug.LogWarning("no link " + child); continue; }
            var ax = ((string)j.Element("axis")?.Attribute("xyz") ?? "1 0 0").Split(' ').Select(v => float.Parse(v, CultureInfo.InvariantCulture)).ToArray();
            var lim = j.Element("limit");
            rig.joints.Add(new RobotRig.Joint
            {
                name = (string)j.Attribute("name"),
                link = link,
                axis = new Vector3(-ax[1], ax[2], ax[0]),  // ROS (x fwd, y left, z up) to Unity (x right, y up, z fwd)
                rest = link.localRotation,
                lower = lim != null ? float.Parse((string)lim.Attribute("lower"), CultureInfo.InvariantCulture) : -3.14f,
                upper = lim != null ? float.Parse((string)lim.Attribute("upper"), CultureInfo.InvariantCulture) : 3.14f,
            });
        }
        Debug.Log($"ROBOT_JOINTS {rig.joints.Count}: {string.Join(",", rig.joints.Select(j => j.name))}");
        var b = TwinBatch.WorldBounds(robot);
        Debug.Log($"ROBOT_BOUNDS size={b.size} min={b.min}");

        Directory.CreateDirectory(Path.GetDirectoryName(PREFAB));
        var prefab = PrefabUtility.SaveAsPrefabAsset(robot, PREFAB);
        Debug.Log("ROBOT_PREFAB " + AssetDatabase.GetAssetPath(prefab));
        return robot;
    }

    static int Depth(Transform t) { int d = 0; while (t.parent != null) { t = t.parent; d++; } return d; }

    // the robot in the living room, in each named pose, for a visual check of joint signs
    static void Preview(string outDir)
    {
        if (string.IsNullOrEmpty(outDir)) return;
        Directory.CreateDirectory(outDir);
        foreach (var pose in new[] { "stand", "reach", "call", "hold", "step" })
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            Rooms.Build("living", false);
            var g = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(PREFAB));
            var rig = g.GetComponent<RobotRig>();
            if (pose == "step") rig.Step(1.2f); else rig.Pose(pose);
            var b = TwinBatch.WorldBounds(g);
            g.transform.position += new Vector3(-0.3f - b.center.x, -b.min.y, 0.2f - b.center.z);
            var cam = new GameObject("cam").AddComponent<Camera>();
            cam.transform.position = new Vector3(1.6f, 1.2f, -1.6f); cam.transform.LookAt(new Vector3(-0.3f, 0.7f, 0.2f));
            cam.fieldOfView = 55f;
            var rt = RenderTexture.GetTemporary(512, 512, 24); rt.antiAliasing = 4;
            cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
            var tex = new Texture2D(512, 512, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, 512, 512), 0, 0); tex.Apply();
            File.WriteAllBytes(Path.Combine(outDir, "robot_" + pose + ".png"), tex.EncodeToPNG());
            RenderTexture.active = null; RenderTexture.ReleaseTemporary(rt);
        }
    }
}
