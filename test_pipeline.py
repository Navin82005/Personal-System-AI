import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test_pipeline():
    try:
        # Check if the server is up
        health = requests.get(f"{BASE_URL}/")
        print("Health Check:", health.json())
    except Exception as e:
        print("Server not running. Please start it first.")
        return

    print("1. Scanning folder...")
    resp = requests.post(
        f"{BASE_URL}/scan-folder", 
        json={"folder_path": "/Users/naveenn/Documents/Projects/Personal System AI/test_data"}
    )
    print("Scan Response:", resp.json())
    
    time.sleep(2)
    
    print("\n2. Getting documents...")
    resp = requests.get(f"{BASE_URL}/documents")
    print("Documents Response:", resp.json())
    
    print("\n3. Querying (Global)...")
    resp = requests.post(f"{BASE_URL}/query", json={"query": "What is the Personal System AI?", "top_k": 3})
    print("Query Response:", resp.json())
    
    print("\n4. Querying (File-Specific - Existing)...")
    resp = requests.post(f"{BASE_URL}/query", json={"query": "What does it say in architecture_notes.md?", "top_k": 3})
    print("Query Response:", resp.json())

    print("\n5. Querying (File-Specific - Non-Existing)...")
    resp = requests.post(f"{BASE_URL}/query", json={"query": "Summarize the file missing_file.pdf", "top_k": 3})
    print("Query Response:", resp.json())

if __name__ == "__main__":
    test_pipeline()
