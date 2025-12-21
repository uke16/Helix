# HELIX v4 CLI Reference

## Global Options

```bash
helix --version    # Show version
helix --help       # Show help
```

## Commands

### helix new

Create a new project.

```bash
helix new <name> [OPTIONS]

Options:
  --type, -t    Project type: feature|bugfix|documentation|research
  --output, -o  Output directory
```

Examples:
```bash
helix new bom-export --type feature
helix new fix-login --type bugfix
helix new api-docs --type documentation
```

### helix run

Execute a project workflow.

```bash
helix run <project_path> [OPTIONS]

Options:
  --phase, -p   Start from specific phase
  --model, -m   LLM model to use
  --dry-run     Show what would be done
```

Examples:
```bash
helix run ./projects/my-feature
helix run ./projects/my-feature --phase 02-development
helix run ./projects/my-feature --model opus
```

### helix status

Show project status.

```bash
helix status <project_path>
```

Output includes:
- Current phase
- Phase status (pending/running/completed/failed)
- Quality gate results

### helix debug

Show debug logs.

```bash
helix debug <project_path> [phase] [OPTIONS]

Options:
  --tail, -n    Number of log lines (default: 50)
```

Examples:
```bash
helix debug ./projects/my-feature
helix debug ./projects/my-feature 02-development --tail 100
```

### helix costs

Show token usage and costs.

```bash
helix costs <project_path> [OPTIONS]

Options:
  --detailed, -d  Show per-phase breakdown
```

Output includes:
- Total tokens (input/output)
- Cost in USD
- Per-phase breakdown (with --detailed)
