# HELIX v4 Bootstrap - Phase 10: End-to-End Test

This phase tests the complete HELIX workflow by building a real tool.

## Objective

Test the full HELIX pipeline:
1. Fix missing `helix discuss` CLI command
2. Create a test project
3. Run Consultant Meeting (real LLM calls)
4. Execute the generated workflow
5. Verify the output

## Part 1: Add Missing CLI Command

The `helix discuss` command is missing. Add it to `/home/aiuser01/helix-v4/src/helix/cli/commands.py`:

```python
@click.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--request", "-r", help="Path to request.md file or direct request text")
@click.option("--model", "-m", default="claude-opus-4", help="LLM model for consultant")
@handle_error
def discuss(project_path: str, request: Optional[str], model: str) -> None:
    """Start a consultant meeting for a project.

    PROJECT_PATH is the path to the project directory.
    
    The consultant will analyze the request, consult domain experts,
    and generate spec.yaml, phases.yaml, and ADR documents.
    """
    from helix.consultant import ConsultantMeeting, ExpertManager
    from helix.llm_client import LLMClient

    project = Path(project_path).resolve()
    
    # Load request
    if request and Path(request).exists():
        user_request = Path(request).read_text()
    elif request:
        user_request = request
    else:
        request_file = project / "input" / "request.md"
        if not request_file.exists():
            click.secho("✗ No request provided. Use --request or create input/request.md", fg="red")
            sys.exit(1)
        user_request = request_file.read_text()

    click.secho(f"→ Starting consultant meeting for: {project.name}", fg="blue")
    click.secho(f"→ Using model: {model}", fg="blue")
    
    llm_client = LLMClient()
    expert_manager = ExpertManager()
    meeting = ConsultantMeeting(llm_client, expert_manager)

    async def run_meeting():
        result = await meeting.run(project, user_request)
        return result

    try:
        result = asyncio.run(run_meeting())
        
        click.secho("\n✓ Consultant meeting completed!", fg="green")
        click.secho(f"  → Experts consulted: {', '.join(result.experts_consulted)}", fg="white")
        click.secho(f"  → Duration: {result.duration_seconds:.1f}s", fg="white")
        
        if result.spec:
            click.secho(f"  → Created: spec.yaml", fg="green")
        if result.phases:
            click.secho(f"  → Created: phases.yaml", fg="green")
        if result.adr_path:
            click.secho(f"  → Created: {result.adr_path.name}", fg="green")
            
        click.secho(f"\n→ Next step: helix run {project_path}", fg="blue")
        
    except Exception as e:
        click.secho(f"✗ Meeting failed: {e}", fg="red")
        sys.exit(1)
```

Also register the command in `main.py`:
```python
cli.add_command(discuss)
```

## Part 2: Create Test Project

Create the test project structure:

```bash
# Create project directory
mkdir -p /home/aiuser01/helix-v4/projects/external/config-validator/{input,phases,adr,output}

# Create the user request
cat > /home/aiuser01/helix-v4/projects/external/config-validator/input/request.md << 'REQUEST'
# Feature Request: HELIX Config Validator

I need a Python CLI tool that validates all YAML configuration files in the HELIX config/ directory.

## Requirements

1. **Validate all config files**:
   - config/llm-providers.yaml
   - config/quality-gates.yaml
   - config/escalation.yaml
   - config/streaming.yaml
   - config/domain-experts.yaml

2. **Validation checks**:
   - YAML syntax is valid
   - Required fields are present
   - Field values are of correct type
   - Cross-references are valid (e.g., model aliases point to existing models)

3. **Output**:
   - Console output with colored status (green=OK, red=ERROR)
   - Summary at the end (X files checked, Y errors found)
   - Exit code 0 if all valid, 1 if errors

4. **Usage**:
   ```
   python config_validator.py [--verbose]
   ```

## Expected Output

```
Validating HELIX configuration files...

✓ llm-providers.yaml - OK (3 providers, 8 models)
✓ quality-gates.yaml - OK (5 gates defined)
✗ escalation.yaml - ERROR: missing 'max_retries' field
✓ streaming.yaml - OK (4 levels defined)
✓ domain-experts.yaml - OK (7 experts)

Summary: 4/5 files valid, 1 error found
```

REQUEST
```

## Part 3: Run the Consultant Meeting

Execute the discuss command:

```bash
cd /home/aiuser01/helix-v4
export PYTHONPATH=/home/aiuser01/helix-v4/src
export HELIX_OPENROUTER_API_KEY=$(cat /home/aiuser01/.helix-openrouter-key 2>/dev/null || echo "")

# Run the consultant meeting
python -m helix.cli.main discuss ./projects/external/config-validator --model openrouter:claude-sonnet-4
```

The consultant should:
1. Analyze the request
2. Select relevant experts (helix, infrastructure)
3. Generate spec.yaml
4. Generate phases.yaml
5. Optionally create an ADR

## Part 4: Execute the Workflow

After the consultant meeting, run the implementation:

```bash
cd /home/aiuser01/helix-v4
python -m helix.cli.main run ./projects/external/config-validator
```

This should:
1. Load the generated phases.yaml
2. Execute each phase using Claude Code
3. Check quality gates
4. Produce the final tool

## Part 5: Verify the Result

Test that the config validator was created and works:

```bash
cd /home/aiuser01/helix-v4/projects/external/config-validator

# Check if the tool was created
ls -la output/

# Run the validator on HELIX config
python output/config_validator.py --verbose

# Or if it's in a different location, find it
find . -name "*.py" -newer input/request.md
```

## Success Criteria

1. ✅ `helix discuss` command added and works
2. ✅ Consultant meeting completes successfully
3. ✅ spec.yaml generated with correct structure
4. ✅ phases.yaml generated with implementation phases
5. ✅ `helix run` executes without errors
6. ✅ config_validator.py created and functional
7. ✅ Validator correctly checks HELIX config files

## Output

Create `/home/aiuser01/helix-v4/projects/internal/helix-v4-bootstrap/phases/10-e2e-test/output/result.json`:

```json
{
  "status": "success",
  "e2e_test": {
    "discuss_command_added": true,
    "consultant_meeting_completed": true,
    "spec_yaml_generated": true,
    "phases_yaml_generated": true,
    "workflow_executed": true,
    "tool_created": true,
    "tool_functional": true
  },
  "files_created": [
    "src/helix/cli/commands.py (modified)",
    "projects/external/config-validator/spec.yaml",
    "projects/external/config-validator/phases.yaml",
    "projects/external/config-validator/output/config_validator.py"
  ],
  "validation_result": {
    "files_checked": 5,
    "errors_found": 0
  }
}
```

## Notes

- Use `openrouter:claude-sonnet-4` for cost efficiency
- The consultant meeting makes real LLM API calls
- If API errors occur, check the HELIX_OPENROUTER_API_KEY
- All output should be in English
