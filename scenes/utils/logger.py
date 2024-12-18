# utils/logger.py
import json
import os

STAGE_LOG_FILE = "stage_logs.json"

def initialize_stage_logs(total_stages=10):
    """Initialize the stage logs file if it doesn't exist."""
    if not os.path.exists(STAGE_LOG_FILE):
        logs = {str(i+1): {"cleared": False, "remaining_time": 0.0} for i in range(total_stages)}
        save_stage_logs(logs)
    else:
        # Load existing logs
        try:
            with open(STAGE_LOG_FILE, 'r') as f:
                existing_logs = json.load(f)
        except json.JSONDecodeError:
            print("Error: stage_logs.json is corrupted. Reinitializing logs.")
            logs = {str(i+1): {"cleared": False, "remaining_time": 0.0} for i in range(total_stages)}
            save_stage_logs(logs)
            return

        # Update logs to include new stages
        updated = False
        for i in range(total_stages):
            stage_key = str(i+1)
            if stage_key not in existing_logs:
                existing_logs[stage_key] = {"cleared": False, "remaining_time": 0.0}
                updated = True
        if updated:
            save_stage_logs(existing_logs)

def load_stage_logs():
    """Load stage logs from the JSON file."""
    if not os.path.exists(STAGE_LOG_FILE):
        initialize_stage_logs()
    try:
        with open(STAGE_LOG_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("Error: stage_logs.json is corrupted. Reinitializing logs.")
        initialize_stage_logs()
        with open(STAGE_LOG_FILE, 'r') as f:
            return json.load(f)

def save_stage_logs(logs):
    """Save stage logs to the JSON file."""
    with open(STAGE_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=4)
