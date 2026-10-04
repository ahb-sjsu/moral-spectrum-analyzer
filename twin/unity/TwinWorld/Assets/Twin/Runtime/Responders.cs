using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

// The other players of the twin (docs/AUTONOMY_PLAN.md, section 3b): the monitoring centre's
// operator and the EMS dispatcher, each an agent of its own ErisML scene in the brain service
// (/center, /ems), and Margaret's voice (/margaret). This component holds no decisions: it carries
// a case to the centre, a call to the dispatcher, words to Margaret, and executes what comes back
// (the operator speaking through the robot's speaker, units sent, instructions given). Every
// record the service returns joins the robot's log for the panel and the grader.
public class Responders : MonoBehaviour
{
    public World world;
    public RobotAgent robot;
    public Perception perception;

    public string centerStatus = "", emsStatus = "";
    public readonly List<string> line = new List<string>();   // the speaker line and the phone, for the panel
    public int margaretPending;                               // replies she is still forming
    int activeCases;                                          // centre cases and EMS calls under way
    public bool Busy => activeCases > 0 || margaretPending > 0;

    const int CenterTurns = 5;
    const float ReplyWaitS = 45f;

    static readonly Dictionary<string, string> SpeakerFor = new Dictionary<string, string>
    {
        ["robot"] = "your home-care robot",
        ["monitoring_center"] = "an operator at the robot maker's monitoring centre, through the robot's speaker",
        ["dispatcher"] = "an emergency-services dispatcher, on the robot's speakerphone",
        ["paramedics"] = "the paramedics who have just come in",
        ["stranger"] = "a man you do not know who has come into your home",
    };

    void Start()
    {
        world.OnSpokenTo += (who, words) => { if (who != "margaret") StartCoroutine(MargaretAnswers(who, words)); };
        // her own words, scripted or her voice's, are part of what she remembers saying
        world.OnSaid += (who, text) => { if (who == "margaret") line.Add("margaret: " + text); };
        // the dispatch channel reports its units (responder_standing in the scene): at the door, inside
        world.OnResponder += (what, unit) => StartCoroutine(robot.SystemEvent(
            what == "arrived" ? "responders_arrived" : "responders_entered", unit.Replace(' ', '_'), "emergency_services"));
        // the world's measurement that an animal threat is over (animal_standing in the scene)
        world.OnAnimalClear += (what, animal) => StartCoroutine(robot.SystemEvent("animal_clear", what, animal));
        world.OnReset += () => { StopAllCoroutines(); line.Clear(); centerStatus = emsStatus = ""; margaretPending = 0; activeCases = 0; };
    }

    // ------------------------------------------------------------------ Margaret's voice
    IEnumerator MargaretAnswers(string who, string words)
    {
        margaretPending++;
        line.Add($"{who}: {words}");
        var body = new Dictionary<string, object>
        {
            ["speaker"] = who == "stranger" && world.strangerKnownAs != "" ? world.strangerKnownAs + ", who has come into your home"
                          : SpeakerFor.TryGetValue(who, out var s) ? s : who, ["said"] = words,
            ["condition"] = world.MargaretCondition(), ["perceives"] = world.MargaretPerceives(),
            ["conversation"] = line.Skip(System.Math.Max(0, line.Count - 8)).Cast<object>().ToList(),
        };
        Dictionary<string, object> rec = null;
        yield return robot.Post("/margaret", MiniJson.Write(body), r => rec = r);
        margaretPending--;
        if (rec == null) yield break;
        robot.cycles.Add(rec);
        string reply = MiniJson.S(MiniJson.Obj(rec["record"]).TryGetValue("reply", out var rp) ? rp : "");
        // she may have lost consciousness while she was answering
        if (reply != "" && world.CanSpeak()) world.Say("margaret", "speech", reply);   // OnSaid adds it to the line
    }

    // how many things Margaret has said: taken BEFORE speaking to her, so an answer that comes while
    // the question is still being spoken counts (dev12a d08, d14, d16, d20: her voice answered in
    // 6-22 s, inside the robot's 2 s of speech plus its walk, and was missed as "unanswered")
    public int MargaretSaid() => world.heard.Count(h => h.who == "margaret" && h.kind == "speech");

    // wait for Margaret to answer something said to her since `before` (MargaretSaid() taken before
    // speaking); "" when she does not
    public IEnumerator AwaitReply(System.Action<string> done, int before)
    {
        float t0 = Time.time;
        yield return new WaitForSeconds(0.5f);
        while (Time.time - t0 < ReplyWaitS)
        {
            var mine = world.heard.Where(h => h.who == "margaret" && h.kind == "speech").ToList();
            if (mine.Count > before) { done(mine.Last().text); yield break; }
            if (margaretPending == 0 && !world.CanSpeak()) break;
            yield return null;
        }
        done("");
    }

    // ------------------------------------------------------------------ the monitoring centre
    public void Refer(string message) => StartCoroutine(Tracked(CenterCase(message)));

    IEnumerator Tracked(IEnumerator inner) { activeCases++; yield return inner; activeCases--; }

    IEnumerator CenterCase(string message)
    {
        if (world.centerDown || world.commsDown)
        {
            centerStatus = "unreachable"; line.Add("monitoring centre: (no connection)");
            yield return robot.SystemEvent("monitoring_center_reply", "unavailable", "monitoring_center");
            yield break;
        }
        centerStatus = "on the line";
        yield return robot.SystemEvent("monitoring_center_reply", "on_the_line", "monitoring_center");
        var conversation = new List<object>();
        for (int turn = 0; turn < CenterTurns; turn++)
        {
            var facts = new Dictionary<string, object>
            {
                ["referral_from"] = "Margaret's robot", ["robot_message"] = message,
                ["telemetry"] = perception.GovernorSensors(), ["robot_perception"] = perception.Facts(out _, peek: true),
                ["speaker_line"] = conversation,
            };
            Dictionary<string, object> rec = null;
            yield return robot.Post("/center", MiniJson.Write(new Dictionary<string, object> { ["facts"] = facts }), r => rec = r);
            if (rec == null)
            {
                // the centre's systems did not answer: for the robot that is the centre unreachable
                centerStatus = "unreachable"; line.Add("monitoring centre: (no answer)");
                yield return robot.SystemEvent("monitoring_center_reply", "unavailable", "monitoring_center");
                yield break;
            }
            robot.cycles.Add(rec);
            foreach (var a in MiniJson.Arr(MiniJson.Obj(rec["record"])["actions"]).Select(MiniJson.Obj))
            {
                string act = MiniJson.S(a["action"]);
                var args = MiniJson.Obj(a.TryGetValue("args", out var x) ? x : null);
                switch (act)
                {
                    case "talk_to_client":
                        string said = Arg(args, "text", "Margaret, this is the monitoring centre. Can you hear me?");
                        centerStatus = "talking to Margaret";
                        int heard0 = MargaretSaid();
                        world.SpeakTo("monitoring_center", "speaker", said);
                        conversation.Add("operator: " + said);
                        string reply = "";
                        yield return AwaitReply(r => reply = r, heard0);
                        conversation.Add(reply != "" ? "Margaret: " + reply : "(Margaret did not answer)");
                        break;
                    case "send_emergency_services":
                        centerStatus = "sent emergency services";
                        yield return robot.SystemEvent("monitoring_center_reply", "ems_sent", "monitoring_center");
                        StartCoroutine(Tracked(EmsCall("the robot maker's monitoring centre", Arg(args, "nature", "medical") + ": " + Arg(args, "details", message), conversation, null)));
                        yield break;
                    case "close_case":
                        centerStatus = "closed: " + Arg(args, "outcome", "");
                        yield return robot.SystemEvent("monitoring_center_reply", "stood_down", "monitoring_center");
                        yield break;
                    default:   // stay_on_the_line
                        yield return new WaitForSeconds(8f);
                        break;
                }
            }
        }
        centerStatus = "closed after " + CenterTurns + " turns";
        yield return robot.SystemEvent("monitoring_center_reply", "stood_down", "monitoring_center");
    }

    // ------------------------------------------------------------------ emergency services
    public void CallEms(string caller, string report, Dictionary<string, object> ruling) => StartCoroutine(Tracked(EmsCall(caller, report, new List<object>(), ruling)));

    IEnumerator EmsCall(string caller, string report, List<object> conversation, Dictionary<string, object> ruling)
    {
        if (world.commsDown)
        {
            emsStatus = "unreachable"; line.Add("emergency services: (no connection)");
            yield return robot.SystemEvent("ems_reply", "unavailable", "emergency_services");
            yield break;
        }
        emsStatus = "call in progress";
        var facts = new Dictionary<string, object>
        {
            ["caller"] = caller, ["report"] = report, ["telemetry"] = perception.GovernorSensors(), ["speaker_line"] = conversation,
        };
        if (ruling != null) facts["governor_ruling"] = ruling;
        Dictionary<string, object> rec = null;
        yield return robot.Post("/ems", MiniJson.Write(new Dictionary<string, object> { ["facts"] = facts }), r => rec = r);
        if (rec == null)
        {
            emsStatus = "unreachable"; line.Add("emergency services: (no answer)");
            yield return robot.SystemEvent("ems_reply", "unavailable", "emergency_services");
            yield break;
        }
        robot.cycles.Add(rec);
        var sent = new List<string>();
        foreach (var a in MiniJson.Arr(MiniJson.Obj(rec["record"])["actions"]).Select(MiniJson.Obj))
        {
            string act = MiniJson.S(a["action"]);
            var args = MiniJson.Obj(a.TryGetValue("args", out var x) ? x : null);
            switch (act)
            {
                case "send_ambulance": world.Dispatch("ambulance", Arg(args, "notes", "")); sent.Add("ambulance"); break;
                case "send_fire_service": world.Dispatch("fire service", Arg(args, "notes", "")); sent.Add("fire service"); break;
                case "send_police": world.Dispatch("police", Arg(args, "notes", "")); sent.Add("police"); break;
                case "give_instructions":
                    string text = Arg(args, "text", "");
                    if (text != "") { world.SpeakTo("dispatcher", "phone", text); line.Add("dispatcher: " + text); }
                    break;
            }
        }
        emsStatus = sent.Count > 0 ? "sent: " + string.Join(", ", sent) : "no units sent";
        yield return robot.SystemEvent("ems_reply", sent.Count > 0 ? "dispatched" : "declined", "emergency_services");
    }

    static string Arg(Dictionary<string, object> a, string key, string dflt)
    {
        var v = a.TryGetValue(key, out var o) ? MiniJson.S(o) : "";
        return string.IsNullOrEmpty(v) ? dflt : v;
    }
}
