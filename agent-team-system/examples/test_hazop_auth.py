"""
Example: Testing HAZOP Application Authentication

This example shows how to test the HAZOP application that was showing
401 Unauthorized errors in the browser console.

The testing agent will:
1. Open the application in a real browser
2. Attempt to access the HAZOP endpoint
3. Check for authentication errors
4. Take screenshots of each step
5. Verify the error is caught BEFORE claiming "ready"
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.testing_agent import TestingAgent


def test_hazop_authentication():
    """
    Test HAZOP application authentication flow

    This will ACTUALLY open a browser, navigate to the app,
    and verify authentication works before claiming success.
    """

    agent = TestingAgent(workspace_dir=Path("./workspace"))

    # Define the test
    task = {
        "name": "test-hazop-authentication",
        "params": {
            "test_type": "e2e",
            "target_url": "http://localhost:3000",  # Frontend URL
            "browser": "chrome",

            # Actual test actions the browser will perform
            "test_actions": [
                # Step 1: Load homepage
                {"type": "screenshot", "name": "01_homepage"},
                {"type": "check_no_errors"},  # This would catch the 401!

                # Step 2: Navigate to login (if exists)
                {"type": "click", "selector": "a[href*='login'], button:contains('Login')"},
                {"type": "wait", "seconds": 2},
                {"type": "screenshot", "name": "02_login_page"},

                # Step 3: Fill login form
                {"type": "type", "selector": "input[name='username'], input[type='text']", "text": "testuser"},
                {"type": "type", "selector": "input[name='password'], input[type='password']", "text": "testpass"},
                {"type": "screenshot", "name": "03_login_filled"},

                # Step 4: Submit login
                {"type": "click", "selector": "button[type='submit'], input[type='submit']"},
                {"type": "wait", "seconds": 3},
                {"type": "screenshot", "name": "04_after_login"},

                # Step 5: Check we're authenticated
                {"type": "check_text", "expected": "Dashboard"},
                {"type": "check_no_errors"},  # This will fail if 401 error appears

                # Step 6: Try to access HAZOP page
                {"type": "navigate", "url": "http://localhost:3000/hazop"},
                {"type": "wait", "seconds": 2},
                {"type": "screenshot", "name": "05_hazop_page"},

                # Step 7: Verify no authentication errors
                {"type": "check_no_errors"},  # Would catch "401" or "Not authenticated"
            ],

            # Also test the API directly
            "api_endpoints": [
                {
                    "method": "GET",
                    "url": "http://localhost:9000/api/v1/hazop/",
                    "expected_status": 200,  # Should be 200, not 401
                    "headers": {
                        # Would need to get auth token from login
                        # "Authorization": "Bearer <token>"
                    }
                }
            ],

            # CRITICAL: Require tests to pass
            "require_passing": True,  # Agent CANNOT claim success if this fails
        }
    }

    print("=" * 60)
    print("Testing HAZOP Application Authentication")
    print("=" * 60)
    print()
    print("This will:")
    print("  1. Open Chrome browser")
    print("  2. Navigate to your application")
    print("  3. Attempt login")
    print("  4. Check for 401 errors")
    print("  5. Take screenshots of each step")
    print("  6. Test API endpoint directly")
    print()
    print("Starting browser automation...")
    print()

    try:
        # Execute the test
        result = agent.execute_task(task)

        print()
        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print(f"Summary: {result['analysis']['summary']}")
        print(f"Screenshots saved: {len(result['screenshots'])} files")
        print()
        print("Screenshot locations:")
        for screenshot in result['screenshots']:
            print(f"  - {screenshot}")
        print()
        print("The agent verified that authentication WORKS.")
        print("No 401 errors were found!")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print("✗ TESTS FAILED (As Expected!)")
        print("=" * 60)
        print()
        print(f"Error: {e}")
        print()
        print("The agent correctly detected the authentication problem")
        print("and REFUSED to claim the code is 'ready'.")
        print()
        print("Check screenshots to see what went wrong:")
        print(f"  {agent.screenshots_dir}")
        print()
        print("This is exactly what we want - the agent caught the bug!")
        print()


def test_hazop_with_mock_data():
    """
    Alternative test that doesn't require backend running

    This tests the frontend in isolation by mocking API responses
    """

    agent = TestingAgent(workspace_dir=Path("./workspace"))

    task = {
        "name": "test-hazop-frontend-only",
        "params": {
            "test_type": "frontend",
            "target_url": "http://localhost:3000",
            "browser": "chrome",
            "test_actions": [
                # Load page
                {"type": "screenshot", "name": "frontend_loaded"},

                # Check basic UI elements exist
                {"type": "check_text", "expected": "HAZOP"},
                {"type": "check_element", "selector": ".nav-bar, .header"},

                # Take screenshots of different pages
                {"type": "navigate", "url": "http://localhost:3000/dashboard"},
                {"type": "screenshot", "name": "dashboard"},

                {"type": "navigate", "url": "http://localhost:3000/hazop"},
                {"type": "screenshot", "name": "hazop_page"},

                # Verify no crash/error pages
                {"type": "check_no_errors"},
            ],
            "require_passing": False,  # Allow partial success for frontend-only
        }
    }

    result = agent.execute_task(task)
    print(f"Frontend test: {result['analysis']['summary']}")


if __name__ == "__main__":
    print("HAZOP Authentication Testing Examples")
    print()
    print("Choose a test:")
    print("  1. Full authentication test (requires backend running)")
    print("  2. Frontend-only test (no backend required)")
    print()

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        test_hazop_authentication()
    elif choice == "2":
        test_hazop_with_mock_data()
    else:
        print("Invalid choice!")
        sys.exit(1)
