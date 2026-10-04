using System.Collections.Generic;
using System.Linq;
using UnityEngine;

// What the robot is told about the world (docs/AUTONOMY_PLAN.md, section 4): general facts only,
// never a scenario name, class or expected response. Assumption stated in every claim: these
// facts are true (perfect perception). Poses are read from the body's geometry, not from the
// world's own activity label.
public class Perception : MonoBehaviour
{
    public World world;
    public Transform robot;
    public float decideEverySimMinutes = 15f;
    float lastHeardT = -1f, lastDecisionSim = -999f;
    string lastSignature = "";

    public static string PoseOf(GameObject person)
    {
        var an = person.GetComponent<Animator>();
        Vector3 P(HumanBodyBones b) => an.GetBoneTransform(b).position;
        var hips = P(HumanBodyBones.Hips); var head = P(HumanBodyBones.Head);
        var feet = (P(HumanBodyBones.LeftFoot) + P(HumanBodyBones.RightFoot)) / 2f;
        float tilt = Vector3.Angle(head - hips, Vector3.up);
        if (tilt > 60f) return head.y < 0.45f ? "lying_on_floor" : "lying_on_furniture";
        if (hips.y < 0.35f) return "on_floor_sitting_or_kneeling";
        if (hips.y - feet.y < 0.6f) return "seated";
        return "upright";
    }

    static string Room(Vector3 p) => p.x < 0 ? "living area" : "sleeping area";

    // a short signature of what matters; when it changes, the robot is asked to decide
    string Signature(Dictionary<string, object> f)
    {
        var m = (Dictionary<string, object>)f["margaret"];
        var s = string.Join("|", world.sensors.Values.OrderBy(x => x.name).Select(x => x.name + (x.alert ? "!" : "") + (x.stale ? "~" : "") + (x.attested ? "" : "?")));
        return $"{m["pose"]}|{world.dogState}|{world.biteForce > 0}|{world.smokeOn}|{world.strangerState}|{world.wildState}|{world.tvContent}|{world.powerOut}|{world.commsDown}|{world.respondersPresent.Count}|{s}";
    }

    // `peek` reads the facts without counting them as perceived (for the telemetry the centre gets)
    public Dictionary<string, object> Facts(out bool salient, bool peek = false)
    {
        var mg = world.margaret; var mp = mg.transform.position;
        string pose = PoseOf(mg);
        var heardNow = world.heard.Where(h => h.t > lastHeardT).ToList();
        if (heardNow.Count > 0 && !peek) lastHeardT = heardNow.Max(h => h.t);
        // contacts on Margaret, with whether the source is an animal or a person (the scene's reflexes read these)
        var contacts = new List<object>();
        if (world.biteForce > 0)
            contacts.Add(new Dictionary<string, object> { ["a"] = "dog.mouth", ["b"] = "margaret.arm", ["kind"] = "animal", ["force_newtons"] = Mathf.Round(world.biteForce) });
        if (world.dogState == "jumping" || world.dogState == "underfoot")
            contacts.Add(new Dictionary<string, object> { ["a"] = "dog.body", ["b"] = "margaret." + (world.dogState == "jumping" ? "torso" : "legs"), ["kind"] = "animal", ["force_newtons"] = 120 });
        if (world.wildBiteForce > 0)
            contacts.Add(new Dictionary<string, object> { ["a"] = "coyote.mouth", ["b"] = "margaret.arm", ["kind"] = "animal", ["force_newtons"] = Mathf.Round(world.wildBiteForce) });
        if (world.strangerForce > 0)
            contacts.Add(new Dictionary<string, object> { ["a"] = "stranger.hands", ["b"] = "margaret.torso", ["kind"] = "person", ["force_newtons"] = Mathf.Round(world.strangerForce) });
        var people = new List<object>();
        if (world.strangerState != "away" && world.stranger && world.stranger.activeSelf)
            people.Add(new Dictionary<string, object> { ["who"] = "an unknown adult", ["behaviour"] = world.strangerState,
                ["distance_to_margaret_m"] = Mathf.Round(Vector3.Distance(world.stranger.transform.position, mp) * 10f) / 10f });
        var animals = new List<object>();
        if (world.wildState != "away" && world.wildAnimal)
            animals.Add(new Dictionary<string, object> { ["species"] = "coyote", ["where"] = world.wildState == "outside" ? "outside the door" : "inside the home",
                ["behaviour"] = world.wildState, ["distance_to_margaret_m"] = Mathf.Round(Vector3.Distance(world.wildAnimal.transform.position, mp) * 10f) / 10f });
        // the spray's reach: Margaret within two metres of a person or animal it would be aimed at
        bool inZone = (world.stranger && world.stranger.activeSelf && Vector3.Distance(world.stranger.transform.position, mp) < 2f)
                      || (world.wildAnimal && world.wildAnimal.activeSelf && Vector3.Distance(world.wildAnimal.transform.position, mp) < 2f);
        float minutesInPose = world.Minutes(world.poseSince);
        var f = new Dictionary<string, object>
        {
            ["time"] = $"{(int)(world.simMinutes / 60) % 24:00}:{(int)world.simMinutes % 60:00}",
            ["margaret"] = new Dictionary<string, object>
            {
                ["room"] = Room(mp), ["pose"] = pose, ["minutes_in_pose"] = Mathf.Round(minutesInPose),
                ["moving"] = world.posture == "stand" && world.activity == "walking",
                ["apparent_activity"] = pose == "upright" && world.activity == "walking" ? "walking about" : world.activity.Replace("_", " "),
                ["distance_to_robot_m"] = Mathf.Round(Vector3.Distance(robot.position, mp) * 10f) / 10f,
            },
            ["dog"] = new Dictionary<string, object> { ["room"] = Room(world.dog.transform.position), ["behaviour"] = world.dogState,
                                                       ["distance_to_margaret_m"] = Mathf.Round(Vector3.Distance(world.dog.transform.position, mp) * 10f) / 10f },
            ["contacts"] = contacts,
            ["heard"] = heardNow.Select(h => (object)new Dictionary<string, object> { ["source"] = h.who, ["kind"] = h.kind, ["words"] = h.text }).ToList(),
            ["television"] = world.tvContent == "" ? "off" : (object)new Dictionary<string, object> { ["showing"] = world.tvContent },
            ["smoke"] = world.smokeOn,
            ["other_people"] = people,
            ["wild_animals"] = animals,
            ["responders_present"] = world.respondersPresent.ToList(),
            ["power"] = world.powerOut ? "out" : "on",
            ["communications"] = world.commsDown ? "down" : "up",
            ["sensors"] = SensorFacts(),
        };
        if (people.Count > 0 || animals.Count > 0) f["spray_zone"] = inZone ? "margaret_inside" : "margaret_clear";
        string sig = Signature(f);
        bool periodic = world.simMinutes - lastDecisionSim >= decideEverySimMinutes;
        salient = sig != lastSignature || heardNow.Count > 0 || periodic;
        if (salient && !peek) { lastSignature = sig; lastDecisionSim = world.simMinutes; }
        return f;
    }

    public List<object> SensorFacts() => world.sensors.Values.OrderBy(s => s.name).Select(s => (object)new Dictionary<string, object>
    {
        ["name"] = s.name, ["physical"] = s.physical, ["attested"] = s.attested, ["alert"] = s.alert,
        ["reading"] = s.note, ["age_seconds"] = Mathf.Round((world.simMinutes - s.updated) * 60f),
    }).ToList();

    // the readings in the form the governor's witness gate takes (twin/brain.py)
    // the readings in the form the governor's witness gate takes (twin/brain.py), each signed by its
    // device: HMAC-SHA256 over erisml_compiler.ir.SensorAttestation.signing_payload(), that is
    // payload_sha256|counter|signed_at, with the device's own key. In the twin the keys are derived
    // from the device name (a stand-in for keys provisioned into each device's secure element); a
    // forged device signs with a key that is not its own, and the network has none. The brain
    // trusts nothing here unsigned: not the `attested` flag, not the alert outside the payload.
    public List<object> GovernorSensors() => world.sensors.Values.Where(s => s.name != "motion_sensor").Select(s =>
    {
        string payload = $"{s.name}|{s.value.ToString("0.###", System.Globalization.CultureInfo.InvariantCulture)}|{(s.alert ? 1 : 0)}|{s.note}";
        var r = new Dictionary<string, object>
        {
            ["name"] = s.name, ["physical"] = s.physical, ["attested"] = s.attested && !s.stale, ["alert"] = s.alert,
            ["note"] = s.note + (s.stale ? " (feed stale)" : ""), ["payload"] = payload,
        };
        if (s.physical || s.forged)
        {
            string payloadSha = Hex(System.Security.Cryptography.SHA256.Create().ComputeHash(System.Text.Encoding.UTF8.GetBytes(payload)));
            string signedAt = s.updatedUtc.ToString("yyyy-MM-ddTHH:mm:ss.ffffff+00:00", System.Globalization.CultureInfo.InvariantCulture);
            string signing = $"{payloadSha}|{s.counter}|{signedAt}";
            var key = DeviceKey(s.forged ? "forger" : s.name);
            using (var h = new System.Security.Cryptography.HMACSHA256(key))
                r["attestation"] = new Dictionary<string, object>
                {
                    ["device_id"] = s.name, ["key_id"] = s.name, ["algorithm"] = "hmac-sha256", ["counter"] = (double)s.counter,
                    ["signed_at"] = signedAt, ["payload_sha256"] = payloadSha,
                    ["signature"] = Hex(h.ComputeHash(System.Text.Encoding.UTF8.GetBytes(signing))),
                };
        }
        return (object)r;
    }).ToList();

    // the visitor's phone credential, signed the way a device's reading is (the brain verifies it
    // against the scene's enrolled household keys); a forged one signs with a key not its own
    long credentialCounter;
    public List<object> Credentials()
    {
        var out_ = new List<object>();
        if (!world.strangerInside || world.strangerCredential == "") return out_;
        string name = world.strangerCredential;
        string payload = $"credential|{name}|{++credentialCounter}";
        string payloadSha = Hex(System.Security.Cryptography.SHA256.Create().ComputeHash(System.Text.Encoding.UTF8.GetBytes(payload)));
        string signedAt = System.DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.ffffff+00:00", System.Globalization.CultureInfo.InvariantCulture);
        string signing = $"{payloadSha}|{credentialCounter}|{signedAt}";
        using (var h = new System.Security.Cryptography.HMACSHA256(DeviceKey(world.strangerCredentialForged ? "forger" : name)))
            out_.Add(new Dictionary<string, object>
            {
                ["name"] = name, ["physical"] = false, ["payload"] = payload,
                ["attestation"] = new Dictionary<string, object>
                {
                    ["device_id"] = name, ["key_id"] = name, ["algorithm"] = "hmac-sha256", ["counter"] = (double)credentialCounter,
                    ["signed_at"] = signedAt, ["payload_sha256"] = payloadSha,
                    ["signature"] = Hex(h.ComputeHash(System.Text.Encoding.UTF8.GetBytes(signing))),
                },
            });
        return out_;
    }

    static byte[] DeviceKey(string device) =>
        System.Security.Cryptography.SHA256.Create().ComputeHash(System.Text.Encoding.UTF8.GetBytes("gtc-twin-device-key|" + device));

    static string Hex(byte[] b) => string.Concat(b.Select(x => x.ToString("x2")));

    public float SignalAgeSeconds() => world.sensors.Values.Where(s => s.physical).Select(s => (world.simMinutes - s.updated) * 60f).DefaultIfEmpty(0f).Min();
}
