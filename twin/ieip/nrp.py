#!/usr/bin/env python3
"""The I-EIP replay on NRP Nautilus A10s (docs/PREREG_IEIP_TWIN.md, section 8 step 3, A5).
Run on Atlas, which holds the NATS hub, kubectl and the inputs.

    python nrp.py setup                          # CPU: the pinned env as one tar on the volume
    python nrp.py code   --commit SHA            # CPU: this repository's twin/ at SHA, one tar
    python nrp.py stage  --commit SHA            # CPU: Qwen2.5-7B-Instruct, verified against Atlas
    python nrp.py prepare --commit SHA           # CPU: the prompts, from the inputs committed at SHA
    python nrp.py pilot  --commit SHA            # GPU: the first shard, sized by a stated model
    python nrp.py shards --commit SHA            # GPU: the rest, sized by the pilot's measurement
    python nrp.py fetch  --commit SHA            # CPU: the outputs back to Atlas, in chunks
    python nrp.py status

Scored against the NRP preflight (agi-hpc memory reference_nrp_job_policies), in ``preflight``
and ``submit``, not by recall:
- CPU jobs are in the exempt class (1 CPU, 2 GiB). GPU jobs install and download nothing:
  the env, the code, the weights and the finished prompts are staged by CPU jobs first, so a
  GPU pod's opening is untarring a small env and loading weights from a volume in its own
  region (arc-latte is rook-cephfs-east; every pod is pinned to mghpcc, where the A10s are).
- A GPU job's CPU and memory come from the pilot's MEASURED time-averaged usage
  (turboquant-pro's utilization guard writes it; turboquant-pro's sizing.request_for turns it
  into a request or a refusal). The pilot alone is sized by a stated model, and goes out only
  while that guard's heartbeat is fresh.
- Requests equal limits; ephemeral storage is declared; every command ends by itself, bounded
  by `timeout`; nothing sleeps; at most four GPU pods in the namespace at once.
- Jobs are never deleted while active (memory feedback_nrp_no_active_job_deletes); a finished
  Job of the same name is removed before resubmission and the new creationTimestamp is checked.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, "/home/claude/src/nats-bursting/python")
TQP_NRP = "/home/claude/tqp-ci/benchmarks"  # turboquant-pro benchmarks/nrp (sizing, guard)

NS = "ssu-atlas-ai"
PVC = "arc-latte"
ZONE = {"topology.kubernetes.io/zone": "mghpcc"}
GPU_PRODUCT = "NVIDIA-A10"
APP = "gtc-ieip"
BATCH = "gtc-ieip-twin"
IMAGE = "pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime"
REPO = "https://github.com/ahb-sjsu/moral-spectrum-analyzer"
ROOT = "/data/ieip-twin"
STATE = "/archive/unity/ieip"  # on Atlas: the guard's observations, fetched outputs
OBSERVATIONS = os.path.join(STATE, "observations.json")
HEARTBEAT = os.path.join(STATE, "guard.heartbeat")

# erisml-compiler at the commit with HuggingFaceActivationSource(model=...) (erisml-compiler #26);
# its ObservationClassifier is the one deployed on the robot (unchanged since daf84e6)
COMPILER_SHA = "888c07594559d22d90ff357aecdcea5b0853693e"
PINS = (
    "transformers==4.56.1 accelerate==1.14.0 safetensors numpy huggingface_hub "
    f"https://github.com/ahb-sjsu/erisml-compiler/archive/{COMPILER_SHA}.tar.gz"
)
ENV_TAR = f"{ROOT}/env/{hashlib.sha256(PINS.encode()).hexdigest()[:16]}.tar"

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REV = "a09a35458c702b33eeacc393d103063234e8bc28"  # Atlas ~/.cache/huggingface refs/main
MODEL_DIR = f"{ROOT}/models/qwen2.5-7b-instruct-{MODEL_REV[:7]}"
# every file as Atlas's cache names its blob: sha256 for the LFS weights, git sha1 otherwise
EXPECT = {
    "config.json": "0178295f88afc3c7f279ed284f961f8c1be00654",
    "generation_config.json": "0eb3c536657dcd12626e09eca4b6198c0cbcde1e",
    "merges.txt": "20024bfe7c83998e9aeaf98a0cd6a2ce6306c2f0",
    "model-00001-of-00004.safetensors": "a1333e6293854747c481288ea83b348226af178dd565c49b6f9495ba1966aba7",
    "model-00002-of-00004.safetensors": "f5d25a2772cb825164a2a2c0fb6d51a87e282abf21e4dd75bc5cfb3cd0ea6185",
    "model-00003-of-00004.safetensors": "8efdec4c1bc12317ae1a38dc42b595ce777738a64deea3fcb8a0a91381bcdfd5",
    "model-00004-of-00004.safetensors": "1a72d403cdf0c1ec3cb7f289f17b394a01e64394c2e9b3c0f94dbce3faf879bd",
    "model.safetensors.index.json": "14d037fdda5a1311dcc0275003a7a370d84114e6",
    "tokenizer.json": "443909a61d429dff23010e5bddd28ff530edda00",
    "tokenizer_config.json": "07bfe0640cb5a0037f9322287fbfc682806cf672",
    "vocab.json": "4783fe10ac3adce15ac8f358ef5462739852c569",
}

# the registered inputs (PREREG section 2: dev7 and the later development runs made before the
# replay starts; dev8 and dev9 are void and hold no decision cycles, A5), frozen in the repository
INPUTS = [f"twin/ieip/inputs/{r}.results.jsonl" for r in ("dev7", "dev8r", "dev9r")]

# the pilot's stated model (it alone is sized before any measurement): one Python thread drives
# the GPU (about one core); host memory is the CUDA context and libraries (about 1.5 GiB), the
# direct-to-GPU load's transient buffers, and the monitor's float32 copy of four layers' hidden
# states at up to 8192 tokens (0.47 GB). It runs while the utilization guard records its usage.
PILOT_REQUEST = (2, 5, "stated model: 1 driving thread; CUDA context + load buffers + hooks")
PILOT_SHARE = 8  # the pilot takes about an eighth of the prompts, at least PILOT_MIN
PILOT_MIN = 120
ATLAS_VENV = "/archive/unity/ieip-venv"  # the same pins on Atlas, for its own prepare and collect
ATLAS_MODEL = f"/home/claude/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/{MODEL_REV}"
MAX_GPU_PODS = 4
GPU_TIMEOUT_S = 6 * 3600
FETCH_CHUNK = 6 << 20  # raw bytes per fetch job: 8 MiB of base64, under a 10 MiB log rotation
nl = chr(10)


def _head(commit: str) -> str:
    return f"""set -euo pipefail
export PIP_ROOT_USER_ACTION=ignore PYTHONUNBUFFERED=1 HF_HUB_DISABLE_XET=1
tar -xf {ENV_TAR} -C /tmp
mkdir -p /tmp/code && tar -xf {ROOT}/code/{commit}.tar -C /tmp/code
export PATH=/tmp/venv/bin:$PATH
"""


SETUP = f"""set -euo pipefail
export PIP_ROOT_USER_ACTION=ignore PYTHONUNBUFFERED=1
if [ -f {ENV_TAR} ]; then echo "env exists: {ENV_TAR}"; exit 0; fi
python -m venv --system-site-packages /tmp/venv
timeout 1800 /tmp/venv/bin/pip install -q --no-cache-dir {PINS}
/tmp/venv/bin/python -c "import torch, transformers, erisml_compiler.monitor.huggingface_source as h, inspect; \\
assert 'model' in inspect.signature(h.HuggingFaceActivationSource).parameters; \\
print('torch', torch.__version__, 'transformers', transformers.__version__)"
/tmp/venv/bin/pip freeze > /tmp/venv/freeze.txt
mkdir -p {ROOT}/env && tar -cf {ENV_TAR}.tmp -C /tmp venv && mv {ENV_TAR}.tmp {ENV_TAR}
df -h /data | tail -1
echo SETUP_DONE {ENV_TAR}
"""


def code_script(commit: str) -> str:
    tar = f"{ROOT}/code/{commit}.tar"
    return f"""set -euo pipefail
if [ -f {tar} ]; then echo "already staged: {tar}"; exit 0; fi
timeout 600 git clone -q --filter=blob:none --no-checkout {REPO} /tmp/src
git -C /tmp/src sparse-checkout set --no-cone twin/ieip twin/scene
git -C /tmp/src checkout -q {commit}
test "$(git -C /tmp/src rev-parse HEAD)" = "{commit}"
mkdir -p {ROOT}/code
tar -cf {tar}.tmp -C /tmp/src twin && mv {tar}.tmp {tar}
echo "CODE_STAGED {tar}"
"""


def stage_script(commit: str) -> str:
    return _head(commit) + f"""cat > /tmp/expect.json <<'EOF'
{json.dumps(EXPECT)}
EOF
timeout 7200 python /tmp/code/twin/ieip/stage_model.py --model-id {MODEL_ID} --revision {MODEL_REV} \\
    --dest {MODEL_DIR} --expect /tmp/expect.json
df -h /data | tail -1
"""


def prepare_script(commit: str) -> str:
    inputs = " ".join(f"/tmp/code/{p}" for p in INPUTS)
    return _head(commit) + f"""export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
test -f {MODEL_DIR}/STAGED.json
timeout 3600 python /tmp/code/twin/ieip/analysis.py prepare {inputs} --tokenizer {MODEL_DIR} \\
    --out {ROOT}/prep/{commit}
"""


READPROBE = f"""set -euo pipefail
# how fast a pod in this region reads the staged weights: one stream, then the four shards at once
cd {MODEL_DIR}
timeout 1200 python3 - <<'EOF'
import glob, os, threading, time
def read(f):
    with open(f, "rb", buffering=0) as fh:
        while fh.read(16 << 20):
            pass
fs = sorted(glob.glob("model-0000?-of-00004.safetensors"))
t = time.perf_counter(); read(fs[0]); dt = time.perf_counter() - t
print(f"READ_ONE {{os.path.getsize(fs[0]) / 1e6 / dt:.1f}} MB/s", flush=True)
rest = fs[1:]
t = time.perf_counter()
th = [threading.Thread(target=read, args=(f,)) for f in rest]
[x.start() for x in th]; [x.join() for x in th]
dt = time.perf_counter() - t
print(f"READ_PARALLEL {{len(rest)}} streams {{sum(map(os.path.getsize, rest)) / 1e6 / dt:.1f}} MB/s", flush=True)
EOF
"""


# the weights come off the volume again (owner's decision 2026-10-03, after READPROBE measured
# 14.9 MB/s one stream and 38.3 MB/s three: the capture runs on Atlas GPU 1 instead, A6)
CLEANUP = f"""set -euo pipefail
ls -la {MODEL_DIR}
timeout 600 rm -rf {MODEL_DIR}
df -h /data | tail -1
echo CLEANED {MODEL_DIR}
"""


def gpu_script(commit: str, start: int, end: int) -> str:
    return _head(commit) + f"""export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
timeout {GPU_TIMEOUT_S} python /tmp/code/twin/ieip/gpu_capture.py --prompts {ROOT}/prep/{commit}/prompts.jsonl \\
    --start {start} --end {end} --model {MODEL_DIR} --out {ROOT}/run/{commit}
echo CAPTURE_DONE {start} {end}
"""


def fetch_script(commit: str, part: int) -> str:
    """Chunk `part` of the outputs' tar.gz, base64 on stdout. The tar is built once, by part 0,
    under a name holding its sha256, so every part reads the same bytes."""
    return f"""set -euo pipefail
cd {ROOT}
if [ {part} -eq 0 ] || ! ls fetch/{commit}.*.tgz >/dev/null 2>&1; then
  mkdir -p fetch
  tar -czf fetch/{commit}.tmp -C {ROOT} run/{commit} prep/{commit}/manifest.json
  s=$(sha256sum fetch/{commit}.tmp | cut -c1-64)
  rm -f fetch/{commit}.*.tgz && mv fetch/{commit}.tmp fetch/{commit}.$s.tgz
fi
f=$(ls fetch/{commit}.*.tgz)
echo "FETCH_FILE $(basename $f) $(stat -c %s $f)"
echo FETCH_BEGIN
timeout 600 dd if=$f bs={FETCH_CHUNK} skip={part} count=1 status=none | base64 -w0
echo
echo FETCH_END
"""


# ----------------------------------------------------------------------------- sizing


def _tqp_sizing():
    """turboquant-pro's benchmarks/nrp/sizing.py, loaded by path (its package is also `nrp`)."""
    import importlib.util

    path = os.path.join(TQP_NRP, "nrp", "sizing.py")
    spec = importlib.util.spec_from_file_location("tqp_nrp_sizing", path)
    sizing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sizing)
    print("sizing:", path, hashlib.sha256(open(path, "rb").read()).hexdigest()[:12])
    return sizing


def measured_pilot(commit: str, pilot: tuple[int, int]):
    """The pilot's measured time averages, from the utilization guard's observations."""
    try:
        obs = json.load(open(OBSERVATIONS, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    o = obs.get(job_name("pilot", commit, *pilot))
    if not o or not o.get("mean_cpu_cores") or not o.get("mean_mem_gib"):
        return None
    return o


def shard_request(commit: str, pilot: tuple[int, int]):
    """(cpu, mem GiB, why) from the pilot's measurement, or a refusal."""
    o = measured_pilot(commit, pilot)
    if o is None:
        raise SystemExit("PREFLIGHT VETO: the pilot has no measured usage yet (run the guard; let it finish)")
    sizing = _tqp_sizing()
    u = sizing.Usage(o["mean_cpu_cores"], o["mean_mem_gib"], o.get("peak_mem_gib") or o["mean_mem_gib"])
    r = sizing.request_for(u, want_cpu=2)
    if isinstance(r, sizing.Refusal):
        raise SystemExit(f"PREFLIGHT VETO: {r}")
    return r.cpu, r.memory_gib, str(r)


def guard_fresh(max_age_s: float = 180) -> bool:
    try:
        return time.time() - os.path.getmtime(HEARTBEAT) < max_age_s
    except OSError:
        return False


# ----------------------------------------------------------------------------- jobs


def job_name(kind: str, commit: str, start: int | None = None, end: int | None = None) -> str:
    n = f"ieip-{kind}-{commit[:10]}"
    return n + (f"-{start}-{end}" if start is not None else "")


def descriptor(name, script, cpu, mem_gib, eph, role, gpu=0, image=IMAGE):
    from nats_bursting import JobDescriptor, Resources, Volume

    return JobDescriptor(
        name=name,
        image=image,
        command=["/bin/bash", "-lc", script],
        resources=Resources(cpu=str(cpu), memory=f"{mem_gib}Gi", gpu=gpu, ephemeral_storage=eph),
        labels={"app": APP, "atlas.io/batch": BATCH, "atlas.io/role": role},
        node_selector={**ZONE, **({"nvidia.com/gpu.product": GPU_PRODUCT} if gpu else {})},
        backoff_limit=0,
        volumes=[Volume(name="data", mount_path="/data", claim_name=PVC)],
    )


def preflight(desc, gpu: bool) -> list[str]:
    bad = []
    r = desc.resources
    script = " ".join(desc.command)
    if not r.ephemeral_storage:
        bad.append("ephemeral-storage not declared")
    if desc.backoff_limit != 0:
        bad.append("backoff_limit is not 0")
    if re.search(r"\bsleep\b", script):
        bad.append("the command contains sleep")
    if "timeout " not in script:
        bad.append("the command's long step is not bounded by timeout")
    if desc.node_selector.get("topology.kubernetes.io/zone") != ZONE["topology.kubernetes.io/zone"]:
        bad.append("not pinned to the volume's region")
    if gpu and any(w in script for w in ("pip install", "git clone", "snapshot_download", "hf_hub_download", "apt-get")):
        bad.append("a GPU job installs or downloads")
    if not gpu and (float(r.cpu) > 1 or float(str(r.memory).rstrip("Gi")) > 2):
        bad.append("a CPU job outside the exempt class")
    if "SET-AFTER-MERGE" in PINS:
        bad.append("the erisml-compiler commit is not pinned")
    return bad


def kubectl(*args):
    return subprocess.run(["kubectl", "-n", NS, "--request-timeout=60s", *args], capture_output=True, text=True, timeout=120)


def job_state(name: str) -> str:
    """'absent', 'active' or 'finished'."""
    r = kubectl("get", "job", name, "-o", "json")
    if r.returncode != 0:
        return "absent"
    st = json.loads(r.stdout).get("status", {})
    if st.get("succeeded") or st.get("failed") or any(
        c.get("type") in ("Complete", "Failed") and c.get("status") == "True" for c in st.get("conditions", [])
    ):
        return "finished"
    return "active"


def gpu_pods_in_namespace() -> int:
    r = kubectl("get", "pods", "-o", "json")
    n = 0
    for p in json.loads(r.stdout).get("items", []) if r.returncode == 0 else []:
        if p["status"].get("phase") not in ("Pending", "Running"):
            continue
        for c in p["spec"].get("containers", []):
            n += int((c.get("resources", {}).get("requests", {}) or {}).get("nvidia.com/gpu", 0) or 0)
    return n


def submit(desc) -> None:
    from nats_bursting import Client

    state = job_state(desc.name)
    if state == "active":
        raise SystemExit(f"{desc.name} is active; never deleted while running")
    if state == "finished":
        kubectl("delete", "job", desc.name)
    t0 = time.time()
    with Client() as c:
        c.submit(desc)
    for _ in range(60):
        r = kubectl("get", "job", desc.name, "-o", "jsonpath={.metadata.creationTimestamp}")
        if r.returncode == 0 and r.stdout.strip():
            ts = time.mktime(time.strptime(r.stdout.strip(), "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
            if ts < t0 - 120:
                raise SystemExit(f"{desc.name}: stale creationTimestamp {r.stdout.strip()}")
            print(desc.name, "created", r.stdout.strip(), flush=True)
            return
        time.sleep(5)
    raise SystemExit(f"{desc.name}: no job appeared")


def prompts_count(commit: str) -> int:
    """From the prepare job's log: PREPARED {manifest}. Also checked against Atlas's own
    prepare of the same inputs (A5: the prompts must be byte-identical)."""
    r = kubectl("logs", f"job/{job_name('prepare', commit)}")
    m = re.search(r"^PREPARED (\{.*\})$", r.stdout, re.M)
    if not m:
        raise SystemExit("no PREPARED line in the prepare job's log")
    nrp = json.loads(m.group(1))
    local = os.path.join(STATE, "prep", commit, "manifest.json")
    if not os.path.exists(local):
        raise SystemExit(f"PREFLIGHT VETO: run Atlas's own prepare first ({local} missing)")
    mine = json.load(open(local, encoding="utf-8"))
    if (nrp["prompts"], nrp["prompts_sha256"]) != (mine["prompts"], mine["prompts_sha256"]):
        raise SystemExit(f"PREFLIGHT VETO: NRP prompts {nrp['prompts_sha256'][:12]} != Atlas {mine['prompts_sha256'][:12]}")
    return int(nrp["prompts"])


def ranges(n: int) -> tuple[tuple[int, int], list[tuple[int, int]]]:
    """(pilot range, the rest split in at most MAX_GPU_PODS equal ranges)."""
    p = min(n, max(PILOT_MIN, math.ceil(n / PILOT_SHARE)))
    rest = n - p
    k = min(MAX_GPU_PODS, max(1, math.ceil(rest / p))) if rest else 0
    edges = [p + round(i * rest / k) for i in range(k + 1)] if k else []
    return (0, p), list(zip(edges, edges[1:]))


def fetch(commit: str) -> None:
    """Every chunk in turn, each from its own exempt CPU job, reassembled and checked."""
    out = os.path.join(STATE, "fetch", commit)
    os.makedirs(out, exist_ok=True)
    blob, part, total, fname = bytearray(), 0, None, None
    while total is None or len(blob) < total:
        name = f"{job_name('fetch', commit)}-{part}"
        d = descriptor(name, fetch_script(commit, part), 1, 2, "4Gi", "fetch")
        bad = preflight(d, False)
        if bad:
            raise SystemExit(f"PREFLIGHT VETO {name}: {bad}")
        submit(d)
        while job_state(name) != "finished":
            time.sleep(10)
        log = kubectl("logs", f"job/{name}").stdout
        m = re.search(r"^FETCH_FILE (\S+) (\d+)$", log, re.M)
        body = re.search(r"FETCH_BEGIN\n(.*)\nFETCH_END", log, re.S)
        if not m or not body:
            raise SystemExit(f"{name}: no chunk in the log")
        if fname not in (None, m.group(1)):
            raise SystemExit(f"{name}: the tar changed between parts ({fname} -> {m.group(1)})")
        fname, total = m.group(1), int(m.group(2))
        chunk = base64.b64decode(body.group(1))
        if len(chunk) != min(FETCH_CHUNK, total - part * FETCH_CHUNK):
            raise SystemExit(f"{name}: chunk of {len(chunk)} bytes, log truncated?")
        blob += chunk
        kubectl("delete", "job", name)  # finished; logs read
        part += 1
        time.sleep(20)  # spaced, not churned
    want = fname.split(".")[1]
    got = hashlib.sha256(blob).hexdigest()
    if got != want:
        raise SystemExit(f"reassembled sha256 {got} != {want}")
    path = os.path.join(out, fname)
    open(path, "wb").write(blob)
    subprocess.run(["tar", "-xzf", path, "-C", out], check=True)
    print("FETCHED", path, len(blob), "bytes, sha256 verified")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("setup", "code", "stage", "prepare", "pilot", "shards", "fetch", "status",
                                    "atlas-setup", "atlas-prepare", "readprobe", "cleanup"))
    ap.add_argument("--commit", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        print(kubectl("get", "jobs", "-l", f"app={APP}").stdout)
        return 0
    if a.cmd == "atlas-setup":
        if not os.path.exists(ATLAS_VENV):
            subprocess.run([sys.executable, "-m", "venv", ATLAS_VENV], check=True)
        # tokenizing needs no torch, so not accelerate (which would pull a CUDA torch); any
        # difference this makes to the prompts is caught by comparing them with NRP's
        pins = [p for p in PINS.split() if not p.startswith("accelerate")]
        subprocess.run([f"{ATLAS_VENV}/bin/pip", "install", "-q", *pins], check=True)
        return 0
    if a.cmd not in ("setup", "readprobe", "cleanup") and not re.fullmatch(r"[0-9a-f]{40}", a.commit):
        raise SystemExit("--commit must be a full sha")
    if a.cmd == "fetch":
        fetch(a.commit)
        return 0
    if a.cmd == "atlas-prepare":
        # the same prepare, on Atlas, from the code at the same commit and Atlas's own model
        # cache: its prompts.jsonl must match NRP's byte for byte (prompts_count checks)
        src = os.path.join(STATE, "code", a.commit)
        if not os.path.exists(src):
            subprocess.run(["git", "clone", "-q", REPO, src], check=True)
            subprocess.run(["git", "-C", src, "checkout", "-q", a.commit], check=True)
        env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        subprocess.run([f"{ATLAS_VENV}/bin/python", f"{src}/twin/ieip/analysis.py", "prepare",
                        *[f"{src}/{p}" for p in INPUTS], "--tokenizer", ATLAS_MODEL,
                        "--out", os.path.join(STATE, "prep", a.commit)], check=True, env=env)
        return 0
    items = []
    if a.cmd == "cleanup":
        items.append((descriptor(f"ieip-cleanup-{int(time.time())}", CLEANUP, 1, 2, "1Gi", "cleanup"), False))
    elif a.cmd == "readprobe":
        items.append((descriptor(f"ieip-readprobe-{int(time.time())}", READPROBE, 1, 2, "1Gi", "probe"), False))
    elif a.cmd == "setup":
        items.append((descriptor(f"ieip-setup-{os.path.basename(ENV_TAR)[:10]}", SETUP, 1, 2, "12Gi", "setup"), False))
    elif a.cmd == "code":
        items.append((descriptor(job_name("code", a.commit), code_script(a.commit), 1, 2, "2Gi", "code",
                                 image="python:3.12"), False))  # has git; the PyTorch image does not
    elif a.cmd == "stage":
        items.append((descriptor(job_name("stage", a.commit), stage_script(a.commit), 1, 2, "24Gi", "stage"), False))
    elif a.cmd == "prepare":
        items.append((descriptor(job_name("prepare", a.commit), prepare_script(a.commit), 1, 2, "4Gi", "prepare"), False))
    elif a.cmd in ("pilot", "shards"):
        n = prompts_count(a.commit)
        pilot, rest = ranges(n)
        if a.cmd == "pilot":
            if not guard_fresh():
                raise SystemExit(f"PREFLIGHT VETO: the utilization guard's heartbeat ({HEARTBEAT}) is not fresh")
            cpu, mem, why = PILOT_REQUEST
            todo = [pilot]
        else:
            if job_state(job_name("pilot", a.commit, *pilot)) != "finished":
                raise SystemExit("the pilot has not finished")
            cpu, mem, why = shard_request(a.commit, pilot)
            todo = rest
        if gpu_pods_in_namespace() + len(todo) > MAX_GPU_PODS:
            raise SystemExit(f"PREFLIGHT VETO: more than {MAX_GPU_PODS} GPU pods in the namespace")
        for s, e in todo:
            d = descriptor(job_name(a.cmd, a.commit, s, e) if a.cmd == "shards" else job_name("pilot", a.commit, s, e),
                           gpu_script(a.commit, s, e), cpu, mem, "24Gi", a.cmd, gpu=1)
            print(d.name, f"[{s}, {e})", cpu, f"{mem}Gi", GPU_PRODUCT, "|", why)
            items.append((d, True))
    bad = {d.name: preflight(d, g) for d, g in items}
    if any(bad.values()):
        raise SystemExit("PREFLIGHT VETO " + json.dumps({k: v for k, v in bad.items() if v}))
    print(f"{a.cmd}: {len(items)} job(s) pass preflight")
    if a.dry_run:
        return 0
    for i, (d, _) in enumerate(items):
        if i:
            time.sleep(20)
        submit(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
