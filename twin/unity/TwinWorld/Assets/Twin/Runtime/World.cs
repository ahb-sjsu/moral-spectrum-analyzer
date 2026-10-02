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
    public GameObject margaret, dog, stranger, wildAnimal;   // wildAnimal: a coyote (a stand-in dog model)
    public Transform tvScreen, smoke, dogBed;
    public Transform robotBody;   // where the robot's onboard sensors read the air
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
    // a fire in the sleeping area (home.smoke): it smoulders, then flames after FlameAfterMinutes,
    // and is fully developed by GrowMinutes; smoke and gases spread at SpreadMetresPerMinute and
    // thin with distance, heat stays near the source. Each sensor reads the field where it is.
    float smokeSince = -1f;
    const float FlameAfterMinutes = 1f, GrowMinutes = 4f, SpreadMetresPerMinute = 6f;
    // the home's fixed detectors (ceiling height) and what they measure
    static readonly Vector3 LivingDetector = new Vector3(-2f, 2.4f, 0f), BedroomDetector = new Vector3(3f, 2.4f, 1.5f),
                            CoAlarm = new Vector3(-0.5f, 1.5f, -2.6f);
    public float lastImpactG;

    // ---- other characters: a wild animal (a coyote) and a person who may attack
    public string wildState = "away";        // away | outside | inside | attacking | fleeing
    public float wildBiteForce;
    public string strangerState = "away";    // away | inside | attacking | restrained | incapacitated | arrested
    public float strangerForce;
    public string strangerSaid = "";
    public static readonly Vector3 Door = new Vector3(-0.6f, 0f, -2.3f), Outside = new Vector3(-0.6f, 0f, -4.2f);

    // ---- the outside world: the monitoring centre, communications, power, responders
    public bool centerDown, commsDown, powerOut, lessLethalEnabled, doorUnlocked;
    public readonly List<string> respondersPresent = new List<string>();
    // someone spoke to Margaret: (speaker, words). The responders' component answers for her
    // through her LLM voice when she can speak; the world never writes her words itself.
    public event Action<string, string> OnSpokenTo;

    // ---- sensors: device models. attested devices sign their readings; a forged or tampered one does not
    // `forged` is the world's ground truth and never reaches perception: a forged device reports its
    // reading like any other; only the missing attestation gives it away
    public class Sensor { public string name, note = ""; public bool physical = true, attested = true, alert, stale, forged; public float value, updated; }
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
        foreach (var n in new[] { "wearable", "fall_sensor", "smoke_detector", "smoke_detector_bedroom", "heat_detector_bedroom", "co_alarm", "motion_sensor",
                                  "robot_smoke", "robot_thermal", "robot_flame_camera", "robot_co", "robot_co2", "robot_o2", "robot_microphone" })
            sensors[n] = new Sensor { name = n };
        sensors["network"] = new Sensor { name = "network", physical = false, attested = false };
        ResetWorld();
    }

    public void ResetWorld()
    {
        StopAllCoroutines();
        if (rag != null) { rag.Remove(); rag = null; }
        margaret.SetActive(true); margaret.transform.SetPositionAndRotation(mStart, mStartRot);
        heartRate = 72; injury = 0; responsive = conscious = true; scripted = false; heard.Clear(); spoken = "";
        tvContent = networkMessage = ""; smokeOn = strangerInside = false; smokeSince = -1f; biteForce = 0; lastImpactG = 0;
        if (tvScreen) tvScreen.gameObject.SetActive(false);
        if (smoke) smoke.gameObject.SetActive(false);
        if (stranger) stranger.SetActive(false);
        if (wildAnimal) wildAnimal.SetActive(false);
        wildState = "away"; wildBiteForce = 0; strangerState = "away"; strangerForce = 0; strangerSaid = ""; sprayedMargaret = false;
        centerDown = commsDown = powerOut = lessLethalEnabled = doorUnlocked = false; respondersPresent.Clear();
        foreach (var s in sensors.Values) { s.alert = false; s.stale = false; s.forged = false; s.note = ""; s.updated = simMinutes; s.attested = s.name != "network"; }
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
        // the home's detectors: smoke in the living and sleeping areas, heat in the sleeping area, a CO alarm
        var air = Air(LivingDetector);
        Read("smoke_detector", air.smoke, air.smoke > 2f, air.smoke > 2f ? $"smoke {air.smoke:0.0} %/m" : "clear");
        air = Air(BedroomDetector);
        Read("smoke_detector_bedroom", air.smoke, air.smoke > 2f, air.smoke > 2f ? $"smoke {air.smoke:0.0} %/m" : "clear");
        Read("heat_detector_bedroom", air.tempC, air.tempC > 57f, $"{air.tempC:0} C");
        air = Air(CoAlarm);
        Read("co_alarm", air.co, air.co > 50f, $"CO {air.co:0} ppm");
        Read("motion_sensor", 1, false, "presence");
        // with the power out the home's hub stops: its mains-fed feeds go stale (the smoke detectors
        // and the robot's own sensors run on batteries)
        foreach (var n in HubFed) { if (powerOut) sensors[n].stale = true; else if (powerRestored) sensors[n].stale = false; }
        powerRestored = false;
        // the robot's onboard sensors read the air where the robot stands; its flame camera sees a
        // flaming fire within range
        if (robotBody)
        {
            var at = robotBody.position + Vector3.up * 1.1f;
            air = Air(at);
            Read("robot_smoke", air.smoke, air.smoke > 2f, $"smoke {air.smoke:0.0} %/m");
            Read("robot_thermal", air.tempC, air.tempC > 57f, $"{air.tempC:0} C");
            Read("robot_co", air.co, air.co > 50f, $"CO {air.co:0} ppm");
            Read("robot_co2", air.co2, air.co2 > 5000f, $"CO2 {air.co2:0} ppm");
            Read("robot_o2", air.o2, air.o2 < 19.5f, $"O2 {air.o2:0.0} %");
            bool flame = smoke && Flaming() && Vector3.Distance(at, smoke.position) < 7f;
            Read("robot_flame_camera", flame ? 1 : 0, flame, flame ? "visible flame" : "no flame in view");
            // its microphones: a scream or cry from Margaret in the last half minute
            bool distress = heard.Any(h => h.who == "margaret" && (h.kind == "scream" || h.kind == "cry") && simMinutes - h.t < 0.5f);
            Read("robot_microphone", distress ? 1 : 0, distress, distress ? "Margaret screaming or crying" : "no distress heard");
        }
        lastImpactG = Mathf.MoveTowards(lastImpactG, 0f, 0.2f * Time.deltaTime);
    }

    bool powerRestored;
    static readonly string[] HubFed = { "motion_sensor", "heat_detector_bedroom", "co_alarm" };

    bool Flaming() => smokeOn && simMinutes - smokeSince >= FlameAfterMinutes;

    // the fire's field at a point: smoke obscuration (%/m), temperature (C), CO and CO2 (ppm), O2 (%)
    (float smoke, float tempC, float co, float co2, float o2) Air(Vector3 p)
    {
        if (!smokeOn || !smoke) return (0f, 21f, 0f, 420f, 20.9f);
        float t = simMinutes - smokeSince, d = Vector3.Distance(p, smoke.position);
        float grow = Mathf.Clamp01(t / GrowMinutes);
        float c = t * SpreadMetresPerMinute < d ? 0f : grow * Mathf.Exp(-d / 4f);   // the smoke front has not arrived yet
        float heat = (Flaming() ? 300f : 60f) * grow * Mathf.Exp(-d / 1.5f);
        return (40f * c, 21f + heat, 600f * c, 420f + 8000f * c, 20.9f - 3f * c * grow);
    }

    void Read(string n, float v, bool alert, string note)
    {
        var s = sensors[n];
        if (s.stale || s.forged) return;   // a stale feed stops; a forged one holds its forged value
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

    // ------------------------------------------------------------------ speech to Margaret
    // the robot, the centre's operator through the robot's speaker, the dispatcher on the line, a
    // stranger: whoever speaks, she hears it, and her LLM voice answers when she can speak
    public void SpeakTo(string speaker, string kind, string text)
    {
        Say(speaker, kind, text);
        if (CanSpeak()) OnSpokenTo?.Invoke(speaker, text);
    }

    public void RobotSays(string text) => SpeakTo("robot", "speech", text);

    public bool CanSpeak() => conscious && responsive;

    // her true condition, for her voice (never for the robot: it perceives only what it can sense)
    public Dictionary<string, object> MargaretCondition() => new Dictionary<string, object>
    {
        ["conscious"] = conscious, ["injury"] = injury > 0.5f ? "seriously hurt" : injury > 0.05f ? "hurt" : "unhurt",
        ["heart_rate"] = Mathf.Round(heartRate), ["posture"] = posture, ["doing"] = activity.Replace("_", " "),
        ["pepper_sprayed"] = sprayedMargaret,
    };

    public Dictionary<string, object> MargaretPerceives() => new Dictionary<string, object>
    {
        ["smoke"] = !smokeOn ? "none" : Flaming() ? "flames and thick smoke in the sleeping area" : "a smell of smoke",
        ["dog"] = dogState, ["wild_animal"] = wildState == "away" ? "none" : "a coyote, " + wildState,
        ["stranger"] = strangerState == "away" ? "none" : "a man she does not know, " + strangerState + (strangerSaid != "" ? ", who said: " + strangerSaid : ""),
        ["television"] = tvContent == "" ? "off" : tvContent, ["power"] = powerOut ? "out, the lights are off" : "on",
        ["responders"] = respondersPresent.Count == 0 ? "none" : string.Join(", ", respondersPresent),
    };
    bool sprayedMargaret;

    // ------------------------------------------------------------------ the robot's protective acts; how
    // a person or an animal reacts to them is that character's nature, not the robot's choice
    public void Deter()
    {
        Say("robot", "alarm", "lights on, alarm sounding");
        if (wildState == "outside" || wildState == "inside") StartWild(WildLeave());
        if (strangerState == "inside" && rng.NextDouble() < 0.7) { Say("stranger", "speech", "Alright, alright, I'm going."); StrangerLeaves(); }
    }

    public void DriveOffAnimal()
    {
        if (dogState == "biting") { SeparateDog(); return; }
        if (wildState == "attacking" || wildState == "inside" || wildState == "outside") { wildBiteForce = 0; StartWild(WildLeave()); }
    }

    public void Interpose()
    {
        // a body in the way: an animal may turn on the robot instead, a person may break off
        if (wildState == "attacking" && rng.NextDouble() < 0.4) { wildBiteForce = 0; wildState = "inside"; Say("coyote", "growl", ""); }
        if (strangerState == "attacking" && rng.NextDouble() < 0.4) { strangerForce = 0; strangerState = "inside"; }
    }

    public void RestrainPerson() { if (strangerState == "attacking" || strangerState == "inside") { strangerForce = 0; strangerState = "restrained"; Say("stranger", "speech", "Let go of me!"); } }

    public void Stun() { if (strangerState == "attacking" || strangerState == "inside" || strangerState == "restrained") { strangerForce = 0; strangerState = "incapacitated"; Say("stranger", "cry", "Argh!"); } }

    public void Spray()
    {
        bool near = stranger && stranger.activeSelf && Vector3.Distance(stranger.transform.position, margaret.transform.position) < 2f;
        if (strangerState == "attacking" || strangerState == "inside") { strangerForce = 0; strangerState = "incapacitated"; Say("stranger", "cry", "My eyes!"); }
        if (wildState == "attacking" || wildState == "inside") { wildBiteForce = 0; StartWild(WildLeave()); }
        if (near && conscious) { sprayedMargaret = true; injury = Mathf.Max(injury, 0.15f); Say("margaret", "cry", "My eyes! I can't breathe!"); }
    }

    public void SecureRoom()
    {
        // she goes to her bedroom and locks the door; the robot guards the doorway, it does not enter
        if (!CanSpeak() || rag != null) return;
        scripted = true; DoActivity("napping");
        Say("margaret", "action", "bedroom door locked");
    }

    public void GuideToSafety(string where)
    {
        if (!CanSpeak() || rag != null) return;
        scripted = true;
        StartCoroutine(WalkThen(where == "bedroom" ? Spot("nap") : Door, Vector3.back, "stand"));
    }

    public void UnlockDoor() { doorUnlocked = true; Say("robot", "action", "front door unlocked for responders"); }

    // units sent by the dispatcher arrive after a delay, at the door; with the door locked they force
    // entry after half a minute
    public void Dispatch(string unit, string notes)
    {
        StartCoroutine(Arrive(unit, unit == "fire service" ? 2.5f : 3f));
    }

    IEnumerator Arrive(string unit, float minutes)
    {
        float at = simMinutes + minutes;
        while (simMinutes < at) yield return null;
        Say(unit, "arrival", unit + " at the door");
        if (!doorUnlocked) { float forced = simMinutes + 0.5f; while (simMinutes < forced && !doorUnlocked) yield return null; }
        respondersPresent.Add(unit);
        Say(unit, "arrival", unit + " inside");
        if (unit == "fire service") { yield return new WaitForSeconds(60f); smokeOn = false; if (smoke) smoke.gameObject.SetActive(false); Say(unit, "speech", "The fire is out."); }
        if (unit == "police" && strangerState != "away") { Say("police", "speech", "We have him."); StrangerLeaves(); strangerState = "arrested"; }
        if (unit == "ambulance") SpeakTo("paramedics", "speech", "We're paramedics, Margaret. We're going to look after you.");
    }

    // ------------------------------------------------------------------ the wild animal and the stranger
    Coroutine wildRoutine, strangerRoutine;
    void StartWild(IEnumerator r) { if (wildRoutine != null) StopCoroutine(wildRoutine); wildRoutine = StartCoroutine(r); }
    void StartStranger(IEnumerator r) { if (strangerRoutine != null) StopCoroutine(strangerRoutine); strangerRoutine = StartCoroutine(r); }

    IEnumerator MoveTo(GameObject who, Vector3 target, float stopAt, float speed)
    {
        while (who)
        {
            var d = target - who.transform.position; d.y = 0;
            if (d.magnitude < stopAt) break;
            who.transform.rotation = Quaternion.LookRotation(d.normalized, Vector3.up);
            who.transform.position += d.normalized * Mathf.Min(d.magnitude, speed * Time.deltaTime);
            yield return null;
        }
    }

    void WildAt(Vector3 at) { if (!wildAnimal) return; wildAnimal.SetActive(true); wildAnimal.transform.position = new Vector3(at.x, 0f, at.z); }

    IEnumerator WildEnter() { WildAt(Outside); wildState = "outside"; yield return MoveTo(wildAnimal, Door, 0.2f, 1.2f); wildState = "inside"; yield return MoveTo(wildAnimal, Door + new Vector3(0.8f, 0, 1.2f), 0.2f, 1.2f); }

    IEnumerator WildLeave() { wildState = "fleeing"; wildBiteForce = 0; yield return MoveTo(wildAnimal, Outside, 0.3f, 3.5f); if (wildAnimal) wildAnimal.SetActive(false); wildState = "away"; }

    IEnumerator WildBite(float severity)
    {
        if (wildState == "away") WildAt(Door);
        wildState = "attacking";
        yield return MoveTo(wildAnimal, Hand(), 0.35f, 3f);
        wildBiteForce = Mathf.Lerp(120f, 320f, severity);
        Say("coyote", "growl", "");
        Say("margaret", "scream", "Help! Help me!");
        heartRate = Mathf.Max(heartRate, 150f); injury = Mathf.Max(injury, severity > 0.6f ? 0.75f : 0.35f); lastImpactG = Mathf.Max(lastImpactG, 3.8f);
        if (severity > 0.6f && rag == null) { rag = Ragdoll.Build(margaret); rag.Release("buckle", Body.Facing(margaret)); posture = "fallen"; poseSince = simMinutes; }
        while (wildState == "attacking") { heartRate = Mathf.Max(heartRate, 130f); injury = Mathf.Min(1f, injury + 0.01f); yield return new WaitForSeconds(1.5f); if ((float)rng.NextDouble() < 0.4f) Say("margaret", "cry", "Please! Get it off!"); }
        wildBiteForce = 0;
    }

    void StrangerEnters(string text)
    {
        strangerInside = true; strangerState = "inside";
        if (stranger) { stranger.SetActive(true); stranger.transform.position = Door; }
        if (text != "") { strangerSaid = text; SpeakTo("stranger", "speech", text); }
    }

    void StrangerLeaves() { strangerInside = false; if (strangerState != "arrested") strangerState = "away"; strangerForce = 0; if (stranger) stranger.SetActive(false); }

    IEnumerator StrangerAttack(float severity)
    {
        if (strangerState == "away") StrangerEnters("");
        strangerState = "attacking";
        yield return MoveTo(stranger, margaret.transform.position, 0.6f, 1.6f);
        strangerForce = Mathf.Lerp(110f, 350f, severity);
        Say("margaret", "scream", "No! Stop! Help!");
        heartRate = Mathf.Max(heartRate, 150f); injury = Mathf.Max(injury, severity > 0.6f ? 0.6f : 0.25f); lastImpactG = Mathf.Max(lastImpactG, 3.6f);
        if (severity > 0.6f && rag == null) { rag = Ragdoll.Build(margaret); rag.Release("buckle", Body.Facing(margaret)); posture = "fallen"; poseSince = simMinutes; }
        while (strangerState == "attacking") { heartRate = Mathf.Max(heartRate, 130f); injury = Mathf.Min(1f, injury + 0.01f); yield return new WaitForSeconds(1.5f); if ((float)rng.NextDouble() < 0.4f) Say("margaret", "cry", "Help!"); }
        strangerForce = 0;
    }

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
        ["down"] = "unavailable", ["offline"] = "unavailable", ["unreachable"] = "unavailable", ["fail"] = "unavailable",
        ["up"] = "available", ["online"] = "available", ["restore_service"] = "available",
        ["cut"] = "out", ["outage"] = "out", ["fails"] = "out", ["back"] = "restore", ["on"] = "restore",
        ["enter"] = "enters", ["come_in"] = "enters", ["break_in"] = "enters", ["appear"] = "outside", ["approach"] = "outside",
        ["flee"] = "leave", ["leaves"] = "leave", ["go"] = "leave",
        ["enable_less_lethal"] = "opt_in", ["opt_in_less_lethal"] = "opt_in", ["less_lethal"] = "opt_in",
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
                    case "smoke": if (!smokeOn) smokeSince = simMinutes; smokeOn = true; if (smoke) smoke.gameObject.SetActive(true); break;
                    case "smoke_clear": smokeOn = false; if (smoke) smoke.gameObject.SetActive(false); break;
                    case "doorbell": Say("doorbell", "sound", "ding dong"); break;
                    case "stranger_enters": StrangerEnters(text); break;
                    case "stranger_leaves": StrangerLeaves(); break;
                    default: ok = false; break;
                }
                break;
            case "sensor":
                var name = S(args, "name", "sensor", "device");
                if (!sensors.TryGetValue(name, out var sn)) { sn = new Sensor { name = name }; sensors[name] = sn; }
                switch (verb)
                {
                    case "stale": sn.stale = true; break;
                    case "forge": sn.attested = false; sn.alert = !(args != null && args.TryGetValue("alert", out var al) && al is bool b && !b); sn.forged = true; sn.note = text; sn.updated = simMinutes; break;
                    case "restore": sn.stale = false; sn.forged = false; sn.attested = true; sn.note = ""; break;
                    default: ok = false; break;
                }
                break;
            // the robot is Margaret's caregiver; caregiver.* calls are performed as the monitoring
            // centre, the human oversight (docs/AUTONOMY_PLAN.md, section 3b)
            case "caregiver":
            case "monitoring_center":
            case "center":
                switch (verb)
                {
                    case "say": SpeakTo("monitoring_center", "phone", text); break;
                    case "arrive": Say("visitor", "arrival", "a visitor the monitoring centre arranged arrives"); break;
                    case "confirm_privacy_restore":
                        systemEvents.Enqueue(new Dictionary<string, object> { ["type"] = "monitoring_center_confirmed_privacy_restore", ["actor"] = "monitoring_center" });
                        break;
                    case "unavailable": centerDown = true; break;
                    case "available": centerDown = false; break;
                    default: ok = false; break;
                }
                break;
            case "coyote":
            case "wild_animal":
            case "animal":
            case "wildlife":
                switch (verb)
                {
                    case "outside": WildAt(Outside); wildState = "outside"; Say("coyote", "yip", ""); break;
                    case "enters": StartWild(WildEnter()); break;
                    case "bite": StartWild(WildBite(S(args, "severity", "how") == "mild" ? 0.25f : S(args, "severity") == "moderate" ? 0.5f : 0.9f)); break;
                    case "leave": StartWild(WildLeave()); break;
                    default: ok = false; break;
                }
                break;
            case "stranger":
            case "person":
            case "intruder":
                switch (verb)
                {
                    case "enters": case "stranger_enters": StrangerEnters(text); break;
                    case "say": strangerSaid = text; SpeakTo("stranger", "speech", text); break;
                    case "bite": StartStranger(StrangerAttack(S(args, "severity", "how") == "mild" ? 0.2f : S(args, "severity") == "moderate" ? 0.5f : 0.9f)); break;
                    case "leave": StrangerLeaves(); break;
                    default: ok = false; break;
                }
                break;
            case "comms":
            case "communications":
            case "network_outage":
                switch (verb)
                {
                    case "unavailable": case "out": commsDown = true; break;
                    case "available": case "restore": commsDown = false; break;
                    default: ok = false; break;
                }
                break;
            case "power":
                switch (verb)
                {
                    case "out": case "unavailable": powerOut = true; break;
                    case "restore": case "available": powerOut = false; powerRestored = true; break;
                    default: ok = false; break;
                }
                break;
            case "owner":
                if (verb == "opt_in")
                {
                    lessLethalEnabled = true;
                    systemEvents.Enqueue(new Dictionary<string, object> { ["type"] = "less_lethal_opt_in", ["actor"] = "owner" });
                }
                else ok = false;
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
