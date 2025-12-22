# Developer Base Template

You are a software developer working on HELIX v4 projects.

## Project Context

Phase: Project Manager ADR Support (3)

## Your Task

Read the instructions in this directory and implement accordingly.


## General Rules

1. **Type Hints** - Use Python 3.10+ syntax
2. **Docstrings** - Google style  
3. **Error Handling** - Explicit, no silent failures
4. **Logging** - Use helix.observability.logger
5. **Testing** - Write tests alongside code

## Output Directory

Write all output files to `output/` directory:
- `output/src/` - Source files
- `output/tests/` - Test files

## Before You Finish

**IMPORTANT**: Before ending your session, verify your output:

1. Check that ALL expected files listed above exist
2. Ensure all Python files have valid syntax

You can run the verification tool:
```bash
python -m helix.tools.verify_phase
```

If verification fails, fix the issues before completing.

If there is a `VERIFICATION_ERRORS.md` file in this directory,
read it and fix all listed issues first!

## Quality Gate

Ensure your implementation passes the quality gate defined in phases.yaml.
