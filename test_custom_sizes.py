import requests
import time
import sys
import os
import json

API_URL = "http://localhost:3000/api"
# Use a valid image path. If test_image.png doesn't exist, try to find one.
IMAGE_PATH = "test_image.png"
if not os.path.exists(IMAGE_PATH):
    # Try to find an image in example folder
    if os.path.exists("example/generated.png"):
        IMAGE_PATH = "example/generated.png"

def test_custom_sizes():
    print(f"Testing custom sizes with {IMAGE_PATH}...")

    if not os.path.exists(IMAGE_PATH):
        print(f"Error: {IMAGE_PATH} not found.")
        sys.exit(1)

    custom_sizes = {
        "tiny_icon": [32, 32, 32],
        "banner": [100, 200, 100]
    }
    
    files = {'file': open(IMAGE_PATH, 'rb')}
    data = {
        'output_sizes_json': json.dumps(custom_sizes),
        'alpha_threshold': 50
    }

    try:
        print(f"Uploading to {API_URL}/process with custom sizes: {custom_sizes}")
        response = requests.post(f"{API_URL}/process", files=files, data=data)
            
        if response.status_code != 200:
            print(f"Error uploading file: {response.text}")
            sys.exit(1)
            
        data = response.json()
        task_id = data.get("task_id")
        print(f"Task submitted. ID: {task_id}")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is it running?")
        sys.exit(1)

    # Poll status
    print("Polling status...")
    while True:
        try:
            status_response = requests.get(f"{API_URL}/status/{task_id}")
            if status_response.status_code != 200:
                print(f"Error checking status: {status_response.text}")
                break
                
            status_data = status_response.json()
            status = status_data.get("status")
            print(f"Status: {status}")
            
            if status == "SUCCESS":
                download_url = status_data.get("download_url")
                print(f"Task finished! Download URL: {download_url}")
                
                # Download result
                # Note: The API_URL already includes /api, but the download_url returned by status usually starts with /download/... 
                # Wait, the status endpoint returns "/download/{id}" which is relative to API root in the python code but 
                # in the nuxt proxy it might be mapped differently.
                # Let's assume the python API returns a relative path from the API root.
                # But wait, api/main.py returns `/download/{task_id}`.
                # So if we hit `http://localhost:3000/api/status/...` and get `/download/...`
                # We should hit `http://localhost:3000/api/download/...`
                
                full_download_url = f"{API_URL}{download_url}"
                print(f"Downloading from {full_download_url}...")
                r = requests.get(full_download_url)
                if r.status_code == 200:
                    with open("custom_sizes_result.zip", "wb") as f:
                        f.write(r.content)
                    print("Success! Result saved to custom_sizes_result.zip")
                else:
                    print(f"Error downloading result: {r.text}")
                break
                
            elif status == "FAILURE":
                print(f"Task failed: {status_data.get('error')}")
                break
                
            time.sleep(2)
            
        except Exception as e:
            print(f"Error during polling: {e}")
            break

if __name__ == "__main__":
    test_custom_sizes()
