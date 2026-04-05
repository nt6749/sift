import os
import re
import json
import logging
import time
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import google.generativeai as genai
import pdfplumber
import requests
import urllib

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ----------------------------
# Config
# ----------------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
REQUEST_HEADERS = {"User-Agent": USER_AGENT}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
def search_duckduckgo(query: str, max_results: int = 10) -> List[str]:
    """
    Search DuckDuckGo HTML endpoint and return result links.
    """
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

        # dedupe while preserving order
        deduped = list(dict.fromkeys(links))
        return deduped[:max_results]

    except Exception as e:
        logging.error(f"Search failed for query '{query}': {e}")
        return []


def domain_matches(url: str, allowed_domains: List[str]) -> bool:
    """
    Check whether a URL belongs to one of the allowed domains.
    """
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
    """
    Run multiple templated queries for a drug and return filtered results.
    """
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
# 2. Download / fetch content
# ----------------------------
def safe_filename_from_url(url: str) -> str:
    """
    Build a safe local filename from URL.
    """
    parsed = urllib.parse.urlparse(url)
    base = os.path.basename(parsed.path.strip("/")) or f"doc_{int(time.time())}"
    base = re.sub(r"[^\w\-_\.]", "_", base)
    return base


def download_file(url: str, output_dir: str) -> Optional[str]:
    """
    Download a file from URL. Adds .pdf if content-type says PDF.
    """
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
        elif not os.path.splitext(filename)[1]:
            if "html" in content_type:
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
# 3. Text extraction
# ----------------------------
def extract_pages_from_pdf(filepath: str) -> List[Dict[str, Any]]:
    pages = []

    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({
                    "page_number": page_num,
                    "text": text
                })

    return pages

def contains_any(text: str, keywords: List[str]) -> bool:
    text_lower = (text or "").lower()
    return any(k.lower() in text_lower for k in keywords)


def build_extraction_text(
    doc: Dict[str, Any],
    drug_keywords: List[str],
    max_pages: int = 12
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

    # Always include first page for metadata
    add_page(pages[0])

    if classification == "single_drug_simple":
        for page in pages[1:]:
            text = page.get("text", "")
            if contains_any(text, SECTION_KEYWORDS):
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
        # fallback
        for page in pages[1:4]:
            add_page(page)

    # limit size
    selected = selected[:max_pages]

    blocks = []
    for i, page in enumerate(selected):
        page_num = page.get("page_number", "?")
        text = page.get("text", "")

        label = "METADATA PAGE" if i == 0 else "RELEVANT PAGE"
        blocks.append(f"=== {label} {page_num} ===\n{text}")

    return "\n\n".join(blocks)

