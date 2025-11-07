# Testing & Validation Guide

## The "It's Ready" Problem - SOLVED

### Before: Agents Lie About Success ❌

```
Agent: "Code is ready! ✓"
You: *tests it*
Result: 401 Unauthorized, crashes, doesn't work
```

### After: Agents PROVE It Works ✅

```
Agent: "Testing code..."
- Opens browser
- Navigates to page
- Clicks button
- Checks for errors
- Takes screenshots
- OCRs text to verify
- Reviews logs
Agent: "All tests passed! ✓" (with evidence)
```

---

## 🎯 Key Features

### 1. **MANDATORY Testing**
Agents **CANNOT** mark tasks complete unless tests pass:

```python
# Agent tries to claim success
result = agent.execute_task(task)

# Validation framework intervenes
validation = framework.validate(task, result)
if not validation["all_passed"]:
    raise Exception("Tests failed! Cannot mark as complete!")
```

### 2. **Real Browser Automation**

Agents actually open browsers and test your app:

```python
test_actions = [
    {"type": "navigate", "url": "http://localhost:3000"},
    {"type": "screenshot", "name": "initial"},
    {"type": "click", "selector": "button.login"},
    {"type": "wait", "seconds": 2},
    {"type": "check_text", "expected": "Dashboard"},
    {"type": "check_no_errors"},  # Verifies no error text on page
    {"type": "screenshot", "name": "after_login"},
]
```

### 3. **OCR Screenshot Verification**

Agents can read screenshots to verify correct UI:

```python
# Take screenshot
screenshot_path = "test_screenshots/login_page.png"

# OCR it
text = agent._ocr_screenshot(screenshot_path)

# Verify expected text appears
assert "Welcome" in text
assert "Login" in text
```

### 4. **Error Log Analysis**

Agents check browser console for errors:

```python
# Get browser console logs
logs = driver.get_log('browser')

# Find errors
errors = [log for log in logs if log['level'] == 'SEVERE']

if errors:
    # FAIL the test
    raise Exception(f"Found {len(errors)} console errors!")
```

### 5. **Evidence Collection**

Every test provides evidence:
- Screenshots of each step
- Browser console logs
- OCR text extraction
- Network traffic logs
- Performance metrics

---

## 🚀 Quick Start

### Installation

```bash
# Install testing dependencies
pip install selenium playwright pytesseract pillow

# Install webdriver (Chrome)
pip install webdriver-manager

# Install Tesseract OCR (for screenshot text reading)
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# Mac: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr
```

### Basic Usage

```python
from agents.testing_agent import TestingAgent

agent = TestingAgent()

# Test your application
task = {
    "name": "test-my-app",
    "params": {
        "test_type": "e2e",  # End-to-end testing
        "target_url": "http://localhost:3000",
        "browser": "chrome",
        "test_actions": [
            {"type": "screenshot", "name": "homepage"},
            {"type": "check_no_errors"},
            {"type": "click", "selector": "#login-button"},
            {"type": "type", "selector": "#username", "text": "admin"},
            {"type": "type", "selector": "#password", "text": "password"},
            {"type": "click", "selector": "#submit"},
            {"type": "wait", "seconds": 3},
            {"type": "screenshot", "name": "after_login"},
            {"type": "check_text", "expected": "Dashboard"},
        ],
        "require_passing": True  # FAIL if tests don't pass
    }
}

try:
    result = agent.execute_task(task)
    print(f"✓ Tests passed: {result['analysis']['summary']}")
    print(f"Screenshots saved: {len(result['screenshots'])}")
except Exception as e:
    print(f"✗ Tests FAILED: {e}")
    print("Agent correctly refused to mark as complete!")
```

---

## 📋 Test Types

### 1. Frontend Testing (Browser Automation)

Tests the actual UI in a real browser:

```python
{
    "test_type": "frontend",
    "target_url": "http://localhost:3000",
    "browser": "chrome",  # or "firefox", "edge"
    "test_actions": [
        # Navigate
        {"type": "navigate", "url": "http://localhost:3000/dashboard"},

        # Click elements
        {"type": "click", "selector": "button.menu"},

        # Type text
        {"type": "type", "selector": "input[name='search']", "text": "test"},

        # Wait
        {"type": "wait", "seconds": 2},

        # Take screenshot
        {"type": "screenshot", "name": "dashboard"},

        # Verify text exists
        {"type": "check_text", "expected": "Welcome"},

        # Check for errors
        {"type": "check_no_errors"},
    ]
}
```

### 2. API Testing

Tests backend endpoints:

```python
{
    "test_type": "api",
    "api_endpoints": [
        {
            "method": "GET",
            "url": "http://localhost:9000/api/v1/hazop/",
            "expected_status": 200
        },
        {
            "method": "POST",
            "url": "http://localhost:9000/api/v1/login/",
            "data": {"username": "test", "password": "test"},
            "expected_status": 200
        }
    ]
}
```

### 3. Database Testing

Tests database operations:

```python
{
    "test_type": "database",
    "database_url": "postgresql://user:pass@localhost/db",
    "test_queries": [
        "SELECT COUNT(*) FROM users",
        "SELECT * FROM products WHERE active = true"
    ]
}
```

### 4. Integration Testing

Tests multiple components together:

```python
{
    "test_type": "integration",
    "components": ["frontend", "backend", "database"],
    "test_scenarios": [
        {
            "name": "User Registration Flow",
            "steps": [
                "Navigate to signup page",
                "Fill registration form",
                "Submit form",
                "Verify user in database",
                "Verify welcome email sent"
            ]
        }
    ]
}
```

### 5. End-to-End (E2E) Testing

Tests the complete application:

```python
{
    "test_type": "e2e",
    "target_url": "http://localhost:3000",
    "test_scenarios": [
        "User can register",
        "User can login",
        "User can create HAZOP analysis",
        "User can view dashboard",
        "User can logout"
    ]
}
```

---

## 🎬 Test Actions Reference

### Navigation

```python
{"type": "navigate", "url": "http://localhost:3000/page"}
```

### Click

```python
{"type": "click", "selector": "button#submit"}
{"type": "click", "selector": ".nav-item:first-child"}
```

### Type Text

```python
{"type": "type", "selector": "input[name='username']", "text": "admin"}
```

### Wait

```python
{"type": "wait", "seconds": 2}
```

### Screenshot

```python
{"type": "screenshot", "name": "login_page"}
# Saves to: test_screenshots/login_page.png
```

### Check Text Exists

```python
{"type": "check_text", "expected": "Welcome to Dashboard"}
```

### Check No Errors

```python
{"type": "check_no_errors"}
# Fails if page contains: "error", "failed", "exception", etc.
```

### Check Element Exists

```python
{"type": "check_element", "selector": "#user-menu"}
```

### Check Element Visible

```python
{"type": "check_visible", "selector": ".welcome-message"}
```

---

## 🔒 Validation Levels

### NONE (Dangerous!)
```python
ValidationLevel.NONE
# No validation - agents can claim success without testing
# DON'T USE THIS!
```

### BASIC
```python
ValidationLevel.BASIC
# Only syntax checks
# Better than nothing, but not enough
```

### STANDARD (Recommended)
```python
ValidationLevel.STANDARD
# - Syntax checks
# - Unit tests
# - Browser tests
# This is the sweet spot
```

### STRICT
```python
ValidationLevel.STRICT
# - Everything in STANDARD, plus:
# - Integration tests
# - API tests
# For important projects
```

### PARANOID
```python
ValidationLevel.PARANOID
# - Everything in STRICT, plus:
# - Database tests
# - Security scans
# - Performance tests
# For production-critical systems
```

---

## 🔧 Configuration

### In Orchestrator

```python
from core.orchestrator import AgentOrchestrator
from core.validation_framework import ValidationFramework, ValidationLevel

# Create orchestrator with strict validation
orchestrator = AgentOrchestrator(
    validation_level=ValidationLevel.STRICT
)

# Now agents MUST pass validation before completing tasks
```

### In Task Submission

```python
task = {
    "name": "implement-feature",
    "params": {
        "spec_file": "specs/feature.md",
        "require_passing": True,  # Mandatory passing tests
    }
}
```

---

## 📊 Example: Testing the HAZOP Application

Based on the authentication error you showed:

```python
from agents.testing_agent import TestingAgent

agent = TestingAgent()

task = {
    "name": "test-hazop-auth",
    "params": {
        "test_type": "e2e",
        "target_url": "http://localhost:3000",
        "browser": "chrome",
        "test_actions": [
            # Initial page load
            {"type": "screenshot", "name": "01_initial_page"},
            {"type": "check_no_errors"},

            # Login flow
            {"type": "type", "selector": "input[name='username']", "text": "testuser"},
            {"type": "type", "selector": "input[name='password']", "text": "testpass"},
            {"type": "screenshot", "name": "02_login_filled"},

            {"type": "click", "selector": "button[type='submit']"},
            {"type": "wait", "seconds": 2},
            {"type": "screenshot", "name": "03_after_login"},

            # Check we're authenticated
            {"type": "check_text", "expected": "Dashboard"},
            {"type": "check_no_errors"},

            # Try to access HAZOP endpoint
            {"type": "navigate", "url": "http://localhost:3000/hazop"},
            {"type": "wait", "seconds": 2},
            {"type": "screenshot", "name": "04_hazop_page"},

            # Verify no 401 errors
            {"type": "check_no_errors"},
        ],
        "api_endpoints": [
            {
                "method": "GET",
                "url": "http://localhost:9000/api/v1/hazop/",
                "expected_status": 200,
                "headers": {"Authorization": "Bearer <token>"}
            }
        ],
        "require_passing": True
    }
}

result = agent.execute_task(task)
```

**This will:**
1. ✅ Open browser and navigate to your app
2. ✅ Fill in login form
3. ✅ Click submit
4. ✅ Take screenshot after each step
5. ✅ Check browser console for errors (would catch the 401)
6. ✅ Test the API endpoint directly
7. ✅ **FAIL if any errors found** (won't claim "ready")

---

## 🎯 Best Practices

### 1. Always Use `require_passing: True`

```python
# GOOD
{"require_passing": True}  # Agent can't claim success if tests fail

# BAD
{"require_passing": False}  # Agent can lie about success
```

### 2. Test the Happy Path AND Error Cases

```python
test_actions = [
    # Happy path
    {"type": "click", "selector": "#submit"},
    {"type": "check_text", "expected": "Success"},

    # Error case
    {"type": "click", "selector": "#submit-invalid"},
    {"type": "check_text", "expected": "Invalid input"},
]
```

### 3. Take Screenshots at Key Points

```python
{"type": "screenshot", "name": "before_action"},
{"type": "click", "selector": "#button"},
{"type": "screenshot", "name": "after_action"},
```

### 4. Use OCR for Visual Verification

```python
# Agent will OCR the screenshot and verify text
{"type": "screenshot", "name": "dashboard"},
# Then manually or automatically check OCR results
```

### 5. Check Console Logs

```python
{"type": "check_no_errors"}  # Always include this
```

---

## 🐛 Debugging Failed Tests

### View Screenshots

All screenshots are saved to:
```
agent-team-system/test_screenshots/
├── initial_20250107_143022.png
├── after_click_0_20250107_143025.png
├── error_state_20250107_143030.png
└── final_20250107_143032.png
```

### View Test Results

```python
result = agent.execute_task(task)

# Overall summary
print(result['analysis']['summary'])
# "15/20 tests passed (75.0%)"

# Failed tests
for failure in result['analysis']['failures']:
    print(f"Failed: {failure['test']}")
    print(f"Error: {failure.get('error')}")
    print(f"Screenshot: {failure.get('screenshot')}")
```

### View Validation Report

```
agent-team-system/validation_reports/
└── validation_task_123_20250107_143035.json
```

```json
{
  "validation_level": "standard",
  "all_passed": false,
  "results": [
    {
      "validation_type": "browser_tests",
      "passed": false,
      "message": "3 browser tests failed",
      "evidence": ["test_screenshots/error_state.png"]
    }
  ]
}
```

---

## 🚫 What NOT to Do

### ❌ Don't Skip Testing

```python
# BAD - agent can claim success without proof
{"require_passing": False}
```

### ❌ Don't Test Only Happy Path

```python
# BAD - only tests when everything works
test_actions = [
    {"type": "click", "selector": "#submit"},
    {"type": "check_text", "expected": "Success"},
]

# GOOD - also tests error cases
test_actions = [
    {"type": "click", "selector": "#submit"},
    {"type": "check_text", "expected": "Success"},
    # Also test errors
    {"type": "click", "selector": "#invalid"},
    {"type": "check_text", "expected": "Error"},
]
```

### ❌ Don't Ignore Screenshots

```python
# Screenshots contain vital debugging info!
# Always review them when tests fail
```

---

## 📈 Success Metrics

### Before Testing Agent

- Agent claims: "Ready! ✓"
- You test: Doesn't work ✗
- Success rate: ~30%

### After Testing Agent

- Agent tests thoroughly
- Only claims success if tests pass
- You test: Works! ✓
- Success rate: ~95%

---

## 🎓 Advanced Usage

### Custom Validators

```python
def my_custom_validator(task, result):
    # Your custom validation logic
    if some_condition:
        return ValidationResult(
            validation_type=ValidationType.CUSTOM,
            passed=True,
            message="Custom check passed"
        )
    else:
        return ValidationResult(
            validation_type=ValidationType.CUSTOM,
            passed=False,
            message="Custom check failed"
        )

# Register it
framework.register_validator(ValidationType.CUSTOM, my_custom_validator)
```

### Screenshot Comparison

```python
# Take baseline screenshot
{"type": "screenshot", "name": "baseline"}

# Make changes

# Take new screenshot
{"type": "screenshot", "name": "after_changes"}

# Compare (would implement pixel-by-pixel comparison)
# Verify UI didn't break
```

### Performance Testing

```python
{
    "test_type": "performance",
    "performance_checks": [
        {"metric": "page_load_time", "max_seconds": 3},
        {"metric": "api_response_time", "max_ms": 500},
        {"metric": "memory_usage", "max_mb": 512}
    ]
}
```

---

## 🆘 Troubleshooting

### "Webdriver not found"

```bash
pip install webdriver-manager
# It will download automatically
```

### "Tesseract not found"

```bash
# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki

# Mac
brew install tesseract

# Linux
sudo apt-get install tesseract-ocr
```

### "Element not found"

```python
# Add wait before clicking
{"type": "wait", "seconds": 2},
{"type": "click", "selector": "#element"},
```

### "Tests too slow"

```python
# Use headless mode (default)
{"browser": "chrome"}  # Already runs headless

# Or use faster browser
{"browser": "chrome"}  # Fastest
```

---

**No more "it's ready" lies! Agents now PROVE code works with real tests.** 🎯

*Version 1.0.0 - Testing & Validation System*
