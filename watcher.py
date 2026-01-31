import os
import time
import glob
import re
from datetime import datetime

# --- CONFIGURATION ---
# Standard VRChat log location
VRC_LOG_DIR = os.path.join(os.environ["USERPROFILE"], "AppData", "LocalLow", "VRChat", "VRChat")
# How many seconds between a leave and a join to flag as suspicious?
SUSPICIOUS_DELTA = 90  

# --- DATA STORAGE ---
# Stores the last 5 people who left: { "username": timestamp_they_left }
recent_leavers = {}

def get_latest_log():
    """Finds the most recent VRChat log file."""
    list_of_files = glob.glob(os.path.join(VRC_LOG_DIR, "output_log_*.txt"))
    if not list_of_files:
        print("[-] No VRChat logs found. Is VRChat installed?")
        return None
    return max(list_of_files, key=os.path.getctime)

def clean_username(raw_name):
    """Removes junk from log usernames if present."""
    return raw_name.strip()

def follow(file):
    """Generator that reads a file like 'tail -f'."""
    file.seek(0, os.SEEK_END) # Go to the end of the file
    while True:
        line = file.readline()
        if not line:
            time.sleep(0.1) # Sleep briefly
            continue
        yield line

def analyze_traffic(new_user_name):
    """The Logic Engine: Checks if this new user matches a recent leaver."""
    current_time = time.time()
    
    # 1. Check against recent leavers
    potential_matches = []
    
    for leaver_name, leave_time in list(recent_leavers.items()):
        # Remove leavers older than 5 minutes to keep memory clean
        if current_time - leave_time > 300:
            del recent_leavers[leaver_name]
            continue
            
        time_diff = current_time - leave_time
        
        # THE ALGORITHM:
        # If someone joins < 90s after someone left, flag it.
        if time_diff < SUSPICIOUS_DELTA:
            potential_matches.append((leaver_name, time_diff))

    # 2. Alert User
    if potential_matches:
        print("\n" + "="*40)
        print(f"[!] POTENTIAL BAN EVASION DETECTED")
        print(f"[+] New Joiner: {new_user_name}")
        for old_name, delta in potential_matches:
            print(f"[-] Match: '{old_name}' left {int(delta)} seconds ago.")
            print(f"    (Typical Steam Restart Time: 45-60s)")
        print("="*40 + "\n")

def main():
    print("[*] VRChat Doppelgänger Watcher Initialized...")
    print(f"[*] Watching Directory: {VRC_LOG_DIR}")
    
    current_log = get_latest_log()
    if not current_log:
        return

    print(f"[*] Hooked into: {os.path.basename(current_log)}")
    print("[*] Waiting for events... (Press Ctrl+C to stop)")

    try:
        with open(current_log, "r", encoding="utf-8", errors="ignore") as f:
            log_lines = follow(f)
            
            for line in log_lines:
                # REGEX: Looking for specific VRChat event lines
                
                # Event: Player Left
                # Line format: "[Behaviour] OnPlayerLeft User Name"
                if "[Behaviour] OnPlayerLeft" in line:
                    parts = line.split("[Behaviour] OnPlayerLeft")
                    if len(parts) > 1:
                        user = clean_username(parts[1])
                        print(f"[-] Left: {user}")
                        recent_leavers[user] = time.time()

                # Event: Player Joined
                # Line format: "[Behaviour] OnPlayerJoined User Name"
                elif "[Behaviour] OnPlayerJoined" in line:
                    parts = line.split("[Behaviour] OnPlayerJoined")
                    if len(parts) > 1:
                        user = clean_username(parts[1])
                        print(f"[+] Join: {user}")
                        # Trigger the analysis
                        analyze_traffic(user)

    except KeyboardInterrupt:
        print("\n[*] Watcher stopped.")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()