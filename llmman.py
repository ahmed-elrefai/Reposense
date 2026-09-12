import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv("./secrets/.env")

REQUIRED_KEYS = {
    "status", "repo", "goal", "inputs", "outputs",
    "how_it_works", "stack", "confidence", "gaps", "sources"
}


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    # allow accidental fences
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def generate_report(prompt: str, model: str = "openai/gpt-oss-120b") -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing")

    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Return the JSON report now."},
        ],
        temperature=0.2,
    )
    content = resp.choices[0].message.content
    data = _extract_json(content)

    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"report missing keys: {sorted(missing)}")

    return data