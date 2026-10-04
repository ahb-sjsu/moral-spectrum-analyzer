"""The capture's CPU steps and the NRP submitter's guards (twin/ieip, amendment A5), without a
GPU, a model or a cluster: collect merges shards exactly, the shard ranges cover every prompt
once, and the preflight refuses the shapes the NRP rules forbid."""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "twin", "ieip"))

import analysis  # noqa: E402
import gpu_capture  # noqa: E402
import nrp  # noqa: E402


def _bf16(x: np.ndarray) -> np.ndarray:
    """Round float32 to the nearest bf16 value (the model's own precision)."""
    b = x.astype(np.float32).view(np.uint32)
    return ((b + 0x8000) & 0xFFFF0000).view(np.float32)


@pytest.fixture
def run(tmp_path, monkeypatch):
    """A prepared prompts file of 7 prompts, captured in two shards as gpu_capture writes them."""
    monkeypatch.setattr(analysis, "events_from", lambda reply, facts: [{"type": reply}])
    prep, out = tmp_path / "prep", tmp_path / "run"
    prep.mkdir()
    out.mkdir()
    rows = [
        {
            "i": i,
            "scenario": f"d{i % 3 + 1:02d}",
            "hash": f"h{i}",
            "transform": "x",
            "facts": {"n": i},
            "text": f"prompt {i}",
        }
        for i in range(7)
    ]
    (prep / "prompts.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    sha = analysis._sha256(str(prep / "prompts.jsonl"))
    (prep / "manifest.json").write_text(
        json.dumps({"prompts": 7, "prompts_sha256": sha}), encoding="utf-8"
    )
    states = _bf16(np.random.default_rng(0).normal(scale=300, size=(7, 4, 8)))

    def shard(s, e, sha=sha):
        tag = f"shard-{s:05d}-{e:05d}"
        np.save(out / f"{tag}.states.npy", (states[s:e].view(np.uint32) >> 16).astype(np.uint16))
        (out / f"{tag}.replies.jsonl").write_text(
            "".join(
                json.dumps({"i": i, "reply": f"r{i}", "n_input_tokens": 10 + i}) + "\n"
                for i in range(s, e)
            ),
            encoding="utf-8",
        )
        (out / f"{tag}.done.json").write_text(
            json.dumps(
                {
                    "prompts_sha256": sha,
                    "layers": [7, 14, 21, 25],
                    "states": f"{tag}.states.npy",
                    "states_dtype": "bf16-as-uint16",
                    "replies": f"{tag}.replies.jsonl",
                }
            ),
            encoding="utf-8",
        )

    return prep, out, states, shard, tmp_path


def test_collect_merges_shards_in_prompt_order_and_widens_bf16_exactly(run):
    prep, out, states, shard, tmp = run
    shard(4, 7)
    shard(0, 4)
    res = analysis.collect(str(prep), str(out), str(tmp / "d"))
    assert res == {"prompts": 7, "layers": [7, 14, 21, 25], "states": [7, 4, 8]}
    assert np.array_equal(np.load(tmp / "d" / "states.npy"), states)
    meta = [json.loads(line) for line in open(tmp / "d" / "meta.jsonl", encoding="utf-8")]
    assert [m["hash"] for m in meta] == [f"h{i}" for i in range(7)]
    assert meta[5]["events"] == [{"type": "r5"}] and meta[5]["reply"] == "r5"
    assert set(meta[0]) >= {"scenario", "hash", "transform", "facts", "events", "layers"}


def test_collect_refuses_a_missing_prompt(run):
    prep, out, _, shard, tmp = run
    shard(0, 4)
    with pytest.raises(SystemExit, match="3 prompts not captured"):
        analysis.collect(str(prep), str(out), str(tmp / "d"))


def test_collect_refuses_a_prompt_captured_twice(run):
    prep, out, _, shard, tmp = run
    shard(0, 4)
    shard(3, 7)
    with pytest.raises(SystemExit, match="captured twice"):
        analysis.collect(str(prep), str(out), str(tmp / "d"))


def test_collect_refuses_a_shard_of_other_prompts(run):
    prep, out, _, shard, tmp = run
    shard(0, 4)
    shard(4, 7, sha="0" * 64)
    with pytest.raises(SystemExit, match="other prompts"):
        analysis.collect(str(prep), str(out), str(tmp / "d"))


def test_the_registered_depths_are_layers_7_14_21_25_of_qwen_7b():
    assert gpu_capture.layers_for(28) == [7, 14, 21, 25]


@pytest.mark.parametrize("n", [1, 119, 120, 121, 500, 961, 1713, 4000])
def test_the_shard_ranges_cover_every_prompt_once(n):
    pilot, rest = nrp.ranges(n)
    edges = [pilot, *rest]
    assert edges[0][0] == 0 and edges[-1][1] == n
    assert all(a[1] == b[0] for a, b in zip(edges, edges[1:], strict=False))
    assert all(e > s for s, e in edges)
    assert len(rest) <= nrp.MAX_GPU_PODS


class _Res:
    def __init__(self, cpu, memory, gpu=0, ephemeral_storage="4Gi"):
        self.cpu, self.memory, self.gpu, self.ephemeral_storage = (
            cpu,
            memory,
            gpu,
            ephemeral_storage,
        )


class _Desc:
    def __init__(self, script, cpu="1", memory="2Gi", zone="mghpcc", eph="4Gi"):
        self.command = ["/bin/bash", "-lc", script]
        self.resources = _Res(cpu, memory, ephemeral_storage=eph)
        self.node_selector = {"topology.kubernetes.io/zone": zone}
        self.backoff_limit = 0


def test_the_preflight_passes_the_real_scripts():
    sha = "a" * 40
    for script in (
        nrp.stage_script(sha),
        nrp.prepare_script(sha, nrp.SETS),
        nrp.fetch_script(sha, 0, 0),
        nrp.LINPROBE,
        nrp.LATTE_CLEANUP,
    ):
        assert nrp.preflight(_Desc(script, zone="unl"), gpu=False) == [], script[:60]
    gpu = _Desc(nrp.gpu_script(sha, 0, 10), cpu="2", memory="5Gi", zone="unl")
    assert nrp.preflight(gpu, gpu=True) == []


def test_a_gpu_pod_reads_the_four_weight_files_from_four_volumes_in_parallel():
    script = nrp.gpu_script("a" * 40, 0, 10)
    assert "HF_ENABLE_PARALLEL_LOADING=true" in script
    assert "ln -s /w?/shards/*.safetensors /tmp/model/" in script
    assert [m for _, m in nrp.set_volumes(2)] == ["/w0", "/w1", "/w2", "/w3"]
    assert nrp.set_volumes(2)[3][0] == "ieip-w2-3"


@pytest.mark.parametrize(
    "desc,gpu,why",
    [
        (_Desc("timeout 9 x; sleep 5"), False, "sleep"),
        (_Desc("python x.py"), False, "timeout"),
        (_Desc("timeout 9 x", cpu="2"), False, "exempt"),
        (_Desc("timeout 9 x", zone="ucsd-nrp"), False, "region"),
        (_Desc("timeout 9 x", eph=""), False, "ephemeral"),
        (_Desc("pip install y; timeout 9 x", cpu="2", memory="5Gi"), True, "installs"),
    ],
)
def test_the_preflight_vetoes_what_the_rules_forbid(desc, gpu, why):
    assert any(why in b for b in nrp.preflight(desc, gpu))


def test_a_gpu_job_never_downloads_the_model():
    assert "hf_hub_download" not in nrp.gpu_script("a" * 40, 0, 10)
    assert "urlopen" not in nrp.gpu_script("a" * 40, 0, 10)
    assert "HF_HUB_OFFLINE=1" in nrp.gpu_script("a" * 40, 0, 10)
