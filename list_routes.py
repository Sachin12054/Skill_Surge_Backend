"""
List all available API routes from OpenAPI schema
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def list_all_routes():
    """Fetch and display all available API routes"""
    print("="*80)
    print("AVAILABLE API ROUTES")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            openapi = response.json()
            paths = openapi.get("paths", {})
            
            print(f"\nFound {len(paths)} endpoints:\n")
            
            for path, methods in sorted(paths.items()):
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        summary = details.get('summary', 'No description')
                        print(f"  {method.upper():6} {path:50} - {summary}")
            
            print(f"\n{'='*80}\n")
            return paths
        else:
            print(f"Failed to fetch OpenAPI schema: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error: {e}")
        return {}

if __name__ == "__main__":
    list_all_routes()
