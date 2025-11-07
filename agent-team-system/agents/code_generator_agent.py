"""
Code Generator Agent

Generates code from specifications while respecting style guides
and reusing existing components.

Supports multiple domains:
- Industrial systems (SCADA, PLC communications)
- Business software (billing, project management)
- Engineering tools (CAD integrations)
- Web applications
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_base import BaseAgent


class CodeGeneratorAgent(BaseAgent):
    """
    Agent that generates code from specifications.

    Features:
    - Respects existing style guides
    - Reuses pre-built components
    - Supports multiple languages and frameworks
    - Follows project-specific patterns
    """

    def __init__(self, **kwargs):
        super().__init__(name="code_generator", **kwargs)

        # Load style guide
        self.style_guide = self._load_style_guide()

        # Load reusable components registry
        self.components_registry = self._load_components_registry()

        # Supported languages and frameworks
        self.supported_languages = {
            'python': ['flask', 'fastapi', 'django'],
            'javascript': ['react', 'vue', 'angular'],
            'typescript': ['react', 'vue', 'angular'],
            'c': ['embedded', 'drivers'],
            'cpp': ['scada', 'embedded'],
            'csharp': ['wpf', 'winforms', '.net'],
        }

        self.logger.info("Code Generator Agent initialized")

    def _load_style_guide(self) -> Dict[str, Any]:
        """Load project style guide"""
        style_guide_file = self.workspace_dir / "config" / "style_guide.json"

        if style_guide_file.exists():
            with open(style_guide_file, 'r') as f:
                return json.load(f)

        # Return default style guide
        return {
            "naming_conventions": {
                "classes": "PascalCase",
                "functions": "snake_case",
                "variables": "snake_case",
                "constants": "UPPER_SNAKE_CASE"
            },
            "indentation": "4 spaces",
            "max_line_length": 100,
            "docstring_style": "google",
            "import_order": ["standard_library", "third_party", "local"],
        }

    def _load_components_registry(self) -> Dict[str, Any]:
        """Load registry of reusable components"""
        registry_file = self.workspace_dir / "config" / "components_registry.json"

        if registry_file.exists():
            with open(registry_file, 'r') as f:
                return json.load(f)

        # Return default registry
        return {
            "ui_components": {
                "data_table": "components/ui/DataTable",
                "chart": "components/ui/Chart",
                "form": "components/ui/Form",
                "modal": "components/ui/Modal",
            },
            "backend_modules": {
                "authentication": "modules/auth",
                "logging": "modules/logging",
                "database": "modules/database",
            },
            "communication_drivers": {
                "modbus": "drivers/modbus_driver",
                "opcua": "drivers/opcua_driver",
                "serial": "drivers/serial_driver",
            },
            "industrial_protocols": {
                "scada": "protocols/scada_protocol",
                "plc": "protocols/plc_protocol",
            }
        }

    def _execute_task_impl(self, task: Dict[str, Any]) -> Any:
        """
        Generate code based on task parameters

        Task params:
        - spec_file: Path to specification file
        - output_dir: Where to write generated code
        - language: Target programming language
        - framework: Framework to use (optional)
        - domain: Domain type (industrial, business, engineering, etc.)
        - reuse_components: Whether to use existing components
        """
        self.update_progress(5, "Loading specification")

        # Extract parameters
        spec_file = task.get("params", {}).get("spec_file")
        output_dir = Path(task.get("params", {}).get("output_dir", "generated"))
        language = task.get("params", {}).get("language", "python")
        framework = task.get("params", {}).get("framework")
        domain = task.get("params", {}).get("domain", "general")
        reuse_components = task.get("params", {}).get("reuse_components", True)

        if not spec_file:
            raise ValueError("spec_file parameter is required")

        # Load specification
        spec = self._load_specification(spec_file)
        self.update_progress(15, "Specification loaded")

        # Analyze spec and identify reusable components
        if reuse_components:
            self.update_progress(25, "Identifying reusable components")
            components_to_reuse = self._identify_reusable_components(spec, domain)
            self.logger.info(f"Found {len(components_to_reuse)} reusable components")

        # Generate code structure
        self.update_progress(40, "Generating code structure")
        code_structure = self._generate_code_structure(spec, language, framework, domain)

        # Generate actual code files
        self.update_progress(60, "Generating code files")
        generated_files = self._generate_code_files(
            code_structure,
            output_dir,
            language,
            reuse_components
        )

        # Apply style guide
        self.update_progress(80, "Applying style guide")
        self._apply_style_guide(generated_files, language)

        # Generate tests
        self.update_progress(90, "Generating tests")
        test_files = self._generate_tests(generated_files, language)

        self.update_progress(100, "Code generation complete")

        return {
            "generated_files": [str(f) for f in generated_files],
            "test_files": [str(f) for f in test_files],
            "language": language,
            "framework": framework,
            "domain": domain,
            "components_reused": len(components_to_reuse) if reuse_components else 0,
        }

    def _load_specification(self, spec_file: str) -> Dict[str, Any]:
        """Load specification from file"""
        spec_path = Path(spec_file)

        if not spec_path.exists():
            raise FileNotFoundError(f"Specification file not found: {spec_file}")

        # Support multiple spec formats
        if spec_path.suffix == '.json':
            with open(spec_path, 'r') as f:
                return json.load(f)
        elif spec_path.suffix in ['.yaml', '.yml']:
            import yaml
            with open(spec_path, 'r') as f:
                return yaml.safe_load(f)
        elif spec_path.suffix == '.md':
            # Parse markdown specification
            return self._parse_markdown_spec(spec_path)
        else:
            raise ValueError(f"Unsupported specification format: {spec_path.suffix}")

    def _parse_markdown_spec(self, spec_path: Path) -> Dict[str, Any]:
        """Parse markdown specification"""
        # Simplified parser - extract key information
        with open(spec_path, 'r') as f:
            content = f.read()

        spec = {
            "title": "Untitled",
            "description": "",
            "modules": [],
            "components": [],
            "requirements": [],
        }

        # Extract title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            spec["title"] = title_match.group(1)

        # Extract sections
        sections = re.split(r'^##\s+(.+)$', content, flags=re.MULTILINE)

        for i in range(1, len(sections), 2):
            section_title = sections[i].lower()
            section_content = sections[i + 1] if i + 1 < len(sections) else ""

            if "module" in section_title or "component" in section_title:
                # Extract module/component names
                items = re.findall(r'^[-*]\s+(.+)$', section_content, re.MULTILINE)
                spec["modules"].extend(items)

        return spec

    def _identify_reusable_components(self, spec: Dict[str, Any], domain: str) -> List[str]:
        """Identify which components from the registry can be reused"""
        reusable = []

        # Check for common UI components
        if "ui" in spec or "frontend" in spec:
            for component in ["data_table", "chart", "form", "modal"]:
                if component in str(spec).lower():
                    reusable.append(self.components_registry["ui_components"].get(component))

        # Check for domain-specific components
        if domain == "industrial":
            # Check for communication protocols
            for protocol in ["modbus", "opcua", "scada", "plc"]:
                if protocol in str(spec).lower():
                    if protocol in self.components_registry.get("communication_drivers", {}):
                        reusable.append(self.components_registry["communication_drivers"][protocol])
                    elif protocol in self.components_registry.get("industrial_protocols", {}):
                        reusable.append(self.components_registry["industrial_protocols"][protocol])

        # Remove None values
        return [r for r in reusable if r]

    def _generate_code_structure(
        self,
        spec: Dict[str, Any],
        language: str,
        framework: Optional[str],
        domain: str
    ) -> Dict[str, Any]:
        """Generate high-level code structure"""
        structure = {
            "directories": [],
            "files": {},
            "dependencies": [],
        }

        # Domain-specific structure
        if domain == "industrial":
            structure["directories"] = [
                "drivers",
                "protocols",
                "scada",
                "monitoring",
                "alarms",
                "tests",
            ]
            structure["dependencies"] = ["pymodbus", "opcua", "pyserial"]

        elif domain == "business":
            structure["directories"] = [
                "models",
                "services",
                "api",
                "billing",
                "reporting",
                "tests",
            ]
            structure["dependencies"] = ["sqlalchemy", "pydantic", "pandas"]

        elif domain == "engineering":
            structure["directories"] = [
                "cad",
                "calculations",
                "analysis",
                "export",
                "tests",
            ]
            structure["dependencies"] = ["numpy", "scipy", "matplotlib"]

        else:  # general
            structure["directories"] = [
                "src",
                "tests",
                "docs",
            ]

        # Add framework-specific structure
        if framework == "fastapi":
            structure["directories"].extend(["routers", "schemas", "crud"])
            structure["files"]["main.py"] = self._generate_fastapi_main()

        elif framework == "react":
            structure["directories"].extend(["components", "hooks", "contexts"])
            structure["files"]["App.tsx"] = self._generate_react_app()

        return structure

    def _generate_code_files(
        self,
        structure: Dict[str, Any],
        output_dir: Path,
        language: str,
        reuse_components: bool
    ) -> List[Path]:
        """Generate actual code files"""
        generated_files = []

        # Create directories
        for directory in structure["directories"]:
            dir_path = output_dir / directory
            dir_path.mkdir(parents=True, exist_ok=True)

        # Generate files
        for file_path, content in structure["files"].items():
            full_path = output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w') as f:
                f.write(content)

            generated_files.append(full_path)
            self.logger.info(f"Generated: {full_path}")

        return generated_files

    def _generate_fastapi_main(self) -> str:
        """Generate FastAPI main.py"""
        return '''"""
FastAPI Application

Auto-generated by Agent Team System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="API Server",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "API is running"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
'''

    def _generate_react_app(self) -> str:
        """Generate React App.tsx"""
        return '''/**
 * React Application
 *
 * Auto-generated by Agent Team System
 */

import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Application</h1>
        <p>Auto-generated by Agent Team System</p>
      </header>
    </div>
  );
}

export default App;
'''

    def _apply_style_guide(self, files: List[Path], language: str):
        """Apply style guide to generated files"""
        for file_path in files:
            if language == "python" and file_path.suffix == ".py":
                self._format_python_file(file_path)
            elif language in ["javascript", "typescript"] and file_path.suffix in [".js", ".ts", ".tsx"]:
                self._format_javascript_file(file_path)

    def _format_python_file(self, file_path: Path):
        """Format Python file according to style guide"""
        # In production, would use black or similar
        self.logger.debug(f"Formatting Python file: {file_path}")

    def _format_javascript_file(self, file_path: Path):
        """Format JavaScript/TypeScript file"""
        # In production, would use prettier or similar
        self.logger.debug(f"Formatting JavaScript file: {file_path}")

    def _generate_tests(self, generated_files: List[Path], language: str) -> List[Path]:
        """Generate test files for generated code"""
        test_files = []

        for file_path in generated_files:
            # Skip non-code files
            if file_path.suffix not in ['.py', '.js', '.ts', '.tsx']:
                continue

            # Generate test file
            if language == "python":
                test_file = file_path.parent.parent / "tests" / f"test_{file_path.name}"
            else:
                test_file = file_path.parent / "__tests__" / f"{file_path.stem}.test{file_path.suffix}"

            test_file.parent.mkdir(parents=True, exist_ok=True)

            # Generate basic test structure
            test_content = self._generate_test_content(file_path, language)

            with open(test_file, 'w') as f:
                f.write(test_content)

            test_files.append(test_file)
            self.logger.info(f"Generated test: {test_file}")

        return test_files

    def _generate_test_content(self, source_file: Path, language: str) -> str:
        """Generate test content for a source file"""
        if language == "python":
            return f'''"""
Tests for {source_file.name}

Auto-generated by Agent Team System
"""

import pytest


def test_placeholder():
    """Placeholder test"""
    assert True


# TODO: Add real tests for {source_file.stem}
'''
        else:  # JavaScript/TypeScript
            return f'''/**
 * Tests for {source_file.name}
 *
 * Auto-generated by Agent Team System
 */

describe('{source_file.stem}', () => {{
  test('placeholder test', () => {{
    expect(true).toBe(true);
  }});

  // TODO: Add real tests for {source_file.stem}
}});
'''

    def _attempt_recovery(self, task: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Attempt recovery from code generation errors"""
        self.logger.info(f"Attempting recovery from: {error}")

        # Try with simplified specification
        if "complexity" in str(error).lower():
            self.logger.info("Retrying with simplified approach")
            task["params"]["simplified"] = True
            try:
                result = self._execute_task_impl(task)
                return {
                    "recovered": True,
                    "result": result,
                    "recovery_method": "simplified_spec"
                }
            except Exception as e:
                return {"recovered": False, "error": str(e)}

        return {"recovered": False, "error": str(error)}


# Example usage
if __name__ == "__main__":
    agent = CodeGeneratorAgent(workspace_dir=Path("./workspace"))

    # Example task for industrial system
    task = {
        "name": "generate-scada-interface",
        "params": {
            "spec_file": "specs/scada_interface.md",
            "output_dir": "output/scada",
            "language": "python",
            "framework": "fastapi",
            "domain": "industrial",
            "reuse_components": True,
        }
    }

    result = agent.execute_task(task)
    print(f"Generated {len(result['generated_files'])} files")
