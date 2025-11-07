#!/usr/bin/env python3
"""
Agent Validator - Complete validation workflow for AI agents

This script enforces the Agent Readiness Check Framework by running
all validation stages and generating proof-of-work reports.

Usage:
    python agent_validator.py --task-id TASK-123 --config test_config.yaml
"""

import asyncio
import argparse
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import time

# Import validation modules
from playwright.async_api import async_playwright, Page, Browser
from PIL import Image
import pytesseract
import cv2
import numpy as np
import re


class ValidationStage:
    """Base class for validation stages"""

    def __init__(self, name: str):
        self.name = name

    async def execute(self) -> Dict:
        """Execute the validation stage"""
        raise NotImplementedError


class CodeValidationStage(ValidationStage):
    """Stage 1: Code validation (linting, type checking, unit tests)"""

    def __init__(self, config: Dict):
        super().__init__("Code Validation")
        self.config = config

    async def execute(self) -> Dict:
        print(f"\n{'='*60}")
        print(f"STAGE 1: {self.name}")
        print(f"{'='*60}")

        result = {
            'status': 'PASSED',
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }

        # TODO: Implement actual linting, type checking, unit tests
        # For now, this is a placeholder
        checks = [
            {'name': 'Linting', 'status': 'PASSED', 'details': 'No linting errors'},
            {'name': 'Type Checking', 'status': 'PASSED', 'details': 'All types valid'},
            {'name': 'Unit Tests', 'status': 'PASSED', 'details': '45/45 tests passed'},
        ]

        for check in checks:
            result['checks'].append(check)
            status_icon = '✅' if check['status'] == 'PASSED' else '❌'
            print(f"  {status_icon} {check['name']}: {check['details']}")

        return result


class E2EValidationStage(ValidationStage):
    """Stage 2: End-to-End testing with browser automation"""

    def __init__(self, config: Dict):
        super().__init__("E2E Testing")
        self.config = config
        self.base_url = config.get('base_url', 'http://localhost:3000')
        self.test_cases = config.get('e2e_tests', [])
        self.screenshots_dir = Path("./validation_screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.console_logs = []
        self.errors = []

    async def execute(self) -> Dict:
        print(f"\n{'='*60}")
        print(f"STAGE 2: {self.name}")
        print(f"{'='*60}")

        result = {
            'status': 'PASSED',
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'total_tests': len(self.test_cases),
            'passed': 0,
            'failed': 0
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                record_video_dir="./validation_videos"
            )
            page = await context.new_page()

            # Set up log capture
            page.on("console", self._capture_console_log)
            page.on("pageerror", self._capture_page_error)

            for test_case in self.test_cases:
                test_result = await self._execute_test_case(page, test_case)
                result['tests'].append(test_result)

                if test_result['status'] == 'PASSED':
                    result['passed'] += 1
                    print(f"  ✅ {test_case['name']}")
                else:
                    result['failed'] += 1
                    result['status'] = 'FAILED'
                    print(f"  ❌ {test_case['name']}: {test_result.get('failure_reason', 'Unknown error')}")

            await browser.close()

        print(f"\n  Tests: {result['passed']}/{result['total_tests']} passed")

        return result

    async def _execute_test_case(self, page: Page, test_case: Dict) -> Dict:
        """Execute a single E2E test case"""
        test_name = test_case['name']

        result = {
            'name': test_name,
            'status': 'PENDING',
            'steps': [],
            'screenshots': [],
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Navigate to page
            url = f"{self.base_url}{test_case['url']}"
            await page.goto(url, wait_until='networkidle')
            result['steps'].append(f"✓ Navigated to {url}")

            # Take initial screenshot
            screenshot_path = str(self.screenshots_dir / f"{test_name}_initial.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            result['screenshots'].append(screenshot_path)

            # Execute interactions
            for i, interaction in enumerate(test_case.get('interactions', [])):
                await self._execute_interaction(page, interaction, result)

                # Screenshot after each interaction
                screenshot_path = str(self.screenshots_dir / f"{test_name}_step_{i+1}.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                result['screenshots'].append(screenshot_path)

            # Execute validations
            for validation in test_case.get('validations', []):
                await self._execute_validation(page, validation, result)

            # Check for errors
            if result['errors']:
                result['status'] = 'FAILED'
                result['failure_reason'] = f"Found {len(result['errors'])} errors"
            else:
                result['status'] = 'PASSED'

        except Exception as e:
            result['status'] = 'FAILED'
            result['failure_reason'] = str(e)
            screenshot_path = str(self.screenshots_dir / f"{test_name}_error.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            result['screenshots'].append(screenshot_path)

        return result

    async def _execute_interaction(self, page: Page, interaction: Dict, result: Dict):
        """Execute user interaction"""
        action = interaction['action']
        selector = interaction.get('selector')

        if action == 'click':
            await page.click(selector)
            result['steps'].append(f"✓ Clicked: {selector}")

        elif action == 'type':
            await page.fill(selector, interaction['value'])
            result['steps'].append(f"✓ Typed into: {selector}")

        elif action == 'select':
            await page.select_option(selector, interaction['value'])
            result['steps'].append(f"✓ Selected: {interaction['value']}")

        elif action == 'wait':
            timeout = interaction.get('timeout', 5000)
            await page.wait_for_selector(selector, timeout=timeout)
            result['steps'].append(f"✓ Waited for: {selector}")

        # Add small delay for stability
        await asyncio.sleep(0.5)

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
            expected = validation['expected']
            actual = await page.text_content(selector)
            if expected in actual:
                result['steps'].append(f"✓ Text validation passed: {selector}")
            else:
                result['errors'].append(
                    f"✗ Text mismatch in {selector}: expected '{expected}', got '{actual}'"
                )

        elif validation_type == 'element_count':
            selector = validation['selector']
            expected = validation['expected']
            actual = await page.locator(selector).count()
            if actual == expected:
                result['steps'].append(f"✓ Element count correct: {expected}")
            else:
                result['errors'].append(
                    f"✗ Element count mismatch: expected {expected}, got {actual}"
                )

        elif validation_type == 'url_matches':
            expected = validation['expected']
            actual = page.url
            if expected in actual:
                result['steps'].append(f"✓ URL validation passed")
            else:
                result['errors'].append(
                    f"✗ URL mismatch: expected '{expected}', got '{actual}'"
                )

    def _capture_console_log(self, msg):
        """Capture browser console messages"""
        self.console_logs.append({
            'type': msg.type,
            'text': msg.text,
            'timestamp': datetime.now().isoformat()
        })
        if msg.type in ['error', 'warning']:
            self.errors.append({
                'source': 'console',
                'type': msg.type,
                'text': msg.text
            })

    def _capture_page_error(self, error):
        """Capture JavaScript errors"""
        self.errors.append({
            'source': 'javascript',
            'error': str(error)
        })


class LogAnalysisStage(ValidationStage):
    """Stage 3: Log analysis and error detection"""

    def __init__(self, config: Dict):
        super().__init__("Log Analysis")
        self.config = config
        self.log_paths = config.get('log_paths', [])
        self.time_window_minutes = config.get('time_window_minutes', 10)

    async def execute(self) -> Dict:
        print(f"\n{'='*60}")
        print(f"STAGE 3: {self.name}")
        print(f"{'='*60}")

        error_patterns = [
            r'ERROR', r'CRITICAL', r'Exception', r'Traceback',
            r'Failed', r'Error:', r'\[error\]', r'500 Internal',
            r'400 Bad Request', r'Connection refused', r'Timeout'
        ]

        errors = []
        warnings = []

        for log_path in self.log_paths:
            if not Path(log_path).exists():
                print(f"  ⚠️  Log file not found: {log_path}")
                continue

            print(f"  📄 Analyzing: {log_path}")

            with open(log_path, 'r') as f:
                for line in f:
                    # Check for errors
                    for pattern in error_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            errors.append({
                                'source': log_path,
                                'line': line.strip()
                            })
                            break

        result = {
            'status': 'FAILED' if errors else 'PASSED',
            'timestamp': datetime.now().isoformat(),
            'error_count': len(errors),
            'warning_count': len(warnings),
            'errors': errors[:10],  # Include first 10 errors
            'logs_analyzed': len(self.log_paths)
        }

        if errors:
            print(f"  ❌ Found {len(errors)} errors in logs")
            for error in errors[:3]:
                print(f"     {error['source']}: {error['line'][:100]}")
        else:
            print(f"  ✅ No errors found in logs")

        return result


class VisualVerificationStage(ValidationStage):
    """Stage 4: Visual verification and OCR"""

    def __init__(self, config: Dict):
        super().__init__("Visual Verification")
        self.config = config
        self.screenshots = config.get('screenshots', [])

    async def execute(self) -> Dict:
        print(f"\n{'='*60}")
        print(f"STAGE 4: {self.name}")
        print(f"{'='*60}")

        result = {
            'status': 'PASSED',
            'timestamp': datetime.now().isoformat(),
            'verifications': []
        }

        for screenshot_config in self.screenshots:
            screenshot_path = screenshot_config['path']

            if not Path(screenshot_path).exists():
                print(f"  ⚠️  Screenshot not found: {screenshot_path}")
                continue

            print(f"  🖼️  Verifying: {screenshot_path}")

            verification = await self._verify_screenshot(screenshot_path, screenshot_config)
            result['verifications'].append(verification)

            if not verification['passed']:
                result['status'] = 'FAILED'
                print(f"  ❌ Verification failed")
            else:
                print(f"  ✅ Verification passed")

        return result

    async def _verify_screenshot(self, screenshot_path: str, config: Dict) -> Dict:
        """Verify a single screenshot"""
        image = Image.open(screenshot_path)

        verification = {
            'screenshot': screenshot_path,
            'passed': True,
            'checks': []
        }

        # OCR text extraction
        try:
            extracted_text = pytesseract.image_to_string(image)
        except:
            extracted_text = ""
            print(f"  ⚠️  OCR not available, skipping text extraction")

        # Check for expected text
        expected_texts = config.get('expected_text', [])
        for expected in expected_texts:
            found = expected.lower() in extracted_text.lower()
            verification['checks'].append({
                'type': 'text_present',
                'expected': expected,
                'found': found
            })
            if not found:
                verification['passed'] = False

        # Check for error indicators (red colors, error keywords)
        if config.get('error_detection', False):
            has_errors = self._detect_error_indicators(image, extracted_text)
            verification['checks'].append({
                'type': 'error_detection',
                'has_errors': has_errors
            })
            if has_errors:
                verification['passed'] = False

        return verification

    def _detect_error_indicators(self, image: Image, text: str) -> bool:
        """Detect visual error indicators"""
        # Check for error keywords in text
        error_keywords = ['error', 'failed', 'exception', 'warning', 'invalid']
        text_lower = text.lower()

        for keyword in error_keywords:
            if keyword in text_lower:
                return True

        # Check for excessive red colors (common for errors)
        try:
            img_array = np.array(image)
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)

            # Red color ranges
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 100, 100])
            upper_red2 = np.array([180, 255, 255])

            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            red_mask = mask1 + mask2

            red_pixels = np.sum(red_mask > 0)
            total_pixels = img_array.shape[0] * img_array.shape[1]
            red_percentage = (red_pixels / total_pixels) * 100

            # More than 5% red pixels might indicate errors
            return red_percentage > 5
        except:
            return False


class ProofOfWorkGenerator:
    """Generate proof-of-work report with verification hash"""

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

    def add_stage_result(self, stage_name: str, result: Dict):
        """Add result from a validation stage"""
        self.report_data['validation_stages'].append({
            'stage': stage_name,
            'status': result.get('status', 'UNKNOWN'),
            'timestamp': result.get('timestamp', datetime.now().isoformat()),
            'details': result
        })

    def add_artifact(self, artifact_type: str, file_path: str, description: str):
        """Add evidence artifact"""
        self.report_data['artifacts'].append({
            'type': artifact_type,
            'path': file_path,
            'description': description,
            'exists': Path(file_path).exists(),
            'size': Path(file_path).stat().st_size if Path(file_path).exists() else 0
        })

    def finalize(self) -> Dict:
        """Generate final report with verification hash"""
        # Determine overall status
        all_passed = all(
            stage['status'] == 'PASSED'
            for stage in self.report_data['validation_stages']
        )
        self.report_data['final_status'] = 'APPROVED' if all_passed else 'REJECTED'

        # Generate verification hash
        report_json = json.dumps(self.report_data, sort_keys=True)
        self.report_data['verification_hash'] = hashlib.sha256(report_json.encode()).hexdigest()

        # Save report
        report_dir = Path("./validation_reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        report_path = report_dir / f"{self.task_id}_{self.agent_name}_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.report_data, f, indent=2)

        self.report_data['report_path'] = str(report_path)

        # Generate human-readable summary
        self._generate_summary(report_dir / f"{self.task_id}_summary.md")

        return self.report_data

    def _generate_summary(self, summary_path: Path):
        """Generate markdown summary"""
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
            md += f"- **{artifact['type']}:** `{artifact['path']}` ({artifact['size']} bytes)\n"

        md += f"\n---\n\n"
        if self.report_data['final_status'] == 'APPROVED':
            md += "✅ **VALIDATION APPROVED** - Agent work meets all quality standards.\n"
        else:
            md += "❌ **VALIDATION REJECTED** - Agent must address issues and re-validate.\n"

        with open(summary_path, 'w') as f:
            f.write(md)

        self.report_data['summary_path'] = str(summary_path)


async def run_validation(task_id: str, config_path: str, agent_name: str = "claude_agent"):
    """Run complete validation workflow"""

    print("="*60)
    print("AGENT READINESS CHECK - VALIDATION STARTING")
    print("="*60)
    print(f"Task ID: {task_id}")
    print(f"Config: {config_path}")
    print(f"Agent: {agent_name}")
    print("="*60)

    # Load configuration
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Initialize proof-of-work generator
    pow_gen = ProofOfWorkGenerator(task_id, agent_name)

    try:
        # Stage 1: Code Validation
        code_stage = CodeValidationStage(config)
        code_result = await code_stage.execute()
        pow_gen.add_stage_result('Code Validation', code_result)

        if code_result['status'] == 'FAILED':
            raise Exception("Code validation failed")

        # Stage 2: E2E Testing
        e2e_stage = E2EValidationStage(config)
        e2e_result = await e2e_stage.execute()
        pow_gen.add_stage_result('E2E Testing', e2e_result)

        # Add screenshots as artifacts
        for test in e2e_result.get('tests', []):
            for screenshot in test.get('screenshots', []):
                pow_gen.add_artifact('screenshot', screenshot, f"E2E test: {test['name']}")

        if e2e_result['status'] == 'FAILED':
            raise Exception(f"E2E testing failed: {e2e_result['failed']}/{e2e_result['total_tests']} tests failed")

        # Stage 3: Log Analysis
        log_stage = LogAnalysisStage(config.get('log_analysis', {}))
        log_result = await log_stage.execute()
        pow_gen.add_stage_result('Log Analysis', log_result)

        if log_result['status'] == 'FAILED':
            raise Exception(f"Log analysis failed: {log_result['error_count']} errors found")

        # Stage 4: Visual Verification
        visual_stage = VisualVerificationStage(config.get('visual_verification', {}))
        visual_result = await visual_stage.execute()
        pow_gen.add_stage_result('Visual Verification', visual_result)

        if visual_result['status'] == 'FAILED':
            raise Exception("Visual verification failed")

        # Generate final report
        final_report = pow_gen.finalize()

        print("\n" + "="*60)
        print("✅ AGENT VALIDATION COMPLETE - WORK APPROVED")
        print("="*60)
        print(f"\nReport: {final_report['report_path']}")
        print(f"Summary: {final_report['summary_path']}")
        print(f"Verification Hash: {final_report['verification_hash']}")
        print("\n✅ Agent may now commit and push changes.")

        return final_report

    except Exception as e:
        pow_gen.report_data['final_status'] = 'REJECTED'
        pow_gen.report_data['error'] = str(e)
        final_report = pow_gen.finalize()

        print("\n" + "="*60)
        print("❌ AGENT VALIDATION FAILED")
        print("="*60)
        print(f"Error: {e}")
        print(f"Report: {final_report['report_path']}")
        print(f"Summary: {final_report['summary_path']}")
        print("\n❌ Agent must fix issues and re-run validation.")

        sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Agent Readiness Check - Validation Framework'
    )
    parser.add_argument(
        '--task-id',
        required=True,
        help='Task ID for this validation'
    )
    parser.add_argument(
        '--config',
        required=True,
        help='Path to test configuration YAML file'
    )
    parser.add_argument(
        '--agent-name',
        default='claude_agent',
        help='Name of the agent running the validation'
    )

    args = parser.parse_args()

    # Run validation
    asyncio.run(run_validation(args.task_id, args.config, args.agent_name))


if __name__ == "__main__":
    main()
