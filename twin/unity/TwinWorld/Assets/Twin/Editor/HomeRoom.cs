using System.Collections.Generic;
using UnityEngine;

// Margaret's home for the real-time twin: one open-plan space, 9 m by 6 m, with a living area to
// the west (sofa, television, armchair, yoga mat, the dog's spot) and a sleeping area to the east
// (bed, nightstand, planter), plus the robot's charging dock. The batch renderer's rooms are not
// touched, so the committed suite renders still reproduce.
public static class HomeRoom
{
    public const float W = 9f, D = 6f;

    public class Layout
    {
        public Dictionary<string, Vector3> spots = new Dictionary<string, Vector3>();
        public Dictionary<string, Vector3> faces = new Dictionary<string, Vector3>();
        public Vector3 dock, dogSpot, roomCam, roomCamLook;
        public GameObject tv;
        public List<(string task, Vector3 at, Vector3 look)> chores = new List<(string, Vector3, Vector3)>();
    }

    public static Layout Build()
    {
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.78f, 0.78f, 0.82f);
        RenderSettings.ambientEquatorColor = new Color(0.62f, 0.60f, 0.56f);
        RenderSettings.ambientGroundColor = new Color(0.36f, 0.33f, 0.30f);
        Rooms.Shell(W, D, "laminate_floor_02", "beige_wall_001");
        var L = new Layout();

        // ---- living area (west)
        Rooms.Put("Sofa_01", -2.2f, 2.55f, 0f);
        Rooms.Put("CoffeeTable_01", -2.2f, 1.45f, 0f, scale: 0.6f);
        Rooms.Put("side_table_01", -4.15f, 0.6f, 90f);
        L.tv = Rooms.Put("Television_01", -4.15f, 0.6f, 90f, y: 0.62f);
        Rooms.Screen(L.tv);
        Rooms.Put("ArmChair_01", -0.5f, 1.3f, 240f);
        Rooms.Put("Shelf_01", -4.15f, -2.2f, 90f);
        Rooms.Put("potted_plant_01", -4.1f, 2.6f, 0f);
        Rooms.Box("rug", new Vector3(-2.2f, 0.005f, 0.6f), new Vector3(3.0f, 0.01f, 2.0f), TwinBatch.Flat(new Color(0.42f, 0.30f, 0.26f), 0.05f));
        Rooms.Box("yoga_mat", new Vector3(-2.6f, 0.012f, -1.4f), new Vector3(0.65f, 0.012f, 1.85f), TwinBatch.Flat(new Color(0.27f, 0.48f, 0.55f), 0.1f));
        Rooms.Box("dog_bed", new Vector3(-0.9f, 0.04f, -1.6f), new Vector3(0.8f, 0.08f, 0.6f), TwinBatch.Flat(new Color(0.55f, 0.36f, 0.22f), 0.05f));

        // ---- sleeping area (east)
        Rooms.Put("old_bed_frame", 2.9f, 1.9f, 180f);
        Rooms.Box("mattress", new Vector3(2.9f, 0.52f, 1.9f), new Vector3(1.45f, 0.22f, 1.95f), TwinBatch.Flat(new Color(0.86f, 0.84f, 0.8f), 0.05f), collide: true);
        Rooms.Box("blanket", new Vector3(2.9f, 0.64f, 1.6f), new Vector3(1.5f, 0.04f, 1.2f), TwinBatch.Flat(new Color(0.36f, 0.42f, 0.55f), 0.05f));
        Rooms.Put("side_table_01", 1.8f, 2.6f, 180f);
        Rooms.Put("wooden_bookshelf_worn", 4.2f, -0.6f, 270f);
        Rooms.Put("potted_plant_02", 4.1f, -2.5f, 0f);
        Rooms.Put("planter_box_01", 1.2f, -2.65f, 0f);
        Rooms.Box("dock", new Vector3(0.2f, 0.03f, -2.6f), new Vector3(0.7f, 0.06f, 0.6f), TwinBatch.Flat(new Color(0.2f, 0.25f, 0.3f), 0.4f));

        // ---- where Margaret does things (the surface under each spot is found by a downward ray)
        void S(string id, Vector3 at, Vector3 face) { L.spots[id] = at; L.faces[id] = face; }
        S("read", new Vector3(-0.55f, 0.45f, 1.25f), new Vector3(-1f, 0f, -0.6f));
        S("sofa", new Vector3(-2.2f, 0.45f, 2.3f), new Vector3(0f, 0f, -1f));
        S("lie_tv", new Vector3(-3.0f, 0f, 0.5f), new Vector3(-1f, 0f, 0f));
        S("yoga", new Vector3(-2.6f, 0.02f, -1.4f), new Vector3(0f, 0f, 1f));
        S("dog", new Vector3(-0.9f, 0f, -0.75f), new Vector3(0f, 0f, -1f));
        S("nap", new Vector3(2.9f, 0.65f, 1.85f), new Vector3(0f, 0f, -1f));
        S("water", new Vector3(1.2f, 0f, -1.95f), new Vector3(0f, 0f, -1f));
        S("window", new Vector3(3.2f, 0f, -1.6f), new Vector3(0.3f, 0f, -1f));
        S("middle", new Vector3(0.4f, 0f, 0.2f), new Vector3(-1f, 0f, 0f));
        L.dogSpot = new Vector3(-0.9f, 0.08f, -1.6f);
        L.dock = new Vector3(0.2f, 0f, -2.3f);

        // ---- the robot's chores: where it goes and what it looks at while working
        L.chores.Add(("tidying the shelf", new Vector3(-3.5f, 0f, -2.0f), new Vector3(-4.2f, 1.0f, -2.2f)));
        L.chores.Add(("wiping the coffee table", new Vector3(-2.2f, 0f, 0.6f), new Vector3(-2.2f, 0.4f, 1.45f)));
        L.chores.Add(("folding laundry on the bed", new Vector3(2.9f, 0f, 0.55f), new Vector3(2.9f, 0.6f, 1.6f)));
        L.chores.Add(("checking the bookshelf", new Vector3(3.5f, 0f, -0.6f), new Vector3(4.2f, 1.0f, -0.6f)));
        L.chores.Add(("charging at the dock", new Vector3(0.2f, 0f, -2.3f), new Vector3(0.2f, 0.8f, 0f)));

        // the attested room camera that witnesses falls: high in the south-west corner, whole room in view
        L.roomCam = new Vector3(0f, 2.4f, -2.85f);
        L.roomCamLook = new Vector3(0f, 0.4f, 0.6f);
        return L;
    }
}
