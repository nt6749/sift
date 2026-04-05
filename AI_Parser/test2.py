import os
import re
import json
import logging
import time
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from google import genai
import pdfplumber
import requests
import urllib
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
load_dotenv("key.env")

# ----------------------------
# Config
# ----------------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
REQUEST_HEADERS = {"User-Agent": USER_AGENT}

SECTION_KEYWORDS = [
    "policy",
    "criteria",
    "coverage",
    "covered",
    "indication",
    "diagnosis",
    "prior authorization",
    "step therapy",
    "site of care",
    "quantity limit",
    "dosing",
    "dose",
    "frequency",
    "medically necessary",
    "authorization"
]

# ----------------------------
# Gemini setup
# ----------------------------
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"

GENERAL_EXTRACTION_PROMPT = """
You are an information extraction agent.

Your task is to read the provided medical policy text and extract the relevant structured information exactly in the JSON format below.

Rules:
1. Output valid JSON only.
2. Do not include markdown, explanations, comments, or extra text.
3. Do not add fields that are not in the schema.
4. Preserve the exact field names and nesting.
5. If a value is not stated in the text, use null.
6. If a boolean-style coverage requirement is unclear or not explicitly stated, use "unknown" where allowed.
7. For arrays, return [] if no items are found.
8. Normalize dates to YYYY-MM-DD when possible; otherwise use null.
9. Do not guess. Only extract what is supported by the text.
10. If multiple covered indications, PA criteria, step therapy steps, site-of-care restrictions, or dosing/quantity limits are present, include all of them.
11. For payer_name, extract the payer or health plan name from the text if present; otherwise use null.
12. For access_status.status, only use one of: "preferred", "non-preferred", "restricted", "unknown".
13. For coverage.covered, prior_authorization.required, and step_therapy.required, only use one of: true, false, "unknown".
14. If the text mentions both brand and generic drug names, place them in their correct fields. If only one is explicitly available, fill that field and use null for the other.
15. For covered_indications, extract each condition separately. Put any approval conditions tied to that indication into the "criteria" field.
16. For prior_authorization.criteria, include each requirement as a separate string.
17. For step_therapy.steps, preserve the order if the text implies an order. Use step_number starting at 1.
18. For dosing_and_quantity_limits.limits.type, only use one of: "dose", "frequency", "quantity".
19. For site_of_care.restrictions, include each restriction as a separate string.
20. For policy_metadata fields, extract only if explicitly available in the text.

Return exactly this JSON structure:

{
  "payer_name": null,
  "drug_name": {
    "brand": null,
    "generic": null
  },
  "drug_category": null,
  "access_status": {
    "status": "unknown",
    "preferred_count_in_category": null,
    "notes": null
  },
  "coverage": {
    "covered": "unknown",
    "covered_indications": []
  },
  "prior_authorization": {
    "required": "unknown",
    "criteria": []
  },
  "step_therapy": {
    "required": "unknown",
    "steps": []
  },
  "site_of_care": {
    "restrictions": [],
    "notes": null
  },
  "dosing_and_quantity_limits": {
    "limits": []
  },
  "policy_metadata": {
    "effective_date": null,
    "policy_name": null,
    "policy_id": null,
    "source_file": null
  }
}

Expected object formats inside arrays:

covered_indications item:
{
  "condition": "string",
  "criteria": "string or null"
}

step_therapy.steps item:
{
  "step_number": 1,
  "required_drug_or_class": "string",
  "notes": "string or null"
}

dosing_and_quantity_limits.limits item:
{
  "type": "dose",
  "value": "string",
  "notes": "string or null"
}

Now extract the information from the provided text and return only the completed JSON.
""".strip()

# ----------------------------
# 1. Search
# ----------------------------
def search_duckduckgo(query: str, max_results: int = 10) -> List[str]:
    url = "https://html.duckduckgo.com/html/"

    try:
        response = requests.post(
            url,
            data={"q": query},
            headers=REQUEST_HEADERS,
            timeout=20
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = []

        for a in soup.find_all("a", class_="result__a"):
            href = a.get("href")
            if not href:
                continue

            if href.startswith("/l/?uddg="):
                decoded_url = urllib.parse.unquote(
                    href.split("uddg=")[1].split("&rut=")[0]
                )
                links.append(decoded_url)
            else:
                links.append(href)

        return list(dict.fromkeys(links))[:max_results]

    except Exception as e:
        logging.error(f"Search failed for query '{query}': {e}")
        return []


def domain_matches(url: str, allowed_domains: List[str]) -> bool:
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return any(
            netloc == domain.lower() or netloc.endswith("." + domain.lower())
            for domain in allowed_domains
        )
    except Exception:
        return False


def search_queries_for_drug(
    drug_name: str,
    query_templates: List[str],
    allowed_domains: Optional[List[str]] = None,
    max_results_per_query: int = 10
) -> List[Dict[str, str]]:
    all_results = []
    seen = set()

    for template in query_templates:
        query = template.format(drug=drug_name)
        logging.info(f"Searching: {query}")

        urls = search_duckduckgo(query, max_results=max_results_per_query)

        for url in urls:
            if allowed_domains and not domain_matches(url, allowed_domains):
                continue

            if url not in seen:
                seen.add(url)
                all_results.append({
                    "query": query,
                    "url": url
                })

    return all_results


# ----------------------------
# 2. Download
# ----------------------------
def safe_filename_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    base = os.path.basename(parsed.path.strip("/")) or f"doc_{int(time.time())}"
    base = re.sub(r"[^\w\-_\.]", "_", base)
    return base


def download_file(url: str, output_dir: str) -> Optional[str]:
    try:
        response = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=30,
            stream=True,
            allow_redirects=True
        )
        response.raise_for_status()

        os.makedirs(output_dir, exist_ok=True)

        filename = safe_filename_from_url(url)
        content_type = response.headers.get("Content-Type", "").lower()

        if "pdf" in content_type and not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        elif not os.path.splitext(filename)[1] and "html" in content_type:
            filename += ".html"

        filepath = os.path.join(output_dir, filename)

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return filepath

    except Exception as e:
        logging.error(f"Download failed for {url}: {e}")
        return None


# ----------------------------
# 3. PDF extraction
# ----------------------------
def extract_pages_from_pdf(filepath: str) -> List[Dict[str, Any]]:
    pages = []

    try:
        with pdfplumber.open(filepath) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({
                        "page_number": page_num,
                        "text": text
                    })
    except Exception as e:
        logging.error(f"PDF extraction failed for {filepath}: {e}")

    return pages


# ----------------------------
# 4. Text selection
# ----------------------------
def contains_any(text: str, keywords: List[str]) -> bool:
    text_lower = (text or "").lower()
    return any(k.lower() in text_lower for k in keywords)


def build_extraction_text(
    doc: Dict[str, Any],
    drug_keywords: List[str],
    max_pages: int = 20
) -> str:
    classification = doc.get("classification", "unknown")
    pages = doc.get("pages", [])

    if not pages:
        return ""

    selected = []
    selected_page_nums = set()

    def add_page(page):
        pnum = page.get("page_number")
        if pnum not in selected_page_nums:
            selected.append(page)
            selected_page_nums.add(pnum)

    # Always include first page
    add_page(pages[0])

    if classification == "single_drug_simple":
        for page in pages[1:]:
            text = page.get("text", "")
            if contains_any(text, SECTION_KEYWORDS) or contains_any(text, drug_keywords):
                add_page(page)

    elif classification == "single_drug_mixed":
        for page in pages[1:]:
            text = page.get("text", "")
            if contains_any(text, SECTION_KEYWORDS) or contains_any(text, drug_keywords):
                add_page(page)

    elif classification == "multi_drug_large":
        hit_indices = []
        for i, page in enumerate(pages):
            text = page.get("text", "")
            if contains_any(text, drug_keywords):
                hit_indices.append(i)

        expanded = set()
        for i in hit_indices:
            for j in range(max(0, i - 1), min(len(pages), i + 2)):
                expanded.add(j)

        for idx in sorted(expanded):
            add_page(pages[idx])

    else:
        for page in pages[1:4]:
            add_page(page)

    selected = selected[:max_pages]

    print("Selected pages:", [p["page_number"] for p in selected])

    blocks = []
    for i, page in enumerate(selected):
        page_num = page.get("page_number", "?")
        text = page.get("text", "")

        label = "METADATA PAGE" if i == 0 else "RELEVANT PAGE"
        blocks.append(f"=== {label} {page_num} ===\n{text}")

    return "\n\n".join(blocks)


# ----------------------------
# 5. Gemini call
# ----------------------------
def run_extraction(model_name: str, prepared_text: str) -> Dict[str, Any]:
    prompt = GENERAL_EXTRACTION_PROMPT + "\n\nPolicy text:\n" + prepared_text
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    raw = response.text.strip()

    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)

# ----------------------------
# 6. Small manual test
# ----------------------------
if __name__ == "__main__":
    drug_name = "Rituximab"
    drug_keywords = ["rituximab", "rituxan"]

    query_templates = [
        'https://fm.formularynavigator.com/FBO/208/MDL_EmployerGroupMyPriority_2026.pdf'
    ]

    results = search_queries_for_drug(
        drug_name=drug_name,
        query_templates=query_templates,
        allowed_domains=None,
        max_results_per_query=5
    )

    if not results:
        print("No search results found.")
        raise SystemExit

    pdf_results = [r for r in results if r["url"].lower().endswith(".pdf")]
    if not pdf_results:
        print("No PDF results found.")
        raise SystemExit

    test_url = pdf_results[0]["url"]
    print("Testing URL:", test_url)

    filepath = download_file(test_url, "test_docs")
    if not filepath:
        print("Download failed.")
        raise SystemExit

    pages = extract_pages_from_pdf(filepath)
    if not pages:
        print("No PDF text extracted.")
        raise SystemExit

    doc1 = {
        "source_file": filepath,
        "classification": "multi_drug_large",
        "pages": pages
    }

    prepared_text = build_extraction_text(doc1, drug_keywords, max_pages=20) + f"EXTRACT DATA FOR '{drug_name}' ONLY.\n\n"

    print("\n===== PREPARED TEXT PREVIEW =====\n")
    print(prepared_text[:3000])

    result = run_extraction(MODEL_NAME, prepared_text)

    output_file = "medical_policy_extractions.jsonl"

    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"\nSaved result to {output_file}")

    print("\n===== EXTRACTION RESULT =====\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))