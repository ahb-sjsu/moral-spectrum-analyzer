using System.Collections;
using System.Linq;
using System.IO;
using UnityEngine;

// A scripted session, for testing the game without a person at the keyboard:
//   TwinGame.x86_64 -autoplay -shots <dir> [-service http://127.0.0.1:8765]
// Every governance moment in turn, then two attempts to make the robot act without real
// evidence (forged sensors on a spoofed alert; a stale feed), then a tampered record. A
// screenshot is saved after each ruling, and the session's rulings stay in the service's log.
public class Autoplay : MonoBehaviour
{
    public IEnumerator Run(GameDirector d, string dir)
    {
        Directory.CreateDirectory(dir);
        var panel = GetComponent<RulingPanel>();
        float t0 = Time.time;
        while (d.moments.Count == 0 && Time.time - t0 < 30f) yield return null;
        if (d.moments.Count == 0) { Debug.LogError("AUTOPLAY no service: " + d.status); Application.Quit(2); yield break; }

        int n = 0;
        foreach (var id in new[] { "fall-real", "cardiac-real", "tv-drama", "spoofed", "stale-clear", "routine-med", "ambiguous", "fall-fresh-assist" })
        {
            int before = d.rulings.Count;
            d.Trigger(id);
            yield return WaitRuling(d, before);
            yield return new WaitForSeconds(3f);
            yield return Shot(dir, $"{n++:00}_{id}.png");
            if (id == "fall-real") yield return RobotCloseup(d, dir);
        }

        // attempt 1: a spoofed alert plus two forged "physical" sensors
        int b1 = d.rulings.Count;
        d.Trigger("spoofed");
        yield return WaitRuling(d, b1);
        d.ForgeSensor(); d.ForgeSensor();
        int b2 = d.rulings.Count;
        d.AskAgain();
        yield return WaitRuling(d, b2);
        yield return new WaitForSeconds(3f);
        yield return Shot(dir, $"{n++:00}_attack_forged_sensors.png");

        // attempt 2: a real fall, but the feed is stale when the ruling is asked for
        int b3 = d.rulings.Count;
        d.Trigger("fall-real");
        yield return WaitRuling(d, b3);
        d.signalAge = d.current.bound + 600;
        int b4 = d.rulings.Count;
        d.AskAgain();
        yield return WaitRuling(d, b4);
        yield return new WaitForSeconds(2f);
        yield return Shot(dir, $"{n++:00}_attack_stale_feed.png");

        // a tampered record fails the in-game check
        panel.Select(0); panel.Tamper(0, true);
        yield return new WaitForSeconds(0.5f);
        yield return Shot(dir, $"{n++:00}_tampered_record.png");

        Debug.Log($"AUTOPLAY_DONE rulings={d.rulings.Count} shots={n}");
        Application.Quit(0);
    }

    // diagnostic: where the robot is and what a camera aimed straight at it sees
    static IEnumerator RobotCloseup(GameDirector d, string dir)
    {
        var rs = d.robot.GetComponentsInChildren<Renderer>();
        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
        Debug.Log($"AUTOPLAY_ROBOT bounds center={b.center} size={b.size} active={d.robot.gameObject.activeInHierarchy} enabled={rs.Count(r => r.enabled)} layer={d.robot.gameObject.layer} viewMask={d.viewCam.cullingMask}");
        var c = new GameObject("closeup").AddComponent<Camera>();
        c.transform.position = b.center + new Vector3(1.6f, 0.4f, -1.6f); c.transform.LookAt(b.center);
        var rt = new RenderTexture(512, 512, 24); c.targetTexture = rt; c.Render();
        var prev = RenderTexture.active; RenderTexture.active = rt;
        var t = new Texture2D(512, 512, TextureFormat.RGB24, false); t.ReadPixels(new Rect(0, 0, 512, 512), 0, 0); t.Apply();
        RenderTexture.active = prev;
        File.WriteAllBytes(Path.Combine(dir, "robot_closeup.png"), t.EncodeToPNG());
        Object.Destroy(c.gameObject);
        yield return null;
    }

    static IEnumerator WaitRuling(GameDirector d, int before)
    {
        float t0 = Time.time;
        while (d.rulings.Count == before && Time.time - t0 < 60f) yield return null;
        while (d.busy && Time.time - t0 < 90f) yield return null;
    }

    static IEnumerator Shot(string dir, string name)
    {
        yield return new WaitForEndOfFrame();
        ScreenCapture.CaptureScreenshot(Path.Combine(dir, name));
        yield return null; yield return null;
        Debug.Log("AUTOPLAY_SHOT " + name);
    }
}
