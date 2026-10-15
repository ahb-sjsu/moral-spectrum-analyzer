using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

// Plays scenario scripts (docs/AUTONOMY_PLAN.md, section 6) against the running twin:
//   TwinGame.x86_64 -scenarios <file.jsonl> -results <file.jsonl> [-only id,id] [-shots dir]
//                   [-storyboard dir] [-stay]
// -storyboard: a framed render of the room (no UI) after each script call, after each action the
// robot performs, and at the end, written as <id>_<nn>.png with storyboard.jsonl captions.
// For each scenario: reset the world, run its timed world-API calls, let the robot act for the
// scenario's length plus a margin, then write one result line: the scenario id, the calls the
// simulator could not perform, and the robot's decision records (seq, hash, events, rulings,
// actions) for grading. The runner reads only `id` and `script` (and `title`, `intro` and each
// proposal's `say` for the audience's cards and captions); descriptions, classes and expected
// actions are never passed to the world or the robot, and the cards never reach the brain.
public class ScenarioRunner : MonoBehaviour
{
    public World world;
    public RobotAgent robot;
    public Responders responders;

    // the storyboard capture (-storyboard dir)
    string storyDir, storyId; int storyN; StreamWriter storyLog; Camera storyCam;

    // the scene card (owner, 2026-10-15: "each scene should have a clear beginning and end, and an
    // intro explaining what it is demonstrating"): an intro card before the scene's clock starts, a
    // banner while it runs, and an end card listing each proposal's verdict, read from its record
    public enum Phase { None, Intro, Running, End }
    public Phase phase = Phase.None;
    public string cardTitle = "", cardBody = "", banner = "";

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
        // every Start has run before the first reset, so the robot is subscribed and the brain is reset:
        // the first reset used to fire inside this Start, and the first scenario of each launch inherited
        // the brain's moral state from the run before (dev33: d16 began owing a centre call from d15)
        yield return null; yield return null;
        var keep = string.IsNullOrEmpty(only) ? null : new HashSet<string>(only.Split(','));
        var lines = File.ReadAllLines(file).Where(l => l.Trim() != "").ToList();
        if (!string.IsNullOrEmpty(shots)) Directory.CreateDirectory(shots);
        var scenes = lines.Select(l => MiniJson.Obj(MiniJson.Parse(l))).Where(s => keep == null || keep.Contains(MiniJson.S(s["id"]))).ToList();
        using (var w = new StreamWriter(results, append: true))
        {
            for (int k = 0; k < scenes.Count; k++)
            {
                var sc = scenes[k];
                string id = MiniJson.S(sc["id"]);
                string title = sc.TryGetValue("title", out var tt) ? MiniJson.S(tt) : id;
                string intro = sc.TryGetValue("intro", out var iv) ? MiniJson.S(iv) : "";
                string which = scenes.Count > 1 ? $"Scene {k + 1} of {scenes.Count}" : "Scene";
                // world calls, and in a gate demonstration the scripted proposals, in one timeline
                // (a proposal is marked by "propose"; owner, 2026-10-14: DEME gates proposed acts)
                var proposals = MiniJson.Arr(sc.TryGetValue("proposals", out var pv) ? pv : null).Select(MiniJson.Obj)
                    .Select(x => { var y = new Dictionary<string, object>(x); y["propose"] = true; return y; });
                var script = MiniJson.Arr(sc["script"]).Select(MiniJson.Obj).Concat(proposals)
                    .OrderBy(c => c.TryGetValue("t", out var t) && t is double d ? d : 0).ToList();
                float w0 = Time.time;
                while ((robot.busy || robot.performing || responders.Busy) && Time.time - w0 < 120f) yield return null;
                world.ResetWorld(); world.unsupported.Clear(); robot.NewScene();
                while (robot.busy) yield return null;
                yield return new WaitForSeconds(1f);   // the brain's reset arrives before the script starts
                // the intro card, before the scene's clock starts: what happens and what it shows
                if (intro != "")
                {
                    cardTitle = $"{which}: {title}"; cardBody = intro; phase = Phase.Intro;
                    yield return new WaitForSeconds(sc.TryGetValue("intro_s", out var isv) && isv is double ids ? (float)ids : 18f);
                }
                banner = $"{which}: {title}"; phase = Phase.Running;
                int first = robot.cycles.Count, errors0 = robot.brainErrors, refused0 = robot.actuatorRefusals.Count, her0 = robot.withheldForHerWords.Count;
                storyId = id; storyN = 0;
                float t0 = Time.time, end = script.Count == 0 ? 0 : script.Max(c => c.TryGetValue("t", out var t) && t is double d ? (float)d : 0f);
                foreach (var c in script)
                {
                    float at = c.TryGetValue("t", out var tv) && tv is double dv ? (float)dv : 0f;
                    while (Time.time - t0 < at) yield return null;
                    if (c.ContainsKey("propose"))
                    {
                        var prop = new Dictionary<string, object>(c); prop.Remove("propose");
                        if (!prop.ContainsKey("by")) prop["by"] = "script";
                        yield return robot.Propose(prop);
                        if (storyDir != null) StartCoroutine(Shot("proposed: " + MiniJson.S(prop["action"]), 1.5f));
                        continue;
                    }
                    world.Call(MiniJson.S(c["call"]), MiniJson.Obj(c.TryGetValue("args", out var a) ? a : null));
                    if (storyDir != null) StartCoroutine(Shot("world: " + MiniJson.S(c["call"]), 2.5f));
                }
                // let the robot respond: a decision takes tens of seconds, so allow up to five minutes
                // after the last call, ending once the robot has been idle (not deciding, not acting) for 60 s;
                // in a gate demonstration the robot acts only on proposals, so 15 s idle ends the scene
                // (owner, 2026-10-15: the scenes had no clear end)
                float settle = Time.time, idle = robot.gate ? 15f : 60f;
                while (Time.time - t0 < end + 300f)
                {
                    if (robot.busy || robot.performing || responders.Busy) settle = Time.time;
                    if (Time.time - settle > idle && Time.time - t0 > end + idle) break;
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
                      ["brain_errors"] = (double)(robot.brainErrors - errors0), ["records"] = recs,
                      ["actuator"] = robot.manifestStatus, ["actuator_refusals"] = robot.actuatorRefusals.Skip(refused0).Cast<object>().ToList(),
                      ["withheld_for_her_words"] = robot.withheldForHerWords.Skip(her0).Cast<object>().ToList() }));
                w.Flush();
                Debug.Log($"SCENARIO_DONE {id} records={recs.Count} unsupported={world.unsupported.Count} brain_errors={robot.brainErrors - errors0}");
                // the end card: each proposal of the scene and its verdict, from the records
                if (intro != "")
                {
                    var lines2 = robot.cycles.Skip(first).Select(r => MiniJson.Obj(r["record"]))
                        .Where(r => MiniJson.S(r.TryGetValue("kind", out var kk) ? kk : "") == "proposal" && r.TryGetValue("proposal", out var pp) && pp != null)
                        .Select(r =>
                        {
                            string act = MiniJson.S(MiniJson.Obj(r["proposal"])["action"]).Replace("_", " ");
                            bool ok = MiniJson.S(r["verdict"]) == "passed";
                            string by = MiniJson.S(r.TryGetValue("stopped_by", out var sb) ? sb : "");
                            return ok ? $"<b>{act}</b>:  <color=#56d364>passed all checks</color>, the robot went ahead"
                                      : $"<b>{act}</b>:  <color=#ff7b72>stopped by {(by == "deme" ? "DEME" : by)}</color>, the robot held";
                        }).ToList();
                    string next = k + 1 < scenes.Count ? $"Next: {MiniJson.S(scenes[k + 1].TryGetValue("title", out var nt) ? nt : scenes[k + 1]["id"])}" : "End of the scenes.";
                    cardTitle = $"End of {which.ToLower()}: {title}";
                    cardBody = (lines2.Count > 0 ? "What was proposed, and what the checks did:\n" + string.Join("\n", lines2) : "No act was proposed.") + "\n\n<i>" + next + "</i>";
                    phase = Phase.End;
                    yield return new WaitForSeconds(12f);
                }
                phase = Phase.None; banner = "";
            }
        }
        storyLog?.Dispose();
        Debug.Log("SCENARIOS_ALL_DONE");
        // -stay: a live demonstration keeps the window open for questions after the last scenario
        if (System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-stay") < 0) Application.Quit(0);
    }
    // where a body is drawn: root transforms of the imported avatars sit away from their meshes
    static Vector3 Drawn(GameObject g)
    {
        var rs = g.GetComponentsInChildren<Renderer>().Where(r => r.enabled).ToList();
        if (rs.Count == 0) return g.transform.position;
        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
        return b.center;
    }

    // tall things inside the room that can stand between the camera and the people (a partition,
    // the wardrobe, the bookshelf); the outer walls, floor and ceiling are not counted
    List<Bounds> blockers;
    List<Bounds> Blockers()
    {
        var actors = new[] { world.margaret, robot.gameObject, world.dog, world.stranger, world.wildAnimal };
        return FindObjectsOfType<Renderer>()
            .Where(r => r.bounds.size.y > 1.2f && !r.name.StartsWith("wall_") && r.name != "floor" && r.name != "ceiling")
            .Where(r => !actors.Any(a => a && r.transform.IsChildOf(a.transform)))
            .Select(r => r.bounds).ToList();
    }

    // one framed render of the room, without the UI: from inside the room, below the ceiling and
    // close to who is there (Margaret, the robot, the dog, a visitor, the coyote), on the first of
    // eight bearings that sees all of them past the tall furniture
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
        var pivot = new Vector3(mid.x, 0.75f, mid.z);
        float spread = pts.Max(p => new Vector2(p.x - mid.x, p.z - mid.z).magnitude);
        float reach = Mathf.Clamp(2.4f + spread * 1.3f, 2.8f, 5.5f);
        blockers ??= Blockers();
        Vector3 best = Vector3.zero; int bestSeen = -1; float bestReach = 0f;
        for (int k = 0; k < 8; k++)
        {
            // the first bearing looks from the room's south-west, as the live view does
            var dir = Quaternion.Euler(0f, -35f + 45f * k, 0f) * Vector3.back;
            var c = pivot + dir * reach;
            c = new Vector3(Mathf.Clamp(c.x, room.min.x + 0.3f, room.max.x - 0.3f), 2.2f, Mathf.Clamp(c.z, room.min.z + 0.3f, room.max.z - 0.3f));
            // clear of tall furniture by 0.6 m: a camera just outside a shelf's bounds draws the
            // shelf as a wedge across the frame
            if (blockers.Any(b => { var e = b; e.Expand(1.2f); return e.Contains(c); })) continue;
            int seen = pts.Count(p => !blockers.Any(b => b.IntersectRay(new Ray(c, p - c), out float d) && d < Vector3.Distance(c, p) - 0.3f));
            float got = new Vector2(c.x - pivot.x, c.z - pivot.z).magnitude;
            // all actors seen first, then the bearing the walls cut least
            if (seen > bestSeen || (seen == bestSeen && got > bestReach + 0.5f)) { best = c; bestSeen = seen; bestReach = got; }
        }
        if (bestSeen < 0) best = new Vector3(Mathf.Clamp(pivot.x, room.min.x + 0.3f, room.max.x - 0.3f), 2.2f, room.min.z + 0.3f);
        float fov0 = storyCam.fieldOfView; storyCam.fieldOfView = 60f;
        var tr = storyCam.transform; var pos0 = tr.position; var rot0 = tr.rotation;
        tr.position = best;
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
        // with -shots as well: what the audience sees at the same moment (the live view and its UI)
        string live = RobotAgent.Arg("-shots");
        if (!string.IsNullOrEmpty(live)) ScreenCapture.CaptureScreenshot(Path.Combine(live, $"{id}_{storyN:00}_live.png"));
        storyLog.WriteLine(MiniJson.Write(new Dictionary<string, object>
            { ["id"] = id, ["n"] = (double)storyN, ["file"] = name, ["label"] = label, ["sim_minutes"] = (double)world.simMinutes,
              ["robot"] = robot.status, ["speech"] = robot.speech,
              // where each figure is drawn and where its root transform is (perception measures roots)
              ["margaret_at"] = Drawn(world.margaret).ToString("F2"), ["robot_at"] = Drawn(robot.gameObject).ToString("F2"),
              ["margaret_root"] = world.margaret.transform.position.ToString("F2"), ["robot_root"] = robot.transform.position.ToString("F2") }));
        storyLog.Flush();
    }
}
