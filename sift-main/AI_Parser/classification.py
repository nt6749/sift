import os
import pdfplumber
from dotenv import load_dotenv
from google import genai

base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, "key.env"))

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)


def classify_policy_document(pdf_path: str, preview_pages: int = 2) -> str:
    """
    Returns only:
      - 'single_drug'
      - 'multi_drug'

    Uses first 1-2 pages only.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texts = []
            for i in range(min(preview_pages, len(pdf.pages))):
                texts.append(pdf.pages[i].extract_text() or "")
            preview_text = "\n\n".join(texts)[:4000]

        prompt = f"""
You are classifying a medical coverage document.

Return ONLY one of these two labels:
- single_drug
- multi_drug

Use these rules:
- single_drug = policy mainly focused on one medication or one product family
- multi_drug = formulary, policy covering multiple drugs, biosimilars, therapeutic class, or large list

Document preview:
{preview_text}
""".strip()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        label = (response.text or "").strip().lower()
        if "multi_drug" in label:
            return "multi_drug"
        return "single_drug"

    except Exception as e:
        print(f"Classification failed for {pdf_path}: {e}")
        return "single_drug"