#!/usr/bin/env python3
"""The I-EIP replay on NRP Nautilus A10s (docs/PREREG_IEIP_TWIN.md, section 8 step 3, A5, A6).
Run on Atlas, which holds the NATS hub, kubectl and the inputs.

    python nrp.py volumes                        # the volume sets (kubectl apply of PVCs only)
    python nrp.py stage  --commit SHA            # CPU: env + verified weights onto every set
    python nrp.py prepare --commit SHA           # CPU: the prompts, from the inputs committed at SHA
    python nrp.py pilot  --commit SHA            # GPU: the first shard, sized by a stated model
    python nrp.py shards --commit SHA            # GPU: the rest, sized by the pilot's measurement
    python nrp.py fetch  --commit SHA            # CPU: every set's outputs back to Atlas, in chunks
    python nrp.py release                        # delete the volume sets once no job is active
    python nrp.py status | atlas-setup | atlas-prepare --commit SHA | linprobe | latte-cleanup

Where the weights live (A6). A first layout put them on the rook-cephfs-east volume arc-latte,
where pods read them at 14.9 MB/s on one stream and 38.3 MB/s on three: about seven minutes of
an idle A10 per pod. The owner proposed many small block volumes read in parallel; `linprobe`
measured four linstor-unl volumes at 149.2 MB/s alone and 578.5 MB/s together. So each GPU pod
has its own SET of four linstor-unl volumes at UNL (volumes are single-attach): weight file k of
four on volume k, read in parallel by transformers' parallel loader, and volume 0 also holding
the env, the code, the prompts and that pod's outputs. A pod reads nothing from another region.

Scored against the NRP preflight (agi-hpc memory reference_nrp_job_policies), in ``preflight``
and ``submit``, not by recall:
- CPU jobs are in the exempt class (1 CPU, 2 GiB). GPU jobs install and download nothing:
  the env, the code, the weights and the finished prompts are staged by CPU jobs first.
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
ZONE = {"topology.kubernetes.io/zone": "unl"}
GPU_PRODUCT = "NVIDIA-A10"
APP = "gtc-ieip"
BATCH = "gtc-ieip-twin"
IMAGE = "pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime"
REPO = "https://github.com/ahb-sjsu/moral-spectrum-analyzer"
STATE = "/archive/unity/ieip"  # on Atlas: the guard's observations, fetched outputs
OBSERVATIONS = os.path.join(STATE, "observations.json")
HEARTBEAT = os.path.join(STATE, "guard.heartbeat")

# the volume sets: SETS sets of WEIGHT_FILES linstor-unl volumes, mounted at /w0 .. /w3
LIN_CLASS = "linstor-unl"
SETS = 4
WEIGHT_FILES = 4
VOL0_GIB, VOLK_GIB = 8, 5  # volume 0: one weight file (<= 4 GB) + env + code + prompts + outputs


def vol(s: int, k: int) -> str:
    return f"ieip-w{s}-{k}"


# erisml-compiler at the commit with HuggingFaceActivationSource(model=...) (erisml-compiler #26);
# its ObservationClassifier is the one deployed on the robot (unchanged since daf84e6)
COMPILER_SHA = "888c07594559d22d90ff357aecdcea5b0853693e"
PINS = (
    "transformers==4.56.1 accelerate==1.14.0 safetensors numpy huggingface_hub "
    f"https://github.com/ahb-sjsu/erisml-compiler/archive/{COMPILER_SHA}.tar.gz"
)

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REV = "a09a35458c702b33eeacc393d103063234e8bc28"  # Atlas ~/.cache/huggingface refs/main
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
# parallel loader's transient buffers, and the monitor's float32 copy of four layers' hidden
# states at up to 8192 tokens (0.47 GB). It runs while the utilization guard records its usage.
PILOT_REQUEST = (2, 5, "stated model: 1 driving thread; CUDA context + load buffers + hooks")
PILOT_SHARE = 8  # the pilot takes about an eighth of the prompts, at least PILOT_MIN
PILOT_MIN = 120
ATLAS_VENV = "/archive/unity/ieip-venv"  # the same pins on Atlas, for its own prepare and collect
ATLAS_MODEL = f"/home/claude/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/{MODEL_REV}"
MAX_GPU_PODS = 4
GPU_TIMEOUT_S = 6 * 3600
FETCH_CHUNK = 6 << 20  # raw bytes per fetch job: 8 MiB of base64, under a 10 MiB log rotation


def _code(commit: str) -> str:
    """The repository at `commit` into /tmp/code, from GitHub's tarball (no git in the image)."""
    return f"""timeout 600 python3 - <<'EOF'
import io, os, shutil, tarfile, urllib.request
raw = urllib.request.urlopen("{REPO}/archive/{commit}.tar.gz", timeout=300).read()
tarfile.open(fileobj=io.BytesIO(raw)).extractall("/tmp/src")
(top,) = os.listdir("/tmp/src")
shutil.move(os.path.join("/tmp/src", top), "/tmp/code")
EOF
test -f /tmp/code/twin/ieip/gpu_capture.py
"""


def stage_script(commit: str) -> str:
    """One set: the pinned env as one tar on volume 0, then the weights across the set."""
    shards = ",".join(f"/w{k}/shards" for k in range(WEIGHT_FILES))
    return f"""set -euo pipefail
export PIP_ROOT_USER_ACTION=ignore PYTHONUNBUFFERED=1 HF_HUB_DISABLE_XET=1
if [ -f /w0/env.tar ]; then
  tar -xf /w0/env.tar -C /tmp
else
  python -m venv --system-site-packages /tmp/venv
  timeout 1800 /tmp/venv/bin/pip install -q --no-cache-dir {PINS}
  /tmp/venv/bin/python -c "import torch, transformers, inspect, erisml_compiler.monitor.huggingface_source as h; \\
assert 'model' in inspect.signature(h.HuggingFaceActivationSource).parameters; \\
print('torch', torch.__version__, 'transformers', transformers.__version__)"
  /tmp/venv/bin/pip freeze > /tmp/venv/freeze.txt
  tar -cf /w0/env.tar.tmp -C /tmp venv && mv /w0/env.tar.tmp /w0/env.tar
fi
{_code(commit)}cat > /tmp/expect.json <<'EOF'
{json.dumps(EXPECT)}
EOF
timeout 7200 /tmp/venv/bin/python /tmp/code/twin/ieip/stage_model.py --model-id {MODEL_ID} --revision {MODEL_REV} \\
    --dest /w0/model --shard-dests {shards} --expect /tmp/expect.json
df -h {" ".join(f"/w{k}" for k in range(WEIGHT_FILES))}
"""


def prepare_script(commit: str, sets: int) -> str:
    """The prompts from the inputs at `commit`, built once and copied with the code to every
    set's volume 0 (mounted at /s0 .. /s{sets-1})."""
    inputs = " ".join(f"/tmp/code/{p}" for p in INPUTS)
    copy = "\n".join(
        f"mkdir -p /s{s}/prep/{commit} /s{s}/code && cp /tmp/prep/* /s{s}/prep/{commit}/ "
        f"&& tar -cf /s{s}/code/{commit}.tar -C /tmp/code ." for s in range(sets)
    )
    return f"""set -euo pipefail
export PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
tar -xf /s0/env.tar -C /tmp
{_code(commit)}test -f /s0/model/STAGED.json
timeout 3600 /tmp/venv/bin/python /tmp/code/twin/ieip/analysis.py prepare {inputs} --tokenizer /s0/model \\
    --out /tmp/prep
{copy}
"""


def gpu_script(commit: str, start: int, end: int) -> str:
    """One shard on one set: env, code and prompts from volume 0, the four weight files from
    the four volumes at once, outputs to volume 0."""
    return f"""set -euo pipefail
export PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export HF_ENABLE_PARALLEL_LOADING=true HF_PARALLEL_LOADING_WORKERS={WEIGHT_FILES}
tar -xf /w0/env.tar -C /tmp
mkdir -p /tmp/code && tar -xf /w0/code/{commit}.tar -C /tmp/code
mkdir -p /tmp/model && cp /w0/model/* /tmp/model/ && ln -s /w?/shards/*.safetensors /tmp/model/
export PATH=/tmp/venv/bin:$PATH
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
timeout {GPU_TIMEOUT_S} python /tmp/code/twin/ieip/gpu_capture.py --prompts /w0/prep/{commit}/prompts.jsonl \\
    --start {start} --end {end} --model /tmp/model --out /w0/run/{commit}
echo CAPTURE_DONE {start} {end}
"""


def fetch_script(commit: str, s: int, part: int) -> str:
    """Chunk `part` of set `s`'s outputs as a tar.gz, base64 on stdout. The tar is built once,
    by part 0, under a name holding its sha256, so every part reads the same bytes."""
    tag = f"{commit}-set{s}"
    return f"""set -euo pipefail
cd /w0
if [ {part} -eq 0 ] || ! ls fetch/{tag}.*.tgz >/dev/null 2>&1; then
  mkdir -p fetch
  timeout 600 tar -czf fetch/{tag}.tmp run/{commit} prep/{commit}/manifest.json
  h=$(sha256sum fetch/{tag}.tmp | cut -c1-64)
  rm -f fetch/{tag}.*.tgz && mv fetch/{tag}.tmp fetch/{tag}.$h.tgz
fi
f=$(ls fetch/{tag}.*.tgz)
echo "FETCH_FILE $(basename $f) $(stat -c %s $f)"
echo FETCH_BEGIN
timeout 600 dd if=$f bs={FETCH_CHUNK} skip={part} count=1 status=none | base64 -w0
echo
echo FETCH_END
"""


# the measurement behind the layout (A6): four linstor-unl volumes written and read with direct
# I/O, one alone and then all at once (149.2 and 578.5 MB/s, 2026-10-03)
LIN_PROBE_N = 4
LINPROBE = f"""set -euo pipefail
for i in $(seq 0 {LIN_PROBE_N - 1}); do
  timeout 600 dd if=/dev/zero of=/v$i/blob bs=16M count=128 oflag=direct status=none &
done
wait
t() {{ python3 -c 'import time; print(time.perf_counter())'; }}
a=$(t); timeout 600 dd if=/v0/blob of=/dev/null bs=16M iflag=direct status=none; b=$(t)
python3 -c "print('LIN_READ_ONE', round(2147.48/($b-$a), 1), 'MB/s')"
a=$(t)
for i in $(seq 0 {LIN_PROBE_N - 1}); do timeout 600 dd if=/v$i/blob of=/dev/null bs=16M iflag=direct status=none & done
wait
b=$(t)
python3 -c "print('LIN_READ_PARALLEL', {LIN_PROBE_N}, 'volumes', round({LIN_PROBE_N}*2147.48/($b-$a), 1), 'MB/s')"
rm -f /v*/blob
"""

# the first layout's files on LaTTE's volume, removed (owner's decision 2026-10-03)
LATTE_CLEANUP = """set -euo pipefail
timeout 600 rm -rf /data/ieip-twin
df -h /data | tail -1
echo LATTE_CLEANED
"""


def pvcs(names_gib: list[tuple[str, int]]) -> str:
    return "".join(
        f"""---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: {{name: {n}, namespace: {NS}, labels: {{app: {APP}}}}}
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: {LIN_CLASS}
  resources: {{requests: {{storage: {g}Gi}}}}
"""
        for n, g in names_gib
    )


# ----------------------------------------------------------------------------- sizing


def _tqp_sizing():
    """turboquant-pro's benchmarks/nrp/sizing.py, loaded by path (its package is also `nrp`)."""
    import importlib.util

    path = os.path.join(TQP_NRP, "nrp", "sizing.py")
    spec = importlib.util.spec_from_file_location("tqp_nrp_sizing", path)
    sizing = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = sizing  # its dataclasses look their module up while being defined
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


def descriptor(name, script, cpu, mem_gib, eph, role, gpu=0, volumes=(), zone=None):
    """`volumes`: (pvc, mount path) pairs."""
    from nats_bursting import JobDescriptor, Resources, Volume

    return JobDescriptor(
        name=name,
        image=IMAGE,
        command=["/bin/bash", "-lc", script],
        resources=Resources(cpu=str(cpu), memory=f"{mem_gib}Gi", gpu=gpu, ephemeral_storage=eph),
        labels={"app": APP, "atlas.io/batch": BATCH, "atlas.io/role": role},
        node_selector={**(zone or ZONE), **({"nvidia.com/gpu.product": GPU_PRODUCT} if gpu else {})},
        backoff_limit=0,
        volumes=[Volume(name=f"v{i}", mount_path=m, claim_name=c) for i, (c, m) in enumerate(volumes)],
    )


def set_volumes(s: int) -> list[tuple[str, str]]:
    return [(vol(s, k), f"/w{k}") for k in range(WEIGHT_FILES)]


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
    if desc.node_selector.get("topology.kubernetes.io/zone") not in ("unl", "mghpcc"):
        bad.append("not pinned to the volumes' region")
    if gpu and any(w in script for w in ("pip install", "git clone", "urlopen", "snapshot_download", "hf_hub_download", "apt-get")):
        bad.append("a GPU job installs or downloads")
    if not gpu and (float(r.cpu) > 1 or float(str(r.memory).rstrip("Gi")) > 2):
        bad.append("a CPU job outside the exempt class")
    return bad


def kubectl(*args, stdin=None):
    return subprocess.run(["kubectl", "-n", NS, "--request-timeout=60s", *args], capture_output=True, text=True,
                          timeout=120, input=stdin)


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


def active_jobs() -> list[str]:
    r = kubectl("get", "jobs", "-l", f"app={APP}", "-o", "jsonpath={.items[*].metadata.name}")
    return [n for n in r.stdout.split() if job_state(n) == "active"]


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


def wait_finished(name: str) -> None:
    while job_state(name) != "finished":
        time.sleep(15)


def prompts_count(commit: str) -> int:
    """From the prepare job's log: PREPARED {manifest}, checked against Atlas's own prepare of
    the same inputs (A5: the prompts must be byte-identical)."""
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
    k = min(MAX_GPU_PODS, SETS, max(1, math.ceil(rest / p))) if rest else 0
    edges = [p + round(i * rest / k) for i in range(k + 1)] if k else []
    return (0, p), list(zip(edges, edges[1:], strict=False))


def fetch(commit: str) -> None:
    """Every set's outputs, chunk by chunk, each chunk from its own exempt CPU job,
    reassembled, checked against the sha256 in its name, and unpacked into one directory."""
    out = os.path.join(STATE, "fetch", commit)
    os.makedirs(out, exist_ok=True)
    pilot, rest = ranges(prompts_count(commit))
    for s in range(max(1, len(rest))):
        blob, part, total, fname = bytearray(), 0, None, None
        while total is None or len(blob) < total:
            name = f"{job_name('fetch', commit)}-s{s}-{part}"
            d = descriptor(name, fetch_script(commit, s, part), 1, 2, "4Gi", "fetch", volumes=[(vol(s, 0), "/w0")])
            bad = preflight(d, False)
            if bad:
                raise SystemExit(f"PREFLIGHT VETO {name}: {bad}")
            submit(d)
            wait_finished(name)
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
        want, got = fname.split(".")[1], hashlib.sha256(blob).hexdigest()
        if got != want:
            raise SystemExit(f"set {s}: reassembled sha256 {got} != {want}")
        path = os.path.join(out, fname)
        open(path, "wb").write(blob)
        subprocess.run(["tar", "-xzf", path, "-C", out], check=True)
        print("FETCHED", path, len(blob), "bytes, sha256 verified", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("volumes", "stage", "prepare", "pilot", "shards", "fetch", "release", "status",
                                    "atlas-setup", "atlas-prepare", "linprobe", "latte-cleanup"))
    ap.add_argument("--commit", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        print(kubectl("get", "jobs", "-l", f"app={APP}").stdout, kubectl("get", "pvc", "-l", f"app={APP}").stdout)
        return 0
    if a.cmd == "volumes":
        names = [(vol(s, k), VOL0_GIB if k == 0 else VOLK_GIB) for s in range(SETS) for k in range(WEIGHT_FILES)]
        r = kubectl("apply", "-f", "-", stdin=pvcs(names))
        print(r.stdout or r.stderr)
        return 0
    if a.cmd == "release":
        if active_jobs():
            raise SystemExit(f"jobs still active: {active_jobs()}")
        print(kubectl("delete", "pvc", "-l", f"app={APP}").stdout)
        return 0
    if a.cmd == "atlas-setup":
        if not os.path.exists(ATLAS_VENV):
            subprocess.run([sys.executable, "-m", "venv", ATLAS_VENV], check=True)
        # tokenizing needs no torch, so not accelerate (which would pull a CUDA torch); any
        # difference this makes to the prompts is caught by comparing them with NRP's
        pins = [p for p in PINS.split() if not p.startswith("accelerate")]
        subprocess.run([f"{ATLAS_VENV}/bin/pip", "install", "-q", *pins], check=True)
        return 0
    if a.cmd not in ("linprobe", "latte-cleanup") and not re.fullmatch(r"[0-9a-f]{40}", a.commit):
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
    if a.cmd == "linprobe":
        names = [(f"ieip-linprobe-{i}", 5) for i in range(LIN_PROBE_N)]
        print(kubectl("apply", "-f", "-", stdin=pvcs(names)).stdout)
        items.append((descriptor(f"ieip-linprobe-{int(time.time())}", LINPROBE, 1, 2, "1Gi", "probe",
                                 volumes=[(n, f"/v{i}") for i, (n, _) in enumerate(names)]), False))
    elif a.cmd == "latte-cleanup":
        items.append((descriptor(f"ieip-latte-cleanup-{int(time.time())}", LATTE_CLEANUP, 1, 2, "1Gi", "cleanup",
                                 volumes=[("arc-latte", "/data")], zone={"topology.kubernetes.io/zone": "mghpcc"}), False))
    elif a.cmd == "stage":
        for s in range(SETS):
            items.append((descriptor(f"{job_name('stage', a.commit)}-s{s}", stage_script(a.commit), 1, 2, "24Gi",
                                     "stage", volumes=set_volumes(s)), False))
    elif a.cmd == "prepare":
        items.append((descriptor(job_name("prepare", a.commit), prepare_script(a.commit, SETS), 1, 2, "4Gi", "prepare",
                                 volumes=[(vol(s, 0), f"/s{s}") for s in range(SETS)]), False))
    elif a.cmd in ("pilot", "shards"):
        n = prompts_count(a.commit)
        pilot, rest = ranges(n)
        if a.cmd == "pilot":
            if not guard_fresh():
                raise SystemExit(f"PREFLIGHT VETO: the utilization guard's heartbeat ({HEARTBEAT}) is not fresh")
            cpu, mem, why = PILOT_REQUEST
            todo = [(0, pilot)]
            names = [job_name("pilot", a.commit, *pilot)]
        else:
            if job_state(job_name("pilot", a.commit, *pilot)) != "finished":
                raise SystemExit("the pilot has not finished")
            cpu, mem, why = shard_request(a.commit, pilot)
            todo = list(enumerate(rest))
            names = [job_name("shards", a.commit, s, e) for s, e in rest]
        if gpu_pods_in_namespace() + len(todo) > MAX_GPU_PODS:
            raise SystemExit(f"PREFLIGHT VETO: more than {MAX_GPU_PODS} GPU pods in the namespace")
        for name, (s, (lo, hi)) in zip(names, todo, strict=True):
            d = descriptor(name, gpu_script(a.commit, lo, hi), cpu, mem, "24Gi", a.cmd, gpu=1, volumes=set_volumes(s))
            print(d.name, f"set {s} [{lo}, {hi})", cpu, f"{mem}Gi", GPU_PRODUCT, "|", why)
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
