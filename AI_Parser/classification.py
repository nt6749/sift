import base64
import json
import os
import pdfplumber
from dotenv import load_dotenv
from google import genai
from google.genai import types

base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, "key.env"))

API_KEY = os.getenv("GEMINI_API_KEY")
PROMPT_FILE = os.path.join(base_dir, "prompt.txt")
client = genai.Client(api_key=API_KEY)

def classify_policy_document(pdf_path: str, mega_doc_threshold: int = 40) -> str:
    """
    Classifies the PDF to determine the best extraction route.
    Returns: 'MEGA_DOCUMENT', 'SINGLE_DRUG', or 'DRUG_CLASS'
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            
            # Route 1: Check for massive files (e.g., Priority Health Formulary)
            if page_count > mega_doc_threshold:
                return "MEGA_DOCUMENT"
            
            # Extract first page text for classification
            first_page_text = pdf.pages[0].extract_text() or ""
            
        # Route 2: Use a lightweight AI call to check the content type
        classification_prompt = (
            "Analyze the following text from a medical policy. "
            "Return ONLY one of these two strings:\n"
            "1. 'SINGLE_DRUG': If the policy is dedicated to one specific medication.\n"
            "2. 'DRUG_CLASS': If the policy covers multiple drugs, biosimilars, or a therapeutic category.\n\n"
            f"TEXT:\n{first_page_text[:2000]}"
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash", # Using the stable flash model
            contents=[classification_prompt]
        )
        
        classification = response.text.strip().upper()
        
        if "DRUG_CLASS" in classification:
            return "DRUG_CLASS"
        return "SINGLE_DRUG"
            
    except Exception as e:
        print(f"Error during classification: {e}")
        return "ERROR"

def generate_payers_json(pdf_paths: list[str]):
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
    except FileNotFoundError:
        return "Error: prompt.txt not found."

    uploaded_files = []
    for path in pdf_paths:
        uploaded = client.files.upload(
            file=path,
            config={"mime_type": "application/pdf"}
        )
        uploaded_files.append(uploaded)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt_content] + uploaded_files
    )

    return response.text

def generate_json_from_text(text_content: str):
    """Specific engine for Mega-Document snippets."""
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
    except FileNotFoundError:
        return "Error: prompt.txt not found."

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt_content, f"EXTRACT DATA FROM THIS TEXT:\n\n{text_content}"]
    )
    return response.text
def coordinate_extraction(pdf_path, target_drug=None):
    """
    The Master Router:
    1. Classifies the document.
    2. Routes to the File API if small.
    3. Routes to the Text Snippet API if it's a Mega-Doc.
    """
    # 1. Get the classification
    doc_type = classify_policy_document(pdf_path)
    
    print(f"--- Routing {os.path.basename(pdf_path)} ---")
    print(f"Type Identified: {doc_type}")

    # 2. Route 1 & 2: Standard and Drug Class (Small enough for File API)
    if doc_type in ["SINGLE_DRUG", "DRUG_CLASS"]:
        print("Action: Sending full PDF to Gemini File API...")
        return generate_payers_json([pdf_path])
    
    # 3. Route 3: Mega-Document (Too large for full upload)
    elif doc_type == "MEGA_DOCUMENT":
        print(f"Action: Extracting relevant pages for '{target_drug}'...")
        # This calls the keyword search function from your test1.py logic
        relevant_text = extract_pages_by_keyword(pdf_path, target_drug)
        
        if not relevant_text.strip():
            return {"error": f"Keyword '{target_drug}' not found in Mega-Doc."}
            
        return generate_json_from_text(relevant_text)
    
    else:
        return {"error": "Unknown document classification."}

def extract_pages_by_keyword(pdf_path, keyword, window=2):
    """
    Helper to pull text from a Mega-Doc without crashing the AI.
    Finds the keyword and grabs the surrounding pages.
    """
    relevant_chunks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and keyword.lower() in text.lower():
                    # Grab a window (e.g., 1 page before, 2 pages after)
                    start = max(0, i - 1)
                    end = min(len(pdf.pages), i + window)
                    
                    for j in range(start, end):
                        page_text = pdf.pages[j].extract_text()
                        relevant_chunks.append(f"--- PAGE {j+1} ---\n{page_text}")
                    break # Stop once we find the primary section
    except Exception as e:
        print(f"Extraction failed: {e}")
                
    return "\n".join(relevant_chunks)

# ---------------------------------------------------------
# Test block for the Router
# ---------------------------------------------------------
if __name__ == "__main__":
    # Test with your Cigna or Aetna file
    sample_pdf = os.path.join(base_dir, "Cigna Rituximab Intravenous Products for Non-Oncology Indications.pdf")
    drug_name = "Rituxan" 
    
    if os.path.exists(sample_pdf):
        final_json = coordinate_extraction(sample_pdf, target_drug=drug_name)
        print("\n--- Final Extracted Result ---")
        print(final_json)