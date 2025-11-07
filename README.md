# Software-Development

## Agent Readiness Check Framework

This repository includes a comprehensive validation framework that ensures AI agents properly test their work before claiming success.

### 🎯 Quick Start

```bash
# Install dependencies
pip install -r requirements_validation.txt
playwright install

# Run validation on your feature
python agent_validator.py --task-id YOUR-TASK-ID --config test_config.yaml
```

### 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Get started in 5 minutes
- **[AGENT_READINESS_FRAMEWORK.md](./AGENT_READINESS_FRAMEWORK.md)** - Complete framework documentation
- **[test_config.example.yaml](./test_config.example.yaml)** - Example configuration file

### 🔍 What Gets Validated

1. ✅ Code validation (linting, type checking, tests)
2. ✅ E2E testing (browser automation)
3. ✅ Log analysis (error detection)
4. ✅ Visual verification (OCR, screenshot analysis)
5. ✅ Proof-of-work report generation

### 🤖 For AI Agents

**MANDATORY WORKFLOW:** Before claiming any task is "ready" or "complete", you MUST:

1. Create a `test_config.yaml` for your changes
2. Run `python agent_validator.py --task-id TASK-ID --config test_config.yaml`
3. Ensure ALL validation stages pass
4. Only commit if validation status is **APPROVED**

**No exceptions. No shortcuts.**

---

## Industrial Loading System Documentation

See [DEVELOPER_MANUAL_V5.md](./DEVELOPER_MANUAL_V5.md) for complete system documentation.
