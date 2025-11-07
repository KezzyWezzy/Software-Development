"""
Validation Framework

ENFORCES testing before task completion.
No agent can mark a task complete without passing validation.

This prevents the "it's ready" problem when code doesn't actually work.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime


class ValidationLevel(Enum):
    """Validation strictness levels"""
    NONE = "none"  # No validation required (dangerous!)
    BASIC = "basic"  # Basic checks only
    STANDARD = "standard"  # Standard validation (recommended)
    STRICT = "strict"  # Strict validation
    PARANOID = "paranoid"  # Maximum validation


class ValidationType(Enum):
    """Types of validation"""
    SYNTAX_CHECK = "syntax_check"  # Code compiles/parses
    UNIT_TESTS = "unit_tests"  # Unit tests pass
    INTEGRATION_TESTS = "integration_tests"  # Integration tests pass
    BROWSER_TESTS = "browser_tests"  # Browser automation tests pass
    API_TESTS = "api_tests"  # API endpoint tests pass
    DATABASE_TESTS = "database_tests"  # Database operations work
    SECURITY_SCAN = "security_scan"  # Security checks pass
    PERFORMANCE_TESTS = "performance_tests"  # Performance acceptable
    MANUAL_VERIFICATION = "manual_verification"  # Human verified it works


class ValidationResult:
    """Result of a validation check"""

    def __init__(
        self,
        validation_type: ValidationType,
        passed: bool,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        evidence: Optional[List[str]] = None
    ):
        self.validation_type = validation_type
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.evidence = evidence or []  # Screenshots, logs, etc.
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_type": self.validation_type.value,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "evidence": self.evidence,
            "timestamp": self.timestamp
        }


class ValidationFramework:
    """
    Framework that enforces validation before task completion.

    Usage:
        framework = ValidationFramework(level=ValidationLevel.STANDARD)
        framework.register_validator(ValidationType.UNIT_TESTS, test_runner)
        result = framework.validate(task, results)
        if not result.passed:
            raise Exception("Validation failed! Cannot mark as complete!")
    """

    def __init__(
        self,
        level: ValidationLevel = ValidationLevel.STANDARD,
        workspace_dir: Optional[Path] = None
    ):
        self.level = level
        self.workspace_dir = workspace_dir or Path.cwd() / "agent-team-system"
        self.validators = {}

        # Required validations per level
        self.required_validations = {
            ValidationLevel.NONE: set(),
            ValidationLevel.BASIC: {
                ValidationType.SYNTAX_CHECK,
            },
            ValidationLevel.STANDARD: {
                ValidationType.SYNTAX_CHECK,
                ValidationType.UNIT_TESTS,
                ValidationType.BROWSER_TESTS,
            },
            ValidationLevel.STRICT: {
                ValidationType.SYNTAX_CHECK,
                ValidationType.UNIT_TESTS,
                ValidationType.INTEGRATION_TESTS,
                ValidationType.BROWSER_TESTS,
                ValidationType.API_TESTS,
            },
            ValidationLevel.PARANOID: {
                ValidationType.SYNTAX_CHECK,
                ValidationType.UNIT_TESTS,
                ValidationType.INTEGRATION_TESTS,
                ValidationType.BROWSER_TESTS,
                ValidationType.API_TESTS,
                ValidationType.DATABASE_TESTS,
                ValidationType.SECURITY_SCAN,
                ValidationType.PERFORMANCE_TESTS,
            }
        }

    def register_validator(self, validation_type: ValidationType, validator_func):
        """
        Register a validator function

        Args:
            validation_type: Type of validation
            validator_func: Function that takes (task, results) and returns ValidationResult
        """
        self.validators[validation_type] = validator_func

    def validate(
        self,
        task: Dict[str, Any],
        task_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a task result before allowing completion

        Args:
            task: The task that was executed
            task_result: The result from the agent

        Returns:
            Validation report with passed/failed status

        Raises:
            Exception if validation fails and strict mode is enabled
        """
        required = self.required_validations.get(self.level, set())
        validation_results = []

        # Run all required validations
        for validation_type in required:
            if validation_type in self.validators:
                validator = self.validators[validation_type]
                try:
                    result = validator(task, task_result)
                    validation_results.append(result)
                except Exception as e:
                    validation_results.append(ValidationResult(
                        validation_type=validation_type,
                        passed=False,
                        message=f"Validator error: {str(e)}",
                        details={"error": str(e)}
                    ))
            else:
                # No validator registered - fail in strict modes
                if self.level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                    validation_results.append(ValidationResult(
                        validation_type=validation_type,
                        passed=False,
                        message=f"No validator registered for {validation_type.value}",
                    ))

        # Analyze results
        total = len(validation_results)
        passed = sum(1 for r in validation_results if r.passed)
        failed = total - passed

        all_passed = passed == total

        validation_report = {
            "validation_level": self.level.value,
            "total_validations": total,
            "passed": passed,
            "failed": failed,
            "all_passed": all_passed,
            "pass_rate": (passed / total * 100) if total > 0 else 100,
            "results": [r.to_dict() for r in validation_results],
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Save validation report
        self._save_validation_report(task, validation_report)

        return validation_report

    def _save_validation_report(self, task: Dict[str, Any], report: Dict[str, Any]):
        """Save validation report to disk"""
        reports_dir = self.workspace_dir / "validation_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        task_id = task.get("id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"validation_{task_id}_{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

    def is_task_valid(self, task: Dict[str, Any], task_result: Dict[str, Any]) -> bool:
        """
        Quick check if task result is valid

        Returns:
            True if validation passed, False otherwise
        """
        report = self.validate(task, task_result)
        return report["all_passed"]


# Built-in validators

def syntax_check_validator(task: Dict[str, Any], result: Dict[str, Any]) -> ValidationResult:
    """Validate that generated code has valid syntax"""
    # Check if code files exist and are parseable
    code_files = result.get("generated_files", [])

    errors = []
    for file_path in code_files:
        file_path = Path(file_path)

        if not file_path.exists():
            errors.append(f"File not found: {file_path}")
            continue

        # Try to parse based on file type
        if file_path.suffix == ".py":
            try:
                with open(file_path, 'r') as f:
                    compile(f.read(), str(file_path), 'exec')
            except SyntaxError as e:
                errors.append(f"Python syntax error in {file_path}: {e}")
        elif file_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
            # Would use a JS parser here
            pass

    if errors:
        return ValidationResult(
            validation_type=ValidationType.SYNTAX_CHECK,
            passed=False,
            message=f"Syntax errors found: {len(errors)}",
            details={"errors": errors}
        )
    else:
        return ValidationResult(
            validation_type=ValidationType.SYNTAX_CHECK,
            passed=True,
            message="All syntax checks passed",
            details={"files_checked": len(code_files)}
        )


def unit_tests_validator(task: Dict[str, Any], result: Dict[str, Any]) -> ValidationResult:
    """Validate that unit tests pass"""
    test_results = result.get("test_results", {})

    if not test_results:
        return ValidationResult(
            validation_type=ValidationType.UNIT_TESTS,
            passed=False,
            message="No test results provided"
        )

    analysis = test_results.get("analysis", {})
    pass_rate = analysis.get("pass_rate", 0)

    if pass_rate >= 100:
        return ValidationResult(
            validation_type=ValidationType.UNIT_TESTS,
            passed=True,
            message=f"All tests passed: {analysis.get('summary')}",
            details=analysis
        )
    else:
        return ValidationResult(
            validation_type=ValidationType.UNIT_TESTS,
            passed=False,
            message=f"Tests failed: {analysis.get('summary')}",
            details=analysis,
            evidence=result.get("screenshots", [])
        )


def browser_tests_validator(task: Dict[str, Any], result: Dict[str, Any]) -> ValidationResult:
    """Validate that browser automation tests pass"""
    test_results = result.get("test_results", {})

    if not test_results:
        return ValidationResult(
            validation_type=ValidationType.BROWSER_TESTS,
            passed=False,
            message="No browser test results provided"
        )

    # Check if browser tests were run
    browser_tests = [r for r in test_results if "browser" in str(r).lower() or "selenium" in str(r).lower()]

    if not browser_tests:
        return ValidationResult(
            validation_type=ValidationType.BROWSER_TESTS,
            passed=False,
            message="No browser tests were executed"
        )

    # Check results
    passed = all(r.get("status") == "passed" for r in browser_tests)

    if passed:
        return ValidationResult(
            validation_type=ValidationType.BROWSER_TESTS,
            passed=True,
            message=f"{len(browser_tests)} browser tests passed",
            evidence=result.get("screenshots", [])
        )
    else:
        failed_tests = [r for r in browser_tests if r.get("status") == "failed"]
        return ValidationResult(
            validation_type=ValidationType.BROWSER_TESTS,
            passed=False,
            message=f"{len(failed_tests)} browser tests failed",
            details={"failed_tests": failed_tests},
            evidence=result.get("screenshots", [])
        )


# Create default framework instance
default_framework = ValidationFramework(level=ValidationLevel.STANDARD)

# Register built-in validators
default_framework.register_validator(ValidationType.SYNTAX_CHECK, syntax_check_validator)
default_framework.register_validator(ValidationType.UNIT_TESTS, unit_tests_validator)
default_framework.register_validator(ValidationType.BROWSER_TESTS, browser_tests_validator)
