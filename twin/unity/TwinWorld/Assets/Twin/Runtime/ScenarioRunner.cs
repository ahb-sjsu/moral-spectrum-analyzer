using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

// Plays scenario scripts (docs/AUTONOMY_PLAN.md, section 6) against the running twin:
//   TwinGame.x86_64 -scenarios <file.jsonl> -results <file.jsonl> [-only id,id] [-shots dir]
//                   [-storyboard dir]
// -storyboard: a framed render of the room (no UI) after each script call, after each action the
// robot performs, and at the end, written as <id>_<nn>.png with storyboard.jsonl captions.
// For each scenario: reset the world, run its timed world-API calls, let the robot act for the
// scenario's length plus a margin, then write one result line: the scenario id, the calls the
// simulator could not perform, and the robot's decision records (seq, hash, events, rulings,
// actions) for grading. The runner reads only `id` and `script`; descriptions, classes and
// expected actions are never passed to the world or the robot.
public class ScenarioRunner : MonoBehaviour
{
    public World world;
    public RobotAgent robot;
    public Responders responders;

    // the storyboard capture (-storyboard dir)
    string storyDir, storyId; int storyN; StreamWriter storyLog; Camera storyCam;

    void Start()
    {
        storyDir = RobotAgent.Arg("-storyboard");
        if (!string.IsNullOrEmpty(storyDir))
        {
            Directory.CreateDirectory(storyDir);
            storyLog = new StreamWriter(Path.Combine(storyDir, "storyboard.jsonl"), append: true);
            storyCam = GameObject.Find("view_camera")?.GetComponent<Camera>();
            robot.OnPerformed += a => { if (storyId != null) StartCoroutine(Shot("robot: " + a, 0.5f)); };
        }
        else storyDir = null;
        string file = RobotAgent.Arg("-scenarios");
        if (!string.IsNullOrEmpty(file)) StartCoroutine(Run(file, RobotAgent.Arg("-results") ?? "results.jsonl", RobotAgent.Arg("-only"), RobotAgent.Arg("-shots")));
    }

    IEnumerator Run(string file, string results, string only, string shots)
    {
        var keep = string.IsNullOrEmpty(only) ? null : new HashSet<string>(only.Split(','));
        var lines = File.ReadAllLines(file).Where(l => l.Trim() != "").ToList();
        if (!string.IsNullOrEmpty(shots)) Directory.CreateDirectory(shots);
        using (var w = new StreamWriter(results, append: true))
        {
            foreach (var line in lines)
            {
                var sc = MiniJson.Obj(MiniJson.Parse(line));
                string id = MiniJson.S(sc["id"]);
                if (keep != null && !keep.Contains(id)) continue;
                var script = MiniJson.Arr(sc["script"]).Select(MiniJson.Obj).OrderBy(c => c.TryGetValue("t", out var t) && t is double d ? d : 0).ToList();
                float w0 = Time.time;
                while ((robot.busy || robot.performing || responders.Busy) && Time.time - w0 < 120f) yield return null;
                world.ResetWorld(); world.unsupported.Clear();
                while (robot.busy) yield return null;
                yield return new WaitForSeconds(1f);   // the brain's reset arrives before the script starts
                int first = robot.cycles.Count, errors0 = robot.brainErrors;
                storyId = id; storyN = 0;
                float t0 = Time.time, end = script.Count == 0 ? 0 : script.Max(c => c.TryGetValue("t", out var t) && t is double d ? (float)d : 0f);
                foreach (var c in script)
                {
                    float at = c.TryGetValue("t", out var tv) && tv is double dv ? (float)dv : 0f;
                    while (Time.time - t0 < at) yield return null;
                    world.Call(MiniJson.S(c["call"]), MiniJson.Obj(c.TryGetValue("args", out var a) ? a : null));
                    if (storyDir != null) StartCoroutine(Shot("world: " + MiniJson.S(c["call"]), 2.5f));
                }
                // let the robot respond: a decision takes tens of seconds, so allow up to five minutes
                // after the last call, ending once the robot has been idle (not deciding, not acting) for 60 s
                float settle = Time.time;
                while (Time.time - t0 < end + 300f)
                {
                    if (robot.busy || robot.performing || responders.Busy) settle = Time.time;
                    if (Time.time - settle > 60f && Time.time - t0 > end + 60f) break;
                    yield return null;
                }
                float w1 = Time.time;
                while ((robot.busy || robot.performing || responders.Busy) && Time.time - w1 < 120f) yield return null;
                if (!string.IsNullOrEmpty(shots)) { ScreenCapture.CaptureScreenshot(Path.Combine(shots, id + ".png")); yield return null; }
                if (storyDir != null) { yield return Shot("end", 0f); storyId = null; }
                var recs = robot.cycles.Skip(first).Select(r => (object)new Dictionary<string, object>
                    { ["seq"] = MiniJson.Obj(r["record"])["seq"], ["hash"] = r["hash"], ["record"] = r["record"] }).ToList();
                w.WriteLine(MiniJson.Write(new Dictionary<string, object>
                    { ["id"] = id, ["unsupported_calls"] = world.unsupported.ToList(), ["sim_minutes"] = world.simMinutes,
                      ["brain_errors"] = (double)(robot.brainErrors - errors0), ["records"] = recs }));
                w.Flush();
                Debug.Log($"SCENARIO_DONE {id} records={recs.Count} unsupported={world.unsupported.Count} brain_errors={robot.brainErrors - errors0}");
            }
        }
        storyLog?.Dispose();
        Debug.Log("SCENARIOS_ALL_DONE");
        Application.Quit(0);
    }
    // where a body is drawn: root transforms of the imported avatars sit away from their meshes
    static Vector3 Drawn(GameObject g)
    {
        var rs = g.GetComponentsInChildren<Renderer>().Where(r => r.enabled).ToList();
        if (rs.Count == 0) return g.transform.position;
        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
        return b.center;
    }

    // one framed render of the room, without the UI: from inside the room, high in the corner
    // farthest from the action (below the ceiling), aimed at the middle of who is there
    // (Margaret, the robot, the dog, a visitor, the coyote)
    IEnumerator Shot(string label, float delay)
    {
        if (delay > 0f) yield return new WaitForSeconds(delay);
        string id = storyId;
        if (storyCam == null || id == null) yield break;
        yield return new WaitForEndOfFrame();
        var pts = new List<Vector3> { Drawn(world.margaret), Drawn(robot.gameObject) };
        foreach (var g in new[] { world.dog, world.stranger, world.wildAnimal })
            if (g && g.activeInHierarchy) pts.Add(Drawn(g));
        var floor = GameObject.Find("floor")?.GetComponent<Renderer>();
        var room = floor ? floor.bounds : new Bounds(Vector3.zero, new Vector3(8.4f, 0.1f, 6f));
        pts = pts.Select(p => new Vector3(Mathf.Clamp(p.x, room.min.x, room.max.x), p.y, Mathf.Clamp(p.z, room.min.z, room.max.z))).ToList();
        var mid = pts.Aggregate(Vector3.zero, (a, p) => a + p) / pts.Count;
        var pivot = new Vector3(mid.x, 0.8f, mid.z);
        var corners = new[] { new Vector3(room.min.x, 0, room.min.z), new Vector3(room.min.x, 0, room.max.z),
                              new Vector3(room.max.x, 0, room.min.z), new Vector3(room.max.x, 0, room.max.z) };
        var far = corners.OrderByDescending(c => (c - new Vector3(mid.x, 0, mid.z)).sqrMagnitude).First();
        var inset = (new Vector3(mid.x, 0, mid.z) - far).normalized * 0.35f;
        float fov0 = storyCam.fieldOfView; storyCam.fieldOfView = 62f;
        var tr = storyCam.transform; var pos0 = tr.position; var rot0 = tr.rotation;
        tr.position = far + inset + Vector3.up * 2.35f;
        tr.LookAt(pivot);
        var rt = RenderTexture.GetTemporary(1600, 900, 24);
        var target0 = storyCam.targetTexture; storyCam.targetTexture = rt; storyCam.Render(); storyCam.targetTexture = target0;
        var active0 = RenderTexture.active; RenderTexture.active = rt;
        var tex = new Texture2D(1600, 900, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, 1600, 900), 0, 0); tex.Apply();
        RenderTexture.active = active0; RenderTexture.ReleaseTemporary(rt);
        tr.SetPositionAndRotation(pos0, rot0); storyCam.fieldOfView = fov0;
        storyN++;
        string name = $"{id}_{storyN:00}.png";
        File.WriteAllBytes(Path.Combine(storyDir, name), tex.EncodeToPNG());
        Destroy(tex);
        storyLog.WriteLine(MiniJson.Write(new Dictionary<string, object>
            { ["id"] = id, ["n"] = (double)storyN, ["file"] = name, ["label"] = label, ["sim_minutes"] = (double)world.simMinutes,
              ["robot"] = robot.status, ["speech"] = robot.speech }));
        storyLog.Flush();
    }
}
