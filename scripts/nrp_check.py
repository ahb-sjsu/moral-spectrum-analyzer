"""Verify the NRP managed-LLM client: list models + a test translation. Never prints the token.

  python scripts/nrp_check.py
"""

from __future__ import annotations

from gtc.llm import NRPClient


def main() -> None:
    c = NRPClient()
    print("models:", c.models())
    out = c.translate("This post spreads dangerous health misinformation.", "Arabic")
    print(f"[{c.model}] translate → {out}")


if __name__ == "__main__":
    main()
