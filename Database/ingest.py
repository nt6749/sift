import sqlite3
import json

def ingest_file(file_path, db_name):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read().strip()

        # Clean Markdown tags (```json ... ```)
        if raw_content.startswith("```json"):
            raw_content = raw_content.replace("```json", "", 1)
        if raw_content.endswith("```"):
            raw_content = raw_content.rsplit("```", 1)[0]
        
        data = json.loads(raw_content.strip())
        if isinstance(data, str):
            data = json.loads(data)
            
    except Exception as e:
        print(f"JSON Read Error in {file_path}: {e}")
        return False

    # Extract nested objects safely
    drug_info = data.get("drug_name", {})
    status_info = data.get("access_status", {})
    coverage_info = data.get("coverage", {})
    meta_info = data.get("policy_metadata", {})
    p_id = meta_info.get("policy_id")

    # 1. STORAGE LOGIC
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    try:
        # Check if policy already exists
        cursor.execute('SELECT id FROM policies WHERE policy_id = ?', (p_id,))
        row = cursor.fetchone()
        
        if row:
            policy_row_id = row[0]
            # Wipe sub-tables to prevent orphaned/duplicate data
            cursor.execute('DELETE FROM indications WHERE policy_id = ?', (policy_row_id,))
            cursor.execute('DELETE FROM step_therapy WHERE policy_id = ?', (policy_row_id,))
            cursor.execute('DELETE FROM dosing_limits WHERE policy_id = ?', (policy_row_id,))
            
            # Update main record
            cursor.execute('''
                UPDATE policies SET 
                    payer_name=?, brand_name=?, generic_name=?, drug_category=?,
                    access_status=?, preferred_count=?, access_notes=?,
                    is_covered=?, pa_required=?, st_required=?,
                    soc_restrictions=?, soc_notes=?,
                    effective_date=?, policy_name=?, source_file=?
                WHERE id = ?
            ''', (
                data.get("payer_name"), drug_info.get("brand"), drug_info.get("generic"), data.get("drug_category"),
                status_info.get("status"), status_info.get("preferred_count_in_category"), status_info.get("notes"),
                str(coverage_info.get("covered")), data.get("prior_authorization", {}).get("required"),
                data.get("step_therapy", {}).get("required"), " | ".join(data.get("site_of_care", {}).get("restrictions", [])),
                data.get("site_of_care", {}).get("notes"), meta_info.get("effective_date"),
                meta_info.get("policy_name"), meta_info.get("source_file"), policy_row_id
            ))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO policies (
                    payer_name, brand_name, generic_name, drug_category,
                    access_status, preferred_count, access_notes,
                    is_covered, pa_required, st_required,
                    soc_restrictions, soc_notes,
                    effective_date, policy_name, policy_id, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get("payer_name"), drug_info.get("brand"), drug_info.get("generic"), data.get("drug_category"),
                status_info.get("status"), status_info.get("preferred_count_in_category"), status_info.get("notes"),
                str(coverage_info.get("covered")), data.get("prior_authorization", {}).get("required"),
                data.get("step_therapy", {}).get("required"), " | ".join(data.get("site_of_care", {}).get("restrictions", [])),
                data.get("site_of_care", {}).get("notes"), meta_info.get("effective_date"),
                meta_info.get("policy_name"), p_id, meta_info.get("source_file")
            ))
            policy_row_id = cursor.lastrowid

        # Re-populate Sub-tables
        for ind in coverage_info.get("covered_indications", []):
            cursor.execute('INSERT INTO indications (policy_id, condition, criteria) VALUES (?, ?, ?)',
                           (policy_row_id, ind.get("condition"), ind.get("criteria")))

        for step in data.get("step_therapy", {}).get("steps", []):
            cursor.execute('INSERT INTO step_therapy (policy_id, step_number, required_drug_or_class, notes) VALUES (?, ?, ?, ?)',
                           (policy_row_id, step.get("step_number"), step.get("required_drug_or_class"), step.get("notes")))

        for item in data.get("dosing_and_quantity_limits", {}).get("limits", []):
            cursor.execute('INSERT INTO dosing_limits (policy_id, limit_type, limit_value, notes) VALUES (?, ?, ?, ?)',
                           (policy_row_id, item.get("type"), item.get("value"), item.get("notes")))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"SQL Error in {file_path}: {e}")
        return False
    finally:
        conn.close()