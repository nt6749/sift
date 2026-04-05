import sqlite3
import json

def ingest_file(file_path, db_name):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read().strip()

        # --- FIX: Strip Markdown Code Blocks if present ---
        if raw_content.startswith("```json"):
            raw_content = raw_content.replace("```json", "", 1)
        if raw_content.endswith("```"):
            raw_content = raw_content.rsplit("```", 1)[0]
        
        # Clean up any leftover whitespace or newlines
        raw_content = raw_content.strip()

        # Now load the cleaned string
        data = json.loads(raw_content)

        # In case it's double-serialized (string inside a string)
        if isinstance(data, str):
            data = json.loads(data)
            
    except Exception as e:
        print(f"   ❌ JSON Read Error in {file_path}: {e}")
        return False

    # --- 1. VALIDATION LOGIC ---
    required_checks = {
        "payer_name": "Payer Name",
        "drug_name.brand": "Brand Name",
        "access_status.status": "Access Status",
        "coverage.covered": "Coverage Flag",
        "policy_metadata.policy_id": "Policy ID"
    }

    # Extract nested objects safely for validation
    drug_info = data.get("drug_name", {}) if isinstance(data.get("drug_name"), dict) else {}
    status_info = data.get("access_status", {}) if isinstance(data.get("access_status"), dict) else {}
    coverage_info = data.get("coverage", {}) if isinstance(data.get("coverage"), dict) else {}
    meta_info = data.get("policy_metadata", {}) if isinstance(data.get("policy_metadata"), dict) else {}

    missing_elements = []
    
    if not data.get("payer_name"): missing_elements.append("payer_name")
    if not drug_info.get("brand"): missing_elements.append("drug_name.brand")
    if not status_info.get("status"): missing_elements.append("access_status.status")
    if not coverage_info.get("covered"): missing_elements.append("coverage.covered")
    if not meta_info.get("policy_id"): missing_elements.append("policy_metadata.policy_id")

    if missing_elements:
        print(f"DATA WARNING in {file_path}:")
        for item in missing_elements:
            print(f"      - Missing Required Element: {required_checks[item]}")
    else:
        print(f"All required elements present for {drug_info.get('brand', 'Unknown')}")

    # --- 2. STORAGE LOGIC ---
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    try:
        # Use .get() everywhere to provide 'None' (NULL in SQL) for missing data
        cursor.execute('''
            INSERT INTO policies (
                payer_name, brand_name, generic_name, drug_category,
                access_status, preferred_count, access_notes,
                is_covered, pa_required, st_required,
                soc_restrictions, soc_notes,
                effective_date, policy_name, policy_id, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get("payer_name"),
            drug_info.get("brand"),
            drug_info.get("generic"),
            data.get("drug_category"),
            status_info.get("status"),
            status_info.get("preferred_count_in_category"),
            status_info.get("notes"),
            str(coverage_info.get("covered")),
            data.get("prior_authorization", {}).get("required"),
            data.get("step_therapy", {}).get("required"),
            " | ".join(data.get("site_of_care", {}).get("restrictions", [])),
            data.get("site_of_care", {}).get("notes"),
            meta_info.get("effective_date"),
            meta_info.get("policy_name"),
            meta_info.get("policy_id"),
            meta_info.get("source_file")
        ))

        policy_row_id = cursor.lastrowid

        # Insert indications
        for ind in coverage_info.get("covered_indications", []):
            cursor.execute('INSERT INTO indications (policy_id, condition, criteria) VALUES (?, ?, ?)',
                           (policy_row_id, ind.get("condition"), ind.get("criteria")))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"SQL Error in {file_path}: {e}")
        return False
    finally:
        conn.close()