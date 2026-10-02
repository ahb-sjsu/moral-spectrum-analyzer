#!/usr/bin/env python3
"""Fetch the third-party assets of the 3D twin into a Unity project's Assets folder.

The assets are not in this repository. They are downloaded here, checked against the md5
the publisher lists, and recorded with their sha256 in ASSETS-MANIFEST.json beside them.

  python fetch_assets.py /archive/unity/projects/TwinWorld/Assets/ThirdParty \
      --rocketbox /archive/unity/assets/rocketbox

Sources:
  Poly Haven (CC0)          furniture, props and surface textures, 1k resolution
  Microsoft Rocketbox (MIT) rigged avatars, copied from a local clone of
                            github.com/microsoft/Microsoft-Rocketbox
  Unitree G1 (BSD-3-Clause) humanoid robot description (URDF and meshes), copied from a local
                            clone of github.com/unitreerobotics/unitree_ros
"""

import argparse
import hashlib
import json
import os
import shutil
import urllib.request

API = "https://api.polyhaven.com"
RES = "1k"
UA = {"User-Agent": "gtc-twin-asset-fetch/1.0 (github.com/ahb-sjsu/moral-spectrum-analyzer)"}

MODELS = [
    "Sofa_01", "ArmChair_01", "modern_arm_chair_01", "CoffeeTable_01", "Television_01",
    "old_bed_frame", "dining_table", "dining_chair_02", "WoodenChair_01", "WoodenTable_01", "vintage_cabinet_01",
    "side_table_01", "Shelf_01", "wooden_bookshelf_worn", "potted_plant_01", "potted_plant_02",
    "planter_box_01", "modern_ceiling_lamp_01", "Ottoman_01", "book_encyclopedia_set_01",
    "ceramic_vase_01",
]
# surface textures: Diffuse, normal (OpenGL convention, as Unity expects) and roughness
TEXTURES = {
    "laminate_floor_02": "living and bedroom floor",
    "herringbone_parquet": "hallway floor",
    "floor_tiles_06": "bathroom and kitchen floor",
    "long_white_tiles": "bathroom wall",
    "beige_wall_001": "interior walls",
    "kitchen_wood": "kitchen counter",
    "marble_01": "counter top and sink",
}
TEX_MAPS = {"Diffuse": "jpg", "nor_gl": "jpg", "Rough": "jpg"}

ANIMALS = ["Dog_Beagle_01", "Dog_GermanShepard_01"]  # Margaret's dog, and the stand-in for a coyote, from the same Rocketbox library

AVATARS = [
    "Adults/Male_Adult_05", "Adults/Male_Adult_12", "Adults/Female_Adult_03",
    "Adults/Female_Adult_09", "Children/Female_Child_01", "Professions/Medical_Female_01",
]


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def download(url, dest, md5=None):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        tmp = dest + ".part"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(tmp, dest)
    data = open(dest, "rb").read()
    if md5 and hashlib.md5(data).hexdigest() != md5:
        os.remove(dest)
        raise SystemExit(f"md5 mismatch for {url}")
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dest", help="the Unity project's Assets/ThirdParty folder")
    ap.add_argument("--rocketbox", required=True, help="local clone of Microsoft-Rocketbox")
    ap.add_argument("--unitree", help="local clone of unitreerobotics/unitree_ros (for the G1)")
    a = ap.parse_args()
    manifest = {"polyhaven_models": {}, "polyhaven_textures": {}, "rocketbox": {}}

    for name in MODELS:
        rec = get_json(f"{API}/files/{name}")["fbx"][RES]["fbx"]
        base = os.path.join(a.dest, "PolyHaven", "Models", name)
        files = {os.path.basename(rec["url"]): download(rec["url"], os.path.join(base, os.path.basename(rec["url"])), rec["md5"])}
        for rel, inc in rec.get("include", {}).items():
            files[rel] = download(inc["url"], os.path.join(base, rel), inc.get("md5"))
        manifest["polyhaven_models"][name] = files
        print("model", name, len(files), "files", flush=True)

    for name, use in TEXTURES.items():
        rec = get_json(f"{API}/files/{name}")
        base = os.path.join(a.dest, "PolyHaven", "Textures", name)
        files = {}
        for kind, fmt in TEX_MAPS.items():
            f = rec[kind][RES][fmt]
            fn = os.path.basename(f["url"])
            files[fn] = download(f["url"], os.path.join(base, fn), f.get("md5"))
        manifest["polyhaven_textures"][name] = {"use": use, "files": files}
        print("texture", name, flush=True)

    rb_commit = os.popen(f"git -C {a.rocketbox} rev-parse HEAD").read().strip()
    for av in AVATARS:
        src = os.path.join(a.rocketbox, "Assets", "Avatars", av)
        name = os.path.basename(av)
        dst = os.path.join(a.dest, "Rocketbox", name)
        files = {}
        for sub in ("Export", "Textures"):
            for fn in sorted(os.listdir(os.path.join(src, sub))):
                if sub == "Export" and "_facial" in fn:
                    continue  # the facial-rig variant is not used
                s, d = os.path.join(src, sub, fn), os.path.join(dst, sub, fn)
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
                files[f"{sub}/{fn}"] = hashlib.sha256(open(d, "rb").read()).hexdigest()
        manifest["rocketbox"][name] = files
        print("avatar", name, len(files), "files", flush=True)
    for an in ANIMALS:
        src = os.path.join(a.rocketbox, "Assets", "Animals", an)
        dst = os.path.join(a.dest, "RocketboxAnimals", an)
        files = {}
        for sub in ("Export", "Textures"):
            for fn in sorted(os.listdir(os.path.join(src, sub))):
                s_, d_ = os.path.join(src, sub, fn), os.path.join(dst, sub, fn)
                os.makedirs(os.path.dirname(d_), exist_ok=True)
                shutil.copy2(s_, d_)
                files[f"{sub}/{fn}"] = hashlib.sha256(open(d_, "rb").read()).hexdigest()
        manifest.setdefault("rocketbox_animals", {})[an] = files
        print("animal", an, len(files), "files", flush=True)
    manifest["rocketbox_commit"] = rb_commit
    if a.unitree:
        src = os.path.join(a.unitree, "robots", "g1_description")
        dst = os.path.join(a.dest, "Robots", "g1_description")
        files = {}
        for rel in ["g1_29dof_rev_1_0.urdf"] + [os.path.join("meshes", f) for f in sorted(os.listdir(os.path.join(src, "meshes")))]:
            s_, d_ = os.path.join(src, rel), os.path.join(dst, rel)
            if os.path.isdir(s_):
                continue
            os.makedirs(os.path.dirname(d_), exist_ok=True)
            shutil.copy2(s_, d_)
            files[rel] = hashlib.sha256(open(d_, "rb").read()).hexdigest()
        manifest["unitree_g1"] = files
        manifest["unitree_commit"] = os.popen(f"git -C {a.unitree} rev-parse HEAD").read().strip()
        print("robot g1", len(files), "files", flush=True)
    manifest["licenses"] = {"polyhaven": "CC0 1.0", "rocketbox": "MIT (Microsoft, 2020)",
                            "unitree_g1": "BSD-3-Clause (Unitree Robotics)"}
    json.dump(manifest, open(os.path.join(a.dest, "ASSETS-MANIFEST.json"), "w"), indent=1)
    print("ASSETS_DONE", flush=True)


if __name__ == "__main__":
    main()
