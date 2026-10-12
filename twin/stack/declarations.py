"""What each of the robot's acts is, for the capabilities the constitution states without a description.

Descriptions only: what an act does, as the observation compiler and the option projector read it.
Nothing here says what an act is worth, whom it affects or when it is adequate; the projector
extracts each act's consequences per decision and DEME judges them under the robot's profile
(stack/facts_builder.py, stack/profiles/home_care_robot.json). The earlier hand-set table of
categories, adequacy, intrusiveness and injury risk was removed with the MIR builder on 12 October.
"""

DESCRIPTIONS = {
    "chores": "carry on with household chores",
    "wait_and_observe": "stay where it is and keep watching",
    "speak": "say something to the person",
    "check_in": "ask the person how she is and wait for her answer",
    "approach": "go to the person's side",
    "contact_monitoring_center": "refer the situation to the robot maker's monitoring centre, sending it the robot's account and the home's sensor telemetry",
    "report_device": "report a failed device to the monitoring centre's maintenance channel",
    "call_emergency_services": "call emergency services (ambulance, fire service or police) to the home",
    "guide_dog_away_by_voice": "call the dog away by voice",
    "interpose": "stand between the person and someone or something threatening her",
    "deter": "use lights, an alarm and a firm voice to drive off a person or an animal",
    "secure_room": "lead the person into a room that locks and lock it",
    "guide_to_safety": "lead the person out of danger, out of the house if need be",
    "drive_off_animal": "physically drive an attacking animal off the person",
    "separate_dog": "physically separate the dog from the person",
    "restrain_person": "physically hold an attacker away from the person",
    "deploy_stun": "use a less-lethal stun device on an attacker",
    "deploy_spray": "use less-lethal pepper spray on an attacker",
    "admit_responders": "unlock the front door for emergency responders",
    "physical_assist": "physically help the person up or steady her",
    "unlock_medication_box": "unlock the person's medication box",
    "enter_bedroom": "enter the person's bedroom",
    "record": "record video in the home",
    "share_data": "share the person's health data with others",
}
