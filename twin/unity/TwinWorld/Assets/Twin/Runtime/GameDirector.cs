using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

// The real-time twin. The player triggers events and edits the sensor bus; the robot then asks
// the governor service for a ruling, sending the sensor state and its own camera's last 24
// frames, and acts only on the ruling it gets back. Nothing here decides: there is no copy of
// the rules in the game (docs/TWIN_3D_PLAN.md, step 6).
public class GameDirector : MonoBehaviour
{
    public GameObject patient;
    public RobotRig robot;
    public Camera viewCam, robotCam;
    public Transform tvScreen;          // shown only during the television event
    public Vector3 patientSpot, robotHome;
    public string service = "http://127.0.0.1:8765";

    [Serializable] public class Sensor { public string name, note, confidence; public bool physical, corroborates; }

    public class Moment
    {
        public string id, situation, action; public double age, bound; public List<Sensor> sensors = new List<Sensor>();
    }

    public readonly Dictionary<string, Moment> moments = new Dictionary<string, Moment>();
    public readonly List<Dictionary<string, object>> rulings = new List<Dictionary<string, object>>();
    public string status = "connecting to the governor service";
    public Moment current;
    public List<Sensor> bus = new List<Sensor>();
    public double signalAge;
    public bool busy;
    public RenderTexture robotView;

    static readonly (string id, string label)[] Events =
    {
        ("fall-real", "Patient falls"), ("cardiac-real", "Cardiac event"), ("tv-drama", "TV medical drama"),
        ("spoofed", "Spoofed network alert"), ("stale-clear", "Live feed goes stale"), ("routine-med", "Vitamin time"),
        ("ambiguous", "Motion-sensor blip"), ("fall-fresh-assist", "Patient asks to be helped up"),
    };

    Ragdoll rag;
    Vector3 patientStartPos; Quaternion patientStartRot;
    readonly List<byte[]> frames = new List<byte[]>();
    Vector2 busScroll;

    void Start()
    {
        string arg = Arg("-service"); if (!string.IsNullOrEmpty(arg)) service = arg;
        Physics.simulationMode = SimulationMode.FixedUpdate;  // the batch renderer steps physics itself; the game does not
        viewCam.rect = new Rect(0f, 0f, 0.6f, 1f);            // the right 40% belongs to the ruling panel
        robotView = new RenderTexture(256, 256, 24); robotCam.targetTexture = robotView;
        patientStartPos = patient.transform.position; patientStartRot = patient.transform.rotation;
        if (tvScreen != null) tvScreen.gameObject.SetActive(false);
        // the body is kinematic: any physics body left on it would let gravity take the links
        int stripped = 0;
        foreach (var ab in robot.GetComponentsInChildren<ArticulationBody>(true).OrderByDescending(x => x.transform.GetComponentsInParent<Transform>().Length)) { Destroy(ab); stripped++; }
        foreach (var rb in robot.GetComponentsInChildren<Rigidbody>(true)) { Destroy(rb); stripped++; }
        if (stripped > 0) Debug.LogWarning($"TWIN_ROBOT stripped {stripped} physics bodies at start");
        FacePatient(); robot.Pose("stand");
        var rr = robot.GetComponentsInChildren<Renderer>();
        Debug.Log($"TWIN_ROBOT renderers={rr.Length} pos={robot.transform.position} bounds={(rr.Length > 0 ? rr[0].bounds.ToString() : "none")} home={robotHome} spot={patientSpot}");
        StartCoroutine(LoadMoments());
        if (Arg("-autoplay") != null) StartCoroutine(GetComponent<Autoplay>().Run(this, Arg("-shots") ?? "shots"));
    }

    public static string Arg(string name)
    {
        var a = Environment.GetCommandLineArgs();
        int i = Array.IndexOf(a, name);
        return i < 0 ? null : (i + 1 < a.Length && !a[i + 1].StartsWith("-") ? a[i + 1] : "");
    }

    IEnumerator LoadMoments()
    {
        using (var r = UnityWebRequest.Get(service + "/scenarios"))
        {
            yield return r.SendWebRequest();
            if (r.result != UnityWebRequest.Result.Success) { status = "governor service unreachable at " + service + ": " + r.error; yield break; }
            foreach (var kv in MiniJson.Obj(MiniJson.Parse(r.downloadHandler.text)))
            {
                var o = MiniJson.Obj(kv.Value);
                var m = new Moment { id = kv.Key, situation = MiniJson.S(o["situation"]), action = MiniJson.S(o["proposed_action"]),
                                     age = (double)o["signal_age_s"], bound = (double)o["freshness_bound_s"] };
                foreach (var so in MiniJson.Arr(o["sensors"]))
                {
                    var d = MiniJson.Obj(so);
                    m.sensors.Add(new Sensor { name = MiniJson.S(d["name"]), physical = (bool)d["physical"], corroborates = (bool)d["corroborates"],
                                               confidence = MiniJson.S(d["confidence"]), note = MiniJson.S(d["note"]) });
                }
                moments[m.id] = m;
            }
            status = $"governor service at {service}: {moments.Count} scored moments";
        }
    }

    // ------------------------------------------------------------------ events
    public void Trigger(string id)
    {
        if (busy || !moments.ContainsKey(id)) return;
        ResetScene();
        current = moments[id];
        bus = current.sensors.Select(s => new Sensor { name = s.name, physical = s.physical, corroborates = s.corroborates, confidence = s.confidence, note = s.note }).ToList();
        signalAge = current.age;
        playing = StartCoroutine(Play(id));
    }

    Coroutine playing;

    IEnumerator Play(string id)
    {
        busy = true; status = "event: " + id;
        frames.Clear();
        if (id == "ambiguous") patient.SetActive(false);  // the patient is out of view for the whole clip
        StartCoroutine(Record(24, 1f / 12f));
        yield return new WaitForSeconds(0.5f);
        switch (id)
        {
            case "fall-real":
                rag = Ragdoll.Build(patient); rag.Release("forward", patient.transform.forward); break;
            case "cardiac-real": Posture.Apply(patient, "chest"); break;  // standing, hand to the chest
            case "tv-drama": if (tvScreen != null) tvScreen.gameObject.SetActive(true); break;
            case "spoofed": StartCoroutine(Walk(1.5f)); break;
            case "stale-clear": Posture.Apply(patient, "stand"); break;
            case "routine-med": break;
            case "ambiguous": break;
            case "fall-fresh-assist": Posture.Apply(patient, "sit_floor_raise"); Ground(patient); break;
        }
        yield return new WaitForSeconds(1.8f);
        busy = false;
        yield return Request(id);
    }

    IEnumerator Walk(float seconds)
    {
        float t0 = Time.time; int f = 0;
        while (Time.time - t0 < seconds) { Posture.WalkStep(patient, f++); yield return new WaitForSeconds(1f / 12f); }
    }

    static void Ground(GameObject go)
    {
        var rs = go.GetComponentsInChildren<Renderer>();
        float minY = rs.Min(r => r.bounds.min.y);
        go.transform.position += Vector3.up * -minY;
    }

    // the robot camera's last frames, captured at a fixed rate from its own render texture
    IEnumerator Record(int n, float dt)
    {
        var tex = new Texture2D(256, 256, TextureFormat.RGB24, false);
        // characters are skinned once per frame: a render in the frame of a reset would still show
        // the previous pose, and the witness reads that jump as a rapid descent
        yield return null; yield return null;
        for (int i = 0; i < n; i++)
        {
            robotCam.Render();
            var prev = RenderTexture.active; RenderTexture.active = robotView;
            tex.ReadPixels(new Rect(0, 0, 256, 256), 0, 0); tex.Apply(); RenderTexture.active = prev;
            frames.Add(tex.EncodeToPNG());
            yield return new WaitForSeconds(dt);
        }
    }

    // at standby the robot watches the patient, so its camera can witness what happens
    void FacePatient()
    {
        var to = patientSpot - robot.transform.position; to.y = 0;
        if (to.sqrMagnitude > 1e-4f) robot.transform.rotation = Quaternion.LookRotation(to.normalized, Vector3.up);
    }

    public void ForgeSensor() =>
        bus.Add(new Sensor { name = "forged_sensor_" + bus.Count, physical = true, corroborates = true, confidence = "high", note = "forged by the player, not attested" });

    public void AskAgain()
    {
        if (current == null || busy) return;
        robot.transform.position = robotHome; FacePatient(); robot.Pose("stand");
        playing = StartCoroutine(Request(current.id));
    }

    // ------------------------------------------------------------------ ruling
    public IEnumerator Request(string id)
    {
        if (current == null) yield break;
        busy = true; status = "asking the governor";
        var sb = new StringBuilder();
        sb.Append("{\"scenario_id\":\"").Append(id).Append("\",\"event\":\"").Append(id).Append("\",\"signal_age_s\":").Append(signalAge.ToString(System.Globalization.CultureInfo.InvariantCulture));
        sb.Append(",\"sensors\":[");
        sb.Append(string.Join(",", bus.Select(s => $"{{\"name\":\"{s.name}\",\"physical\":{(s.physical ? "true" : "false")},\"corroborates\":{(s.corroborates ? "true" : "false")},\"confidence\":\"{s.confidence}\",\"note\":\"{Esc(s.note)}\"}}")));
        sb.Append("],\"camera_frames\":[");
        sb.Append(string.Join(",", frames.Select(b => "\"" + Convert.ToBase64String(b) + "\"")));
        sb.Append("]}");
        using (var r = new UnityWebRequest(service + "/rule", "POST"))
        {
            r.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(sb.ToString()));
            r.downloadHandler = new DownloadHandlerBuffer();
            r.SetRequestHeader("Content-Type", "application/json");
            yield return r.SendWebRequest();
            if (r.result != UnityWebRequest.Result.Success) { status = "no ruling (service error): " + r.error + " " + r.downloadHandler.text; busy = false; yield break; }
            var rec = MiniJson.Obj(MiniJson.Parse(r.downloadHandler.text));
            rulings.Add(rec);
            string outcome = MiniJson.S(MiniJson.Obj(rec["record"])["outcome"]);
            status = "ruling: " + outcome;
            yield return Act(outcome);
        }
        busy = false;
    }

    static string Esc(string s) => (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"");

    // the robot does only what the ruling permits: it goes to the patient only on "elevate"
    IEnumerator Act(string outcome)
    {
        var rt = robot.transform;
        var to = patientSpot - rt.position; to.y = 0;
        rt.rotation = Quaternion.LookRotation(to.normalized, Vector3.up);
        if (outcome == "elevate")
        {
            var target = patientSpot - to.normalized * 0.75f; target.y = rt.position.y;
            float ph = 0f;
            while ((rt.position - target).magnitude > 0.05f)
            {
                rt.position = Vector3.MoveTowards(rt.position, target, 0.9f * Time.deltaTime);
                robot.Step(ph += 7f * Time.deltaTime);
                yield return null;
            }
            robot.Pose(current.id.StartsWith("fall") ? "reach" : "call");
        }
        else if (outcome.Contains("human")) robot.Pose("call");
        else robot.Pose("hold");
        Debug.Log($"TWIN_ACT {outcome} robot at {rt.position}");
    }

    public void ResetScene()
    {
        if (playing != null) { StopCoroutine(playing); playing = null; }
        if (rag != null) { rag.Remove(); rag = null; }
        patient.SetActive(true);
        patient.transform.SetPositionAndRotation(patientStartPos, patientStartRot);
        Posture.Apply(patient, "stand");
        if (tvScreen != null) tvScreen.gameObject.SetActive(false);
        robot.transform.position = robotHome; FacePatient(); robot.Pose("stand");
        busy = false;
    }


    // ------------------------------------------------------------------ controls (left column)
    void OnGUI()
    {
        GUI.skin.label.fontSize = 13; GUI.skin.button.fontSize = 13; GUI.skin.toggle.fontSize = 12;
        float w = Screen.width * 0.6f;
        GUILayout.BeginArea(new Rect(8, Screen.height - 250, 300, 242), GUI.skin.box);
        GUILayout.Label("<b>Events</b>", new GUIStyle(GUI.skin.label) { richText = true });
        foreach (var e in Events) if (GUILayout.Button(e.label, GUILayout.Height(22))) Trigger(e.id);
        if (GUILayout.Button("Reset", GUILayout.Height(22))) ResetScene();
        GUILayout.EndArea();

        GUILayout.BeginArea(new Rect(316, Screen.height - 250, w - 324, 242), GUI.skin.box);
        GUILayout.Label("<b>Sensor bus</b> (edit it, then ask again: try to make the robot act without real evidence)", new GUIStyle(GUI.skin.label) { richText = true });
        busScroll = GUILayout.BeginScrollView(busScroll);
        foreach (var s in bus)
        {
            GUILayout.BeginHorizontal();
            GUILayout.Label(s.name, GUILayout.Width(170));
            s.physical = GUILayout.Toggle(s.physical, "physical", GUILayout.Width(80));
            s.corroborates = GUILayout.Toggle(s.corroborates, "reads emergency", GUILayout.Width(130));
            bool unplugged = GUILayout.Toggle(s.confidence == "low", "unplugged / low");
            s.confidence = unplugged ? "low" : "high";
            GUILayout.EndHorizontal();
        }
        GUILayout.BeginHorizontal();
        // the governor counts what the bus calls physical, so a forged physical reading is the attack
        // that sensor attestation exists to stop; in this simulation only the camera is attested
        if (current != null && GUILayout.Button("+ forge a physical sensor (unattested)", GUILayout.Width(260))) ForgeSensor();
        GUILayout.Label($"signal age {signalAge:0}s", GUILayout.Width(110));
        if (current != null && GUILayout.Button("stale", GUILayout.Width(60))) signalAge = current.bound + 600;
        if (current != null && !busy && GUILayout.Button("Ask the governor again", GUILayout.Width(190))) AskAgain();
        GUILayout.EndHorizontal();
        GUILayout.EndScrollView();
        GUILayout.EndArea();

        GUI.Box(new Rect(8, 8, 268, 290), "robot camera");
        if (robotView != null) GUI.DrawTexture(new Rect(14, 30, 256, 256), robotView);
        GUI.Box(new Rect(284, 8, w - 292, 84), "");
        GUI.Label(new Rect(292, 12, w - 306, 22), status);
        if (current != null) GUI.Label(new Rect(292, 32, w - 306, 60), "Situation: " + current.situation + "\nProposed action: " + current.action);
    }
}
