import json, os, time
from openai import OpenAI
c = OpenAI(base_url=os.environ.get("ERISML_LLM_BASE_URL", "https://ellm.nrp-nautilus.io/v1"),
           api_key=os.environ["ERISML_LLM_API_KEY"])
fact = {"type": "object", "additionalProperties": False, "required": ["kind", "subjects", "description", "severity"],
        "properties": {"kind": {"enum": ["harm", "benefit"]}, "subjects": {"type": "array", "items": {"enum": ["margaret"]}},
                       "description": {"type": "string"}, "severity": {"enum": ["minor", "moderate", "grave"]}}}
schema = {"type": "object", "additionalProperties": False, "required": ["chores", "check_in"],
          "properties": {a: {"type": "array", "maxItems": 2, "items": fact} for a in ("chores", "check_in")}}
msg = [{"role": "user", "content": "Margaret fell. For each act (chores, check_in) give its consequences. "
        "Write each fact as a plain sentence string, not an object."}]
for label, rf in (("without schema", None), ("with schema", {"type": "json_schema", "json_schema": {"name": "p", "schema": schema, "strict": True}})):
    t = time.time()
    kw = {"response_format": rf} if rf else {}
    try:
        r = c.chat.completions.create(model=os.environ.get("ERISML_LLM_MODEL", "gpt-oss"), messages=msg, max_tokens=2000, **kw)
        out = r.choices[0].message.content or ""
        print(label, round(time.time() - t, 1), "s finish", r.choices[0].finish_reason, "|", out[:300].replace("\n", " "))
        try:
            obj = json.loads(out); print("   objects:", all(isinstance(f, dict) for v in obj.values() for f in v))
        except Exception as e:
            print("   not JSON:", e)
    except Exception as e:
        print(label, "ERROR", type(e).__name__, str(e)[:300])
