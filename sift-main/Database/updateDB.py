import os
import shutil
from database import initialize_db
from ingest import ingest_file

DB_NAME = "Health_Plans.db"
INCOMING_DIR = "incoming"
PROCESSED_DIR = "processed"

def updateDB():
    initialize_db(DB_NAME)
    os.makedirs(INCOMING_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    files_to_process = [f for f in os.listdir(INCOMING_DIR) if f.endswith(".json")]

    if not files_to_process:
        print(f"No new files found in '{INCOMING_DIR}/'. Standing by...")
        return

    print(f"Found {len(files_to_process)} new file(s).")

    for filename in files_to_process:
        in_path = os.path.join(INCOMING_DIR, filename)
        out_path = os.path.join(PROCESSED_DIR, filename)

        print(f"Ingesting: {filename}...")
        if ingest_file(in_path, DB_NAME):
            shutil.move(in_path, out_path)
            print(f"Success: {filename} moved to '{PROCESSED_DIR}/'")
        else:
            print(f"Skipping move: {filename} failed to ingest.")