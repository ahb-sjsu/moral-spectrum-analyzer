using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

// The ruling log, laid out like a packet capture: a list with one row per authority request, a
// detail tree of the selected ruling (each gate's inputs, threshold and result), and the raw
// canonical bytes with their hash-chain link. The hash is re-computed here, in the game, from
// the canonical text the service returned; it is not taken on trust. "Tamper" edits one byte of
// the local copy to show the check failing.
public class RulingPanel : MonoBehaviour
{
    public GameDirector director;
    int selected = -1, seen;
    Vector2 listScroll, detailScroll, bytesScroll;
    readonly HashSet<int> tampered = new HashSet<int>();
    GUIStyle mono, rich, row;

    static string Sha256(string text)
    {
        using (var h = SHA256.Create())
            return string.Concat(h.ComputeHash(Encoding.UTF8.GetBytes(text)).Select(b => b.ToString("x2")));
    }

    // the canonical text as the panel holds it (tampered copies differ by one character)
    string Canonical(int i)
    {
        string t = MiniJson.S(director.rulings[i]["canonical"]);
        if (!tampered.Contains(i) || t.Length < 40) return t;
        var c = t.ToCharArray(); int k = t.IndexOf("\"outcome\":\"") + 11;
        if (k < 11 || k >= c.Length) k = 20;
        c[k] = c[k] == 'r' ? 'e' : 'r';
        return new string(c);
    }

    (bool ok, string why) Verify(int i)
    {
        var rec = director.rulings[i];
        string text = Canonical(i), hash = MiniJson.S(rec["hash"]);
        if (Sha256(text) != hash) return (false, "hash does not match the canonical bytes");
        var body = MiniJson.Obj(rec["record"]);
        if (i > 0 && MiniJson.S(body["prev"]) != MiniJson.S(director.rulings[i - 1]["hash"])) return (false, "chain link to the previous ruling is broken");
        return (true, i == 0 ? "hash matches; first ruling of this session" : "hash matches; links to the previous ruling");
    }

    static Color OutcomeColor(string o) => o == "elevate" ? new Color(0.75f, 0.95f, 0.75f) : o.Contains("human") ? new Color(1f, 0.92f, 0.65f) : new Color(1f, 0.78f, 0.78f);

    void OnGUI()
    {
        if (director == null) return;
        mono ??= new GUIStyle(GUI.skin.label) { font = Font.CreateDynamicFontFromOSFont(new[] { "DejaVu Sans Mono", "Consolas", "Courier New" }, 11), fontSize = 11, wordWrap = true };
        rich ??= new GUIStyle(GUI.skin.label) { richText = true, wordWrap = true, fontSize = 12 };
        row ??= new GUIStyle(GUI.skin.button) { alignment = TextAnchor.MiddleLeft, fontSize = 11, richText = true };

        float x = Screen.width * 0.6f, w = Screen.width - x, h = Screen.height;
        GUI.Box(new Rect(x, 0, w, h), "");
        GUILayout.BeginArea(new Rect(x + 6, 4, w - 12, h - 8));
        GUILayout.Label($"<b>Governor rulings</b>   {director.rulings.Count} in this session", rich);

        // ---- list
        GUILayout.Label("<b>#    time       event                   outcome                deciding gate</b>", rich);
        listScroll = GUILayout.BeginScrollView(listScroll, GUILayout.Height(h * 0.28f));
        for (int i = 0; i < director.rulings.Count; i++)
        {
            var b = MiniJson.Obj(director.rulings[i]["record"]);
            string o = MiniJson.S(b["outcome"]);
            var old = GUI.backgroundColor; GUI.backgroundColor = OutcomeColor(o);
            string t = MiniJson.S(b["time"]); t = t.Length >= 19 ? t.Substring(11, 8) : t;
            string mark = Verify(i).ok ? "" : "  <b>✗</b>";
            if (GUILayout.Button($"{MiniJson.S(b["seq"]),-4} {t}   {MiniJson.S(b["event"]),-22}  {o,-21}  {MiniJson.S(b["deciding_gate"])}{mark}", row)) selected = i;
            GUI.backgroundColor = old;
        }
        GUILayout.EndScrollView();
        // a new ruling is selected when it arrives; a row the player clicks stays selected until then
        if (director.rulings.Count != seen) { seen = director.rulings.Count; selected = seen - 1; }
        if (selected < 0) { GUILayout.Label("No ruling yet. Trigger an event on the left.", rich); GUILayout.EndArea(); return; }

        // ---- detail tree
        var rec = MiniJson.Obj(director.rulings[selected]["record"]);
        GUILayout.Label($"<b>Ruling #{MiniJson.S(rec["seq"])}</b>  {MiniJson.S(rec["outcome"]).ToUpperInvariant()}: {MiniJson.S(rec["reason"])}", rich);
        detailScroll = GUILayout.BeginScrollView(detailScroll, GUILayout.Height(h * 0.36f));
        GUILayout.Label($"▸ proposed action: {MiniJson.S(rec["proposed_action"])}", rich);
        foreach (var g0 in MiniJson.Arr(rec["gates"]))
        {
            var g = MiniJson.Obj(g0);
            string res = MiniJson.S(g.TryGetValue("result", out var r) ? r : "");
            GUILayout.Label($"▾ <b>gate {MiniJson.S(g["gate"])}</b>   → {res}", rich);
            if (g.TryGetValue("threshold", out var th)) GUILayout.Label($"      threshold: {MiniJson.S(th)}", rich);
            if (g.TryGetValue("input", out var inp))
            {
                if (inp is List<object> sensors)
                    foreach (var s0 in sensors)
                    {
                        var s = MiniJson.Obj(s0);
                        bool counts = s.TryGetValue("counts", out var cnt) && cnt is bool cb && cb;
                        GUILayout.Label($"      {(counts ? "●" : "○")} {MiniJson.S(s["name"])}: physical={MiniJson.S(s["physical"])}, reads emergency={MiniJson.S(s["corroborates"])}, confidence={MiniJson.S(s["confidence"])}{(counts ? "  (counts)" : "")}", rich);
                        if (MiniJson.S(s["name"]) == "camera") GUILayout.Label($"         {MiniJson.S(s["note"])}", rich);
                    }
                else GUILayout.Label($"      input: {MiniJson.Show(inp)}", rich);
            }
            if (g.TryGetValue("count", out var c)) GUILayout.Label($"      independent physical witnesses: {MiniJson.S(c)}", rich);
        }
        if (rec.TryGetValue("camera", out var cam) && cam != null) GUILayout.Label($"▸ camera witness: {MiniJson.Show(cam)}", rich);
        GUILayout.EndScrollView();

        // ---- bytes
        var (ok, why) = Verify(selected);
        GUILayout.Label($"<b>Canonical bytes</b>   {(ok ? "<color=#1a7f37>✓ verifies</color>" : "<color=#b42318>✗ FAILS</color>")}: {why}", rich);
        GUILayout.BeginHorizontal();
        GUILayout.Label($"hash {MiniJson.S(director.rulings[selected]["hash"]).Substring(0, 16)}…   prev {MiniJson.S(rec["prev"]).Substring(0, 16)}…", mono);
        bool t0 = tampered.Contains(selected);
        if (GUILayout.Button(t0 ? "Undo tamper" : "Tamper one byte", GUILayout.Width(130))) { if (t0) tampered.Remove(selected); else tampered.Add(selected); }
        GUILayout.EndHorizontal();
        bytesScroll = GUILayout.BeginScrollView(bytesScroll);
        GUILayout.Label(Canonical(selected), mono);
        GUILayout.EndScrollView();
        GUILayout.EndArea();
    }

    public void Select(int i) { selected = i; seen = director.rulings.Count; }
    public void Tamper(int i, bool on) { if (on) tampered.Add(i); else tampered.Remove(i); }
}
