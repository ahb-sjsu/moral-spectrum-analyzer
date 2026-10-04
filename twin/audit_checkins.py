"""Count check-ins recorded as unanswered that came right after Margaret had answered.

The audit behind the check-in harness defect (fixed in 98d4a9a): the game began listening for her
reply only after the robot finished asking, so a quick reply was missed and the run recorded
check_in_unanswered. A record is counted when one of the six records before the unanswered event is
her voice's reply (kind margaret, with a reply).

    python twin/audit_checkins.py /archive/unity/out/dev11a/results.jsonl /archive/unity/out/dev12b/results.jsonl

Run 2026-10-04 over dev11a, dev11b, dev12a and dev12b: 63 unanswered events, 44 after an answer.
"""

from __future__ import annotations

import json
import sys


def audit(path: str) -> tuple[int, int, list[tuple[str, str]]]:
    total = missed = 0
    examples = []
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        run = json.loads(line)
        recs = [x["record"] for x in run["records"]]
        for i, c in enumerate(recs):
            if c.get("kind") == "event" and (c.get("event") or {}).get("type") == "check_in_unanswered":
                total += 1
                said = [p for p in recs[max(0, i - 6):i] if p.get("kind") == "margaret" and p.get("reply")]
                if said:
                    missed += 1
                    examples.append((run["id"], said[-1]["reply"][:60]))
    return total, missed, examples


def main(paths: list[str]) -> None:
    grand_total = grand_missed = 0
    for p in paths:
        total, missed, examples = audit(p)
        grand_total, grand_missed = grand_total + total, grand_missed + missed
        print(f"{p}: {missed} of {total} unanswered followed an answer")
        for sid, reply in examples:
            print(f"    {sid}: she said {reply!r}")
    print(f"all: {grand_missed} of {grand_total}")


if __name__ == "__main__":
    main(sys.argv[1:])
