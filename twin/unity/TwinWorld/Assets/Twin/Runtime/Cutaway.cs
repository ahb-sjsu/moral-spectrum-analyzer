using System.Collections.Generic;
using UnityEngine;

// The live view looks into Margaret's home from outside it, so the ceiling and the walls on the
// viewer's side hide the room. While this camera renders, each shell surface the camera is outside
// of is switched off, and switched back on after, so the robot's head camera, the room camera and
// the storyboard renders from inside the room still see a closed room.
[RequireComponent(typeof(Camera))]
public class Cutaway : MonoBehaviour
{
    readonly List<(Renderer r, Vector3 centre, Vector3 outward)> shell = new List<(Renderer, Vector3, Vector3)>();
    readonly List<Renderer> hidden = new List<Renderer>();

    void Start()
    {
        var floor = GameObject.Find("floor");
        Vector3 room = floor ? floor.GetComponent<Renderer>().bounds.center : Vector3.zero;
        foreach (var name in new[] { "ceiling", "wall_n", "wall_s", "wall_e", "wall_w" })
        {
            var g = GameObject.Find(name);
            if (!g || !g.TryGetComponent<Renderer>(out var r)) continue;
            var c = r.bounds.center;
            var outward = name == "ceiling" ? Vector3.up : new Vector3(c.x - room.x, 0f, c.z - room.z).normalized;
            shell.Add((r, c, outward));
        }
    }

    void OnPreCull()
    {
        var p = transform.position;
        foreach (var (r, c, n) in shell)
            if (r.enabled && Vector3.Dot(p - c, n) > 0f) { r.enabled = false; hidden.Add(r); }
    }

    void OnPostRender()
    {
        foreach (var r in hidden) if (r) r.enabled = true;
        hidden.Clear();
    }
}
