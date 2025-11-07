# Agent Readiness Check Framework

## Overview

This framework establishes mandatory validation protocols for AI agents before they can report "ready" or "good to go" status. Agents must provide **proof of work** through automated testing, log analysis, and visual verification.

**Problem Statement:** Agents frequently claim task completion without proper validation, leading to failures when humans attempt to verify the work.

**Solution:** Enforce a multi-stage validation pipeline that agents cannot bypass.

---

## 1. Agent Validation Protocol

### 1.1 Mandatory Validation Stages

All agents MUST complete these stages before reporting success:

```
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: Code Validation                                   │
│  ├─ Syntax check (linting)                                  │
│  ├─ Type checking (TypeScript/mypy)                         │
│  ├─ Unit test execution                                     │
│  └─ Code coverage minimum: 80%                              │
├─────────────────────────────────────────────────────────────┤
│  STAGE 2: Integration Testing                               │
│  ├─ API endpoint testing                                    │
│  ├─ Database migration validation                           │
│  ├─ Service dependency checks                               │
│  └─ Mock external services                                  │
├─────────────────────────────────────────────────────────────┤
│  STAGE 3: End-to-End Testing (MANDATORY)                    │
│  ├─ Browser automation                                      │
│  ├─ User interaction simulation                             │
│  ├─ Form submission and validation                          │
│  ├─ Navigation flow testing                                 │
│  └─ Error state handling                                    │
├─────────────────────────────────────────────────────────────┤
│  STAGE 4: Log Analysis                                      │
│  ├─ Review application logs                                 │
│  ├─ Scan for ERROR/WARNING messages                         │
│  ├─ Verify expected log entries                             │
│  └─ Check for stack traces                                  │
├─────────────────────────────────────────────────────────────┤
│  STAGE 5: Visual Verification                               │
│  ├─ Screenshot capture                                      │
│  ├─ OCR text extraction                                     │
│  ├─ UI element detection                                    │
│  └─ Visual regression testing                               │
├─────────────────────────────────────────────────────────────┤
│  STAGE 6: Proof-of-Work Report                              │
│  ├─ Generate test execution report                          │
│  ├─ Attach screenshots and logs                             │
│  ├─ Document all test results                               │
│  └─ Sign off with verification hash                         │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Validation Enforcement

**Agents CANNOT proceed to the next stage if the current stage fails.**

Example validation gate:

```python
class AgentValidationGate:
    def __init__(self):
        self.stages = [
            CodeValidationStage(),
            IntegrationTestingStage(),
            E2ETestingStage(),
            LogAnalysisStage(),
            VisualVerificationStage(),
            ProofOfWorkStage()
        ]

    async def validate_agent_work(self, task_id: str) -> ValidationReport:
        """Run all validation stages sequentially"""
        report = ValidationReport(task_id=task_id)

        for stage in self.stages:
            print(f"[VALIDATION] Running {stage.name}...")
            result = await stage.execute()
            report.add_stage_result(stage.name, result)

            if not result.passed:
                report.status = "FAILED"
                report.failed_at_stage = stage.name
                raise ValidationFailure(
                    f"Agent work REJECTED at stage: {stage.name}\n"
                    f"Reason: {result.error_message}\n"
                    f"Agent must re-work and re-validate."
                )

        report.status = "PASSED"
        return report
```

---

## 2. End-to-End Testing Requirements

### 2.1 Browser Automation Stack

**Required Tools:**
- **Playwright** (recommended) - Cross-browser automation with auto-wait
- **Selenium** (alternative) - Mature ecosystem
- **Cypress** (alternative) - Developer-friendly testing

**Installation:**
```bash
# Playwright (recommended)
pip install playwright pytest-playwright
playwright install

# Selenium (alternative)
pip install selenium webdriver-manager

# Cypress (JavaScript/TypeScript)
npm install --save-dev cypress @cypress/playwright
```

### 2.2 E2E Test Template for Agents

Agents MUST use this template when validating their work:

```python
# test_e2e_agent_validation.py
import pytest
from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict
import json
from datetime import datetime

class E2EValidationTest:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.screenshots_dir = "./validation_screenshots"
        self.logs_dir = "./validation_logs"
        self.test_results: List[Dict] = []

    async def run_validation(self, test_cases: List[Dict]) -> Dict:
        """
        Execute E2E validation for agent work

        Args:
            test_cases: List of test scenarios to execute

        Returns:
            Validation report with screenshots and logs
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                record_video_dir="./validation_videos"
            )

            # Capture console logs
            page = await context.new_page()
            page.on("console", self._capture_console_log)
            page.on("pageerror", self._capture_page_error)

            for test_case in test_cases:
                result = await self._execute_test_case(page, test_case)
                self.test_results.append(result)

            await browser.close()

            return self._generate_report()

    async def _execute_test_case(self, page: Page, test_case: Dict) -> Dict:
        """Execute a single test case with full validation"""
        test_name = test_case['name']
        print(f"\n[E2E TEST] Executing: {test_name}")

        result = {
            'name': test_name,
            'status': 'PENDING',
            'steps': [],
            'screenshots': [],
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Step 1: Navigate to page
            await page.goto(f"{self.base_url}{test_case['url']}")
            await page.wait_for_load_state('networkidle')

            screenshot_path = f"{self.screenshots_dir}/{test_name}_step1_loaded.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            result['screenshots'].append(screenshot_path)
            result['steps'].append("✓ Page loaded successfully")

            # Step 2: Execute interactions
            for interaction in test_case.get('interactions', []):
                await self._execute_interaction(page, interaction, result)

            # Step 3: Validate expected outcomes
            for validation in test_case.get('validations', []):
                await self._execute_validation(page, validation, result)

            # Step 4: Check for errors in console
            if result['errors']:
                result['status'] = 'FAILED'
                result['failure_reason'] = f"Found {len(result['errors'])} console errors"
            else:
                result['status'] = 'PASSED'

        except Exception as e:
            result['status'] = 'FAILED'
            result['failure_reason'] = str(e)
            screenshot_path = f"{self.screenshots_dir}/{test_name}_error.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            result['screenshots'].append(screenshot_path)

        return result

    async def _execute_interaction(self, page: Page, interaction: Dict, result: Dict):
        """Execute user interaction (click, type, select, etc.)"""
        action = interaction['action']
        selector = interaction['selector']

        if action == 'click':
            await page.click(selector)
            result['steps'].append(f"✓ Clicked: {selector}")

        elif action == 'type':
            await page.fill(selector, interaction['value'])
            result['steps'].append(f"✓ Typed into: {selector}")

        elif action == 'select':
            await page.select_option(selector, interaction['value'])
            result['steps'].append(f"✓ Selected: {interaction['value']} in {selector}")

        elif action == 'wait':
            await page.wait_for_selector(selector, timeout=interaction.get('timeout', 5000))
            result['steps'].append(f"✓ Waited for: {selector}")

        # Always take screenshot after interaction
        screenshot_path = f"{self.screenshots_dir}/{result['name']}_{action}_{len(result['screenshots'])}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        result['screenshots'].append(screenshot_path)

    async def _execute_validation(self, page: Page, validation: Dict, result: Dict):
        """Validate expected outcomes"""
        validation_type = validation['type']

        if validation_type == 'element_visible':
            selector = validation['selector']
            is_visible = await page.is_visible(selector)
            if is_visible:
                result['steps'].append(f"✓ Element visible: {selector}")
            else:
                result['errors'].append(f"✗ Element NOT visible: {selector}")

        elif validation_type == 'text_content':
            selector = validation['selector']
            expected_text = validation['expected']
            actual_text = await page.text_content(selector)
            if expected_text in actual_text:
                result['steps'].append(f"✓ Text validation passed: {selector}")
            else:
                result['errors'].append(
                    f"✗ Text mismatch in {selector}:\n"
                    f"  Expected: {expected_text}\n"
                    f"  Actual: {actual_text}"
                )

        elif validation_type == 'element_count':
            selector = validation['selector']
            expected_count = validation['expected']
            actual_count = await page.locator(selector).count()
            if actual_count == expected_count:
                result['steps'].append(f"✓ Element count correct: {selector} = {actual_count}")
            else:
                result['errors'].append(
                    f"✗ Element count mismatch for {selector}:\n"
                    f"  Expected: {expected_count}\n"
                    f"  Actual: {actual_count}"
                )

        elif validation_type == 'url_matches':
            expected_url = validation['expected']
            actual_url = page.url
            if expected_url in actual_url:
                result['steps'].append(f"✓ URL validation passed")
            else:
                result['errors'].append(
                    f"✗ URL mismatch:\n"
                    f"  Expected: {expected_url}\n"
                    f"  Actual: {actual_url}"
                )

    def _capture_console_log(self, msg):
        """Capture browser console messages"""
        if msg.type in ['error', 'warning']:
            self.test_results[-1]['errors'].append({
                'type': 'console',
                'level': msg.type,
                'text': msg.text
            })

    def _capture_page_error(self, error):
        """Capture JavaScript errors"""
        self.test_results[-1]['errors'].append({
            'type': 'javascript',
            'message': str(error)
        })

    def _generate_report(self) -> Dict:
        """Generate final validation report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['status'] == 'PASSED')
        failed_tests = total_tests - passed_tests

        return {
            'summary': {
                'total': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': f"{(passed_tests/total_tests)*100:.2f}%"
            },
            'tests': self.test_results,
            'validation_status': 'PASSED' if failed_tests == 0 else 'FAILED'
        }

# Example usage for agents
async def agent_validate_loading_bay_feature():
    """
    Agent MUST run this before claiming success on loading bay work
    """
    validator = E2EValidationTest(base_url="http://localhost:3000")

    test_cases = [
        {
            'name': 'loading_bay_creation',
            'url': '/loading-bays',
            'interactions': [
                {'action': 'click', 'selector': 'button:has-text("New Loading Bay")'},
                {'action': 'type', 'selector': 'input[name="bay_number"]', 'value': 'BAY-001'},
                {'action': 'select', 'selector': 'select[name="status"]', 'value': 'AVAILABLE'},
                {'action': 'click', 'selector': 'button[type="submit"]'},
                {'action': 'wait', 'selector': '.success-message', 'timeout': 5000}
            ],
            'validations': [
                {'type': 'element_visible', 'selector': '.success-message'},
                {'type': 'text_content', 'selector': '.success-message', 'expected': 'Loading bay created'},
                {'type': 'url_matches', 'expected': '/loading-bays'}
            ]
        },
        {
            'name': 'loading_bay_list_display',
            'url': '/loading-bays',
            'interactions': [],
            'validations': [
                {'type': 'element_visible', 'selector': 'table.loading-bays'},
                {'type': 'element_count', 'selector': 'table.loading-bays tbody tr', 'expected': 1},
                {'type': 'text_content', 'selector': 'table.loading-bays tbody tr:first-child', 'expected': 'BAY-001'}
            ]
        }
    ]

    report = await validator.run_validation(test_cases)

    if report['validation_status'] == 'FAILED':
        raise Exception(
            f"E2E Validation FAILED:\n"
            f"  Passed: {report['summary']['passed']}/{report['summary']['total']}\n"
            f"  Failed: {report['summary']['failed']}\n"
            f"Agent cannot claim success until all tests pass."
        )

    print(f"✓ E2E Validation PASSED: {report['summary']['success_rate']}")
    return report

if __name__ == "__main__":
    import asyncio
    asyncio.run(agent_validate_loading_bay_feature())
```

---

## 3. Log Analysis Requirements

### 3.1 Automated Log Review

Agents MUST analyze application logs before claiming success:

```python
# log_analyzer.py
import re
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path

class LogAnalyzer:
    def __init__(self, log_paths: List[str]):
        self.log_paths = log_paths
        self.error_patterns = [
            r'ERROR',
            r'CRITICAL',
            r'Exception',
            r'Traceback',
            r'Failed',
            r'Error:',
            r'\[error\]',
            r'500 Internal Server Error',
            r'400 Bad Request',
            r'404 Not Found',
            r'Connection refused',
            r'Timeout',
            r'ECONNREFUSED',
            r'Cannot read property',
            r'undefined is not',
            r'null reference'
        ]
        self.warning_patterns = [
            r'WARNING',
            r'WARN',
            r'Deprecated',
            r'Memory usage high'
        ]

    def analyze_logs(self, time_window_minutes: int = 10) -> Dict:
        """
        Analyze logs from the last N minutes

        Returns:
            Report with errors, warnings, and recommendations
        """
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)

        errors = []
        warnings = []

        for log_path in self.log_paths:
            if not Path(log_path).exists():
                continue

            with open(log_path, 'r') as f:
                for line in f:
                    # Parse timestamp (adjust regex based on log format)
                    timestamp_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                    if timestamp_match:
                        log_time = datetime.strptime(timestamp_match.group(), '%Y-%m-%d %H:%M:%S')
                        if log_time < cutoff_time:
                            continue

                    # Check for errors
                    for pattern in self.error_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            errors.append({
                                'source': log_path,
                                'line': line.strip(),
                                'pattern': pattern
                            })
                            break

                    # Check for warnings
                    for pattern in self.warning_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            warnings.append({
                                'source': log_path,
                                'line': line.strip(),
                                'pattern': pattern
                            })
                            break

        return {
            'error_count': len(errors),
            'warning_count': len(warnings),
            'errors': errors,
            'warnings': warnings,
            'validation_status': 'FAILED' if len(errors) > 0 else 'PASSED',
            'recommendation': self._generate_recommendation(errors, warnings)
        }

    def _generate_recommendation(self, errors: List, warnings: List) -> str:
        """Generate recommendation based on log analysis"""
        if errors:
            return (
                f"REJECT: Found {len(errors)} errors in logs. "
                f"Agent must fix these issues before claiming success."
            )
        elif warnings:
            return (
                f"WARNING: Found {len(warnings)} warnings in logs. "
                f"Review these before deploying to production."
            )
        else:
            return "APPROVED: No errors or warnings found in recent logs."

# Agent usage
def agent_validate_logs():
    """Agent must call this before claiming task complete"""
    analyzer = LogAnalyzer([
        './backend/logs/application.log',
        './backend/logs/error.log',
        './frontend/logs/console.log',
        '/var/log/nginx/error.log'
    ])

    report = analyzer.analyze_logs(time_window_minutes=10)

    if report['validation_status'] == 'FAILED':
        print(f"❌ LOG VALIDATION FAILED:")
        for error in report['errors'][:5]:  # Show first 5 errors
            print(f"  {error['source']}: {error['line']}")
        raise Exception(
            f"Found {report['error_count']} errors in logs. "
            f"Agent cannot proceed until resolved."
        )

    print(f"✓ LOG VALIDATION PASSED: {report['recommendation']}")
    return report
```

### 3.2 Real-time Log Monitoring

For long-running operations, agents must monitor logs in real-time:

```python
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class LogMonitor(FileSystemEventHandler):
    def __init__(self, error_callback):
        self.error_callback = error_callback
        self.error_count = 0

    def on_modified(self, event):
        if event.src_path.endswith('.log'):
            with open(event.src_path, 'r') as f:
                # Read only new lines
                f.seek(0, 2)  # Go to end
                for line in f:
                    if 'ERROR' in line or 'Exception' in line:
                        self.error_count += 1
                        self.error_callback(line)

# Usage in agent validation
async def agent_monitor_during_operation():
    """Monitor logs while feature is being tested"""
    errors_detected = []

    def on_error(line):
        errors_detected.append(line)
        print(f"⚠️  ERROR DETECTED: {line}")

    monitor = LogMonitor(error_callback=on_error)
    observer = Observer()
    observer.schedule(monitor, path='./logs', recursive=True)
    observer.start()

    try:
        # Run your E2E tests here
        await run_e2e_tests()

        # Wait a bit for any delayed errors
        await asyncio.sleep(5)

        if errors_detected:
            raise Exception(
                f"Detected {len(errors_detected)} errors during operation:\n" +
                "\n".join(errors_detected[:3])
            )
    finally:
        observer.stop()
        observer.join()
```

---

## 4. Visual Verification & OCR

### 4.1 Screenshot Analysis

Agents must capture and analyze screenshots to verify UI state:

```python
# visual_verifier.py
from PIL import Image
import pytesseract
from typing import List, Dict
import cv2
import numpy as np

class VisualVerifier:
    def __init__(self, screenshot_path: str):
        self.screenshot_path = screenshot_path
        self.image = Image.open(screenshot_path)

    def extract_text(self) -> str:
        """Extract all text from screenshot using OCR"""
        text = pytesseract.image_to_string(self.image)
        return text

    def verify_text_present(self, expected_texts: List[str]) -> Dict:
        """Verify specific text appears in screenshot"""
        extracted_text = self.extract_text()

        results = {
            'screenshot': self.screenshot_path,
            'extracted_text': extracted_text,
            'verifications': [],
            'status': 'PASSED'
        }

        for expected in expected_texts:
            found = expected.lower() in extracted_text.lower()
            results['verifications'].append({
                'expected': expected,
                'found': found
            })
            if not found:
                results['status'] = 'FAILED'

        return results

    def detect_error_indicators(self) -> Dict:
        """Detect visual error indicators (red text, error icons, etc.)"""
        img_array = np.array(self.image)

        # Convert to HSV to detect red colors (common for errors)
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)

        # Red color ranges in HSV
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 100])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 + mask2

        red_pixel_count = np.sum(red_mask > 0)
        total_pixels = img_array.shape[0] * img_array.shape[1]
        red_percentage = (red_pixel_count / total_pixels) * 100

        # Also check for error keywords in OCR text
        text = self.extract_text().lower()
        error_keywords = ['error', 'failed', 'exception', 'warning', 'invalid', 'not found']
        found_errors = [kw for kw in error_keywords if kw in text]

        return {
            'red_pixel_percentage': red_percentage,
            'error_keywords_found': found_errors,
            'has_visual_errors': red_percentage > 5 or len(found_errors) > 0,
            'extracted_text': text
        }

    def compare_with_baseline(self, baseline_path: str, threshold: float = 0.95) -> Dict:
        """Compare screenshot with baseline image (visual regression)"""
        baseline = Image.open(baseline_path)

        # Resize to same dimensions
        if self.image.size != baseline.size:
            baseline = baseline.resize(self.image.size)

        # Convert to numpy arrays
        img1 = np.array(self.image)
        img2 = np.array(baseline)

        # Calculate similarity
        diff = cv2.absdiff(img1, img2)
        diff_percentage = (np.sum(diff) / (diff.size * 255)) * 100
        similarity = 1 - (diff_percentage / 100)

        return {
            'similarity': similarity,
            'threshold': threshold,
            'passed': similarity >= threshold,
            'diff_percentage': diff_percentage
        }

# Agent usage
def agent_verify_ui_output(screenshot_path: str):
    """Agent must verify UI shows correct content"""
    verifier = VisualVerifier(screenshot_path)

    # Check for expected content
    text_check = verifier.verify_text_present([
        'Loading Bay',
        'Status: AVAILABLE',
        'BAY-001'
    ])

    if text_check['status'] == 'FAILED':
        missing = [v['expected'] for v in text_check['verifications'] if not v['found']]
        raise Exception(
            f"UI Verification FAILED - Missing text:\n" +
            "\n".join(f"  - {t}" for t in missing)
        )

    # Check for error indicators
    error_check = verifier.detect_error_indicators()

    if error_check['has_visual_errors']:
        raise Exception(
            f"UI shows error indicators:\n"
            f"  Red pixels: {error_check['red_pixel_percentage']:.2f}%\n"
            f"  Error keywords: {error_check['error_keywords_found']}"
        )

    print("✓ VISUAL VERIFICATION PASSED")
    return {
        'text_verification': text_check,
        'error_detection': error_check
    }
```

### 4.2 Installation Requirements

```bash
# OCR and image processing
pip install pytesseract pillow opencv-python numpy

# Install Tesseract OCR engine
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# macOS:
brew install tesseract

# Windows:
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

---

## 5. Proof-of-Work System

### 5.1 Validation Report Generator

Agents must generate a comprehensive report with evidence:

```python
# proof_of_work.py
import json
import hashlib
from datetime import datetime
from typing import Dict, List
from pathlib import Path

class ProofOfWorkGenerator:
    def __init__(self, task_id: str, agent_name: str):
        self.task_id = task_id
        self.agent_name = agent_name
        self.report_data = {
            'task_id': task_id,
            'agent_name': agent_name,
            'timestamp': datetime.now().isoformat(),
            'validation_stages': [],
            'artifacts': [],
            'final_status': 'PENDING'
        }

    def add_validation_stage(self, stage_name: str, result: Dict):
        """Add result from a validation stage"""
        self.report_data['validation_stages'].append({
            'stage': stage_name,
            'status': result.get('status', 'UNKNOWN'),
            'timestamp': datetime.now().isoformat(),
            'details': result
        })

    def add_artifact(self, artifact_type: str, file_path: str, description: str):
        """Add evidence artifact (screenshot, log, video, etc.)"""
        self.report_data['artifacts'].append({
            'type': artifact_type,
            'path': file_path,
            'description': description,
            'file_size': Path(file_path).stat().st_size if Path(file_path).exists() else 0
        })

    def finalize(self) -> Dict:
        """Generate final proof-of-work report with verification hash"""
        # Determine overall status
        all_passed = all(
            stage['status'] == 'PASSED'
            for stage in self.report_data['validation_stages']
        )
        self.report_data['final_status'] = 'APPROVED' if all_passed else 'REJECTED'

        # Generate verification hash
        report_json = json.dumps(self.report_data, sort_keys=True)
        verification_hash = hashlib.sha256(report_json.encode()).hexdigest()
        self.report_data['verification_hash'] = verification_hash

        # Save report
        report_path = f"./validation_reports/{self.task_id}_{self.agent_name}_report.json"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(self.report_data, f, indent=2)

        self.report_data['report_path'] = report_path

        return self.report_data

    def generate_human_readable_summary(self) -> str:
        """Generate markdown summary for humans"""
        md = f"""# Validation Report: {self.task_id}

**Agent:** {self.agent_name}
**Timestamp:** {self.report_data['timestamp']}
**Status:** {self.report_data['final_status']}
**Verification Hash:** {self.report_data.get('verification_hash', 'N/A')}

---

## Validation Stages

"""
        for stage in self.report_data['validation_stages']:
            status_icon = '✅' if stage['status'] == 'PASSED' else '❌'
            md += f"### {status_icon} {stage['stage']}\n\n"
            md += f"**Status:** {stage['status']}  \n"
            md += f"**Timestamp:** {stage['timestamp']}  \n\n"

        md += "\n## Artifacts\n\n"
        for artifact in self.report_data['artifacts']:
            md += f"- **{artifact['type']}:** `{artifact['path']}` - {artifact['description']}\n"

        md += f"\n---\n\n"
        if self.report_data['final_status'] == 'APPROVED':
            md += "✅ **VALIDATION APPROVED** - Agent work meets all quality standards.\n"
        else:
            md += "❌ **VALIDATION REJECTED** - Agent must address issues and re-validate.\n"

        return md

# Complete agent validation workflow
async def agent_complete_validation_workflow(task_id: str):
    """
    Complete validation workflow that agents MUST execute
    """
    pow_gen = ProofOfWorkGenerator(task_id=task_id, agent_name="claude_agent_001")

    try:
        # Stage 1: Code Validation
        print("[1/6] Running code validation...")
        # Run linting, type checking, unit tests
        code_result = {'status': 'PASSED', 'coverage': '85%'}
        pow_gen.add_validation_stage('code_validation', code_result)

        # Stage 2: Integration Tests
        print("[2/6] Running integration tests...")
        integration_result = {'status': 'PASSED', 'tests_passed': '42/42'}
        pow_gen.add_validation_stage('integration_tests', integration_result)

        # Stage 3: E2E Tests
        print("[3/6] Running E2E tests...")
        e2e_validator = E2EValidationTest()
        e2e_result = await agent_validate_loading_bay_feature()
        pow_gen.add_validation_stage('e2e_testing', e2e_result)

        # Add screenshots as artifacts
        for screenshot in e2e_result['tests'][0]['screenshots']:
            pow_gen.add_artifact('screenshot', screenshot, 'E2E test screenshot')

        # Stage 4: Log Analysis
        print("[4/6] Analyzing logs...")
        log_result = agent_validate_logs()
        pow_gen.add_validation_stage('log_analysis', log_result)

        # Stage 5: Visual Verification
        print("[5/6] Running visual verification...")
        visual_result = agent_verify_ui_output('./screenshots/final_ui.png')
        pow_gen.add_validation_stage('visual_verification', visual_result)
        pow_gen.add_artifact('screenshot', './screenshots/final_ui.png', 'Final UI verification')

        # Stage 6: Generate Proof of Work
        print("[6/6] Generating proof-of-work report...")
        final_report = pow_gen.finalize()

        # Generate human-readable summary
        summary = pow_gen.generate_human_readable_summary()
        summary_path = f"./validation_reports/{task_id}_summary.md"
        with open(summary_path, 'w') as f:
            f.write(summary)

        if final_report['final_status'] == 'APPROVED':
            print("\n" + "="*60)
            print("✅ AGENT VALIDATION COMPLETE - WORK APPROVED")
            print("="*60)
            print(f"\nReport: {final_report['report_path']}")
            print(f"Summary: {summary_path}")
            print(f"Hash: {final_report['verification_hash']}")
            return final_report
        else:
            raise Exception("Validation failed - see report for details")

    except Exception as e:
        pow_gen.report_data['final_status'] = 'REJECTED'
        pow_gen.report_data['error'] = str(e)
        final_report = pow_gen.finalize()

        print("\n" + "="*60)
        print("❌ AGENT VALIDATION FAILED")
        print("="*60)
        print(f"Error: {e}")
        print(f"Report: {final_report['report_path']}")

        raise
```

---

## 6. Enforcement Configuration

### 6.1 Agent Pre-Commit Hook

Prevent agents from committing code without validation:

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "🔍 Running Agent Readiness Check..."

# Check if validation report exists for current task
TASK_ID=$(git branch --show-current | grep -oP '(?<=task-).*')

if [ -z "$TASK_ID" ]; then
    echo "❌ No task ID found in branch name"
    exit 1
fi

REPORT_PATH="./validation_reports/${TASK_ID}_*_report.json"

if [ ! -f $REPORT_PATH ]; then
    echo "❌ No validation report found for task $TASK_ID"
    echo "Agent must run complete validation workflow before committing"
    echo "Run: python -m proof_of_work ${TASK_ID}"
    exit 1
fi

# Verify report status
STATUS=$(jq -r '.final_status' $REPORT_PATH)

if [ "$STATUS" != "APPROVED" ]; then
    echo "❌ Validation status: $STATUS"
    echo "Agent cannot commit until all validations pass"
    exit 1
fi

echo "✅ Validation passed - commit allowed"
exit 0
```

### 6.2 CI/CD Integration

Add validation checks to CI pipeline:

```yaml
# .github/workflows/agent-validation.yml
name: Agent Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Check for validation report
        run: |
          TASK_ID=$(echo $GITHUB_REF | grep -oP '(?<=task-).*')
          REPORT="./validation_reports/${TASK_ID}_*_report.json"

          if [ ! -f $REPORT ]; then
            echo "❌ Missing validation report"
            exit 1
          fi

          STATUS=$(jq -r '.final_status' $REPORT)
          if [ "$STATUS" != "APPROVED" ]; then
            echo "❌ Validation status: $STATUS"
            exit 1
          fi

      - name: Verify validation artifacts
        run: |
          python scripts/verify_validation_artifacts.py

      - name: Re-run E2E tests
        run: |
          npm install
          npm run test:e2e
```

---

## 7. Agent Instructions & Usage

### 7.1 Agent Workflow

When an agent is assigned a task, it MUST follow this workflow:

```
1. Receive task assignment
2. Implement feature/fix
3. Run local unit tests
4. Run integration tests
5. Start local development server
6. Run E2E validation suite (browser automation)
7. Monitor logs during E2E tests
8. Capture screenshots and verify UI
9. Analyze logs for errors
10. Generate proof-of-work report
11. IF ALL PASS: Commit code + report
12. IF ANY FAIL: Fix issues and restart from step 6
13. Create pull request with validation report link
```

### 7.2 Quick Start for Agents

```bash
# Install dependencies
pip install -r requirements_validation.txt
playwright install

# Run complete validation
python agent_validator.py --task-id TASK-123 --feature loading-bay-update

# This will:
# - Run all validation stages
# - Generate report
# - Create screenshots
# - Analyze logs
# - Produce proof-of-work

# Check report
cat ./validation_reports/TASK-123_*_report.json
```

### 7.3 Example Test Configuration

Create a `agent_test_config.yaml` for each feature:

```yaml
task_id: TASK-123
feature: loading_bay_management

e2e_tests:
  - name: create_loading_bay
    url: /loading-bays
    interactions:
      - action: click
        selector: button:has-text("New Loading Bay")
      - action: type
        selector: input[name="bay_number"]
        value: BAY-TEST-001
      - action: select
        selector: select[name="status"]
        value: AVAILABLE
      - action: click
        selector: button[type="submit"]
    validations:
      - type: element_visible
        selector: .success-message
      - type: text_content
        selector: .success-message
        expected: "created successfully"

  - name: update_loading_bay_status
    url: /loading-bays/BAY-TEST-001
    interactions:
      - action: click
        selector: button:has-text("Edit")
      - action: select
        selector: select[name="status"]
        value: MAINTENANCE
      - action: click
        selector: button:has-text("Save")
    validations:
      - type: element_visible
        selector: .badge:has-text("MAINTENANCE")

log_analysis:
  paths:
    - ./backend/logs/application.log
    - ./backend/logs/error.log
  time_window_minutes: 10

visual_verification:
  screenshots:
    - path: ./screenshots/loading_bay_list.png
      expected_text:
        - "Loading Bays"
        - "BAY-TEST-001"
        - "MAINTENANCE"
  error_detection: true

success_criteria:
  code_coverage_min: 80
  e2e_pass_rate: 100
  max_log_errors: 0
  max_visual_errors: 0
```

Then run:

```python
# agent_validator.py
import yaml

def run_validation_from_config(config_path: str):
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Run all validations based on config
    # Generate proof-of-work
    # Return approval or rejection
```

---

## 8. Success Metrics & KPIs

Track agent validation effectiveness:

```python
# Track metrics
validation_metrics = {
    'total_validations': 0,
    'passed_validations': 0,
    'failed_validations': 0,
    'false_positives': 0,  # Agent claimed success but failed
    'false_negatives': 0,  # Agent claimed failure but actually worked
    'avg_validation_time_seconds': 0,
    'avg_e2e_test_duration': 0,
    'most_common_failure_stage': None
}

# Goal: Reduce false positives to near 0%
```

---

## 9. Advanced Features

### 9.1 Network Traffic Analysis

Monitor API calls during E2E tests:

```python
from playwright.async_api import async_playwright

async def capture_network_traffic():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        # Capture all network requests
        api_calls = []

        page.on("request", lambda request: api_calls.append({
            'url': request.url,
            'method': request.method,
            'headers': request.headers
        }))

        page.on("response", lambda response: print(
            f"API Response: {response.status} {response.url}"
        ))

        # Run tests...
        await page.goto("http://localhost:3000")

        # Validate expected API calls were made
        expected_calls = [
            '/api/loading-bays',
            '/api/tanks',
            '/api/dashboard/status'
        ]

        for expected in expected_calls:
            if not any(expected in call['url'] for call in api_calls):
                raise Exception(f"Expected API call not made: {expected}")
```

### 9.2 Performance Validation

Ensure no performance regressions:

```python
async def validate_performance():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Measure page load time
        start = time.time()
        await page.goto("http://localhost:3000/loading-bays")
        await page.wait_for_load_state('networkidle')
        load_time = time.time() - start

        if load_time > 3.0:  # 3 second threshold
            raise Exception(f"Page load too slow: {load_time:.2f}s")

        # Check for performance marks
        perf_metrics = await page.evaluate("""
            () => {
                const perfData = performance.getEntriesByType('navigation')[0];
                return {
                    domContentLoaded: perfData.domContentLoadedEventEnd - perfData.fetchStart,
                    loadComplete: perfData.loadEventEnd - perfData.fetchStart,
                    firstPaint: performance.getEntriesByType('paint')[0]?.startTime
                }
            }
        """)

        print(f"Performance metrics: {perf_metrics}")
```

### 9.3 Accessibility Testing

```python
from axe_playwright_python import Axe

async def validate_accessibility():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:3000/loading-bays")

        axe = Axe()
        results = await axe.run(page)

        violations = results['violations']
        if violations:
            print(f"Found {len(violations)} accessibility violations:")
            for v in violations:
                print(f"  - {v['id']}: {v['description']}")
            raise Exception("Accessibility validation failed")
```

---

## 10. FAQ for Agents

**Q: Can I skip E2E testing for minor changes?**
A: No. All changes must go through full validation pipeline.

**Q: What if the E2E tests are flaky?**
A: Fix the tests. Flaky tests indicate real issues.

**Q: Can I run validations in parallel to save time?**
A: Yes, but logs must still be reviewed and screenshots captured for each test.

**Q: What if I'm only updating documentation?**
A: Documentation-only changes can skip E2E tests but must pass markdown linting and link checking.

**Q: How do I add a new validation stage?**
A: Implement the stage in `agent_validator.py` and update this document.

---

## 11. Summary

This framework ensures agents **cannot claim success without proof**. Every agent must:

1. ✅ Pass code validation (linting, types, tests)
2. ✅ Pass integration tests
3. ✅ Run full E2E tests with browser automation
4. ✅ Analyze logs and find zero errors
5. ✅ Verify UI through OCR and visual checks
6. ✅ Generate proof-of-work report with artifacts

**No exceptions. No shortcuts.**

If any stage fails, the agent must fix and re-validate from that stage.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-07
**Maintained By:** Development Team
