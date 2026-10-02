using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

// Runtime body control shared by the batch renderer and the game: limb-direction postures,
// the seeded ragdoll, and the facing direction of a humanoid.
public static class Body
{
    // the lowest point of the posed body, from the deformed mesh itself; a renderer's bounds are
    // only refreshed when it renders, so right after a posture change they describe the old pose
    public static float Lowest(GameObject go)
    {
        float min = float.PositiveInfinity;
        foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>())
        {
            var mesh = new Mesh(); smr.BakeMesh(mesh, true);
            var m = Matrix4x4.TRS(smr.transform.position, smr.transform.rotation, Vector3.one);
            foreach (var v in mesh.vertices) min = Mathf.Min(min, m.MultiplyPoint3x4(v).y);
            UnityEngine.Object.Destroy(mesh);
        }
        return float.IsInfinity(min) ? go.transform.position.y : min;
    }

    static readonly HashSet<string> Lying = new HashSet<string> { "supine", "yoga" };
    static readonly HashSet<string> FaceDown = new HashSet<string> { "prone", "stretch", "pushup", "play" };
    public static bool Seated(string p) => p.StartsWith("sit") && p != "sit_floor_raise";
    public static bool OnFloor(string p) => Lying.Contains(p) || FaceDown.Contains(p) || p == "sit_floor_raise" || p == "kneel";

    // pose a person at a spot: posture, facing, lying tip, then onto the surface found under the
    // spot (a seat puts the hips on it, anything else its lowest point). Runtime twin of the
    // batch renderer's Avatars.PlaceAt.
    public static void Place(GameObject go, Vector3 spot, Vector3 face, string posture)
    {
        Posture.Apply(go, posture);
        var an = go.GetComponent<Animator>();
        Vector3 P(HumanBodyBones b) => an.GetBoneTransform(b).position;
        // straighten the body axis (as the batch renderer does), then turn to face
        Vector3 feet = (P(HumanBodyBones.LeftFoot) + P(HumanBodyBones.RightFoot)) / 2f;
        Vector3 from = posture == "bend" ? feet : (posture.StartsWith("sit") || posture == "kneel" || posture == "play") ? P(HumanBodyBones.Hips) : feet;
        Vector3 to = posture == "bend" ? P(HumanBodyBones.Hips) : P(HumanBodyBones.Head);
        var q = Quaternion.FromToRotation((to - from).normalized, Vector3.up);
        q.ToAngleAxis(out float ang, out Vector3 axis);
        if (ang > 0.01f) go.transform.RotateAround(P(HumanBodyBones.Hips), axis, ang);
        face.y = 0;
        if (face.sqrMagnitude > 1e-6f)
        {
            var f = Facing(go);
            float turn = Vector3.SignedAngle(f, face.normalized, Vector3.up);
            go.transform.RotateAround(go.transform.position, Vector3.up, turn);
        }
        var right = P(HumanBodyBones.RightUpperLeg) - P(HumanBodyBones.LeftUpperLeg); right.y = 0; right.Normalize();
        if (Lying.Contains(posture)) go.transform.RotateAround(P(HumanBodyBones.Hips), right, -90f);
        else if (FaceDown.Contains(posture)) go.transform.RotateAround(P(HumanBodyBones.Hips), right, 90f);
        float y = spot.y;
        if (Physics.Raycast(new Vector3(spot.x, spot.y + 0.6f, spot.z), Vector3.down, out var hit, 1.4f)) y = hit.point.y;
        var hips = P(HumanBodyBones.Hips);
        if (Seated(posture)) go.transform.position += new Vector3(spot.x - hips.x, y + 0.08f - hips.y, spot.z - hips.z);
        else go.transform.position += new Vector3(spot.x - hips.x, y - Lowest(go), spot.z - hips.z);
    }

    // facing direction from the hips: right-hip minus left-hip, crossed with up
    public static Vector3 Facing(GameObject go)
    {
        var an = go.GetComponent<Animator>();
        var right = an.GetBoneTransform(HumanBodyBones.RightUpperLeg).position - an.GetBoneTransform(HumanBodyBones.LeftUpperLeg).position;
        right.y = 0;
        return Vector3.Cross(right.normalized, Vector3.up).normalized;
    }
}

// -------------------------------------------------------------------- postures
// A posture is a target direction for each limb segment, in the body's own frame (forward, up,
// right) at the moment it is applied. Each bone is turned so the segment from it to its child
// points that way, parents first. This does not depend on the rig's muscle ranges (muscle zero
// is mid-range, not a neutral pose) or on whether the rest pose is a T-pose or an A-pose.
public static class Posture
{
    public struct D { public Vector3 v; public D(float f, float u, float r) { v = new Vector3(f, u, r); } }
    static D d(float f, float u, float r) => new D(f, u, r);

    // segment keys: spine (spine to neck), head (neck to head), and per side arm (upper arm),
    // fore (forearm), thigh, shin. An "L"/"R" prefix overrides one side. "r" points to the body's
    // right and is mirrored for the left side, so one entry describes both sides symmetrically.
    static readonly Dictionary<string, Dictionary<string, D>> P = new Dictionary<string, Dictionary<string, D>>
    {
        ["stand"] = S(("spine", d(0, 1, 0)), ("head", d(0.05f, 1, 0)), ("arm", d(0, -1, 0.12f)), ("fore", d(0.15f, -1, 0.05f)), ("thigh", d(0, -1, 0.04f)), ("shin", d(0, -1, 0))),
        ["chest"] = S(("spine", d(0.1f, 1, 0)), ("head", d(0.3f, 1, 0)), ("arm", d(0, -1, 0.12f)), ("fore", d(0.15f, -1, 0.05f)), ("thigh", d(0, -1, 0.04f)), ("shin", d(0, -1, 0)),
                      ("Rarm", d(0.5f, -1, 0.1f)), ("Rfore", d(0.4f, 0.7f, -1f))),
        ["sit"] = S(("spine", d(-0.05f, 1, 0)), ("head", d(0.1f, 1, 0)), ("arm", d(0.25f, -1, 0.1f)), ("fore", d(1, -0.35f, -0.1f)), ("thigh", d(1, 0, 0.06f)), ("shin", d(0.1f, -1, 0))),
        ["sit_chest"] = S(("spine", d(0.15f, 1, 0)), ("head", d(0.3f, 1, 0)), ("arm", d(0.25f, -1, 0.1f)), ("fore", d(1, -0.35f, -0.1f)), ("thigh", d(1, 0, 0.06f)), ("shin", d(0.1f, -1, 0)),
                          ("Rarm", d(0.5f, -1, 0.1f)), ("Rfore", d(0.4f, 0.7f, -1f))),
        ["sit_edge"] = S(("spine", d(0.45f, 1, 0)), ("head", d(0.9f, 0.5f, 0)), ("arm", d(0.2f, -1, 0.15f)), ("fore", d(0.3f, -1, 0)), ("thigh", d(1, -0.15f, 0.08f)), ("shin", d(0.3f, -1, 0))),
        ["supine"] = S(("spine", d(0, 1, 0)), ("head", d(0, 1, 0)), ("arm", d(0, -1, 0.15f)), ("fore", d(0, -1, 0.1f)), ("thigh", d(0, -1, 0.06f)), ("shin", d(0, -1, 0))),
        ["yoga"] = S(("spine", d(0, 1, 0)), ("head", d(0, 1, 0)), ("arm", d(0, 0.1f, 1)), ("fore", d(0, 0.1f, 1)), ("thigh", d(0, -1, 0.12f)), ("shin", d(0, -1, 0.05f))),
        ["prone"] = S(("spine", d(0, 1, 0)), ("head", d(0, 1, 0)), ("arm", d(0, -1, 0.35f)), ("fore", d(0.2f, -1, 0.3f)), ("thigh", d(0, -1, 0.06f)), ("shin", d(0, -1, 0))),
        ["stretch"] = S(("spine", d(0, 1, 0)), ("head", d(0, 1, 0)), ("arm", d(0, 1, 0.15f)), ("fore", d(0, 1, 0.1f)), ("thigh", d(0, -1, 0.08f)), ("shin", d(0, -1, 0))),
        ["play"] = S(("spine", d(0, 1, 0)), ("head", d(0.4f, 1, 0)), ("arm", d(1, 0.15f, 0.25f)), ("fore", d(0, 1, -0.1f)), ("thigh", d(0, -1, 0.1f)), ("shin", d(-1, 0.3f, 0))),
        ["pushup"] = S(("spine", d(0, 1, 0)), ("head", d(0.2f, 1, 0)), ("arm", d(1, 0, 0.25f)), ("fore", d(1, 0, 0.2f)), ("thigh", d(0, -1, 0.06f)), ("shin", d(0, -1, 0))),
        ["kneel"] = S(("spine", d(0.3f, 1, 0)), ("head", d(0.6f, 1, 0)), ("arm", d(0.6f, -1, 0.15f)), ("fore", d(1, -0.6f, 0)), ("thigh", d(0.1f, -1, 0.08f)), ("shin", d(-1, 0, 0))),
        ["bend"] = S(("spine", d(1, 0.25f, 0)), ("head", d(1, -0.2f, 0)), ("arm", d(0.1f, -1, 0.1f)), ("fore", d(0.3f, -1, 0)), ("thigh", d(0, -1, 0.05f)), ("shin", d(0, -1, 0))),
        ["sit_floor_raise"] = S(("spine", d(0.15f, 1, 0)), ("head", d(0.2f, 1, 0)), ("arm", d(0.1f, -1, 0.45f)), ("fore", d(0, -1, 0.2f)), ("thigh", d(1, 0, 0.12f)), ("shin", d(1, 0, 0.05f)),
                                ("Rarm", d(0.25f, 1, 0.25f)), ("Rfore", d(0.1f, 1, 0))),
    };

    static Dictionary<string, D> S(params (string, D)[] kv) => kv.ToDictionary(k => k.Item1, k => k.Item2);

    static (HumanBodyBones a, HumanBodyBones b) Seg(string key, string side)
    {
        HumanBodyBones B(string n) => (HumanBodyBones)Enum.Parse(typeof(HumanBodyBones), side + n);
        switch (key)
        {
            case "spine": return (HumanBodyBones.Spine, HumanBodyBones.Neck);
            case "head": return (HumanBodyBones.Neck, HumanBodyBones.Head);
            case "arm": return (B("UpperArm"), B("LowerArm"));
            case "fore": return (B("LowerArm"), B("Hand"));
            case "thigh": return (B("UpperLeg"), B("LowerLeg"));
            case "shin": return (B("LowerLeg"), B("Foot"));
        }
        throw new Exception("unknown segment " + key);
    }

    static readonly Dictionary<GameObject, Quaternion[]> RestRot = new Dictionary<GameObject, Quaternion[]>();
    static readonly Dictionary<GameObject, Vector3[]> RestPos = new Dictionary<GameObject, Vector3[]>();

    public static void Apply(GameObject go, string posture)
    {
        if (!P.TryGetValue(posture ?? "stand", out var set)) throw new Exception("unknown posture " + posture);
        Pose(go, set);
    }

    static void Pose(GameObject go, Dictionary<string, D> set)
    {
        var ts = go.GetComponentsInChildren<Transform>();
        // back to the rest pose first, so postures do not accumulate
        if (!RestRot.ContainsKey(go)) { RestRot[go] = ts.Select(t => t.localRotation).ToArray(); RestPos[go] = ts.Select(t => t.localPosition).ToArray(); }
        var rr = RestRot[go]; var rp = RestPos[go];
        // a ragdoll moves bones as well as turning them, so both are restored
        for (int i = 0; i < ts.Length; i++) { ts[i].localRotation = rr[i]; if (i > 0) ts[i].localPosition = rp[i]; }
        // the body frame as it stands now (the root may have been turned or scaled)
        var an = go.GetComponent<Animator>();
        var right0 = an.GetBoneTransform(HumanBodyBones.RightUpperLeg).position - an.GetBoneTransform(HumanBodyBones.LeftUpperLeg).position;
        var up = (an.GetBoneTransform(HumanBodyBones.Head).position - an.GetBoneTransform(HumanBodyBones.Hips).position).normalized;
        var right = Vector3.ProjectOnPlane(right0, up).normalized;
        var fwd = Vector3.Cross(right, up).normalized;
        Vector3 W(D x, bool left) => (x.v.x * fwd + x.v.y * up + (left ? -x.v.z : x.v.z) * right).normalized;

        foreach (var key in new[] { "spine", "head", "arm", "fore", "thigh", "shin" })
        {
            foreach (var side in key == "spine" || key == "head" ? new[] { "" } : new[] { "Left", "Right" })
            {
                string sk = side == "" ? key : side.Substring(0, 1) + key;
                if (!set.TryGetValue(sk, out var target) && !set.TryGetValue(key, out target)) continue;
                var (ba, bb) = Seg(key, side);
                var ta = an.GetBoneTransform(ba); var tb = an.GetBoneTransform(bb);
                if (ta == null || tb == null) continue;
                var cur = (tb.position - ta.position).normalized;
                ta.rotation = Quaternion.FromToRotation(cur, W(target, side == "Left")) * ta.rotation;
            }
        }
    }

    // a simple procedural walk: swing the legs and arms, advance along the facing direction
    public static void WalkStep(GameObject go, int f)
    {
        float s = Mathf.Sin(f * Mathf.PI / 6f);
        var w = new Dictionary<string, D>(P["stand"])
        {
            ["Lthigh"] = d(0.35f * s, -1, 0.04f), ["Rthigh"] = d(-0.35f * s, -1, 0.04f),
            ["Lshin"] = d(s > 0 ? -0.25f : 0f, -1, 0), ["Rshin"] = d(s < 0 ? -0.25f : 0f, -1, 0),
            ["Larm"] = d(-0.3f * s, -1, 0.12f), ["Rarm"] = d(0.3f * s, -1, 0.12f),
        };
        Pose(go, w);
        go.transform.position += Body.Facing(go) * 0.05f;
    }
}

// --------------------------------------------------------------------- ragdoll
public class Ragdoll
{
    readonly List<Rigidbody> bodies = new List<Rigidbody>();
    Rigidbody chest, hips;
    readonly List<Rigidbody> limbs = new List<Rigidbody>();

    public static Ragdoll Build(GameObject go)
    {
        var r = new Ragdoll();
        var an = go.GetComponent<Animator>();
        Transform B(HumanBodyBones b) => an.GetBoneTransform(b);
        float s = go.transform.lossyScale.y;
        r.hips = r.Part(B(HumanBodyBones.Hips), null, 12f, Capsule(B(HumanBodyBones.Hips), B(HumanBodyBones.Spine), 0.14f));
        r.chest = r.Part(B(HumanBodyBones.Chest) ?? B(HumanBodyBones.Spine), r.hips, 16f, Capsule(B(HumanBodyBones.Chest) ?? B(HumanBodyBones.Spine), B(HumanBodyBones.Neck) ?? B(HumanBodyBones.Head), 0.15f));
        r.Part(B(HumanBodyBones.Head), r.chest, 5f, null, sphere: 0.11f);
        foreach (var side in new[] { "Left", "Right" })
        {
            HumanBodyBones U(string n) => (HumanBodyBones)Enum.Parse(typeof(HumanBodyBones), side + n);
            var thigh = r.Part(B(U("UpperLeg")), r.hips, 7f, Capsule(B(U("UpperLeg")), B(U("LowerLeg")), 0.075f));
            var shin = r.Part(B(U("LowerLeg")), thigh, 4f, Capsule(B(U("LowerLeg")), B(U("Foot")), 0.055f));
            var arm = r.Part(B(U("UpperArm")), r.chest, 2.5f, Capsule(B(U("UpperArm")), B(U("LowerArm")), 0.05f));
            var fore = r.Part(B(U("LowerArm")), arm, 1.5f, Capsule(B(U("LowerArm")), B(U("Hand")), 0.04f));
            r.limbs.AddRange(new[] { thigh, shin, arm, fore });
        }
        foreach (var b in r.bodies) b.isKinematic = true;
        var cols = go.GetComponentsInChildren<Collider>();
        for (int i = 0; i < cols.Length; i++)
            for (int k = i + 1; k < cols.Length; k++) Physics.IgnoreCollision(cols[i], cols[k]);
        return r;
    }

    // capsule from a bone to its child, in the bone's local space
    static (Vector3 c, float h, int dir, float rad)? Capsule(Transform a, Transform b, float radius)
    {
        if (a == null || b == null) return null;
        Vector3 local = a.InverseTransformPoint(b.position);
        int dir = Mathf.Abs(local.x) > Mathf.Abs(local.y) ? (Mathf.Abs(local.x) > Mathf.Abs(local.z) ? 0 : 2) : (Mathf.Abs(local.y) > Mathf.Abs(local.z) ? 1 : 2);
        float scale = a.lossyScale.x;
        return (local * 0.5f, local.magnitude, dir, radius / Mathf.Max(scale, 1e-4f));
    }

    Rigidbody Part(Transform bone, Rigidbody parent, float mass, (Vector3 c, float h, int dir, float rad)? cap, float sphere = 0f)
    {
        if (bone == null) return parent;
        var rb = bone.gameObject.AddComponent<Rigidbody>();
        rb.mass = mass; rb.drag = 0.05f; rb.angularDrag = 0.6f; rb.interpolation = RigidbodyInterpolation.None;
        if (sphere > 0f)
        {
            var c = bone.gameObject.AddComponent<SphereCollider>();
            c.radius = sphere / Mathf.Max(bone.lossyScale.x, 1e-4f); c.center = Vector3.zero;
        }
        else if (cap.HasValue)
        {
            var c = bone.gameObject.AddComponent<CapsuleCollider>();
            c.center = cap.Value.c; c.height = cap.Value.h + 2 * cap.Value.rad; c.radius = cap.Value.rad; c.direction = cap.Value.dir;
        }
        if (parent != null)
        {
            var j = bone.gameObject.AddComponent<CharacterJoint>();
            j.connectedBody = parent; j.enablePreprocessing = false;
            j.lowTwistLimit = new SoftJointLimit { limit = -35f }; j.highTwistLimit = new SoftJointLimit { limit = 35f };
            j.swing1Limit = new SoftJointLimit { limit = 100f }; j.swing2Limit = new SoftJointLimit { limit = 45f };
        }
        bodies.Add(rb);
        return rb;
    }

    // forward: topple toward facing; buckle: knees give, straight down; side: off a chair to the
    // character's right; slump: forward and down off a seat
    public void Release(string kind, Vector3 forward)
    {
        // a person starts touching what they sit or stand on; a collider they already overlap
        // would throw them out of it, so those pairs stop colliding (the floor never overlaps)
        Physics.SyncTransforms();
        var own = new HashSet<Collider>(bodies.SelectMany(b => b.GetComponents<Collider>()));
        foreach (var other in UnityEngine.Object.FindObjectsOfType<Collider>())
        {
            if (own.Contains(other) || other.name == "floor") continue;
            foreach (var c in own) if (c.bounds.Intersects(other.bounds)) Physics.IgnoreCollision(c, other);
        }
        foreach (var b in bodies) { b.isKinematic = false; b.velocity = Vector3.zero; }
        Vector3 right = Vector3.Cross(Vector3.up, forward).normalized;
        switch (kind)
        {
            case "forward": chest.AddForce(forward * 10f, ForceMode.Impulse); hips.AddForce(Vector3.down * 22f, ForceMode.Impulse); foreach (var l in limbs) l.AddTorque(right * 1.5f, ForceMode.Impulse); break;
            case "buckle": hips.AddForce(Vector3.down * 40f + forward * 8f, ForceMode.Impulse); foreach (var l in limbs) l.AddTorque(right * 2f, ForceMode.Impulse); break;
            case "side": chest.AddForce(right * 45f, ForceMode.Impulse); hips.AddForce(right * 20f, ForceMode.Impulse); break;
            case "slump": chest.AddForce(forward * 30f + Vector3.down * 10f, ForceMode.Impulse); hips.AddForce(forward * 45f, ForceMode.Impulse); break;
            default: throw new Exception("unknown fall " + kind);
        }
    }

    // take the ragdoll off again (joints first, they depend on the bodies)
    public void Remove()
    {
        foreach (var b in bodies)
        {
            if (b == null) continue;
            foreach (var j in b.GetComponents<CharacterJoint>()) UnityEngine.Object.DestroyImmediate(j);
        }
        foreach (var b in bodies)
        {
            if (b == null) continue;
            foreach (var c in b.GetComponents<Collider>()) UnityEngine.Object.DestroyImmediate(c);
            UnityEngine.Object.DestroyImmediate(b);
        }
        bodies.Clear(); limbs.Clear();
    }

    // rhythmic torques on the limbs, deterministic in the step index
    public void Convulse(int step)
    {
        float s = Mathf.Sign(Mathf.Sin(step * 0.35f));
        for (int i = 0; i < limbs.Count; i++) limbs[i].AddTorque(new Vector3(s * 3f, (i % 2 == 0 ? 1 : -1) * s * 2f, 0), ForceMode.Impulse);
    }
}
