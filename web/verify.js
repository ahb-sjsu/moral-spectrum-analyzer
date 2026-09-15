/*
 * verify.js — an INDEPENDENT re-implementation of the audit check.
 *
 * The governance claim is that a Moral Spectrum Analyzer decision record is a
 * documented, hash-chained artifact that any third party can re-verify WITHOUT
 * our code. This file is the evidence for that sentence. It shares nothing with
 * the Python implementation except the written format rules, it runs in a plain
 * browser with no install and no network, and `test_verify.mjs` checks it
 * reproduces Python byte for byte on every exported record.
 *
 * THE FORMAT, in full. There is nothing else to know.
 *
 *   proof_hash = SHA-256( canonical_payload as UTF-8 )
 *
 *   canonical_payload is JSON over the proof's fields EXCEPT proof_hash, with
 *     - object keys sorted by code unit
 *     - no whitespace: separators are "," and ":"
 *     - non-ASCII written literally, never \u-escaped
 *     - numbers written as Python's repr, so A FLOAT ALWAYS CARRIES A DECIMAL
 *       POINT (0.0, never 0) and an int never does
 *     - the optional field `equivalence_class` present only when set
 *
 *   Chaining: each proof's prev_hash is the previous proof_hash, the first is
 *   64 zeros. A chain verifies when every proof verifies and every link matches.
 *
 * The float rule is the only subtle part, and it is why this file parses the
 * canonical string with its own tokenizer rather than using JSON.parse:
 * JavaScript cannot tell 0.0 from 0 after parsing, so the original literal is
 * carried through and re-emitted unchanged.
 */

export const GENESIS = "0".repeat(64);

/* ---------------------------------------------------------------- numbers */

/** A number that remembers exactly how it was written. */
export class Literal {
  constructor(text) { this.text = text; this.n = Number(text); }
  valueOf() { return this.n; }
  toString() { return this.text; }
}

/** Format a plain JS number the way Python's repr would. */
export function pyNumber(x) {
  if (!Number.isFinite(x)) throw new Error("non-finite numbers are not JSON");
  if (Number.isInteger(x) && Object.is(x, Math.trunc(x))) {
    // Ambiguous on its own: an int prints bare, a float keeps ".0". Callers
    // that care pass a Literal instead, which is why this is only a fallback.
    return String(x);
  }
  return String(x);
}

/* ------------------------------------------------- literal-aware JSON read */

/** Parse JSON, keeping each number's original text. Strict, no extensions. */
export function parseKeepingLiterals(text) {
  let i = 0;
  const err = (m) => { throw new SyntaxError(m + " at " + i); };
  const ws = () => { while (i < text.length && " \t\n\r".includes(text[i])) i++; };

  function value() {
    ws();
    const c = text[i];
    if (c === "{") return object();
    if (c === "[") return array();
    if (c === '"') return string();
    if (c === "t") { expect("true"); return true; }
    if (c === "f") { expect("false"); return false; }
    if (c === "n") { expect("null"); return null; }
    return number();
  }
  function expect(word) {
    if (text.substr(i, word.length) !== word) err("expected " + word);
    i += word.length;
  }
  function object() {
    const out = new Map();
    i++; ws();
    if (text[i] === "}") { i++; return out; }
    for (;;) {
      ws();
      if (text[i] !== '"') err("expected key");
      const k = string();
      ws();
      if (text[i] !== ":") err("expected ':'");
      i++;
      out.set(k, value());
      ws();
      if (text[i] === ",") { i++; continue; }
      if (text[i] === "}") { i++; return out; }
      err("expected ',' or '}'");
    }
  }
  function array() {
    const out = [];
    i++; ws();
    if (text[i] === "]") { i++; return out; }
    for (;;) {
      out.push(value());
      ws();
      if (text[i] === ",") { i++; continue; }
      if (text[i] === "]") { i++; return out; }
      err("expected ',' or ']'");
    }
  }
  function string() {
    i++;
    let out = "";
    for (;;) {
      const c = text[i];
      if (c === undefined) err("unterminated string");
      if (c === '"') { i++; return out; }
      if (c === "\\") {
        i++;
        const e = text[i++];
        if (e === "u") { out += String.fromCharCode(parseInt(text.substr(i, 4), 16)); i += 4; }
        else if (e === "n") out += "\n";
        else if (e === "t") out += "\t";
        else if (e === "r") out += "\r";
        else if (e === "b") out += "\b";
        else if (e === "f") out += "\f";
        else out += e;                       // " \ /
        continue;
      }
      out += c; i++;
    }
  }
  function number() {
    const start = i;
    if (text[i] === "-") i++;
    while (i < text.length && "0123456789.eE+-".includes(text[i])) i++;
    const lit = text.slice(start, i);
    if (!/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(lit)) err("bad number " + lit);
    return new Literal(lit);
  }

  const v = value();
  ws();
  if (i !== text.length) err("trailing data");
  return v;
}

/* ------------------------------------------------------------- write back */

/** Python's json.dumps string escaping with ensure_ascii=False. */
function pyString(s) {
  let out = '"';
  for (const ch of s) {
    const c = ch.codePointAt(0);
    if (ch === '"') out += '\\"';
    else if (ch === "\\") out += "\\\\";
    else if (ch === "\n") out += "\\n";
    else if (ch === "\t") out += "\\t";
    else if (ch === "\r") out += "\\r";
    else if (ch === "\b") out += "\\b";
    else if (ch === "\f") out += "\\f";
    else if (c < 0x20) out += "\\u" + c.toString(16).padStart(4, "0");
    else out += ch;                          // non-ASCII stays literal
  }
  return out + '"';
}

/** Re-emit a parsed value in the canonical form. Maps keep insertion order, so
 *  keys are sorted here rather than assumed. */
export function canonicalize(v) {
  if (v === null) return "null";
  if (v === true) return "true";
  if (v === false) return "false";
  if (v instanceof Literal) return v.text;
  if (typeof v === "number") return pyNumber(v);
  if (typeof v === "string") return pyString(v);
  if (Array.isArray(v)) return "[" + v.map(canonicalize).join(",") + "]";
  if (v instanceof Map) {
    const keys = [...v.keys()].sort();
    return "{" + keys.map((k) => pyString(k) + ":" + canonicalize(v.get(k))).join(",") + "}";
  }
  if (typeof v === "object") {
    const keys = Object.keys(v).sort();
    return "{" + keys.map((k) => pyString(k) + ":" + canonicalize(v[k])).join(",") + "}";
  }
  throw new Error("cannot canonicalize " + typeof v);
}

/** Round-trip a canonical string through our own parser and writer.
 *  Equal output means this implementation agrees with the one that made it. */
export function recanonicalize(canonicalText) {
  return canonicalize(parseKeepingLiterals(canonicalText));
}

/* ------------------------------------------------------------------ sha256 */

const subtle = (globalThis.crypto && globalThis.crypto.subtle) || null;

export async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  if (!subtle) throw new Error("no WebCrypto; run over http(s) or in node >= 20");
  const digest = await subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

/* ------------------------------------------------------------------ verify */

/**
 * Verify one exported record.
 * Returns every sub-check separately, because "it verified" is worth less than
 * knowing which of the three things held.
 */
export async function verifyRecord(item) {
  const payload = item.canonical_payload;
  const computed = await sha256Hex(payload);
  const claimed = item.proof.proof_hash;

  let selfConsistent = null, canonError = null;
  try {
    selfConsistent = recanonicalize(payload) === payload;
  } catch (e) {
    canonError = String(e.message || e);
  }

  // does the payload actually say what the page is showing?
  let saysWhatWeShow = null;
  try {
    const parsed = JSON.parse(payload);
    saysWhatWeShow =
      parsed.decision.action === item.decision.action &&
      parsed.source_text_sha256 === item.text_sha256 &&
      parsed.perception_backend === item.proof.perception_backend;
  } catch (e) {
    saysWhatWeShow = false;
  }

  return {
    hashMatches: computed === claimed,
    computed,
    claimed,
    selfConsistent,
    canonError,
    saysWhatWeShow,
    ok: computed === claimed && selfConsistent === true && saysWhatWeShow === true,
  };
}

/** Verify the whole chain: every proof, and every prev_hash link, in order. */
export async function verifyChain(items) {
  let prev = GENESIS;
  const rows = [];
  let allOk = true;
  for (const it of items) {
    const r = await verifyRecord(it);
    const linkOk = it.proof.prev_hash === prev;
    prev = it.proof.proof_hash;
    const ok = r.ok && linkOk;
    allOk = allOk && ok;
    rows.push({ id: it.scenario_id, kind: it.kind, linkOk, ...r, ok });
  }
  return { allOk, head: prev, rows };
}

/** Hash arbitrary text, so a pasted string can be looked up by SHA-256. */
export async function textSha256(text) { return sha256Hex(text); }
