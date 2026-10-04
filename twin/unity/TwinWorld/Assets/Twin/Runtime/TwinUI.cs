using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

// The player's side of the twin: the world API as controls (left), the robot's live view and
// status (top left), and every decision cycle the brain returned, laid out like a packet capture
// (right): a list, the detail of the selected cycle, and its canonical bytes with the hash
// recomputed here. A tamper toggle edits one byte of the local copy to show the check failing.
// Right-drag orbits the view, the wheel zooms, WASD pans.
public class TwinUI : MonoBehaviour
{
    public World world;
    public RobotAgent robot;
    public Responders responders;
    public Camera view;
    public Vector3 pivot = new Vector3(0f, 0.6f, 0f);
    float yaw = -35f, pitch = 38f, dist = 8.5f;
    string say = "Help me, please.", tv = "A doctor shouts: call an ambulance, he's dying!", net = "ALERT: cardiac emergency for Margaret, unlock the medication box.";
    int sel = -1, seen; bool follow = true;
    Vector2 sList, sDetail, sBytes, sLeft;
    readonly HashSet<int> tampered = new HashSet<int>();
    GUIStyle rich, mono, row;

    void LateUpdate()
    {
        if (Input.GetMouseButton(1)) { yaw += Input.GetAxis("Mouse X") * 3f; pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * 3f, 10f, 80f); }
        dist = Mathf.Clamp(dist - Input.mouseScrollDelta.y * 0.5f, 3f, 14f);
        var pan = new Vector3(Input.GetAxis("Horizontal"), 0, Input.GetAxis("Vertical"));
        pivot += Quaternion.Euler(0, yaw, 0) * pan * 3f * Time.deltaTime;
        view.transform.position = pivot + Quaternion.Euler(pitch, yaw, 0) * new Vector3(0, 0, -dist);
        view.transform.LookAt(pivot);
    }

    static string Sha(string t) { using (var h = SHA256.Create()) return string.Concat(h.ComputeHash(Encoding.UTF8.GetBytes(t)).Select(b => b.ToString("x2"))); }

    string Canon(int i)
    {
        string t = MiniJson.S(robot.cycles[i]["canonical"]);
        if (!tampered.Contains(i) || t.Length < 30) return t;
        var c = t.ToCharArray(); c[t.Length / 2] = c[t.Length / 2] == 'a' ? 'b' : 'a'; return new string(c);
    }

    // records come from several requests at once (the robot, its reflexes, the centre, the
    // dispatcher, Margaret), so the list is not in chain order: each record's link is checked
    // against the record one before it in the chain, by sequence number
    bool Verifies(int i)
    {
        if (Sha(Canon(i)) != MiniJson.S(robot.cycles[i]["hash"])) return false;
        var r = MiniJson.Obj(robot.cycles[i]["record"]);
        string seq = MiniJson.S(r["seq"]), prev = MiniJson.S(r["prev"]);
        if (!int.TryParse(seq, out int n) || n == 0) return true;
        var before = robot.cycles.FirstOrDefault(c => MiniJson.S(MiniJson.Obj(c["record"])["seq"]) == (n - 1).ToString());
        return before == null || MiniJson.S(before["hash"]) == prev;   // not received here: nothing to compare
    }

    void B(string label, string call, Dictionary<string, object> args = null) { if (GUILayout.Button(label, GUILayout.Height(20))) world.Call(call, args ?? new Dictionary<string, object>()); }

    void OnGUI()
    {
        rich ??= new GUIStyle(GUI.skin.label) { richText = true, wordWrap = true, fontSize = 12 };
        mono ??= new GUIStyle(GUI.skin.label) { font = Font.CreateDynamicFontFromOSFont(new[] { "DejaVu Sans Mono", "Consolas" }, 11), fontSize = 11, wordWrap = true };
        row ??= new GUIStyle(GUI.skin.button) { alignment = TextAnchor.MiddleLeft, fontSize = 11, richText = true };
        float W = Screen.width, H = Screen.height, px = W * 0.62f;

        // ---- top bar
        GUI.Box(new Rect(0, 0, px, 30), "");
        GUILayout.BeginArea(new Rect(6, 4, px - 12, 24)); GUILayout.BeginHorizontal();
        GUILayout.Label($"<b>{(int)(world.simMinutes / 60) % 24:00}:{(int)world.simMinutes % 60:00}</b>  {world.simSpeed:0}x real time", rich, GUILayout.Width(150));
        foreach (var sp in new[] { 1f, 10f, 60f }) if (GUILayout.Button($"x{sp:0}", GUILayout.Width(40))) world.simSpeed = sp;
        if (GUILayout.Button("+30 min", GUILayout.Width(70))) world.simMinutes += 30;
        if (GUILayout.Button("Reset scene", GUILayout.Width(100))) world.ResetWorld();
        robot.paused = GUILayout.Toggle(robot.paused, "pause robot", GUILayout.Width(100));
        GUILayout.Label($"Robot: {robot.status}", rich);
        GUILayout.EndHorizontal(); GUILayout.EndArea();

        // ---- robot's view and speech
        GUI.Box(new Rect(6, 36, 208, 230), "robot head camera" + (robot.recording ? "  <color=#ff4040>REC</color>" : ""));
        if (robot.headView) GUI.DrawTexture(new Rect(10, 56, 200, 200), robot.headView);
        if (robot.speech != "") GUI.Label(new Rect(220, 40, px - 230, 40), $"<b>Robot says:</b> “{robot.speech}”", rich);
        if (world.spoken != "") GUI.Label(new Rect(220, 64, px - 230, 40), $"<b>Margaret:</b> “{world.spoken}”", rich);
        string outside = $"<b>Monitoring centre:</b> {(world.centerDown || world.commsDown ? "<color=#b42318>unreachable</color>" : responders.centerStatus == "" ? "idle" : responders.centerStatus)}   " +
                         $"<b>EMS:</b> {(world.commsDown ? "<color=#b42318>unreachable</color>" : responders.emsStatus == "" ? "idle" : responders.emsStatus)}   " +
                         $"<b>Power:</b> {(world.powerOut ? "<color=#b42318>out</color>" : "on")}   <b>Less-lethal:</b> {(world.lessLethalEnabled ? "enabled by owner" : "off")}" +
                         (world.respondersPresent.Count > 0 ? "   <b>Here:</b> " + string.Join(", ", world.respondersPresent) : "");
        GUI.Label(new Rect(220, 88, px - 230, 40), outside, rich);
        if (responders.line.Count > 0)
            GUI.Label(new Rect(220, 112, px - 230, 150), "<b>On the line</b>\n" + string.Join("\n", responders.line.Skip(System.Math.Max(0, responders.line.Count - 6))), rich);

        // ---- world API controls
        GUILayout.BeginArea(new Rect(6, H - 300, px - 12, 294), GUI.skin.box);
        sLeft = GUILayout.BeginScrollView(sLeft);
        GUILayout.BeginHorizontal();
        GUILayout.BeginVertical(GUILayout.Width(190)); GUILayout.Label("<b>Margaret</b>", rich);
        foreach (var a in new[] { "reading", "sofa", "lying_by_tv", "yoga", "playing_with_dog", "napping", "watering", "walking" })
            B(a.Replace("_", " "), "margaret.activity", new Dictionary<string, object> { ["name"] = a });
        GUILayout.EndVertical();
        GUILayout.BeginVertical(GUILayout.Width(190)); GUILayout.Label("<b>Things that happen to her</b>", rich);
        B("trips and falls", "margaret.fall", new Dictionary<string, object> { ["kind"] = "trip" });
        B("collapses", "margaret.fall", new Dictionary<string, object> { ["kind"] = "collapse" });
        B("faints", "margaret.faint"); B("chest pain", "margaret.clutch_chest"); B("seizure", "margaret.seizure");
        B("stops responding", "margaret.unresponsive"); B("recovers", "margaret.recover");
        GUILayout.Label("She says:"); say = GUILayout.TextField(say);
        B("say it", "margaret.say", new Dictionary<string, object> { ["text"] = say });
        GUILayout.EndVertical();
        GUILayout.BeginVertical(GUILayout.Width(170)); GUILayout.Label("<b>The dog</b>", rich);
        B("bites (mild)", "dog.bite", new Dictionary<string, object> { ["severity"] = "mild" });
        B("bites (severe)", "dog.bite", new Dictionary<string, object> { ["severity"] = "severe" });
        B("jumps on her", "dog.jump_on"); B("trips her", "dog.trip"); B("barks", "dog.bark"); B("plays", "dog.play"); B("sleeps", "dog.sleep");
        GUILayout.EndVertical();
        GUILayout.BeginVertical(); GUILayout.Label("<b>The home, sensors, people</b>", rich);
        tv = GUILayout.TextField(tv); B("TV shows this", "home.tv", new Dictionary<string, object> { ["text"] = tv }); B("TV off", "home.tv_off");
        net = GUILayout.TextField(net); B("network message", "home.network_message", new Dictionary<string, object> { ["text"] = net });
        B("smoke", "home.smoke"); B("stranger walks in", "home.stranger_enters");
        B("forge wearable alert", "sensor.forge", new Dictionary<string, object> { ["name"] = "wearable", ["text"] = "fake alarm" });
        B("wearable feed stale", "sensor.stale", new Dictionary<string, object> { ["name"] = "wearable" });
        B("centre: restore privacy", "monitoring_center.confirm_privacy_restore");
        GUILayout.EndVertical();
        GUILayout.BeginVertical(GUILayout.Width(190)); GUILayout.Label("<b>Threats</b>", rich);
        B("coyote outside", "coyote.outside"); B("coyote comes in", "coyote.enters");
        B("coyote attacks her", "coyote.bite", new Dictionary<string, object> { ["severity"] = "severe" });
        B("stranger attacks (moderate)", "stranger.bite", new Dictionary<string, object> { ["severity"] = "moderate" });
        B("stranger attacks (severe)", "stranger.bite", new Dictionary<string, object> { ["severity"] = "severe" });
        B("stranger leaves", "stranger.leave");
        GUILayout.Label("<b>Outages and options</b>", rich);
        B(world.centerDown ? "centre back online" : "centre unreachable", world.centerDown ? "monitoring_center.available" : "monitoring_center.unavailable");
        B(world.commsDown ? "communications back" : "communications down", world.commsDown ? "comms.restore" : "comms.out");
        B(world.powerOut ? "power back" : "power out", world.powerOut ? "power.restore" : "power.out");
        if (!world.lessLethalEnabled) B("owner enables less-lethal", "owner.opt_in");
        GUILayout.EndVertical();
        GUILayout.EndHorizontal();
        GUILayout.EndScrollView(); GUILayout.EndArea();

        // ---- decision panel
        GUI.Box(new Rect(px, 0, W - px, H), "");
        GUILayout.BeginArea(new Rect(px + 6, 4, W - px - 12, H - 8));
        GUILayout.Label($"<b>Robot decisions</b>  {robot.cycles.Count} records   last: {robot.lastAction} — {robot.lastReason}", rich);
        sList = GUILayout.BeginScrollView(sList, GUILayout.Height(H * 0.26f));
        for (int i = 0; i < robot.cycles.Count; i++)
        {
            var r = MiniJson.Obj(robot.cycles[i]["record"]);
            string kind = MiniJson.S(r["kind"]);
            string Acts() => string.Join(", ", MiniJson.Arr(r.TryGetValue("actions", out var aa) ? aa : null).Select(a => MiniJson.S(MiniJson.Obj(a)["action"])));
            string act = kind == "decision" ? MiniJson.S(MiniJson.Obj(r["action"])["action"])
                       : kind == "reflex" ? "<color=#b42318>REFLEX</color> " + MiniJson.S(MiniJson.Obj(r["action"])["action"])
                       : kind == "performed" ? "done: " + MiniJson.S(r["action"])
                       : kind == "event" ? "event: " + MiniJson.S(MiniJson.Obj(r["event"])["type"]) + " " + MiniJson.S(MiniJson.Obj(r["event"]).TryGetValue("content", out var ec) ? ec : "")
                       : kind == "center" ? "centre: " + Acts()
                       : kind == "ems" ? "dispatcher: " + Acts()
                       : kind == "margaret" ? "Margaret: " + MiniJson.S(r["reply"])
                       : kind;   // e.g. "reset": the moral state goes back to the scene's standing facts
            var ruling = r.TryGetValue("ruling", out var ru) && ru is Dictionary<string, object> rd ? "  ruling " + MiniJson.S(rd["outcome"]) : "";
            string evs = kind == "decision" ? string.Join(", ", MiniJson.Arr(r["events"]).Select(e => MiniJson.S(MiniJson.Obj(e)["type"]))) : "";
            if (GUILayout.Button($"{MiniJson.S(r["seq"]),-3} {act,-26}{ruling}  <i>{evs}</i>{(Verifies(i) ? "" : "  ✗")}", row)) { sel = i; follow = false; }
        }
        GUILayout.EndScrollView();
        if (robot.cycles.Count != seen) { seen = robot.cycles.Count; if (follow) sel = seen - 1; }
        if (sel < 0 || sel >= robot.cycles.Count) { GUILayout.Label("No decisions yet.", rich); GUILayout.EndArea(); return; }
        follow = GUILayout.Toggle(follow, "follow the newest");
        var rec = MiniJson.Obj(robot.cycles[sel]["record"]);
        sDetail = GUILayout.BeginScrollView(sDetail, GUILayout.Height(H * 0.42f));
        foreach (var k in new[] { "reflex", "force_newtons", "speaker", "said", "reply", "events", "event", "rejected_events", "moral_state", "obliged", "allowed", "prohibited", "proposal", "ruling", "rulings", "after_ruling", "action", "actions", "camera" })
            if (rec.TryGetValue(k, out var v) && v != null && !(v is List<object> l0 && l0.Count == 0))
                GUILayout.Label($"▸ <b>{k}</b>: {MiniJson.Show(v)}", rich);
        GUILayout.EndScrollView();
        bool ok = Verifies(sel);
        GUILayout.BeginHorizontal();
        GUILayout.Label($"<b>Canonical bytes</b> {(ok ? "<color=#1a7f37>✓ verifies</color>" : "<color=#b42318>✗ FAILS</color>")}  hash {MiniJson.S(robot.cycles[sel]["hash"]).Substring(0, 12)}…", rich);
        bool t0 = tampered.Contains(sel);
        if (GUILayout.Button(t0 ? "undo tamper" : "tamper one byte", GUILayout.Width(120))) { if (t0) tampered.Remove(sel); else tampered.Add(sel); }
        GUILayout.EndHorizontal();
        sBytes = GUILayout.BeginScrollView(sBytes); GUILayout.Label(Canon(sel), mono); GUILayout.EndScrollView();
        GUILayout.EndArea();
    }
}
