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
    // one framed render of the room, without the UI: the view camera aimed at the middle of who is
    // there (Margaret, the robot, the dog, a visitor, the coyote) and drawn back to fit them all
    IEnumerator Shot(string label, float delay)
    {
        if (delay > 0f) yield return new WaitForSeconds(delay);
        string id = storyId;
        if (storyCam == null || id == null) yield break;
        yield return new WaitForEndOfFrame();
        var pts = new List<Vector3> { world.margaret.transform.position, robot.transform.position };
        foreach (var g in new[] { world.dog, world.stranger, world.wildAnimal })
            if (g && g.activeInHierarchy) pts.Add(g.transform.position);
        var mid = pts.Aggregate(Vector3.zero, (a, p) => a + p) / pts.Count;
        float r = pts.Max(p => Vector3.Distance(p, mid));
        var pivot = mid + Vector3.up * 0.7f;
        float dist = Mathf.Clamp(3f + r * 1.8f, 3.4f, 9f);
        var tr = storyCam.transform; var pos0 = tr.position; var rot0 = tr.rotation;
        tr.position = pivot + Quaternion.Euler(38f, -35f, 0f) * new Vector3(0f, 0f, -dist);
        tr.LookAt(pivot);
        var rt = RenderTexture.GetTemporary(1600, 900, 24);
        var target0 = storyCam.targetTexture; storyCam.targetTexture = rt; storyCam.Render(); storyCam.targetTexture = target0;
        var active0 = RenderTexture.active; RenderTexture.active = rt;
        var tex = new Texture2D(1600, 900, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, 1600, 900), 0, 0); tex.Apply();
        RenderTexture.active = active0; RenderTexture.ReleaseTemporary(rt);
        tr.SetPositionAndRotation(pos0, rot0);
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
