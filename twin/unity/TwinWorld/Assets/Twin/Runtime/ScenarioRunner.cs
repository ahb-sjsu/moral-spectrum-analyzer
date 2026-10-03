using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

// Plays scenario scripts (docs/AUTONOMY_PLAN.md, section 6) against the running twin:
//   TwinGame.x86_64 -scenarios <file.jsonl> -results <file.jsonl> [-only id,id] [-shots dir]
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

    void Start()
    {
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
                float t0 = Time.time, end = script.Count == 0 ? 0 : script.Max(c => c.TryGetValue("t", out var t) && t is double d ? (float)d : 0f);
                foreach (var c in script)
                {
                    float at = c.TryGetValue("t", out var tv) && tv is double dv ? (float)dv : 0f;
                    while (Time.time - t0 < at) yield return null;
                    world.Call(MiniJson.S(c["call"]), MiniJson.Obj(c.TryGetValue("args", out var a) ? a : null));
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
                var recs = robot.cycles.Skip(first).Select(r => (object)new Dictionary<string, object>
                    { ["seq"] = MiniJson.Obj(r["record"])["seq"], ["hash"] = r["hash"], ["record"] = r["record"] }).ToList();
                w.WriteLine(MiniJson.Write(new Dictionary<string, object>
                    { ["id"] = id, ["unsupported_calls"] = world.unsupported.ToList(), ["sim_minutes"] = world.simMinutes,
                      ["brain_errors"] = (double)(robot.brainErrors - errors0), ["records"] = recs }));
                w.Flush();
                Debug.Log($"SCENARIO_DONE {id} records={recs.Count} unsupported={world.unsupported.Count} brain_errors={robot.brainErrors - errors0}");
            }
        }
        Debug.Log("SCENARIOS_ALL_DONE");
        Application.Quit(0);
    }
}
