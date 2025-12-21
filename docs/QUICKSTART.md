# HELIX v4 Quickstart

## Prerequisites

- Python 3.11+
- Node.js 20+ (for Claude Code)
- Claude Code CLI installed
- API key (Anthropic or OpenRouter)

## Installation

```bash
# Clone repository
git clone <repo-url>
cd helix-v4

# Install Python dependencies
pip install -e .

# Verify installation
helix --version
```

## Your First Project

### 1. Create a new project

```bash
helix new my-feature --type feature
```

### 2. Describe your feature

Edit `projects/my-feature/input/request.md`:
```markdown
I want to create a feature that exports
product data to a CSV file.
```

### 3. Run the project

```bash
helix run ./projects/my-feature
```

### 4. Monitor progress

```bash
helix status ./projects/my-feature
helix debug ./projects/my-feature --tail 50
```

### 5. Check costs

```bash
helix costs ./projects/my-feature
```

## Next Steps

- Read [User Guide](USER-GUIDE.md) for full documentation
- Check [CLI Reference](CLI-REFERENCE.md) for all commands
- See [Configuration](CONFIGURATION.md) for customization
