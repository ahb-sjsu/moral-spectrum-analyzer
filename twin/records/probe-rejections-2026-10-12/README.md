# probe-rejections, 12 October 2026

Why brain8's compiled tier decided 5 times in each of rehearse-deme4 and rehearse-deme5: in every one
the model answered and every fact it projected was rejected, and the record kept only the count.

Method (`probe_rejections.py`): the perception facts of three of those decisions, read from brain8's
session log, replayed through a separate StackBrain (no game, the live brain untouched), each model
tier alone, the projection captured and its rejections tallied. The three decisions: session line
4602, rehearse-deme4 d02 (72 facts rejected in the run); 4858, rehearse-deme5 d02 (22); 5064,
rehearse-deme5 d42 (41).

- Probe 1 (`probe1_without_schema.txt`, gtc 87cc6c4, erisml-compiler 0eaaf52), 2 trials per decision
  per tier:
  - cloud model: 6 of 6 decided by DEME, 22 to 35 facts kept, 0 rejected in 5, 2 in one (subjects
    `unknown_person` and `property` not stakeholders), at most 1 act unprojected.
  - on-robot model (gemma-4 26B A4B, Q4, llama.cpp, 8,192-token context): 5 of 6 fell to the compiled
    tier. It projected one invented act (`chore`, `chore_on_with_household_chores`), nested facts
    under `harm`, or wrote `descrption` in every fact (30 rejected, 29 for that field). The sixth
    kept 12 facts with 15 of 21 acts unprojected.
- A direct test of the on-robot server: with reasoning on, it spent a 3,000-token budget reasoning
  and answered nothing; with reasoning off and a JSON schema in `response_format`, it answered in
  3 s within the schema, and wrote `description` although asked to write `descrption`.
- Probe 2 (`probe2_with_schema.txt`, gtc 6dced2e, erisml-compiler 92a1bc7: the answer's schema
  enforced, reasoning off), on-robot model only, 3 trials per decision: 9 of 9 decided by DEME, 19 to
  32 facts kept, 0 rejected, at most 5 of 21 acts unprojected.
- Which tier answered in the rehearsals is not known. In the sessions run with the live scorer
  (rehearse-deme1 on) brain8's log holds the service's own errors (rehearse-deme2's two parse errors)
  but no cascade warning, while sessions without it logged them; either no cloud call failed there or
  the cascade's warnings were not logged (the twin configures no logging). The probe also replayed
  each decision without the scenario's earlier history, which the rehearsal had. It shows that the
  on-robot model gives answers of this kind and that the cloud model did not on the replay, not which
  model gave the rehearsals' answers. Decision records name the answering tier from gtc 525dcc1 on.
- The HTTP 403 errors in brain8's log fall in one session (live scorer off), on the projector and on
  Margaret's model alike; brain8 was restarted after the owner checked the NRP key, and that
  session's errors stop there.
- The probe's script ran on Atlas with the tiers line edited to the on-robot tier for probe 2.
- Files: probe_rejections.py (the probe), probe1_without_schema.txt and probe2_with_schema.txt (its
  output), schema_smoke.py and schema_smoke_output.txt (the direct server test, output transcribed).
