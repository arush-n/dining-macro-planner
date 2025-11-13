"""
Test API Connection
Verifies that the API is running and accessible
"""
import requests
import sys

API_BASE = "http://localhost:8000"

def test_api():
    """Test if API is accessible"""
    print("=" * 70)
    print("TESTING API CONNECTION")
    print("=" * 70)
    print()

    tests = [
        ("Health Check", "GET", "/health", None),
        ("Root Endpoint", "GET", "/", None),
        ("Get Foods (J2 Lunch)", "GET", "/foods/J2/Lunch", None),
    ]

    passed = 0
    failed = 0

    for test_name, method, endpoint, body in tests:
        print(f"Testing: {test_name}...", end=" ")
        try:
            url = f"{API_BASE}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                response = requests.post(url, json=body, timeout=5)

            if response.status_code == 200:
                print("✓ PASSED")
                passed += 1
            else:
                print(f"✗ FAILED (Status {response.status_code})")
                failed += 1
        except requests.exceptions.ConnectionError:
            print("✗ FAILED (Cannot connect)")
            print("\n⚠️  API server is not running!")
            print("   Start it with: python run_server.py")
            sys.exit(1)
        except Exception as e:
            print(f"✗ FAILED ({e})")
            failed += 1

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All tests passed! API is ready.")
        print("\nYou can now:")
        print("1. Start the frontend: python start_frontend.py")
        print("2. Open browser to: http://localhost:3000")
    else:
        print("\n⚠️  Some tests failed. Check the API server logs.")

    return failed == 0

if __name__ == "__main__":
    test_api()
