import os
import json
import urllib.parse
import random
import string
from datetime import datetime

# Function to generate a random 16-character alphanumeric ID
def generate_random_id():
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return ''.join(random.choice(characters) for _ in range(16))

# Function to generate a playlist JSON file for Foundry VTT
def generate_foundry_playlist(folder_path, output_filename):
    # Get the playlist name from the folder name
    playlist_name = os.path.basename(folder_path)
    
    # List all .webm files in the folder
    webm_files = [f for f in os.listdir(folder_path) if f.endswith('.webm')]
    
    # Generate a list of sound entries
    sounds = []
    for i, filename in enumerate(webm_files):
        # Use the full file name as the sound name (without modifications)
        sound_name = filename
        # Construct the relative path: Music_Import/Honkai Impact 3rd OST/filename
        relative_path = os.path.join("Music_Import", playlist_name, filename)
        # URL-encode the path (e.g., spaces become %20, special characters are encoded)
        encoded_path = urllib.parse.quote(relative_path, safe='/')
        
        # Create a sound entry
        sound = {
            "name": sound_name,
            "path": encoded_path,
            "channel": "music",
            "repeat": False,
            "fade": None,
            "description": "",
            "volume": 0.01,
            "_id": generate_random_id(),  # Generate a 16-character alphanumeric ID
            "playing": False,
            "pausedTime": None,
            "sort": i,
            "flags": {}
        }
        sounds.append(sound)
    
    # Get current timestamp in milliseconds for _stats
    current_time = int(datetime.now().timestamp() * 1000)
    
    # Create the playlist JSON structure, matching the original JSON exactly
    playlist = {
        "folder": "xRZH0HFR0JSeNcZ3",
        "name": playlist_name,
        "sounds": sounds,
        "channel": "music",
        "mode": 0,
        "playing": False,
        "fade": 2000,
        "sorting": "a",
        "seed": 228,
        "flags": {
            "exportSource": {
                "world": "one-piece-dandd-marines",
                "system": "dnd5e",
                "coreVersion": "12.331",
                "systemVersion": "4.3.9"
            }
        },
        "_stats": {
            "coreVersion": "12.331",
            "systemId": "dnd5e",
            "systemVersion": "3.3.1",
            "createdTime": current_time,
            "modifiedTime": current_time,
            "lastModifiedBy": "3AazUso5cQzr2z0e"
        },
        "description": ""
    }
    
    # Write the JSON to a file in the same folder
    output_path = os.path.join(folder_path, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(playlist, f, indent=2)
    
    print(f"JSON file generated successfully at: {output_path}")

# Example usage
if __name__ == "__main__":
    # Folder path containing the .webm files
    folder_path = r"C:\Users\Hp Victus\AppData\Local\FoundryVTT\Data\Music_Import\Honkai Impact 3rd OST"
    output_filename = "honkai_impact_3rd_ost_playlist.json"
    
    generate_foundry_playlist(folder_path, output_filename)