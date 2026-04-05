import sqlite3

def initialize_db(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Main Policy Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id TEXT UNIQUE, 
            payer_name TEXT,
            brand_name TEXT,
            generic_name TEXT,
            drug_category TEXT,
            access_status TEXT,
            preferred_count INTEGER,
            access_notes TEXT,
            is_covered TEXT,
            pa_required TEXT,
            st_required TEXT,
            soc_restrictions TEXT,
            soc_notes TEXT,
            effective_date TEXT,
            policy_name TEXT,
            source_file TEXT
        )
    ''')

    # Indications Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            condition TEXT,
            criteria TEXT,
            FOREIGN KEY (policy_id) REFERENCES policies (id)
        )
    ''')

    # Step Therapy Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS step_therapy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            step_number INTEGER,
            required_drug_or_class TEXT,
            notes TEXT,
            FOREIGN KEY (policy_id) REFERENCES policies (id)
        )
    ''')

    # Dosing Limits Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dosing_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            limit_type TEXT,
            limit_value TEXT,
            notes TEXT,
            FOREIGN KEY (policy_id) REFERENCES policies (id)
        )
    ''')

    conn.commit()
    conn.close()