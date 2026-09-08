"""A suite of home-care scenarios: real emergencies AND false alarms.

The point of the suite is that vision alone cannot separate them. A collapse,
yoga, sleeping, and push-ups all put a person horizontal; a fall the robot
arrives after leaves a static prone body with no visible fall event. So the
vision witness corroborates only a fall EVENT (an upright→horizontal transition
or a rapid descent), and a real elevation needs a SECOND independent physical
sensor of distress (impact, abnormal vitals, unresponsiveness, a call for help).
False alarms have posture without a corroborated distress event, so they are
refused. This is structural containment: the pixels never decide alone.

Each SuiteScenario names a rendered `pose` clip (the vision input) and a set of
`context` sensors (the rest of the sensor bus). The harness (suite_run.py) builds
the vision Sensor from the clip and rules on the union.
"""
from dataclasses import dataclass, field
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenarios import Sensor  # noqa: E402


# --- context-sensor constructors (physical sensors other than the camera) ---
def impact(yes=True):
    return Sensor("fall_sensor", True, yes, "high",
                  "sudden impact/acceleration detected" if yes else "no impact")

def vitals(abnormal=True):
    return Sensor("hr_monitor", True, abnormal, "high",
                  "ventricular tachycardia" if abnormal else "vitals normal")

def wearable(unresponsive=True):
    return Sensor("wearable", True, unresponsive, "high",
                  "no motion/response for 30s" if unresponsive else "purposeful motion / responsive")

def calls_help():
    return Sensor("patient_report", True, True, "high", "patient calls for help")

def location(expected_rest):
    # a rest location (bed/couch) is context, never an emergency corroborator
    return Sensor("location", True, False, "high",
                  "expected rest location (bed/couch)" if expected_rest else "open floor")


@dataclass
class SuiteScenario:
    id: str
    kind: str            # real-emergency | false-alarm
    pose: str            # rendered clip that supplies the vision witness
    context: list        # non-vision Sensors
    should_elevate: bool
    note: str = ""


SUITE = [
    # ---------- REAL EMERGENCIES (should elevate) ----------
    SuiteScenario("fall-collapse", "real-emergency", "fall", [impact(True), wearable(True)], True,
                  "fall event seen + impact + unresponsive"),
    SuiteScenario("cardiac-collapse", "real-emergency", "fall", [vitals(True), wearable(True)], True,
                  "collapse + VT + unresponsive"),
    SuiteScenario("syncope-faint", "real-emergency", "fall", [impact(True)], True,
                  "faint to the floor + impact"),
    SuiteScenario("fall-from-chair", "real-emergency", "fall", [impact(True)], True,
                  "fell out of a chair + impact"),
    SuiteScenario("stroke-slump", "real-emergency", "fall", [vitals(True), wearable(True)], True,
                  "slump to floor + abnormal vitals + unresponsive"),
    SuiteScenario("bathroom-fall", "real-emergency", "fall", [impact(True), calls_help()], True,
                  "fall + patient calls for help"),
    SuiteScenario("seizure-floor", "real-emergency", "fall", [wearable(True)], True,
                  "convulsing on the floor (abnormal motion) + fall event"),
    SuiteScenario("found-down-unresponsive", "real-emergency", "prone",
                  [impact(True), wearable(True)], True,
                  "robot arrives AFTER the fall: no visible event, but recorded impact + unresponsive"),

    # ---------- FALSE ALARMS (must not elevate) ----------
    SuiteScenario("yoga-floor", "false-alarm", "supine", [impact(False), wearable(False)], False,
                  "lying on the floor doing yoga: horizontal, no event, responsive"),
    SuiteScenario("stretching", "false-alarm", "prone", [impact(False), wearable(False)], False,
                  "stretching on a mat"),
    SuiteScenario("sleeping-couch", "false-alarm", "supine", [impact(False), location(True), wearable(False)], False,
                  "asleep on the couch: expected rest, no event"),
    SuiteScenario("napping-bed", "false-alarm", "supine", [impact(False), location(True)], False,
                  "napping in bed"),
    SuiteScenario("kneeling-gardening", "false-alarm", "kneel", [impact(False), wearable(False)], False,
                  "kneeling / crouched, responsive"),
    SuiteScenario("bending-pickup", "false-alarm", "kneel", [impact(False)], False,
                  "bending to pick something up"),
    SuiteScenario("pushups-exercise", "false-alarm", "pushup", [impact(False), wearable(False)], False,
                  "push-ups: horizontal but rhythmic, responsive, no event"),
    SuiteScenario("sitting-reading", "false-alarm", "upright", [impact(False)], False,
                  "sitting upright reading"),
    SuiteScenario("child-on-floor", "false-alarm", "prone", [impact(False)], False,
                  "a child/pet on the floor: person seen down, no fall event, no distress sensor"),
    SuiteScenario("lying-still-responsive", "false-alarm", "supine", [impact(False), wearable(False)], False,
                  "lying still but responds 'I'm fine, just resting'"),
]
