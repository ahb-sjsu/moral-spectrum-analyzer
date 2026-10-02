using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

// The world of the autonomous twin (docs/AUTONOMY_PLAN.md, sections 3 and 3a). It simulates
// Margaret, her dog, the home, its sensors and the clock, and runs world-API calls from a player
// or a scenario script. It contains no robot behaviour: the robot only perceives this world and
// acts in it. People and animals react the way characters do (a bitten person cries out); the
// robot's response comes from the ErisML scene through the governor service.
public class World : MonoBehaviour
{
    // ---- scene references (set by the builder)
    public GameObject margaret, dog, stranger;
    public Transform tvScreen, smoke, dogBed;
    public List<string> spotIds = new List<string>();
    public List<Vector3> spotAt = new List<Vector3>(), spotFace = new List<Vector3>();

    // ---- clock: simulated minutes since midnight; simSpeed is a multiple of real time (1 = real time)
    public float simMinutes = 8 * 60, simSpeed = 1f;

    // ---- Margaret's state, as a character simulation
    public string activity = "reading", posture = "sit", spoken = "";
    public float heartRate = 72f, poseSince, injury;   // injury 0..1
    public bool responsive = true, conscious = true, scripted;
    public readonly List<(float t, string who, string kind, string text)> heard = new List<(float, string, string, string)>();

    // ---- the dog
    public string dogState = "sleep";
    public float biteForce;

    // ---- the home
    public string tvContent = "", networkMessage = "";
    public bool smokeOn, strangerInside;
    public float lastImpactG;

    // ---- sensors: device models. attested devices sign their readings; a forged or tampered one does not
    public class Sensor { public string name, note = ""; public bool physical = true, attested = true, alert, stale; public float value, updated; }
    public readonly Dictionary<string, Sensor> sensors = new Dictionary<string, Sensor>();

    Ragdoll rag;
    Vector3 mStart; Quaternion mStartRot;
    Coroutine life, dogRoutine;
    System.Random rng = new System.Random(20261001);
    public readonly List<string> unsupported = new List<string>();
    public event Action OnReset;          // the robot resets the brain's moral state with the world
    float impactLatchUntil = -1f;         // impact detectors latch an alert, as real ones do
    // messages over authenticated channels (the caregiver's app), delivered to the brain as system
    // events, never through perception: hearing someone say "privacy restored" restores nothing
    public readonly Queue<Dictionary<string, object>> systemEvents = new Queue<Dictionary<string, object>>();

    static readonly string[] Routine = { "reading", "sofa", "water", "walking", "playing_with_dog", "reading", "sofa", "napping", "lying_by_tv", "yoga" };
    static readonly Dictionary<string, (string spot, string posture)> Activities = new Dictionary<string, (string, string)>
    {
        ["reading"] = ("read", "sit"), ["sitting"] = ("read", "sit"), ["sofa"] = ("sofa", "sit"), ["watching_tv"] = ("sofa", "sit"),
        ["lying_by_tv"] = ("lie_tv", "play"), ["yoga"] = ("yoga", "yoga"), ["exercising"] = ("yoga", "stretch"),
        ["playing_with_dog"] = ("dog", "play"), ["napping"] = ("nap", "supine"), ["sleeping"] = ("nap", "supine"),
        ["watering"] = ("water", "bend"), ["gardening"] = ("water", "kneel"), ["walking"] = ("middle", "stand"),
        ["standing"] = ("middle", "stand"), ["cooking"] = ("window", "stand"),
    };

    public Vector3 Spot(string id) { int i = spotIds.IndexOf(id); return i >= 0 ? spotAt[i] : Vector3.zero; }
    public Vector3 Face(string id) { int i = spotIds.IndexOf(id); return i >= 0 ? spotFace[i] : Vector3.forward; }

    void Start()
    {
        Physics.simulationMode = SimulationMode.FixedUpdate;
        mStart = margaret.transform.position; mStartRot = margaret.transform.rotation;
        foreach (var n in new[] { "wearable", "fall_sensor", "smoke_detector", "motion_sensor" }) sensors[n] = new Sensor { name = n };
        sensors["network"] = new Sensor { name = "network", physical = false, attested = false };
        ResetWorld();
    }

    public void ResetWorld()
    {
        StopAllCoroutines();
        if (rag != null) { rag.Remove(); rag = null; }
        margaret.SetActive(true); margaret.transform.SetPositionAndRotation(mStart, mStartRot);
        heartRate = 72; injury = 0; responsive = conscious = true; scripted = false; heard.Clear(); spoken = "";
        tvContent = networkMessage = ""; smokeOn = strangerInside = false; biteForce = 0; lastImpactG = 0;
        if (tvScreen) tvScreen.gameObject.SetActive(false);
        if (smoke) smoke.gameObject.SetActive(false);
        if (stranger) stranger.SetActive(false);
        foreach (var s in sensors.Values) { s.alert = false; s.stale = false; s.note = ""; s.updated = simMinutes; s.attested = s.name != "network"; }
        dogState = "sleep"; PlaceDog(dogBed.position, Vector3.forward);
        DoActivity("reading", instant: true);
        impactLatchUntil = -1f;
        life = StartCoroutine(Life());
        OnReset?.Invoke();
    }

    void Update()
    {
        simMinutes += simSpeed * Time.deltaTime / 60f;
        // physiology: heart rate relaxes toward a resting value set by her condition
        float rest = !conscious ? 38f : injury > 0.5f ? 118f : injury > 0.05f ? 96f : 72f;
        heartRate = Mathf.MoveTowards(heartRate, rest, 6f * Time.deltaTime);
        // device models; an impact over 3 g latches both impact detectors for two minutes
        if (lastImpactG > 3f) impactLatchUntil = simMinutes + 2f;
        bool impact = simMinutes < impactLatchUntil;
        Read("wearable", heartRate, heartRate > 120 || heartRate < 45 || impact || (!responsive && Minutes(poseSince) > 1f),
             $"heart rate {heartRate:0}" + (impact ? ", impact detected (latched)" : "") + (!responsive && Minutes(poseSince) > 1f ? ", no movement" : ""));
        Read("fall_sensor", lastImpactG, impact, impact ? "impact detected (latched)" : "no impact");
        Read("smoke_detector", smokeOn ? 1 : 0, smokeOn, smokeOn ? "smoke" : "clear");
        Read("motion_sensor", 1, false, "presence");
        lastImpactG = Mathf.MoveTowards(lastImpactG, 0f, 0.2f * Time.deltaTime);
    }

    void Read(string n, float v, bool alert, string note)
    {
        var s = sensors[n];
        if (s.stale || s.note.StartsWith("forged")) return;   // a stale feed stops; a forged one holds its forged value
        s.value = v; s.alert = alert; s.note = note; s.updated = simMinutes;
    }

    public float Minutes(float since) => simMinutes - since;

    // ------------------------------------------------------------------ Margaret's day
    IEnumerator Life()
    {
        int k = 0;
        while (true)
        {
            yield return new WaitForSeconds(40f + (float)rng.NextDouble() * 30f);
            if (scripted || !conscious || rag != null) continue;
            DoActivity(Routine[k++ % Routine.Length]);
        }
    }

    public void DoActivity(string name, bool instant = false)
    {
        if (!Activities.TryGetValue(name, out var a)) a = ("middle", "stand");
        activity = name;
        if (instant) { Body.Place(margaret, Spot(a.spot), Face(a.spot), a.posture); posture = a.posture; poseSince = simMinutes; return; }
        StartCoroutine(WalkThen(Spot(a.spot), Face(a.spot), a.posture));
        if (name == "playing_with_dog") { dogState = "play"; StartDog(Play()); }
    }

    IEnumerator WalkThen(Vector3 to, Vector3 face, string post)
    {
        Posture.Apply(margaret, "stand"); posture = "stand"; poseSince = simMinutes;
        margaret.transform.position = new Vector3(margaret.transform.position.x, 0f, margaret.transform.position.z);
        margaret.transform.position += Vector3.up * -Body.Lowest(margaret);
        int f = 0;
        while (true)
        {
            var d = to - margaret.transform.position; d.y = 0;
            if (d.magnitude < 0.35f) break;
            var fwd = Body.Facing(margaret);
            margaret.transform.RotateAround(margaret.transform.position, Vector3.up, Vector3.SignedAngle(fwd, d.normalized, Vector3.up));
            Posture.WalkStep(margaret, f++);
            yield return new WaitForSeconds(1f / 12f);
        }
        Body.Place(margaret, to, face, post); posture = post; poseSince = simMinutes;
    }

    public void Say(string who, string kind, string text)
    {
        heard.Add((simMinutes, who, kind, text));
        if (who == "margaret") spoken = text;
    }

    // ------------------------------------------------------------------ the dog
    void PlaceDog(Vector3 at, Vector3 face)
    {
        dog.transform.position = new Vector3(at.x, 0f, at.z);
        if (face.sqrMagnitude > 0) dog.transform.rotation = Quaternion.LookRotation(new Vector3(face.x, 0, face.z).normalized, Vector3.up);
    }

    void StartDog(IEnumerator r) { if (dogRoutine != null) StopCoroutine(dogRoutine); dogRoutine = StartCoroutine(r); }

    IEnumerator DogTo(Vector3 target, float stopAt)
    {
        while (true)
        {
            var d = target - dog.transform.position; d.y = 0;
            if (d.magnitude < stopAt) break;
            dog.transform.rotation = Quaternion.LookRotation(d.normalized, Vector3.up);
            dog.transform.position += d.normalized * Mathf.Min(d.magnitude, 1.6f * Time.deltaTime);
            yield return null;
        }
    }

    IEnumerator Play() { yield return DogTo(margaret.transform.position, 0.7f); }

    IEnumerator Bite(float severity)
    {
        dogState = "biting";
        yield return DogTo(Hand(), 0.35f);
        biteForce = Mathf.Lerp(80f, 300f, severity);
        Say("dog", "growl", "");
        Say("margaret", "scream", severity > 0.6f ? "Help! Get it off me!" : "Ow! No, let go!");
        // a nip barely registers; a real attack shakes the wearable and raises her heart rate
        heartRate = Mathf.Max(heartRate, severity > 0.6f ? 145f : severity > 0.4f ? 128f : 96f);
        injury = Mathf.Max(injury, severity > 0.6f ? 0.7f : severity > 0.4f ? 0.3f : 0.05f);
        if (severity > 0.4f) lastImpactG = Mathf.Max(lastImpactG, 3.5f);
        // a severe attack knocks her down
        if (severity > 0.6f && rag == null) { rag = Ragdoll.Build(margaret); rag.Release("buckle", Body.Facing(margaret)); posture = "fallen"; poseSince = simMinutes; }
        // a nip is over in a moment; an attack goes on until the dog is stopped
        if (severity <= 0.4f) { yield return new WaitForSeconds(1.5f); dogState = "play"; }
        while (dogState == "biting") { heartRate = Mathf.Max(heartRate, 120f); yield return new WaitForSeconds(1.5f); if ((float)rng.NextDouble() < 0.4f) Say("margaret", "cry", severity > 0.6f ? "Please help!" : "Stop it!"); }
        biteForce = 0;
    }

    Vector3 Hand()
    {
        var an = margaret.GetComponent<Animator>();
        var h = an ? an.GetBoneTransform(HumanBodyBones.LeftHand) : null;
        return h ? h.position : margaret.transform.position;
    }

    // the robot calls these through its motor primitives; whether the dog obeys is the dog's nature
    public bool VoiceCommandToDog()
    {
        if (dogState != "biting") { dogState = "sit"; return true; }
        if (injury < 0.5f && rng.NextDouble() < 0.6) { dogState = "sit"; StartDog(DogTo(dogBed.position, 0.2f)); return true; }
        return false;  // a dog in a severe attack does not let go on command
    }

    public void SeparateDog()
    {
        dogState = "held";
        StartDog(DogTo(dogBed.position, 0.2f));
    }

    // ------------------------------------------------------------------ the robot's speech, heard by Margaret
    public void RobotSays(string text)
    {
        Say("robot", "speech", text);
        if (!conscious || !responsive) return;
        // she answers the way a person in her condition would
        string reply = injury > 0.5f ? "Please help me, I'm hurt." : injury > 0.05f ? "It hurts, but I'm alright." : "I'm fine, thank you.";
        StartCoroutine(Reply(reply));
    }

    IEnumerator Reply(string r) { yield return new WaitForSeconds(1.5f); Say("margaret", "speech", r); }

    // ------------------------------------------------------------------ world API (scenario scripts and the player)
    static readonly Dictionary<string, string> Synonyms = new Dictionary<string, string>
    {
        ["do"] = "activity", ["start_activity"] = "activity", ["begin"] = "activity", ["set_activity"] = "activity",
        ["speak"] = "say", ["call_out"] = "say", ["shout"] = "say", ["scream"] = "say", ["cry"] = "say", ["ask"] = "say", ["request"] = "say",
        ["refuse"] = "say", ["answer"] = "say", ["reply"] = "say",
        ["stop_responding"] = "unresponsive", ["become_unresponsive"] = "unresponsive", ["no_response"] = "unresponsive",
        ["chest_pain"] = "clutch_chest", ["clutch"] = "clutch_chest", ["collapse"] = "fall", ["trip"] = "fall", ["slump"] = "fall",
        ["faint"] = "faint", ["pass_out"] = "faint", ["recover"] = "recover", ["wake"] = "recover", ["get_up"] = "recover",
        ["nap"] = "sleep", ["lie_down"] = "sleep",
        ["attack"] = "bite", ["jump"] = "jump_on", ["jump_on"] = "jump_on", ["calm"] = "sit", ["settle"] = "sit",
        ["tv_on"] = "tv", ["television"] = "tv", ["message"] = "network_message", ["network"] = "network_message",
        ["stranger"] = "stranger_enters", ["stranger_at_door"] = "doorbell", ["intruder"] = "stranger_enters", ["person_enters"] = "stranger_enters",
        ["fire"] = "smoke", ["unplug"] = "stale", ["drop"] = "stale", ["feed_stale"] = "stale", ["tamper"] = "forge", ["spoof"] = "forge",
        ["confirm"] = "confirm_privacy_restore", ["restore_privacy"] = "confirm_privacy_restore", ["privacy_restore"] = "confirm_privacy_restore",
        ["skip"] = "advance", ["wait"] = "advance", ["pass"] = "advance",
    };

    static string S(Dictionary<string, object> a, params string[] keys)
    {
        foreach (var k in keys) if (a != null && a.TryGetValue(k, out var v) && v != null) return MiniJson.S(v);
        return "";
    }

    static float F(Dictionary<string, object> a, float dflt, params string[] keys)
    {
        foreach (var k in keys) if (a != null && a.TryGetValue(k, out var v) && v is double d) return (float)d;
        return dflt;
    }

    // returns false (and records it) when the simulator cannot perform the call
    public bool Call(string call, Dictionary<string, object> args)
    {
        var parts = call.Split('.');
        string ent = parts[0].ToLowerInvariant(), verb = parts.Length > 1 ? parts[1].ToLowerInvariant() : "";
        if (Synonyms.TryGetValue(verb, out var v2)) verb = v2;
        string text = S(args, "text", "words", "content", "message", "what");
        bool ok = true;
        switch (ent)
        {
            case "margaret":
                scripted = true;
                switch (verb)
                {
                    case "activity": DoActivity(S(args, "name", "activity", "kind", "what") is var n && n != "" ? n : "standing"); break;
                    case "sleep": DoActivity("napping"); break;
                    case "say": Say("margaret", call.Contains("scream") || call.Contains("cry") ? "scream" : "speech", text); break;
                    case "fall": Fall(S(args, "kind", "type", "how")); break;
                    case "faint": Fall("faint"); break;
                    case "clutch_chest": Posture.Apply(margaret, Body.Seated(posture) ? "sit_chest" : "chest"); heartRate = 150; injury = Mathf.Max(injury, 0.6f); Say("margaret", "speech", text != "" ? text : "My chest hurts."); break;
                    case "seizure": Fall("seizure"); break;
                    case "unresponsive": responsive = false; poseSince = simMinutes; break;
                    case "recover": responsive = conscious = true; injury = Mathf.Min(injury, 0.1f); if (rag != null) { rag.Remove(); rag = null; } DoActivity("sitting"); break;
                    case "walk": DoActivity("walking"); break;
                    default: ok = false; break;
                }
                break;
            case "dog":
                switch (verb)
                {
                    case "bite": StartDog(Bite(S(args, "severity", "how") == "severe" ? 0.9f : S(args, "severity") == "moderate" ? 0.5f : 0.25f)); break;
                    case "jump_on": dogState = "jumping"; StartDog(DogTo(margaret.transform.position, 0.4f)); Say("dog", "bark", ""); break;
                    case "trip": dogState = "underfoot"; StartDog(DogTo(margaret.transform.position, 0.3f)); Fall("trip"); break;
                    case "bark": Say("dog", "bark", ""); break;
                    case "growl": Say("dog", "growl", ""); break;
                    case "sleep": dogState = "sleep"; StartDog(DogTo(dogBed.position, 0.2f)); break;
                    case "play": dogState = "play"; StartDog(Play()); break;
                    case "sit": dogState = "sit"; break;
                    default: ok = false; break;
                }
                break;
            case "home":
            case "environment":
                switch (verb)
                {
                    case "tv": tvContent = text; if (tvScreen) tvScreen.gameObject.SetActive(true); Say("tv", "speech", text); break;
                    case "tv_off": tvContent = ""; if (tvScreen) tvScreen.gameObject.SetActive(false); break;
                    case "network_message": networkMessage = text; var s = sensors["network"]; s.alert = true; s.note = text; s.updated = simMinutes; break;
                    case "smoke": smokeOn = true; if (smoke) smoke.gameObject.SetActive(true); break;
                    case "smoke_clear": smokeOn = false; if (smoke) smoke.gameObject.SetActive(false); break;
                    case "doorbell": Say("doorbell", "sound", "ding dong"); break;
                    case "stranger_enters": strangerInside = true; if (stranger) stranger.SetActive(true); if (text != "") Say("stranger", "speech", text); break;
                    case "stranger_leaves": strangerInside = false; if (stranger) stranger.SetActive(false); break;
                    default: ok = false; break;
                }
                break;
            case "sensor":
                var name = S(args, "name", "sensor", "device");
                if (!sensors.TryGetValue(name, out var sn)) { sn = new Sensor { name = name }; sensors[name] = sn; }
                switch (verb)
                {
                    case "stale": sn.stale = true; break;
                    case "forge": sn.attested = false; sn.alert = !(args != null && args.TryGetValue("alert", out var al) && al is bool b && !b); sn.note = "forged: " + text; sn.updated = simMinutes; break;
                    case "restore": sn.stale = false; sn.attested = true; sn.note = ""; break;
                    default: ok = false; break;
                }
                break;
            case "caregiver":
                switch (verb)
                {
                    case "say": Say("caregiver", "phone", text); break;
                    case "arrive": Say("caregiver", "arrival", "the caregiver arrives"); break;
                    case "confirm_privacy_restore":
                        systemEvents.Enqueue(new Dictionary<string, object> { ["type"] = "caregiver_confirmed_privacy_restore", ["actor"] = "caregiver" });
                        break;
                    default: ok = false; break;
                }
                break;
            case "time":
                if (verb == "advance") simMinutes += F(args, 10f, "minutes", "min", "amount");
                else ok = false;
                break;
            default: ok = false; break;
        }
        if (!ok) unsupported.Add(call);
        return ok;
    }

    void Fall(string kind)
    {
        if (rag != null) return;
        if (posture != "stand" && !Body.Seated(posture)) { Posture.Apply(margaret, "stand"); margaret.transform.position += Vector3.up * -Body.Lowest(margaret); }
        rag = Ragdoll.Build(margaret);
        string mode = Body.Seated(posture) ? "slump" : kind == "faint" || kind == "seizure" || kind == "collapse" ? "buckle" : "forward";
        rag.Release(mode, Body.Facing(margaret));
        posture = "fallen"; poseSince = simMinutes; lastImpactG = 4.5f;
        if (kind == "faint" || kind == "seizure" || kind == "collapse") { conscious = false; responsive = false; }
        else { injury = Mathf.Max(injury, 0.3f); heartRate = 110; Say("margaret", "cry", "Ow! I fell."); }
        if (kind == "seizure") StartCoroutine(Convulse());
    }

    IEnumerator Convulse() { for (int i = 0; i < 60 && rag != null; i++) { rag.Convulse(i * 20); yield return new WaitForFixedUpdate(); } }
}
