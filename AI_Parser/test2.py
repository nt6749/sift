import os
import re
import json
import logging
import time
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import pdfplumber
import requests
import urllib

from classification import classify_policy_document
from parser import extract_structured_json

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
# 1. Search
# ----------------------------
def search_duckduckgo(query: str, max_results: int = 10, retries: int = 3) -> List[str]:
    url = "https://html.duckduckgo.com/html/"

    for attempt in range(retries):
        try:
            # Rotate user agents to avoid blocks
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
                "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            ]
            headers = {"User-Agent": user_agents[attempt % len(user_agents)]}

            response = requests.post(
                url,
                data={"q": query},
                headers=headers,
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

            results = list(dict.fromkeys(links))[:max_results]

            if results:
                return results

            # Got a response but no links — likely a block page
            logging.warning(f"DDG returned no links on attempt {attempt + 1}, waiting before retry...")
            time.sleep(5 * (attempt + 1))  # 5s, 10s, 15s backoff

        except Exception as e:
            logging.error(f"Search failed (attempt {attempt + 1}): {e}")
            time.sleep(5 * (attempt + 1))

    logging.error(f"All DDG retries failed for: {query}")
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
# 2.5 Pick one file per source bucket
# ----------------------------
def looks_like_pdf(url: str) -> bool:
    return ".pdf" in url.lower()


def pick_top_sources(results: List[Dict[str, str]], wanted_sources: List[str]) -> List[str]:
    """
    Pick the first PDF result for each requested source.
    No domain checker. Source is decided only by the query group.
    """
    chosen = []
    picked = set()

    for source in wanted_sources:
        for r in results:
            if r["source"] != source:
                continue

            url = r["url"]

            if source == "mdl":
                chosen.append(url)
                picked.add(source)
                break

            if looks_like_pdf(url):
                chosen.append(url)
                picked.add(source)
                break

    return chosen


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
    max_pages: int = 20,
    multi_window: int = 2
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

    add_page(pages[0])

    if classification == "single_drug":
        for page in pages[1:]:
            text = page.get("text", "")
            if contains_any(text, SECTION_KEYWORDS) or contains_any(text, drug_keywords):
                add_page(page)

    elif classification == "multi_drug":
        hit_indices = []
        for i, page in enumerate(pages):
            text = page.get("text", "")
            if contains_any(text, drug_keywords):
                hit_indices.append(i)

        expanded = set()
        for i in hit_indices:
            for j in range(max(0, i - 1), min(len(pages), i + multi_window + 1)):
                expanded.add(j)

        for idx in sorted(expanded):
            add_page(pages[idx])

    else:
        for page in pages[1:4]:
            add_page(page)

    selected = selected[:max_pages]

    logging.info(f"Selected pages: {[p['page_number'] for p in selected]}")

    blocks = []
    for i, page in enumerate(selected):
        page_num = page.get("page_number", "?")
        text = page.get("text", "")
        label = "METADATA PAGE" if i == 0 else "RELEVANT PAGE"
        blocks.append(f"=== {label} {page_num} ===\n{text}")

    return "\n\n".join(blocks)


# ----------------------------
# 5. Processing helper
# ----------------------------
def process_one_file(
    filepath: str,
    drug_name: str,
    drug_keywords: List[str]
) -> Dict[str, Any]:
    pages = extract_pages_from_pdf(filepath)
    if not pages:
        raise ValueError(f"No PDF text extracted from {filepath}")

    classification = classify_policy_document(filepath)
    logging.info(f"Classification for {os.path.basename(filepath)}: {classification}")

    doc = {
        "source_file": filepath,
        "classification": classification,
        "pages": pages
    }

    prepared_text = (
        build_extraction_text(doc, drug_keywords, max_pages=20, multi_window=2)
        + f"\n\nEXTRACT DATA FOR '{drug_name}' ONLY.\n"
    )

    logging.info("===== PREPARED TEXT PREVIEW =====")
    logging.info(prepared_text[:2000])

    result = extract_structured_json(
        prepared_text=prepared_text,
        target_drug=drug_name,
        source_file=filepath
    )

    return result


# ----------------------------
# 6. Search + limited processing (FIXED)
# ----------------------------
def search_and_process_limited(
    drug_name: str,
    drug_keywords: List[str],
    query_templates: List[str],
    output_dir: str = "test_docs",
    output_jsonl: str = "medical_policy_extractions.jsonl"
) -> List[Dict[str, Any]]:

    urls_to_download = []

    for template in query_templates:
        if template.startswith("http"):
            logging.info(f"Direct URL: {template}")
            urls_to_download.append(template)
        else:
            query = template.format(drug=drug_name)
            logging.info(f"DDG search: {query}")

            # Delay between queries to avoid rate limiting
            time.sleep(4)

            search_results = search_duckduckgo(query, max_results=5)

            if not search_results:
                logging.warning(f"No results for '{query}'")
            else:
                # Filter to PDFs only for text queries
                pdf_urls = [u for u in search_results if u.lower().endswith(".pdf")]
                if pdf_urls:
                    urls_to_download.append(pdf_urls[0])
                else:
                    logging.warning(f"No PDFs found in results for '{query}', skipping")

    urls_to_download = list(dict.fromkeys(urls_to_download))

    if not urls_to_download:
        logging.error("No URLs to process.")
        return []

    logging.info(f"Downloading {len(urls_to_download)} URLs...")

    downloaded_files = []
    for url in urls_to_download:
        filepath = download_file(url, output_dir)
        if filepath:
            # Sanity check — make sure it's actually a PDF
            with open(filepath, "rb") as f:
                header = f.read(5)
            if not header.startswith(b"%PDF-"):
                logging.warning(f"Not a PDF, skipping: {url}")
                os.remove(filepath)
                continue
            downloaded_files.append(filepath)

    extracted_results = []
    for filepath in downloaded_files:
        try:
            result = process_one_file(filepath, drug_name, drug_keywords)
            extracted_results.append(result)
            with open(output_jsonl, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        except Exception as e:
            logging.error(f"Extraction failed for {filepath}: {e}")

    return extracted_results

# ----------------------------
# PLACE_HOLDER (add emblem health)
# ----------------------------


# ----------------------------
# 7. Main
# ----------------------------
def parserA(drug: str, drug_keywords: list[str]):
    # name of the drug and other name in the family
    drug_name = drug
    drug_keywords = drug_keywords

    # work with 3 for now may change for the future 
    query_templates = [
        'https://fm.formularynavigator.com/FBO/208/MDL_EmployerGroupMyPriority_2026.pdf',
        'Cigna Drug and Biologic Coverage Policy {drug} pdf',
        'UnitedHealthcare Commercial Medical & Drug Policies {drug} pdf'
    ]

    # search the web
    results = search_and_process_limited(
        drug_name=drug_name,
        drug_keywords=drug_keywords,
        query_templates=query_templates,
        output_dir="test_docs",
        output_jsonl="medical_policy_extractions.jsonl"
    )

    # log checker
    # print(f"\nSaved {len(results)} records to medical_policy_extractions.jsonl")