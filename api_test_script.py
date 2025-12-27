import requests
import time
import sys
import os

API_URL = "http://localhost:3000/api"
IMAGE_PATH = "test_image.png"

def test_api():
    # 1. Check API health (optional, but good practice)
    # We'll just jump to processing
    print(f"Uploading {IMAGE_PATH} to {API_URL}/process...")

    if not os.path.exists(IMAGE_PATH):
        print(f"Error: {IMAGE_PATH} not found.")
        sys.exit(1)

    try:
        with open(IMAGE_PATH, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{API_URL}/process", files=files)
            
        if response.status_code != 200:
            print(f"Error uploading file: {response.text}")
            sys.exit(1)
            
        data = response.json()
        task_id = data.get("task_id")
        print(f"Task submitted. ID: {task_id}")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is it running?")
        sys.exit(1)

    # 2. Poll status
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
                
                # 3. Download result
                full_download_url = f"{API_URL}{download_url}"
                print(f"Downloading from {full_download_url}...")
                r = requests.get(full_download_url)
                if r.status_code == 200:
                    with open("result.zip", "wb") as f:
                        f.write(r.content)
                    print("Success! Result saved to result.zip")
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
    test_api()
