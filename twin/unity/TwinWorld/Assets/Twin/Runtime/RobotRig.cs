using System;
using System.Collections.Generic;
using UnityEngine;

// The robot body as a kinematic rig: each revolute joint of the URDF is a link transform turned
// about its joint axis from its rest rotation. No physics drives the body; it moves only where the
// scenario's ruling allows (docs/TWIN_3D_PLAN.md).
public class RobotRig : MonoBehaviour
{
    [Serializable]
    public class Joint
    {
        public string name;
        public Transform link;
        public Vector3 axis;      // joint axis in the link's local frame, already in Unity coordinates
        public Quaternion rest;
        public float lower, upper; // radians, from the URDF limits
    }

    public List<Joint> joints = new List<Joint>();
    Dictionary<string, Joint> map;

    Joint Find(string name)
    {
        if (map == null)
        {
            map = new Dictionary<string, Joint>();
            foreach (var j in joints) map[j.name] = j;
        }
        return map.TryGetValue(name, out var x) ? x : null;
    }

    // set a joint angle in radians, clamped to the URDF limits; unknown names are reported
    public void Set(string name, float rad)
    {
        var j = Find(name);
        if (j == null) { Debug.LogWarning("RobotRig: no joint " + name); return; }
        rad = Mathf.Clamp(rad, j.lower, j.upper);
        // ROS is right-handed and Unity left-handed: the same physical turn is the negated angle
        j.link.localRotation = j.rest * Quaternion.AngleAxis(-rad * Mathf.Rad2Deg, j.axis);
    }

    public void Rest()
    {
        foreach (var j in joints) j.link.localRotation = j.rest;
    }

    // named whole-body poses; angles in radians, joint names as in the G1 URDF
    public void Pose(string pose, float t = 1f)
    {
        Rest();
        switch (pose)
        {
            case "stand":
                Set("left_elbow_joint", 0.3f * t); Set("right_elbow_joint", 0.3f * t);
                break;
            case "reach":   // reach toward a person on the floor in front
                Set("left_hip_pitch_joint", -0.9f * t); Set("right_hip_pitch_joint", -0.9f * t);
                Set("left_knee_joint", 1.4f * t); Set("right_knee_joint", 1.4f * t);
                Set("left_ankle_pitch_joint", -0.5f * t); Set("right_ankle_pitch_joint", -0.5f * t);
                Set("left_shoulder_pitch_joint", -1.0f * t); Set("right_shoulder_pitch_joint", -1.0f * t);
                Set("left_elbow_joint", 0.5f * t); Set("right_elbow_joint", 0.5f * t);
                break;
            case "call":    // stays upright, one hand raised to the head (calling for help)
                Set("right_shoulder_pitch_joint", -1.2f * t); Set("right_elbow_joint", 1.6f * t);
                Set("left_elbow_joint", 0.3f * t);
                break;
            case "hold":    // waits, hands in front, palms down
                Set("left_shoulder_pitch_joint", -0.3f * t); Set("right_shoulder_pitch_joint", -0.3f * t);
                Set("left_elbow_joint", 1.0f * t); Set("right_elbow_joint", 1.0f * t);
                break;
        }
    }

    // a stepping gait for travel: hips and knees swing in opposition
    public void Step(float phase)
    {
        float s = Mathf.Sin(phase);
        Rest();
        Set("left_hip_pitch_joint", -0.35f * s); Set("right_hip_pitch_joint", 0.35f * s);
        Set("left_knee_joint", Mathf.Max(0f, 0.6f * s)); Set("right_knee_joint", Mathf.Max(0f, -0.6f * s));
        Set("left_shoulder_pitch_joint", 0.25f * s); Set("right_shoulder_pitch_joint", -0.25f * s);
        Set("left_elbow_joint", 0.3f); Set("right_elbow_joint", 0.3f);
    }
}
