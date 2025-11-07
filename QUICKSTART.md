# Agent Readiness Check - Quick Start Guide

## 🎯 Purpose

This validation framework ensures AI agents **prove their work** before claiming success. No more "it's ready" followed by failures when humans test it.

## ⚡ Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements_validation.txt

# Install Playwright browsers
playwright install

# Install Tesseract OCR (for screenshot text verification)
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# macOS:
brew install tesseract

# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### 2. Create Your Test Configuration

```bash
# Copy the example config
cp test_config.example.yaml test_config.yaml

# Edit it for your feature
nano test_config.yaml
```

### 3. Run Validation

```bash
# Make validator executable
chmod +x agent_validator.py

# Run complete validation
python agent_validator.py --task-id TASK-123 --config test_config.yaml
```

## 📋 For AI Agents: Mandatory Workflow

When you (the AI agent) are assigned a task, you **MUST** follow this workflow:

### Step-by-Step Process

```
1. ✅ Implement the feature/fix
2. ✅ Create test_config.yaml for your changes
3. ✅ Start the development server (frontend & backend)
4. ✅ Run: python agent_validator.py --task-id YOUR-TASK-ID --config test_config.yaml
5. ✅ Wait for all validation stages to complete
6. ✅ If APPROVED: Commit code + validation report
7. ❌ If REJECTED: Fix issues and return to step 4
```

### What Gets Validated

The framework runs these stages in order:

1. **Code Validation** - Linting, type checking, unit tests
2. **E2E Testing** - Browser automation, clicks buttons, fills forms
3. **Log Analysis** - Scans logs for errors and exceptions
4. **Visual Verification** - OCR on screenshots, detects error indicators
5. **Proof of Work** - Generates report with verification hash

**If ANY stage fails, you CANNOT proceed.**

## 🎨 Creating Test Configurations

### Example: Testing a "Create User" Feature

```yaml
task_id: TASK-456
feature: user_registration
base_url: http://localhost:3000

e2e_tests:
  - name: register_new_user
    url: /register
    interactions:
      - action: type
        selector: 'input[name="email"]'
        value: 'test@example.com'
      - action: type
        selector: 'input[name="password"]'
        value: 'SecurePass123!'
      - action: type
        selector: 'input[name="confirmPassword"]'
        value: 'SecurePass123!'
      - action: click
        selector: 'button[type="submit"]'
      - action: wait
        selector: '.success-message'
        timeout: 5000
    validations:
      - type: element_visible
        selector: '.success-message'
      - type: text_content
        selector: '.success-message'
        expected: 'Registration successful'
      - type: url_matches
        expected: '/dashboard'

log_analysis:
  paths:
    - ./backend/logs/application.log
  time_window_minutes: 5

visual_verification:
  screenshots:
    - path: ./validation_screenshots/register_new_user_step_4.png
      expected_text:
        - 'Registration successful'
        - 'Welcome'
      error_detection: true
```

### Available Interaction Actions

```yaml
# Click an element
- action: click
  selector: 'button.submit'

# Type into an input field
- action: type
  selector: 'input[name="username"]'
  value: 'testuser'

# Select from dropdown
- action: select
  selector: 'select[name="country"]'
  value: 'USA'

# Wait for element to appear
- action: wait
  selector: '.loading-complete'
  timeout: 10000  # milliseconds
```

### Available Validation Types

```yaml
# Check if element is visible
- type: element_visible
  selector: '.success-banner'

# Verify text content
- type: text_content
  selector: '.user-name'
  expected: 'John Doe'

# Count elements
- type: element_count
  selector: 'table tbody tr'
  expected: 5

# Verify URL
- type: url_matches
  expected: '/profile'
```

## 📊 Understanding Validation Output

### Success Output

```
============================================================
AGENT READINESS CHECK - VALIDATION STARTING
============================================================
Task ID: TASK-123
Config: test_config.yaml
Agent: claude_agent
============================================================

============================================================
STAGE 1: Code Validation
============================================================
  ✅ Linting: No linting errors
  ✅ Type Checking: All types valid
  ✅ Unit Tests: 45/45 tests passed

============================================================
STAGE 2: E2E Testing
============================================================
  ✅ create_loading_bay
  ✅ verify_loading_bay_in_list
  ✅ update_loading_bay_status

  Tests: 3/3 passed

============================================================
STAGE 3: Log Analysis
============================================================
  📄 Analyzing: ./backend/logs/application.log
  ✅ No errors found in logs

============================================================
STAGE 4: Visual Verification
============================================================
  🖼️  Verifying: ./validation_screenshots/create_loading_bay_initial.png
  ✅ Verification passed

============================================================
✅ AGENT VALIDATION COMPLETE - WORK APPROVED
============================================================

Report: ./validation_reports/TASK-123_claude_agent_report.json
Summary: ./validation_reports/TASK-123_summary.md
Verification Hash: a3f8d92b1e4c5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0

✅ Agent may now commit and push changes.
```

### Failure Output

```
============================================================
STAGE 2: E2E Testing
============================================================
  ✅ create_loading_bay
  ❌ verify_loading_bay_in_list: Element NOT visible: table.loading-bays
  ❌ update_loading_bay_status: Text mismatch in .status-badge: expected 'MAINTENANCE', got 'AVAILABLE'

  Tests: 1/3 passed

============================================================
❌ AGENT VALIDATION FAILED
============================================================
Error: E2E testing failed: 2/3 tests failed
Report: ./validation_reports/TASK-123_claude_agent_report.json
Summary: ./validation_reports/TASK-123_summary.md

❌ Agent must fix issues and re-run validation.
```

## 🔍 Viewing Validation Reports

### JSON Report (Machine-Readable)

```bash
cat ./validation_reports/TASK-123_claude_agent_report.json
```

Contains:
- All stage results
- Screenshots paths
- Error details
- Verification hash

### Markdown Summary (Human-Readable)

```bash
cat ./validation_reports/TASK-123_summary.md
```

Formatted report with:
- Status icons
- Stage details
- Artifact links
- Final approval/rejection

## 🎥 Reviewing Test Evidence

### Screenshots

All E2E tests automatically capture screenshots:

```bash
ls -lh validation_screenshots/

# Example output:
# create_loading_bay_initial.png
# create_loading_bay_step_1.png
# create_loading_bay_step_2.png
# verify_loading_bay_in_list_initial.png
```

### Videos (Optional)

Playwright can record videos of tests:

```bash
ls -lh validation_videos/

# Videos are saved for each test run
```

## 🔧 Troubleshooting

### Issue: "Tesseract not found"

```bash
# Install Tesseract OCR
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# macOS:
brew install tesseract

# Verify installation:
tesseract --version
```

### Issue: "Playwright browsers not installed"

```bash
playwright install
```

### Issue: "Connection refused" during E2E tests

Make sure your development servers are running:

```bash
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Run validation
python agent_validator.py --task-id TASK-123 --config test_config.yaml
```

### Issue: "Element not found" errors

Check your selectors in `test_config.yaml`:

```yaml
# Use Playwright's selector syntax
selector: 'button:has-text("Submit")'  # Good
selector: 'button.btn-submit'          # Good
selector: '#submit-button'             # Good

# Test selectors in browser console:
document.querySelector('button:has-text("Submit")')
```

### Issue: False positives in visual verification

Adjust error detection sensitivity in config:

```yaml
visual_verification:
  screenshots:
    - path: ./screenshots/page.png
      expected_text:
        - 'Success'
      error_detection: false  # Disable if too sensitive
```

## 📚 Advanced Usage

### Running Specific Stages Only

```python
# Run only E2E tests
from agent_validator import E2EValidationStage

config = {...}
stage = E2EValidationStage(config)
result = await stage.execute()
```

### Custom Validation Stages

Create your own validation stage:

```python
from agent_validator import ValidationStage

class CustomValidationStage(ValidationStage):
    def __init__(self, config):
        super().__init__("Custom Validation")
        self.config = config

    async def execute(self) -> Dict:
        # Your validation logic here
        return {
            'status': 'PASSED',
            'timestamp': datetime.now().isoformat(),
            'details': {...}
        }
```

### CI/CD Integration

Add to your `.github/workflows/agent-validation.yml`:

```yaml
name: Agent Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          pip install -r requirements_validation.txt
          playwright install
          sudo apt-get install tesseract-ocr

      - name: Run validation
        run: |
          python agent_validator.py \
            --task-id ${{ github.event.pull_request.number }} \
            --config test_config.yaml
```

## 🎯 Best Practices

### For Agents

1. **Always start servers before validation**
2. **Use realistic test data** (don't use "test123" everywhere)
3. **Test error states** (not just happy paths)
4. **Review screenshots manually** before claiming success
5. **Check logs thoroughly** even if tests pass

### For Test Configurations

1. **Name tests descriptively** (`create_user` not `test1`)
2. **Use stable selectors** (avoid xpath, prefer data attributes)
3. **Add explicit waits** (don't rely on timing)
4. **Test one thing per test case** (atomic tests)
5. **Include negative tests** (test validation, error handling)

### For Visual Verification

1. **Capture screenshots at key moments** (after actions, before validations)
2. **Use OCR for critical text** (success messages, error messages)
3. **Enable error detection** for pages that should have no errors
4. **Compare with baselines** for visual regression testing

## 📖 Examples

### Example 1: Login Flow

```yaml
e2e_tests:
  - name: successful_login
    url: /login
    interactions:
      - action: type
        selector: 'input[name="email"]'
        value: 'admin@example.com'
      - action: type
        selector: 'input[name="password"]'
        value: 'password123'
      - action: click
        selector: 'button[type="submit"]'
      - action: wait
        selector: '.dashboard'
        timeout: 5000
    validations:
      - type: url_matches
        expected: '/dashboard'
      - type: element_visible
        selector: '.user-menu'

  - name: failed_login_wrong_password
    url: /login
    interactions:
      - action: type
        selector: 'input[name="email"]'
        value: 'admin@example.com'
      - action: type
        selector: 'input[name="password"]'
        value: 'wrongpassword'
      - action: click
        selector: 'button[type="submit"]'
    validations:
      - type: element_visible
        selector: '.error-message'
      - type: text_content
        selector: '.error-message'
        expected: 'Invalid credentials'
```

### Example 2: Form Validation

```yaml
e2e_tests:
  - name: form_validation_empty_fields
    url: /register
    interactions:
      - action: click
        selector: 'button[type="submit"]'
    validations:
      - type: element_visible
        selector: 'input[name="email"] + .error'
      - type: element_visible
        selector: 'input[name="password"] + .error'
      - type: text_content
        selector: 'input[name="email"] + .error'
        expected: 'required'
```

## 🚀 Next Steps

1. Read the full [AGENT_READINESS_FRAMEWORK.md](./AGENT_READINESS_FRAMEWORK.md)
2. Create your first `test_config.yaml`
3. Run validation on a completed feature
4. Review the generated reports
5. Integrate into your git workflow

## 💡 Tips

- **Screenshot everything** - More screenshots = better debugging
- **Verbose logging** - Enable detailed logs during validation
- **Incremental testing** - Test each interaction step-by-step
- **Mock external services** - Don't depend on external APIs
- **Consistent test data** - Use fixtures for repeatable tests

## 📞 Support

For issues or questions:
1. Check [AGENT_READINESS_FRAMEWORK.md](./AGENT_READINESS_FRAMEWORK.md) - comprehensive documentation
2. Review example configs in `test_config.example.yaml`
3. Check troubleshooting section above
4. Verify all dependencies are installed

---

**Remember:** This framework exists to prevent the frustration of agents claiming "ready" when the work isn't actually ready. Embrace the validation process - it makes everyone's life easier! 🎯
