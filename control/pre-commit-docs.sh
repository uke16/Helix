#!/bin/bash
#
# pre-commit-docs
#
# Pre-commit hook for HELIX documentation.
# Checks if generated docs are current and regenerates if needed.
#
# Installation:
#   cp output/scripts/pre-commit-docs .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Or add to existing pre-commit hook.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get repository root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Directories
SOURCES_DIR="$REPO_ROOT/docs/sources"
TEMPLATES_DIR="$REPO_ROOT/docs/templates"
GENERATED_FILES=(
    "CLAUDE.md"
    "skills/helix/SKILL.md"
)

echo -e "${YELLOW}[docs]${NC} Checking documentation..."

# Check if any source files are staged
STAGED_SOURCES=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^docs/sources/.*\.yaml$" || true)
STAGED_TEMPLATES=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^docs/templates/.*\.j2$" || true)
STAGED_PYTHON=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^src/helix/.*\.py$" || true)

# If no relevant files are staged, skip check
if [ -z "$STAGED_SOURCES" ] && [ -z "$STAGED_TEMPLATES" ] && [ -z "$STAGED_PYTHON" ]; then
    echo -e "${GREEN}[docs]${NC} No documentation sources changed, skipping."
    exit 0
fi

echo -e "${YELLOW}[docs]${NC} Documentation sources changed, validating..."

# Run validation
if ! python3 -m helix.tools.docs_compiler validate 2>/dev/null; then
    echo -e "${RED}[docs]${NC} Documentation validation failed!"
    echo "Run: python3 -m helix.tools.docs_compiler validate"
    exit 1
fi

echo -e "${GREEN}[docs]${NC} Validation passed."

# Check if regeneration is needed
NEEDS_REGEN=false

# Get latest modification time of sources
LATEST_SOURCE_TIME=0
if [ -d "$SOURCES_DIR" ]; then
    for yaml_file in "$SOURCES_DIR"/*.yaml; do
        if [ -f "$yaml_file" ]; then
            FILE_TIME=$(stat -c %Y "$yaml_file" 2>/dev/null || stat -f %m "$yaml_file" 2>/dev/null || echo 0)
            if [ "$FILE_TIME" -gt "$LATEST_SOURCE_TIME" ]; then
                LATEST_SOURCE_TIME=$FILE_TIME
            fi
        fi
    done
fi

# Get latest modification time of templates
if [ -d "$TEMPLATES_DIR" ]; then
    for j2_file in "$TEMPLATES_DIR"/*.j2 "$TEMPLATES_DIR"/*/*.j2; do
        if [ -f "$j2_file" ]; then
            FILE_TIME=$(stat -c %Y "$j2_file" 2>/dev/null || stat -f %m "$j2_file" 2>/dev/null || echo 0)
            if [ "$FILE_TIME" -gt "$LATEST_SOURCE_TIME" ]; then
                LATEST_SOURCE_TIME=$FILE_TIME
            fi
        fi
    done
fi

# Check each generated file
for GEN_FILE in "${GENERATED_FILES[@]}"; do
    GEN_PATH="$REPO_ROOT/$GEN_FILE"
    if [ -f "$GEN_PATH" ]; then
        GEN_TIME=$(stat -c %Y "$GEN_PATH" 2>/dev/null || stat -f %m "$GEN_PATH" 2>/dev/null || echo 0)
        if [ "$LATEST_SOURCE_TIME" -gt "$GEN_TIME" ]; then
            echo -e "${YELLOW}[docs]${NC} $GEN_FILE is out of date."
            NEEDS_REGEN=true
        fi
    else
        echo -e "${YELLOW}[docs]${NC} $GEN_FILE does not exist."
        NEEDS_REGEN=true
    fi
done

# Regenerate if needed
if [ "$NEEDS_REGEN" = true ]; then
    echo -e "${YELLOW}[docs]${NC} Regenerating documentation..."

    if python3 -m helix.tools.docs_compiler compile 2>/dev/null; then
        echo -e "${GREEN}[docs]${NC} Documentation regenerated."

        # Add regenerated files to commit
        for GEN_FILE in "${GENERATED_FILES[@]}"; do
            GEN_PATH="$REPO_ROOT/$GEN_FILE"
            if [ -f "$GEN_PATH" ]; then
                git add "$GEN_PATH"
                echo -e "${GREEN}[docs]${NC} Added $GEN_FILE to commit."
            fi
        done
    else
        echo -e "${RED}[docs]${NC} Documentation regeneration failed!"
        echo "Run: python3 -m helix.tools.docs_compiler compile"
        exit 1
    fi
else
    echo -e "${GREEN}[docs]${NC} Documentation is up to date."
fi

# Check for docstrings in changed Python files
if [ -n "$STAGED_PYTHON" ]; then
    echo -e "${YELLOW}[docs]${NC} Checking docstrings in changed Python files..."

    MISSING_DOCSTRINGS=false

    for py_file in $STAGED_PYTHON; do
        if [ -f "$REPO_ROOT/$py_file" ]; then
            # Quick check for module docstring (first string after any initial comments)
            if ! head -20 "$REPO_ROOT/$py_file" | grep -q '"""' && \
               ! head -20 "$REPO_ROOT/$py_file" | grep -q "'''"; then
                echo -e "${YELLOW}[docs]${NC} Warning: $py_file may be missing module docstring"
                MISSING_DOCSTRINGS=true
            fi
        fi
    done

    if [ "$MISSING_DOCSTRINGS" = true ]; then
        echo -e "${YELLOW}[docs]${NC} Some files may be missing docstrings (warning only)."
    else
        echo -e "${GREEN}[docs]${NC} Docstring check passed."
    fi
fi

echo -e "${GREEN}[docs]${NC} Pre-commit documentation check complete."

# ============================================================
# NEW: Check if src/helix/ changed without docs/sources/
# ============================================================
STAGED_HELIX_CODE=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^src/helix/[^/]+/" | grep -v "__pycache__" || true)
STAGED_DOCS_SOURCES=$(git diff --cached --name-only --diff-filter=ACM | grep -E "^docs/sources/.*\.yaml$" || true)

if [ -n "$STAGED_HELIX_CODE" ] && [ -z "$STAGED_DOCS_SOURCES" ]; then
    echo -e "${YELLOW}[docs]${NC} ⚠️  WARNING: New code in src/helix/ without docs/sources/ update!"
    echo -e "${YELLOW}[docs]${NC} Changed modules:"
    echo "$STAGED_HELIX_CODE" | head -5
    echo ""
    echo -e "${YELLOW}[docs]${NC} Consider updating docs/sources/*.yaml for new features."
    echo -e "${YELLOW}[docs]${NC} Then run: python3 -m helix.tools.docs_compiler compile"
    echo ""
    echo -e "${YELLOW}[docs]${NC} (This is a warning, commit will proceed)"
    echo ""
fi

exit 0
