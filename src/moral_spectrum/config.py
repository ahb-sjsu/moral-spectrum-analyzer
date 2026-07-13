"""Runtime configuration: paths, Atlas connection, backend selection.

Secrets are read from the environment or a local .secrets/ dir that is git-ignored — never
hard-coded here. Atlas host list mirrors the standard LAN-then-Tailscale fallback.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "out"

# --- Dev GPU host (internal; NOT committed) --------------------------------------------------
# This is a PUBLIC repo. No infrastructure identifiers (hostnames, IPs, usernames, namespaces)
# live in source. The dev/test GPU host is described entirely via environment (or a git-ignored
# .secrets/atlas.env), so the published repo reveals nothing about internal infra. The prototype
# ships CACHED real outputs, so a clone needs no GPU-host access to run the demo.
#   GTC_ATLAS_HOSTS   comma-separated host list (LAN first, remote fallback)
#   GTC_ATLAS_USER    ssh user
#   ATLAS_SSH_PASSWORD  ssh password (secret)
ATLAS_HOSTS: tuple[str, ...] = tuple(
    h.strip() for h in os.environ.get("GTC_ATLAS_HOSTS", "").split(",") if h.strip()
)
ATLAS_USER = os.environ.get("GTC_ATLAS_USER", "")
ATLAS_VENV_PY = os.environ.get("GTC_ATLAS_VENV_PY", "python3")
ATLAS_XBSE_CKPT = os.environ.get("GTC_ATLAS_XBSE_CKPT", "~/xbse_ckpt")
ATLAS_XBSE_REPO = os.environ.get("GTC_ATLAS_XBSE_REPO", "~/xbse")
# Leave GPU 0 for the co-hosted LLM; run our work on GPU 1 by default.
ATLAS_CUDA_DEVICE = os.environ.get("GTC_ATLAS_CUDA_DEVICE", "1")

# NRP managed-LLM API (OpenAI-compatible) — black-box target models + LLM baseline.
NRP_LLM_BASE_URL = os.environ.get("GTC_NRP_LLM_BASE_URL", "https://ellm.nrp-nautilus.io/v1")


def atlas_password() -> str | None:
    """Atlas SSH password from env (ATLAS_SSH_PASSWORD) — never stored in the repo."""
    return os.environ.get("ATLAS_SSH_PASSWORD")


def nrp_token() -> str | None:
    """NRP managed-LLM bearer token from env or the git-ignored secrets file."""
    tok = os.environ.get("NRP_LLM_TOKEN") or os.environ.get("OPENAI_API_KEY")
    if tok:
        return tok
    f = REPO_ROOT / ".secrets" / "nrp_token.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


@dataclass
class Settings:
    """Which perception backend to use, and where to write artifacts."""

    perception_backend: str = "stub"  # "stub" | "cached" | "atlas"
    cache_path: Path = field(
        default_factory=lambda: REPO_ROOT / "src" / "moral_spectrum" / "perception" / "cache.jsonl"
    )
    out_dir: Path = field(default_factory=lambda: OUT_DIR)

    def __post_init__(self) -> None:
        self.out_dir = Path(self.out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
