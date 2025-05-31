"""
Debug script to check available endpoints
"""

import requests
import json

def check_endpoints():
    """Check what endpoints are available"""
    
    base_url = "http://localhost:8000"
    
    print("🔍 Checking API endpoints...")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Available endpoints:")
            for name, url in data.get('endpoints', {}).items():
                print(f"  - {name}: {url}")
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
    
    # Test docs endpoint
    try:
        response = requests.get(f"{base_url}/docs")
        print(f"✅ Docs endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Docs endpoint failed: {e}")
    
    # Test OpenAPI schema
    try:
        response = requests.get(f"{base_url}/openapi.json")
        print(f"✅ OpenAPI schema: {response.status_code}")
        if response.status_code == 200:
            schema = response.json()
            print("Available paths:")
            for path in schema.get('paths', {}):
                methods = list(schema['paths'][path].keys())
                print(f"  - {path}: {methods}")
    except Exception as e:
        print(f"❌ OpenAPI schema failed: {e}")

if __name__ == "__main__":
    check_endpoints() 