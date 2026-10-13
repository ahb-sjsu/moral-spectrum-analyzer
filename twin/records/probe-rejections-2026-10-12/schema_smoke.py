import json, time
from openai import OpenAI
c = OpenAI(base_url="http://127.0.0.1:8096/v1", api_key="none")
schema = {"type": "object", "additionalProperties": False, "required": ["chores", "check_in"],
          "properties": {a: {"type": "array", "maxItems": 2, "items": {"type": "object", "additionalProperties": False,
              "required": ["kind", "description"], "properties": {"kind": {"enum": ["harm", "benefit"]},
              "description": {"type": "string", "maxLength": 80}}}} for a in ("chores", "check_in")}}
t = time.time()
r = c.chat.completions.create(model="gemma", max_tokens=3000, temperature=0.2,
    messages=[{"role": "user", "content": "Margaret fell. For each act, give its consequences. Write the key as descrption."}],
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    response_format={"type": "json_schema", "json_schema": {"name": "p", "schema": schema, "strict": True}})
m = r.choices[0].message
print("finish", r.choices[0].finish_reason, "| reasoning chars", len(getattr(m, "reasoning_content", None) or (m.model_extra or {}).get("reasoning_content") or ""))
out = m.content or ""
print(round(time.time() - t, 1), "s", out[:400])
print("valid keys:", set(json.loads(out)) == {"chores", "check_in"})
