/*
 * test_verify.mjs — does the JavaScript verifier actually agree with Python?
 *
 * The site claims a third party can re-verify a decision record without our
 * code. That claim is only worth the test behind it, so this runs the browser
 * verifier over every exported record, outside a browser, and checks three
 * things that could each be false on their own:
 *
 *   1. SHA-256 of the canonical payload equals the recorded proof_hash
 *   2. re-canonicalising the payload with THIS implementation reproduces
 *      Python's bytes exactly, which is the part the float rule can break
 *   3. the chain links verify in order from the genesis hash
 *
 * Then it tamper-tests: flip one character and every check must fail. A
 * verifier that has never rejected anything has demonstrated nothing.
 *
 *   node web/test_verify.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  GENESIS, recanonicalize, sha256Hex, verifyRecord, verifyChain,
} from "./verify.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const doc = JSON.parse(readFileSync(join(HERE, "data", "corpus.json"), "utf8"));

let failures = 0;
const check = (ok, label, detail = "") => {
  if (!ok) failures++;
  console.log(`  ${ok ? "ok  " : "FAIL"}  ${label}${detail ? "  " + detail : ""}`);
};

console.log(`JS VERIFIER vs PYTHON, ${doc.n_items} records`);

// 1 + 2, per record
let hashOk = 0, canonOk = 0, showOk = 0;
for (const it of doc.items) {
  const r = await verifyRecord(it);
  if (r.hashMatches) hashOk++;
  if (r.selfConsistent) canonOk++;
  if (r.saysWhatWeShow) showOk++;
  if (!r.ok) {
    console.log(`  FAIL  ${it.scenario_id}/${it.kind}`,
      JSON.stringify({ hash: r.hashMatches, canon: r.selfConsistent,
                       shows: r.saysWhatWeShow, err: r.canonError }));
  }
}
check(hashOk === doc.n_items, "sha256(canonical_payload) == proof_hash",
      `${hashOk}/${doc.n_items}`);
check(canonOk === doc.n_items, "re-canonicalised bytes identical to Python's",
      `${canonOk}/${doc.n_items}`);
check(showOk === doc.n_items, "payload states what the record displays",
      `${showOk}/${doc.n_items}`);

// 3, the chain
const chain = await verifyChain(doc.items);
check(chain.allOk, "every proof and every prev_hash link verifies");
check(chain.head === doc.chain_head, "chain head matches the export",
      chain.head.slice(0, 16));
check(doc.items[0].proof.prev_hash === GENESIS, "first proof chains to genesis");

// 4, the verifier must be able to REJECT
console.log("TAMPER TESTS, each must be rejected");
const victim = doc.items.find((x) => x.decision.action === "remove") || doc.items[0];

const flipped = structuredClone(victim);
flipped.canonical_payload = flipped.canonical_payload.replace('"action":"remove"', '"action":"allow"');
check(flipped.canonical_payload !== victim.canonical_payload, "  (tamper applied)");
let r = await verifyRecord(flipped);
check(!r.hashMatches, "changing the decision breaks the hash");

const nudged = structuredClone(victim);
// move one digit in the first float of the moral vector
nudged.canonical_payload = nudged.canonical_payload.replace(/("moral_vector":\[)(-?\d)/, "$1" + "9");
r = await verifyRecord(nudged);
check(!r.hashMatches, "changing one digit of the moral vector breaks the hash");

const relinked = structuredClone(doc.items);
relinked[3] = structuredClone(relinked[3]);
relinked[3].proof.prev_hash = GENESIS;          // splice the chain
const badChain = await verifyChain(relinked);
check(!badChain.allOk, "a broken prev_hash link fails the chain");

const reordered = [doc.items[1], doc.items[0], ...doc.items.slice(2)];
const badOrder = await verifyChain(reordered);
check(!badOrder.allOk, "reordering two records fails the chain");

// 5, the float rule specifically, because it is the one that silently drifts
console.log("FORMAT RULES");
check(recanonicalize('{"a":0.0,"b":1}') === '{"a":0.0,"b":1}',
      "float keeps its decimal point, int does not");
check(recanonicalize('{"z":1,"a":2}') === '{"a":2,"z":1}', "keys are sorted");
check(recanonicalize('{"s":"café"}') === '{"s":"café"}', "non-ASCII stays literal");
check(await sha256Hex("") ===
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "sha256 of the empty string is the known vector");

// 6, the data contract the page renders against. The realistic failure for a
// UI is not a bad hash, it is a renderer reaching a field that is not there.
console.log("SITE DATA CONTRACT");
const need = (o, path) => path.split(".").reduce((x, k) => (x == null ? x : x[k]), o);
let missing = [], badAction = [], noTamperAnchor = [];
const ACTIONS = new Set(["allow", "escalate", "remove"]);
for (const it of doc.items) {
  for (const f of ["text", "text_sha256", "scores", "validation", "decision",
                   "canonical_payload", "proof.proof_hash", "proof.prev_hash",
                   "decision.action", "decision.satisfaction", "decision.rationale",
                   "decision.requires_human_review", "decision.moral_residue"]) {
    if (need(it, f) === undefined) missing.push(`${it.scenario_id}/${it.kind}:${f}`);
  }
  if (!ACTIONS.has(it.decision.action)) badAction.push(it.decision.action);
  if (!Array.isArray(it.decision.moral_residue)) missing.push(`${it.scenario_id}:residue not array`);
  if (it.decision.contraction !== null && typeof it.decision.contraction !== "object")
    missing.push(`${it.scenario_id}:contraction`);
  for (const [dim, s] of Object.entries(it.scores))
    if (typeof s.value !== "number" || typeof s.confidence !== "number")
      missing.push(`${it.scenario_id}:${dim}`);
  for (const v of it.validation)
    if (typeof v.dimension !== "string" || typeof v.validated !== "boolean")
      missing.push(`${it.scenario_id}:validation`);
  // the tamper button edits this exact substring
  if (!it.canonical_payload.includes(`"action":"${it.decision.action}"`))
    noTamperAnchor.push(`${it.scenario_id}/${it.kind}`);
}
check(missing.length === 0, "every item has every field the page renders",
      missing.slice(0, 3).join(" "));
check(badAction.length === 0, "every action is allow/escalate/remove",
      [...new Set(badAction)].join(","));
check(noTamperAnchor.length === 0, "the tamper control finds its anchor in every payload",
      noTamperAnchor.slice(0, 3).join(" "));
const dims = new Set(doc.items.flatMap((i) => Object.keys(i.scores)));
check(dims.size === doc.dimensions.length, "dimension set is stable across items",
      `${dims.size}`);
const validatedCounts = new Set(doc.items.map(
  (i) => i.validation.filter((v) => v.validated).length));
check(validatedCounts.size === 1, "validated-axis count is the same for every item",
      [...validatedCounts].join(","));
check([...validatedCounts][0] === 9, "nine of ten axes validated, as disclosed");

console.log(failures === 0
  ? "\nALL PASS. The browser verifier agrees with Python and rejects tampering."
  : `\n${failures} FAILURE(S).`);
process.exit(failures === 0 ? 0 : 1);
