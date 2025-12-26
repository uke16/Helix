# LSP Setup for HELIX v4

> Language Server Protocol integration for Claude Code sessions.
>
> Enables real-time syntax checking, go-to-definition, and find-references.

---

## Overview

Claude Code has native LSP support since December 2024. This document explains
how to activate and use LSP features in HELIX development phases.

### Benefits

- **Real-time Diagnostics**: Syntax errors detected immediately
- **Go-to-Definition**: Navigate to function/class definitions
- **Find References**: Find all usages of a symbol
- **Anti-Hallucination**: Verify symbols exist before using them
- **Better Refactoring**: Know all places that need changes

---

## Quick Start

### 1. Install Pyright

```bash
# Via npm (recommended)
npm install -g pyright

# Verify installation
pyright --version
```

### 2. Enable LSP in Claude Code

Set the environment variable:

```bash
export ENABLE_LSP_TOOL=1
```

### 3. Use LSP Operations

The following LSP operations are available in Claude Code:

| Operation | Description |
|-----------|-------------|
| `goToDefinition` | Find where a symbol is defined |
| `findReferences` | Find all usages of a symbol |
| `hover` | Get documentation and type info |
| `documentSymbol` | List all symbols in a file |
| `workspaceSymbol` | Search symbols across the project |

---

## Installation Details

### Python (Pyright)

Pyright is the recommended Python language server.

```bash
# Install globally
npm install -g pyright

# Or via pip
pip install pyright
```

**Requirements:**
- Node.js 16+ (for npm installation)
- Python 3.8+ (for type checking)

### TypeScript (vtsls)

```bash
npm install -g @vtsls/language-server typescript
```

### Go (gopls)

```bash
go install golang.org/x/tools/gopls@latest
```

---

## HELIX Integration

### PhaseExecutor Configuration

The PhaseExecutor automatically enables LSP for development phases:

```python
# src/helix/orchestrator/phase_executor.py

async def execute(self, phase_dir: Path, phase_config: PhaseConfig) -> PhaseResult:
    env = os.environ.copy()

    # LSP enabled for these phase types
    if phase_config.type in ("development", "review", "integration"):
        env["ENABLE_LSP_TOOL"] = "1"

    result = await self._run_claude(phase_dir, env)
    return result
```

### Config File

See `config/lsp.conf` for persistent configuration:

```bash
# LSP Configuration
ENABLE_LSP_TOOL=1
LSP_PYTHON_SERVER=pyright
```

---

## Usage Examples

### Go to Definition

Find where a function is implemented:

```
LSP goToDefinition on "calculate_total" at src/billing/api.py:42
Result: src/billing/calculator.py:15
```

### Find References

Find all places that use a class:

```
LSP findReferences on "UserService" at src/services/user.py:10
Results:
  - src/api/routes.py:12
  - src/api/routes.py:89
  - tests/test_api.py:34
```

### Hover

Get documentation and type info:

```
LSP hover on "process_request" at src/handlers/main.py:25
Result: def process_request(data: dict) -> Response
        """Process incoming API request."""
```

### Document Symbols

List all symbols in a file:

```
LSP documentSymbol on src/models/user.py
Results:
  - class User
  - class UserCreate
  - def validate_email
  - def hash_password
```

### Workspace Symbol

Search for symbols across the project:

```
LSP workspaceSymbol query "*Handler"
Results:
  - RequestHandler (src/handlers/request.py)
  - ErrorHandler (src/handlers/error.py)
  - WebhookHandler (src/handlers/webhook.py)
```

---

## Best Practices

### Anti-Hallucination

Before calling a function, verify it exists:

1. Use `goToDefinition` to confirm the symbol exists
2. Use `hover` to verify the correct signature
3. Then write your code

```python
# Bad: Assuming function exists
result = process_user_data(user)  # Might not exist!

# Good: Verify first
# LSP goToDefinition: process_user_data -> src/utils.py:42
# LSP hover: def process_user_data(user: User) -> dict
result = process_user_data(user)  # Verified!
```

### Safe Refactoring

Before renaming a symbol:

1. Use `findReferences` to find all usages
2. Note all locations
3. Make changes
4. Verify with `findReferences` again

### Diagnostics

- Fix all errors before committing
- Address warnings when possible
- Diagnostics appear automatically after edits

---

## Troubleshooting

### "No LSP server available for file type"

**Cause:** Language server not installed or not in PATH.

**Solution:**
```bash
# Check if pyright is available
which pyright

# If not found, install it
npm install -g pyright

# Verify PATH includes npm global bin
echo $PATH | grep -q "$(npm bin -g)" || export PATH="$PATH:$(npm bin -g)"
```

### LSP Tool Not Available

**Cause:** `ENABLE_LSP_TOOL` not set.

**Solution:**
```bash
export ENABLE_LSP_TOOL=1
```

### Slow Language Server

**Cause:** Large codebase or missing type stubs.

**Solution:**
```bash
# Install type stubs for common packages
pip install types-requests types-PyYAML

# Configure pyrightconfig.json to exclude unnecessary paths
```

### Wrong Python Version

**Cause:** Pyright using wrong Python interpreter.

**Solution:**
Create `pyrightconfig.json` in project root:
```json
{
  "pythonVersion": "3.12",
  "venvPath": ".",
  "venv": ".venv"
}
```

---

## Claude Code Plugin System

When Claude Code's plugin marketplace becomes available:

```bash
# Add marketplace
claude /plugin marketplace add boostvolt/claude-code-lsps

# Install Python LSP
claude /plugin install pyright@claude-code-lsps

# Install TypeScript LSP
claude /plugin install vtsls@claude-code-lsps
```

---

## References

- [ADR-018: LSP Integration](../../adr/018-lsp-integration.md)
- [Claude Code LSP Plugins](https://github.com/boostvolt/claude-code-lsps)
- [Pyright Documentation](https://microsoft.github.io/pyright/)
- [Language Server Protocol Spec](https://microsoft.github.io/language-server-protocol/)

---

## Current Status (2024-12-26)

### System Check Results

| Component | Status | Details |
|-----------|--------|---------|
| Pyright | Installed | Version 1.1.407 via npm |
| Path | `/home/aiuser01/.nvm/versions/node/v20.19.6/bin/pyright` | Available globally |
| ENABLE_LSP_TOOL | Not set by default | Must be set manually or by PhaseExecutor |
| LSP Plugin | Not configured | Claude Code plugin marketplace not connected |

### Known Limitations

1. **LSP Tool returns "No LSP server available"** - This happens when:
   - `ENABLE_LSP_TOOL=1` is not set in the environment
   - The Claude Code LSP plugin is not installed from the marketplace

2. **Plugin Installation** - The `boostvolt/claude-code-lsps` marketplace is not currently added to this Claude Code installation.

### Next Steps

1. Configure PhaseExecutor to set `ENABLE_LSP_TOOL=1` for development phases
2. Add the LSP plugin marketplace when Claude Code plugin system is fully available
3. Test LSP functionality after configuration

---

## Verification Checklist

- [ ] Pyright installed and in PATH
- [ ] `ENABLE_LSP_TOOL=1` environment variable set
- [ ] LSP operations working (goToDefinition, etc.)
- [ ] Diagnostics appearing after edits
- [ ] PhaseExecutor configured for development phases
