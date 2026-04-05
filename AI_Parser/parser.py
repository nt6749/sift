import json
import os
import re
from dotenv import load_dotenv
from google import genai

base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, "key.env"))

API_KEY = os.getenv("GEMINI_API_KEY")
PROMPT_FILE = os.path.join(base_dir, "prompt.txt")

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"


def load_prompt() -> str:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def clean_json_text(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def extract_structured_json(
    prepared_text: str,
    target_drug: str,
    source_file: str | None = None
) -> dict:
    """
    Final extraction step.
    The parser is always the main AI.
    """
    base_prompt = load_prompt()

    final_prompt = f"""
{base_prompt}

Additional extraction rule:
- Extract data for the target drug only: "{target_drug}".
- Ignore other drugs unless they are directly part of step therapy or comparison requirements for the target drug.
- If the document is multi-drug, do not summarize the whole class. Only return the JSON for "{target_drug}".

Policy text:
{prepared_text}
""".strip()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=final_prompt
    )

    raw = clean_json_text(response.text or "")
    data = json.loads(raw)

    if source_file:
        data.setdefault("policy_metadata", {})
        if not data["policy_metadata"].get("source_file"):
            data["policy_metadata"]["source_file"] = os.path.basename(source_file)

    return data