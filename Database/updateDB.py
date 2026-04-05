import os
import shutil
from database import initialize_db
from ingest import ingest_file

# --- CONFIGURATION ---
DB_NAME = "Drug_Policies.db"
INCOMING_DIR = "incoming"
PROCESSED_DIR = "processed"

def updateDB():
    initialize_db(DB_NAME)
    os.makedirs(INCOMING_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # Looking for .json files (change to .jsonl if needed)
    files_to_process = [f for f in os.listdir(INCOMING_DIR) if f.endswith(".json")]

    if not files_to_process:
        print(f"No new files found in '{INCOMING_DIR}/'. Standing by...")
        return

    print(f"Found {len(files_to_process)} new file(s).")

    for filename in files_to_process:
        incoming_path = os.path.join(INCOMING_DIR, filename)
        processed_path = os.path.join(PROCESSED_DIR, filename)

        print(f"Ingesting: {filename}...")

        # Capture the result of the function
        success = ingest_file(incoming_path, DB_NAME)
        
        if success:
            # ONLY move if ingestion actually worked
            shutil.move(incoming_path, processed_path)
            print(f"Success: {filename} moved to '{PROCESSED_DIR}/'")
        else:
            # Stay in 'incoming' so you can inspect the file
            print(f"Skipping move: {filename} failed to ingest.")

    print("\n--- Pipeline Run Complete ---")