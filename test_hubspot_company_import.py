"""
Test script for HubSpot Company CSV Import

This script tests the company import functionality by uploading a sample CSV file.
"""

import requests
import json

def test_company_import():
    """Test the company import endpoint"""
    
    # API endpoint
    url = "http://localhost:8000/api/v1/hubspot/import/companies/"
    
    # Open and upload the CSV file
    try:
        with open('test_companies.csv', 'rb') as f:
            files = {'file': ('test_companies.csv', f, 'text/csv')}
            response = requests.post(url, files=files)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Import successful!")
        else:
            print("❌ Import failed!")
            
    except FileNotFoundError:
        print("❌ test_companies.csv file not found!")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the server is running!")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_company_import() 