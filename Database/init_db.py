import sqlite3
import json
import os

def initialize_db(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Create tables (Shortened for brevity - use the full list from the previous response)
    cursor.execute("""CREATE TABLE IF NOT EXISTS policies (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   payer_name TEXT, brand_name TEXT, 
                   generic_name TEXT, 
                   drug_category TEXT, 
                   access_status TEXT, 
                   preferred_count INTEGER, 
                   access_notes TEXT, 
                   is_covered BOOLEAN, 
                   pa_required TEXT, 
                   st_required TEXT, 
                   soc_restrictions TEXT, 
                   soc_notes TEXT, 
                   effective_date TEXT, 
                   policy_name TEXT, 
                   policy_id TEXT, 
                   source_file TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS indications (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   policy_id INTEGER, 
                   condition TEXT, 
                   criteria TEXT, 
                   FOREIGN KEY(policy_id) REFERENCES policies(id))""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS step_therapy (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   policy_id INTEGER, 
                   step_number INTEGER, 
                   required_drug_or_class TEXT, 
                   notes TEXT, 
                   FOREIGN KEY(policy_id) REFERENCES policies(id))""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS dosing_limits (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   policy_id INTEGER, 
                   limit_type TEXT, 
                   limit_value TEXT, 
                   notes TEXT, 
                   FOREIGN KEY(policy_id) REFERENCES policies(id))""")
    
    conn.commit()
    conn.close()