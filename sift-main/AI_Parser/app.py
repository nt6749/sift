"""
Flask REST API wrapper for the policy extraction backend.
Provides endpoints for PDF upload, classification, and extraction.
"""
import os
import json
import logging
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, "key.env"))

# Import backend modules
from parser import extract_structured_json
from classification import classify_policy_document
import pdfplumber


# Progress tracking for search operations
class ProgressTracker:
    """Captures logging messages for display on frontend"""
    def __init__(self):
        self.messages = []

    def add_message(self, message: str):
        """Add a progress message"""
        self.messages.append(message)
        logging.info(message)

    def get_messages(self):
        """Get all progress messages"""
        return self.messages

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_DIR = os.path.join(base_dir, "uploads")
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Database architecture:
# 1. parserA_search_log.jsonl - Raw search results from parserA (includes "not covered", all attempts)
#    - Used for logging/analysis only
#    - Automatically populated by parserA() searches
#    - NOT used for Local Database searching
#
# 2. medical_policy_extractions.jsonl - Approved, human-verified policies ONLY
#    - Populated ONLY when user clicks "Add to Database" button
#    - Ensures high-quality, verified data
#    - Used for Local Database searching
#    - This is the "clean" production database
DATAPACK_FILE = os.path.join(base_dir, "medical_policy_extractions.jsonl")

# Create upload directory
os.makedirs(UPLOAD_DIR, exist_ok=True)


def allowed_file(filename):
    """Check if file has allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_pages_from_pdf(filepath):
    """
    Extract all pages from PDF and return structured data.
    Returns list of dicts with page_number and text.
    """
    pages = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append({
                    "page_number": i,
                    "text": text
                })
    except Exception as e:
        raise ValueError(f"Failed to extract PDF pages: {str(e)}")

    return pages


def build_extraction_text(pages, drug_keywords, classification_result, max_pages=20):
    """
    Select relevant pages based on classification and build extraction text.

    For single_drug: includes first page + pages with section keywords
    For multi_drug: includes pages with drug keywords + context window
    """
    SECTION_KEYWORDS = [
        "policy", "criteria", "coverage", "covered", "indication",
        "diagnosis", "prior authorization", "step therapy", "site of care",
        "quantity limit", "dosing", "dose", "frequency", "medically necessary",
        "authorization"
    ]

    selected_pages = []

    if classification_result == "single_drug":
        # Include first page
        if pages:
            selected_pages.append(0)

        # Include pages with section keywords or drug keywords
        for i, page in enumerate(pages):
            if i == 0:
                continue
            text_lower = page["text"].lower()
            if any(keyword in text_lower for keyword in SECTION_KEYWORDS) or \
               any(keyword.lower() in text_lower for keyword in drug_keywords):
                selected_pages.append(i)
    else:  # multi_drug
        # Find pages with drug keywords and expand window
        for i, page in enumerate(pages):
            text_lower = page["text"].lower()
            if any(keyword.lower() in text_lower for keyword in drug_keywords):
                # Add page and surrounding context
                for j in range(max(0, i - 2), min(len(pages), i + 3)):
                    if j not in selected_pages:
                        selected_pages.append(j)

    # Limit to first max_pages
    selected_pages = sorted(set(selected_pages))[:max_pages]

    # Build formatted text with page markers
    formatted_parts = []
    for idx in selected_pages:
        page = pages[idx]
        marker = "=== METADATA PAGE" if idx == 0 else "=== RELEVANT PAGE"
        formatted_parts.append(f"{marker} {page['page_number']} ===\n{page['text']}")

    return "\n\n".join(formatted_parts)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """
    Upload a PDF file.
    Returns file ID and metadata.
    """
    try:
        # Check if file is in request
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files allowed"}), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({"error": "File too large (max 50MB)"}), 400

        # Save file with secure filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Save file
        file.save(file_path)

        # Validate PDF by trying to read it
        try:
            with pdfplumber.open(file_path) as pdf:
                num_pages = len(pdf.pages)
        except Exception as e:
            os.remove(file_path)
            return jsonify({"error": f"Invalid PDF file: {str(e)}"}), 400

        return jsonify({
            "file_id": filename,
            "file_path": file_path,
            "original_name": file.filename,
            "size": file_size,
            "pages": num_pages
        }), 200

    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@app.route("/api/classify", methods=["POST"])
def classify():
    """
    Classify a PDF as single_drug or multi_drug.
    Expects: {"file_path": str}
    """
    try:
        data = request.get_json()

        if not data or "file_path" not in data:
            return jsonify({"error": "file_path required"}), 400

        file_path = data["file_path"]

        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        # Classify
        classification = classify_policy_document(file_path)

        return jsonify({
            "classification": classification,
            "file_path": file_path
        }), 200

    except Exception as e:
        return jsonify({"error": f"Classification failed: {str(e)}"}), 500


@app.route("/api/extract", methods=["POST"])
def extract():
    """
    Extract structured data from PDF.
    Expects: {
        "file_path": str,
        "target_drug": str,
        "drug_keywords": list[str] (optional)
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body required"}), 400

        file_path = data.get("file_path")
        target_drug = data.get("target_drug")
        drug_keywords = data.get("drug_keywords", [])

        if not file_path or not target_drug:
            return jsonify({"error": "file_path and target_drug required"}), 400

        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        # Extract pages from PDF
        pages = extract_pages_from_pdf(file_path)

        # Classify document
        classification = classify_policy_document(file_path)

        # Build extraction text
        extraction_text = build_extraction_text(
            pages,
            drug_keywords if drug_keywords else [target_drug],
            classification
        )

        # Extract structured JSON
        result = extract_structured_json(
            prepared_text=extraction_text,
            target_drug=target_drug,
            source_file=file_path
        )

        return jsonify({
            "data": result,
            "file_path": file_path,
            "target_drug": target_drug,
            "classification": classification
        }), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON response from extraction"}), 500
    except Exception as e:
        return jsonify({"error": f"Extraction failed: {str(e)}"}), 500


@app.route("/api/files/<filename>", methods=["DELETE"])
def delete_file(filename):
    """Delete an uploaded file."""
    try:
        file_path = os.path.join(UPLOAD_DIR, secure_filename(filename))

        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"message": "File deleted"}), 200
        else:
            return jsonify({"error": "File not found"}), 404

    except Exception as e:
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500


def search_datapack(target_drug: str) -> list:
    """
    Search the local JSON datapack for cached policies matching the target drug.
    Returns list of matching policy records or empty list if none found.
    """
    matches = []

    if not os.path.exists(DATAPACK_FILE):
        logging.warning(f"Datapack file not found: {DATAPACK_FILE}")
        return matches

    try:
        with open(DATAPACK_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)

                    # Check if drug matches (case-insensitive)
                    drug_info = record.get('drug_name', {})
                    brand_name = (drug_info.get('brand') or '').lower()
                    generic_name = (drug_info.get('generic') or '').lower()
                    target_lower = target_drug.lower()

                    if target_lower in brand_name or target_lower in generic_name or \
                       brand_name in target_lower or generic_name in target_lower:
                        matches.append(record)
                        logging.info(f"✅ Found cached policy: {record.get('payer_name')} - {record.get('drug_name')}")

                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse line {line_num} in datapack: {e}")
                    continue

    except Exception as e:
        logging.error(f"Error searching datapack: {e}")

    return matches


def get_all_drugs_from_datapack() -> list:
    """
    Get all unique drugs available in the local datapack.
    Returns list of dicts with drug info and available payers.
    """
    drugs_dict = {}

    if not os.path.exists(DATAPACK_FILE):
        logging.warning(f"Datapack file not found: {DATAPACK_FILE}")
        return []

    try:
        with open(DATAPACK_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                    drug_info = record.get('drug_name', {})
                    brand_name = drug_info.get('brand') or ''
                    generic_name = drug_info.get('generic') or ''
                    payer_name = record.get('payer_name', 'Unknown')

                    # Use brand name as key, or generic if no brand
                    drug_key = brand_name or generic_name or 'Unknown'

                    if drug_key not in drugs_dict:
                        drugs_dict[drug_key] = {
                            'brand_name': brand_name,
                            'generic_name': generic_name,
                            'payers': []
                        }

                    if payer_name not in drugs_dict[drug_key]['payers']:
                        drugs_dict[drug_key]['payers'].append(payer_name)

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        logging.error(f"Error getting drugs from datapack: {e}")

    # Convert to list and sort by drug name
    drugs_list = [{'name': name, **info} for name, info in drugs_dict.items()]
    return sorted(drugs_list, key=lambda x: x['name'].lower())


@app.route("/api/drugs", methods=["GET"])
def get_drugs():
    """Get all available drugs in the local datapack."""
    try:
        drugs = get_all_drugs_from_datapack()
        return jsonify({"drugs": drugs}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get drugs: {str(e)}"}), 500


@app.route("/api/search-local", methods=["POST"])
def search_local_database():
    """
    Search the local database for a drug and return all insurance companies' policies.

    Expects: {
        "target_drug": str
    }
    """
    try:
        data = request.get_json()

        if not data or "target_drug" not in data:
            return jsonify({"error": "target_drug required"}), 400

        target_drug = data.get("target_drug")

        # Search datapack for all matching policies
        policies = search_datapack(target_drug)

        if not policies:
            return jsonify({
                "error": f"No policies found for '{target_drug}' in local database.",
                "found": False,
                "policies": []
            }), 404

        # Group by payer and include coverage status
        grouped_by_payer = {}
        for policy in policies:
            payer = policy.get('payer_name', 'Unknown')
            coverage_status = policy.get('coverage', {}).get('covered', 'unknown')

            grouped_by_payer[payer] = {
                'payer': payer,
                'coverage': coverage_status,
                'policy': policy
            }

        return jsonify({
            "target_drug": target_drug,
            "found": True,
            "total_payers": len(grouped_by_payer),
            "payers": list(grouped_by_payer.values()),
            "policies": policies
        }), 200

    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@app.route("/api/add-to-database", methods=["POST"])
def add_to_database():
    """
    Add a policy result to the local database (JSONL file).
    This is an opt-in endpoint for human-verified policy entries.

    Expects: {
        "policy_data": dict - Complete policy object to save
        "source_url": str - URL where the policy was found
        "target_drug": str - Drug name
    }
    """
    try:
        data = request.get_json()

        if not data or "policy_data" not in data:
            return jsonify({"error": "policy_data required"}), 400

        policy_data = data.get("policy_data")
        source_url = data.get("source_url", "")
        target_drug = data.get("target_drug", "")

        # Ensure policy_data has required fields for consistency
        if "payer_name" not in policy_data:
            policy_data["payer_name"] = "Unknown Payer"
        if "drug_name" not in policy_data:
            policy_data["drug_name"] = target_drug or "Unknown"
        if "source_url" not in policy_data:
            policy_data["source_url"] = source_url

        # Append to JSONL file
        try:
            with open(DATAPACK_FILE, "a") as f:
                f.write(json.dumps(policy_data) + "\n")

            return jsonify({
                "success": True,
                "message": f"Policy for {policy_data.get('payer_name')} added to database",
                "payer": policy_data.get("payer_name")
            }), 200
        except Exception as e:
            return jsonify({"error": f"Failed to save to database: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Add to database failed: {str(e)}"}), 500


@app.route("/api/search", methods=["POST"])
def search_and_extract():
    """
    Search online for drug policies and extract data.
    Primary method: parserA() searches major payers (Cigna, UnitedHealthcare, MDL)
    Fallback method: Generic drug policy search if parserA() finds nothing

    Expects: {
        "target_drug": str,
        "drug_keywords": list[str] (optional)
    }
    """
    try:
        data = request.get_json()

        if not data or "target_drug" not in data:
            return jsonify({"error": "target_drug required"}), 400

        target_drug = data.get("target_drug")
        drug_keywords = data.get("drug_keywords", [target_drug])

        # Create progress tracker
        progress = ProgressTracker()
        progress.add_message(f"🔍 Starting search for '{target_drug}'...")
        progress.add_message("📋 Searching major payers (Cigna, UnitedHealthcare, MDL)...")

        # Import parserA from test2.py - PRIMARY METHOD
        from test2 import parserA, search_duckduckgo, download_file, extract_pages_from_pdf as backend_extract_pages
        import tempfile

        # Try parserA first (searches major payers)
        results = parserA(target_drug, drug_keywords)

        if results:
            # Successfully found policies from major payers
            result = results[0]  # Use first result

            # Validate that payer information is available
            payer_name = result.get("payer_name", "").strip() if result.get("payer_name") else ""
            if not payer_name or payer_name.lower() == "unknown":
                # No valid payer information found
                progress.add_message(f"⚠️  Found result but missing payer information")
                progress.add_message("❌ Cannot extract valid policy without payer details")

                # Continue to fallback search instead of returning error immediately
            else:
                # Valid payer info exists, return the result
                source_url = result.get("source_file", "")
                classification = result.get("classification", "unknown")

                progress.add_message(f"✅ Found policy from major payer: {payer_name}")
                progress.add_message("📊 Extracting structured data...")

                return jsonify({
                    "data": result,
                    "source_url": source_url,
                    "target_drug": target_drug,
                    "classification": classification,
                    "found": True,
                    "progress": progress.get_messages()
                }), 200

        # FALLBACK: parserA found no major payer policies, try generic search
        progress.add_message("⚠️  No policies found from major payers")
        progress.add_message("🌐 Searching the web for policies...")

        search_query = f"{target_drug} drug policy formulary pdf"
        urls = search_duckduckgo(search_query, max_results=5)

        if not urls:
            progress.add_message("❌ No results found")
            return jsonify({
                "error": f"Unable to find policies for '{target_drug}' online.",
                "found": False,
                "progress": progress.get_messages()
            }), 404

        progress.add_message(f"📄 Found {len(urls)} potential sources, attempting extraction...")

        # Try to download and extract from first URL that works
        for idx, url in enumerate(urls, 1):
            try:
                progress.add_message(f"⬇️  Downloading source {idx}/{len(urls)}...")

                # Download to temp directory
                temp_dir = tempfile.mkdtemp()
                filepath = download_file(url, temp_dir)

                if filepath and filepath.endswith(".pdf"):
                    progress.add_message(f"📖 Extracting text from PDF...")

                    # Extract data
                    pages = backend_extract_pages(filepath)

                    if pages:
                        # Classify
                        classification = classify_policy_document(filepath)
                        progress.add_message(f"🏷️  Classifying document...")

                        # Build extraction text
                        extraction_text = build_extraction_text(
                            pages,
                            drug_keywords,
                            classification
                        )

                        # Extract structured JSON
                        progress.add_message(f"🤖 Analyzing with AI...")
                        result = extract_structured_json(
                            prepared_text=extraction_text,
                            target_drug=target_drug,
                            source_file=url
                        )

                        # Validate that payer information is available in result
                        payer_name = result.get("payer_name", "").strip() if result.get("payer_name") else ""
                        if not payer_name or payer_name.lower() == "unknown":
                            # No valid payer info extracted from this URL
                            progress.add_message(f"⚠️  Source {idx}: Extracted content but missing payer information")
                            continue

                        progress.add_message(f"✅ Successfully extracted policy from {payer_name}!")

                        return jsonify({
                            "data": result,
                            "source_url": url,
                            "target_drug": target_drug,
                            "classification": classification,
                            "found": True,
                            "progress": progress.get_messages()
                        }), 200
            except Exception as e:
                progress.add_message(f"⚠️  Failed to process source {idx}: {str(e)}")
                continue

        progress.add_message("❌ Unable to extract from any source")
        return jsonify({
            "error": f"Unable to find policies for '{target_drug}' online.",
            "found": False,
            "progress": progress.get_messages()
        }), 404

    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
