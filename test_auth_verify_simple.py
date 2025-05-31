"""
Simple Auth Test - Valid Manager Only
"""
from fastapi.testclient import TestClient
from app.main import app

def test_valid_manager():
    """Test valid manager only"""
    
    client = TestClient(app)
    
    print("✅ Manager Verification Test:")
    
    response = client.post(
        "/api/auth/verify-manager",
        json={"email": "first_1@gmail.com"}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Authorized: {data['authorized']}")
        
        if data['authorized']:
            manager = data['manager']
            print(f"Manager: {manager['first_name']} {manager['last_name']}")
            print(f"Role: {manager['role']}")
            print(f"Company: {data['company']['name']}")
            print(f"Properties: {len(data['properties'])}")
            
            for prop in data['properties']:
                print(f"  • {prop['name']} ({prop['address']})")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_valid_manager() 