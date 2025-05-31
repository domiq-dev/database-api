"""
Test Manager Verification API
"""
import pytest
import asyncio
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_verify_manager():
    """Test manager verification using async client"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        print("✅ Manager Verification Test:")
        
        # Test valid manager email
        response = await client.post(
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
                print(f"Error: {data['error']}")
        else:
            print(f"Error: {response.text}")

async def test_invalid_manager():
    """Test invalid manager separately"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        print("\n" + "="*50 + "\n")
        print("❌ Invalid Manager Test:")
        
        response = await client.post(
            "/api/auth/verify-manager",
            json={"email": "invalid@example.com"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Authorized: {data['authorized']}")
            print(f"Error: {data.get('error', 'No error message')}")
        else:
            print(f"Error: {response.text}")

async def test_manager_properties():
    """Test manager properties endpoint separately"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        print("\n" + "="*50 + "\n")
        print("🔍 Manager Properties Test:")
        
        response = await client.get("/api/auth/manager-properties/first_1@gmail.com")
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Property IDs: {data['property_ids']}")
        else:
            print(f"Error: {response.text}")

async def run_all_tests():
    """Run all tests in sequence"""
    await test_verify_manager()
    await test_invalid_manager() 
    await test_manager_properties()

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 