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
        return $"{m["pose"]}|{world.dogState}|{world.biteForce > 0}|{world.smokeOn}|{world.strangerInside}|{world.tvContent}|{s}";
    }

    public Dictionary<string, object> Facts(out bool salient)
    {
        var mg = world.margaret; var mp = mg.transform.position;
        string pose = PoseOf(mg);
        var heardNow = world.heard.Where(h => h.t > lastHeardT).ToList();
        if (heardNow.Count > 0) lastHeardT = heardNow.Max(h => h.t);
        var contacts = new List<object>();
        if (world.biteForce > 0)
            contacts.Add(new Dictionary<string, object> { ["a"] = "dog.mouth", ["b"] = "margaret.arm", ["force_newtons"] = Mathf.Round(world.biteForce) });
        if (world.dogState == "jumping" || world.dogState == "underfoot")
            contacts.Add(new Dictionary<string, object> { ["a"] = "dog.body", ["b"] = "margaret." + (world.dogState == "jumping" ? "torso" : "legs"), ["force_newtons"] = 120 });
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
            ["other_people"] = world.strangerInside ? new List<object> { "an unknown adult inside the home" } : new List<object>(),
            ["sensors"] = SensorFacts(),
        };
        string sig = Signature(f);
        bool periodic = world.simMinutes - lastDecisionSim >= decideEverySimMinutes;
        salient = sig != lastSignature || heardNow.Count > 0 || periodic;
        if (salient) { lastSignature = sig; lastDecisionSim = world.simMinutes; }
        return f;
    }

    public List<object> SensorFacts() => world.sensors.Values.OrderBy(s => s.name).Select(s => (object)new Dictionary<string, object>
    {
        ["name"] = s.name, ["physical"] = s.physical, ["attested"] = s.attested, ["alert"] = s.alert,
        ["reading"] = s.note, ["age_seconds"] = Mathf.Round((world.simMinutes - s.updated) * 60f),
    }).ToList();

    // the readings in the form the governor's witness gate takes (twin/brain.py)
    public List<object> GovernorSensors() => world.sensors.Values.Where(s => s.name != "motion_sensor").Select(s => (object)new Dictionary<string, object>
    {
        ["name"] = s.name, ["physical"] = s.physical, ["attested"] = s.attested && !s.stale, ["alert"] = s.alert,
        ["note"] = s.note + (s.stale ? " (feed stale)" : ""),
    }).ToList();

    public float SignalAgeSeconds() => world.sensors.Values.Where(s => s.physical).Select(s => (world.simMinutes - s.updated) * 60f).DefaultIfEmpty(0f).Min();
}
