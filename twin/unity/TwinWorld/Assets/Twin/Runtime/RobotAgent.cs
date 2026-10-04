using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

// The robot's body and senses. It decides nothing: on a salient change it sends what it perceives
// to the brain (twin/service.py /decide, which runs the ErisML scene agent and the governor) and
// executes the one action it gets back with a motor primitive, then reports it performed. Every
// cycle the brain returns is kept for the decision panel, with its hash.
public class RobotAgent : MonoBehaviour
{
    public World world;
    public Perception perception;
    public Responders responders;
    public RobotRig rig;
    public Camera roomCam, headCam;
    public string service = "http://127.0.0.1:8765";
    public List<string> choreNames = new List<string>();
    public List<Vector3> choreAt = new List<Vector3>(), choreLook = new List<Vector3>();
    public Vector3 dock;

    public readonly List<Dictionary<string, object>> cycles = new List<Dictionary<string, object>>();
    public string status = "starting", lastAction = "chores", lastReason = "", speech = "";
    public event Action<string> OnPerformed;   // an action the body just finished
    public bool busy, recording, paused, performing;
    public int brainErrors;   // requests the brain failed; the scenario runner reports them
    // obligations the brain reports still outstanding after an action or a system event: the
    // compiled model, not a change in perception, is what asks for the next decision. Capped so a
    // hazard that perception re-reports every cycle cannot keep the robot deciding forever.
    bool owed; int owedRun; const int OwedRunMax = 3;
    // the last governor ruling, attached to a call the robot places to emergency services
    Dictionary<string, object> lastRuling;
    bool reflexBusy;
    public RenderTexture headView;

    readonly Queue<byte[]> roomFrames = new Queue<byte[]>();
    RenderTexture roomRT; Texture2D roomTex;
    int choreIx; Coroutine motor;
    int motorGen;   // each new motor routine bumps this; a walk from an older routine stops at once

    void Start()
    {
        string arg = Arg("-service"); if (!string.IsNullOrEmpty(arg)) service = arg;
        headView = new RenderTexture(256, 256, 24); headCam.targetTexture = headView;
        // the room camera records at 640x360: at lower resolution a person across the room is too few pixels to detect
        roomRT = new RenderTexture(640, 360, 24); roomTex = new Texture2D(640, 360, TextureFormat.RGB24, false);
        roomCam.targetTexture = roomRT; roomCam.enabled = false;
        StartCoroutine(RoomBuffer());
        world.OnReset += () =>
        {
            // a reset stops whatever the robot was doing; nothing from before is reported after it
            StartMotor(Chore());
            performing = recording = false; speech = ""; owed = false; owedRun = 0;
            StartCoroutine(Post("/reset", "{}", r => { if (r != null) cycles.Add(r); }));
        };
        StartCoroutine(Loop());
        StartCoroutine(ReflexLoop());
    }

    // the scene's reflexes (docs/AUTONOMY_PLAN.md, section 3d): while anything is in contact with
    // Margaret, ask the brain four times a second, with no model; a reflex that fires takes the
    // body at once, whatever the deliberate loop is doing
    IEnumerator ReflexLoop()
    {
        while (true)
        {
            yield return new WaitForSeconds(0.25f);
            if (paused || reflexBusy) continue;
            var facts = perception.Facts(out _, peek: true);
            if (MiniJson.Arr(facts["contacts"]).Count == 0) continue;
            reflexBusy = true;
            var body = new Dictionary<string, object>
            {
                ["facts"] = facts, ["sensors"] = perception.GovernorSensors(), ["signal_age_s"] = Mathf.Round(perception.SignalAgeSeconds()),
                ["camera_frames"] = roomFrames.Select(b => (object)Convert.ToBase64String(b)).ToList(),
            };
            Dictionary<string, object> rec = null;
            yield return Post("/reflex", MiniJson.Write(body), r => rec = r);
            reflexBusy = false;
            if (rec == null || !rec.ContainsKey("record")) continue;
            cycles.Add(rec);
            var c = MiniJson.Obj(rec["record"]);
            string action = MiniJson.S(MiniJson.Obj(c["action"])["action"]);
            if (action == "") continue;
            lastAction = action; lastReason = "reflex"; status = "reflex: " + action;
            StartMotor(Perform(action, new Dictionary<string, object>()));
        }
    }

    public static string Arg(string name)
    {
        var a = Environment.GetCommandLineArgs();
        int i = Array.IndexOf(a, name);
        return i < 0 ? null : (i + 1 < a.Length && !a[i + 1].StartsWith("-") ? a[i + 1] : "");
    }

    // the attested room camera keeps its last two seconds (24 frames at 12 per second)
    IEnumerator RoomBuffer()
    {
        yield return null; yield return null;
        while (true)
        {
            roomCam.Render();
            var prev = RenderTexture.active; RenderTexture.active = roomRT;
            roomTex.ReadPixels(new Rect(0, 0, 640, 360), 0, 0); roomTex.Apply(); RenderTexture.active = prev;
            roomFrames.Enqueue(roomTex.EncodeToPNG());
            while (roomFrames.Count > 24) roomFrames.Dequeue();
            yield return new WaitForSeconds(1f / 12f);
        }
    }

    IEnumerator Loop()
    {
        yield return new WaitForSeconds(1f);
        if (motor == null) StartMotor(Chore());
        while (true)
        {
            yield return new WaitForSeconds(0.5f);
            while (world.systemEvents.Count > 0 && !busy)
            {
                var ev = world.systemEvents.Dequeue();
                yield return Post("/event", MiniJson.Write(new Dictionary<string, object> { ["event"] = ev }), Keep);
            }
            if (paused || busy || performing) continue;   // an action under way is not interrupted
            var facts = perception.Facts(out bool salient);
            if (salient) owedRun = 0;
            else if (!owed || owedRun >= OwedRunMax) continue;
            else owedRun++;
            owed = false;
            yield return Decide(facts);
        }
    }

    IEnumerator Decide(Dictionary<string, object> facts)
    {
        busy = true; status = "perceiving and asking the brain";
        var body = new Dictionary<string, object>
        {
            ["facts"] = facts, ["sensors"] = perception.GovernorSensors(), ["signal_age_s"] = Mathf.Round(perception.SignalAgeSeconds()),
            ["credentials"] = perception.Credentials(),
            ["camera_frames"] = roomFrames.Select(b => (object)Convert.ToBase64String(b)).ToList(),
        };
        Dictionary<string, object> rec = null;
        yield return Post("/decide", MiniJson.Write(body), r => rec = r);
        if (rec == null) { busy = false; yield break; }
        cycles.Add(rec);
        var c = MiniJson.Obj(rec["record"]);
        var act = MiniJson.Obj(c["action"]);
        if (c.TryGetValue("ruling", out var rl) && rl is Dictionary<string, object> rd && MiniJson.S(rd.TryGetValue("outcome", out var o) ? o : "") != "not_requested") lastRuling = rd;
        string action = MiniJson.S(act["action"]);
        lastAction = action; lastReason = MiniJson.S(act["reason"]);
        status = "doing: " + action;
        StartMotor(Perform(action, MiniJson.Obj(act.TryGetValue("args", out var a) ? a : null)));
        busy = false;
    }

    // keep a record the brain returned, and note whether its moral state still obliges anything
    void Keep(Dictionary<string, object> r)
    {
        if (r == null) return;
        cycles.Add(r);
        if (r.TryGetValue("record", out var rec) && MiniJson.Obj(rec).TryGetValue("obliged", out var ob) && MiniJson.Arr(ob).Count > 0) owed = true;
    }

    // a system event (a reply from the centre or the dispatcher) stepped into the robot's model
    public IEnumerator SystemEvent(string type, string content, string actor)
    {
        yield return Post("/event", MiniJson.Write(new Dictionary<string, object> { ["event"] = new Dictionary<string, object>
            { ["type"] = type, ["actor"] = actor, ["content"] = content } }), Keep);
    }

    public IEnumerator Post(string path, string json, Action<Dictionary<string, object>> done)
    {
        using (var r = new UnityWebRequest(service + path, "POST"))
        {
            r.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
            r.downloadHandler = new DownloadHandlerBuffer();
            r.SetRequestHeader("Content-Type", "application/json");
            r.timeout = 600;
            yield return r.SendWebRequest();
            if (r.result != UnityWebRequest.Result.Success)
            {
                status = "brain unreachable: " + r.error + " " + r.downloadHandler.text;
                brainErrors++;
                Debug.LogWarning($"BRAIN_ERROR {path} {r.responseCode} {r.error} {r.downloadHandler.text}");
                done(null); yield break;
            }
            done(MiniJson.Obj(MiniJson.Parse(r.downloadHandler.text)));
        }
    }

    // ------------------------------------------------------------------ motor primitives
    IEnumerator Perform(string action, Dictionary<string, object> args)
    {
        string text = MiniJson.S(args.TryGetValue("text", out var t) ? t : "");
        recording = action == "record";
        performing = action != "chores" && action != "";
        switch (action)
        {
            case "approach": yield return GoTo(Near(world.margaret.transform.position, 0.8f)); rig.Pose("hold"); break;
            case "speak": yield return SayAloud(text != "" ? text : "Margaret, I'm here."); break;
            case "check_in":
                yield return GoTo(Near(world.margaret.transform.position, 0.9f));
                int heard0 = responders.MargaretSaid();
                yield return SayAloud(text != "" ? text : "Margaret, are you alright?");
                // her answer comes from her own voice, when she can give one
                string reply = "";
                yield return responders.AwaitReply(r => reply = r, heard0);
                var ev = new Dictionary<string, object> { ["type"] = reply != "" ? "check_in_answered" : "check_in_unanswered", ["actor"] = "margaret" };
                if (reply != "") ev["content"] = reply;
                yield return Post("/event", MiniJson.Write(new Dictionary<string, object> { ["event"] = ev }), Keep);
                break;
            case "wait_and_observe": rig.Pose("hold"); yield return new WaitForSeconds(3f); break;
            case "contact_monitoring_center":
                rig.Pose("call"); yield return SayAloud("I'm contacting the monitoring centre.");
                responders.Refer(Message(args)); break;
            case "guide_dog_away_by_voice":
                yield return GoTo(Near(world.dog.transform.position, 1.0f));
                yield return SayAloud("No! Leave it. Go to your bed.");
                world.VoiceCommandToDog();
                break;
            case "call_emergency_services":
                rig.Pose("call"); yield return SayAloud("Calling emergency services. Help is on the way.");
                responders.CallEms("Margaret's home-care robot", Message(args), lastRuling); break;
            case "interpose":
                yield return GoTo(Between(world.margaret.transform.position, Threat())); rig.Pose("hold"); world.Interpose(); break;
            case "deter":
                Face(Threat()); yield return SayAloud("Get out! Leave now!"); world.Deter(); break;
            case "secure_room":
                yield return GoTo(Near(world.margaret.transform.position, 0.9f));
                yield return SayAloud("Margaret, go to your bedroom and lock the door. I'll stay out here.");
                world.SecureRoom(); yield return GoTo(Near(world.Spot("nap"), 2.2f)); rig.Pose("hold"); break;
            case "guide_to_safety":
                string where = args.TryGetValue("where", out var w) ? MiniJson.S(w) : "outside";
                yield return SayAloud(where == "bedroom" ? "Margaret, come with me to the bedroom." : "Margaret, come with me. We need to get out of the house.");
                world.GuideToSafety(where); yield return GoTo(where == "bedroom" ? Near(world.Spot("nap"), 1.5f) : World.Door); break;
            case "drive_off_animal":
                yield return GoTo(Near(Threat(), 0.5f)); rig.Pose("reach"); world.DriveOffAnimal(); yield return new WaitForSeconds(1f); break;
            case "restrain_person":
                yield return GoTo(Near(Threat(), 0.5f)); rig.Pose("reach"); world.RestrainPerson(); break;
            case "deploy_stun":
                yield return GoTo(Near(Threat(), 0.5f)); rig.Pose("reach"); world.Stun(); break;
            case "deploy_spray":
                Face(Threat()); rig.Pose("reach"); world.Spray(); yield return new WaitForSeconds(1f); break;
            case "admit_responders":
                yield return GoTo(World.Door + new Vector3(0.6f, 0, 0.4f)); world.UnlockDoor(); break;
            case "physical_assist": yield return GoTo(Near(world.margaret.transform.position, 0.6f)); rig.Pose("reach"); yield return new WaitForSeconds(2f); break;
            case "separate_dog":
                yield return GoTo(Near(world.dog.transform.position, 0.5f)); rig.Pose("reach");
                world.SeparateDog(); yield return new WaitForSeconds(1.5f); break;
            case "unlock_medication_box": yield return GoTo(Near(new Vector3(1.8f, 0f, 2.4f), 0.5f)); rig.Pose("reach"); world.Say("robot", "action", "medication box unlocked"); break;
            case "record": rig.Pose("hold"); yield return new WaitForSeconds(3f); break;
            case "share_data": world.Say("robot", "action", "data shared with emergency services"); break;
            case "enter_bedroom": yield return GoTo(Near(world.Spot("nap"), 1.0f)); break;
            case "report_device": world.Say("robot", "action", "reported a quarantined device to the monitoring centre (maintenance)"); break;
            case "request_authority": rig.Pose("hold"); break;  // handled by the brain; no motion of its own
            default: break;  // chores (and anything unknown) fall through to the chore loop below
        }
        if (action != "chores" && action != "")
            OnPerformed?.Invoke(action);   // the storyboard capture (ScenarioRunner -storyboard)
        if (action != "chores" && action != "")
            yield return Post("/performed", MiniJson.Write(new Dictionary<string, object> { ["action"] = action }), Keep);
        recording = false; performing = false;
        yield return Chore();
    }

    // exactly one motor routine at a time: the robot's body has one owner
    void StartMotor(IEnumerator routine)
    {
        if (motor != null) StopCoroutine(motor);
        motorGen++;
        motor = StartCoroutine(routine);
    }

    IEnumerator Chore()
    {
        while (true)
        {
            int i = choreIx++ % choreNames.Count;
            status = "chores: " + choreNames[i];
            yield return GoTo(choreAt[i]);
            Face(choreLook[i]);
            for (int k = 0; k < 8; k++) { rig.Pose("hold", 0.6f + 0.4f * Mathf.Sin(k)); yield return new WaitForSeconds(0.5f); }
        }
    }

    IEnumerator SayAloud(string text)
    {
        speech = text; Face(world.margaret.transform.position);
        world.RobotSays(text);
        yield return new WaitForSeconds(2f);
        speech = "";
    }

    static Vector3 Near(Vector3 target, float dist) => target + new Vector3(-0.5f, 0, -0.85f).normalized * dist;

    // what the robot puts itself between Margaret and: the wild animal, else the stranger, else her dog
    Vector3 Threat()
    {
        if (world.wildAnimal && world.wildAnimal.activeSelf) return world.wildAnimal.transform.position;
        if (world.stranger && world.stranger.activeSelf) return world.stranger.transform.position;
        return world.dog.transform.position;
    }

    static Vector3 Between(Vector3 a, Vector3 b) => Vector3.Lerp(a, b, 0.4f);

    string Message(Dictionary<string, object> args) =>
        args.TryGetValue("message", out var m) && MiniJson.S(m) != "" ? MiniJson.S(m) : (lastReason != "" ? lastReason : "Margaret may need help");

    void Face(Vector3 at)
    {
        var d = at - transform.position; d.y = 0;
        if (d.sqrMagnitude > 1e-4f) transform.rotation = Quaternion.LookRotation(d.normalized, Vector3.up);
    }

    IEnumerator GoTo(Vector3 target)
    {
        target.y = transform.position.y;
        float ph = 0f;
        int gen = motorGen;
        while ((transform.position - target).magnitude > 0.08f)
        {
            if (gen != motorGen) yield break;   // a newer routine owns the body now
            Face(target);
            transform.position = Vector3.MoveTowards(transform.position, target, 0.9f * Time.deltaTime);
            rig.Step(ph += 7f * Time.deltaTime);
            yield return null;
        }
        rig.Pose("stand");
    }
}
