# ADR-034 Phase 01: Analysis Report

## Executive Summary

This analysis examines the current Consultant Flow implementation to identify problematic patterns that should be refactored according to ADR-034: "LLM-Native statt State-Machine".

**Key Finding**: The current implementation uses a fragile, index-based state machine with hardcoded trigger-word detection instead of trusting the LLM to understand conversation context naturally.

---

## 1. `extract_state_from_messages()` Analysis

**Location**: `src/helix/api/session_manager.py:331-412`

### Current Implementation

```python
def extract_state_from_messages(self, messages: list[dict]) -> dict[str, Any]:
    """Extract conversation state from message history."""
    state = {
        "original_request": "",
        "step": "what",
        "answers": {"what": None, "why": None, "constraints": None},
        "message_count": len(messages),
    }
    # ... 80+ lines of complex logic
```

### Problematic Patterns

#### 1.1 Index-Based Step Detection (Lines 404-410)

```python
# Default progression based on message count
if len(user_messages) >= 4:
    state["step"] = "generate"
elif len(user_messages) >= 3:
    state["step"] = "constraints"
else:
    state["step"] = "why"
```

**Problem**: Assumes a fixed conversation structure:
- 1st message → "what"
- 2nd message → "why"
- 3rd message → "constraints"
- 4th+ message → "generate"

**Real-world failure cases**:
- User provides all information in first message → stuck on "why"
- User asks clarifying questions → step advances incorrectly
- User combines answers → misinterprets conversation flow

#### 1.2 Hardcoded Trigger-Word Detection (Lines 374-390)

```python
# ADR/Finalize triggers - use word-based detection
has_adr_request = (
    'adr' in last_msg and
    any(word in last_msg for word in ['erstelle', 'create', 'mach', 'schreib', 'generier'])
)

finalize_exact = [
    'finalisiere', 'finalize', 'leg das ab', 'adr schreiben',
]

# Execute triggers
elif any(word in last_msg for word in ['start', 'starte', 'los', 'go']):
    state["step"] = "execute"
```

**Problems**:

| Issue | Example | Consequence |
|-------|---------|-------------|
| **False Positive** | "Ich starte gerade VS Code" | Triggers `step = "execute"` |
| **False Positive** | "Los geht's mit der Analyse" | Triggers `step = "execute"` |
| **False Negative** | "Bitte das ADR jetzt generieren" | No exact trigger match |
| **False Negative** | "Kannst du das fertigmachen?" | Intent not recognized |
| **Language Gap** | Mixed DE/EN triggers | Incomplete coverage |

#### 1.3 Answer Indicator Detection (Lines 394-401)

```python
answer_indicators = [
    '1.', '2.', '3.', 'option', 'antwort', 'answer',
    'mount', 'auth', 'oauth', 'intern', 'extern',
    'ja', 'nein', 'yes', 'no', 'richtig', 'korrekt',
]
has_answers = any(ind in all_followup_content.lower() for ind in answer_indicators)
```

**Problems**:
- Domain-specific words (`mount`, `oauth`) shouldn't be step indicators
- Common words (`ja`, `nein`) trigger false positives
- No semantic understanding of actual answer content

### Classification

| Element | Classification | Reasoning |
|---------|----------------|-----------|
| Index-based step detection | **CARGO-CULT** | LLM understands conversation flow naturally |
| Trigger-word matching | **CARGO-CULT** | LLM understands intent semantically |
| Answer indicator detection | **CARGO-CULT** | LLM knows what constitutes an answer |
| `original_request` extraction | **KEEP** | Useful for context/logging |
| `message_count` tracking | **KEEP** | Useful for analytics |

---

## 2. Template Branches Analysis

**Location**: `templates/consultant/session.md.j2:115-351`

### Current Implementation

The template uses extensive `{% if step == "X" %}` branching:

```jinja2
{% if step == "what" %}
### Phase: Anforderungsklärung (WAS)
**Ziel**: Verstehe genau WAS gebaut werden soll.
...
{% elif step == "why" %}
### Phase: Bedarfsanalyse (WARUM)
**Ziel**: Verstehe den Business Case und die Motivation.
...
{% elif step == "constraints" %}
### Phase: Rahmenbedingungen (CONSTRAINTS)
...
{% elif step == "generate" %}
### Phase: Spezifikation erstellen
...
{% elif step == "execute" %}
### Phase: Projekt-Start
...
{% elif step == "finalize" %}
### Phase: ADR Finalisieren
...
{% endif %}
```

### Problematic Patterns

#### 2.1 Template-Driven Flow (Lines 115-351)

**Current Flow**:
```
Python detects step → Template shows only that step → LLM can only do that
```

**Problems**:
1. **No Backtracking**: User cannot say "wait, let me change that"
2. **Rigid Path**: User must follow predefined sequence
3. **Context Loss**: LLM only sees current phase instructions
4. **Overrides LLM Intelligence**: Template forces behavior

#### 2.2 Step-Specific Instructions

Each step has unique instructions that only appear when that step is active:

- `step == "what"`: Shows only "Was soll gebaut werden?" instructions
- `step == "why"`: Shows only "Warum wird das benötigt?" instructions
- etc.

**Consequence**: If Python incorrectly detects `step`, LLM receives wrong instructions entirely.

#### 2.3 Missing Flexibility

| Scenario | Current Behavior | Desired Behavior |
|----------|------------------|------------------|
| User wants to go back | Not possible | LLM understands "lass uns zurück..." |
| User provides all info at once | Forced through steps | LLM recognizes completeness |
| User changes mind | Step doesn't adapt | LLM adapts naturally |
| User asks unrelated question | Step forces topic | LLM handles gracefully |

### Classification

| Element | Classification | Reasoning |
|---------|----------------|-----------|
| `{% if step == "X" %}` branches | **CARGO-CULT** | One unified template is sufficient |
| Step-specific instructions | **CARGO-CULT** | LLM can select relevant information |
| Session metadata display | **KEEP** | Useful context for LLM |
| Skills/documentation references | **KEEP** | Important domain knowledge |
| ADR tools section | **KEEP** | Actionable instructions |

---

## 3. Expert Selection Analysis

**Location**: `src/helix/consultant/expert_manager.py:227-273`

### Current Implementation

```python
def select_experts(self, request: str) -> list[str]:
    """Select experts based on keywords in the request."""
    request_lower = request.lower()
    request_normalized = re.sub(r'[^\w\s]', ' ', request_lower)
    words = set(request_normalized.split())

    for expert_id, expert in experts.items():
        for trigger in expert.triggers:
            trigger_lower = trigger.lower()
            # Exact word match
            if trigger_lower in words:
                score += 2
            # Partial match (substring)
            elif trigger_lower in request_lower:
                score += 1
```

### Expert Trigger Configuration (Lines 72-175)

```python
DEFAULT_EXPERTS = {
    "helix": {
        "triggers": ["helix", "architektur", "architecture", "adr", ...]
    },
    "pdm": {
        "triggers": ["pdm", "stückliste", "bom", "revision", ...]
    },
    "infrastructure": {
        "triggers": ["docker", "container", "kubernetes", ...]
    },
    # ... more experts
}
```

### Problematic Patterns

#### 3.1 Keyword-Based Selection

**Problems**:

| Request | Expected Expert | Actual Selection | Issue |
|---------|-----------------|------------------|-------|
| "Wie deploye ich das?" | infrastructure | helix (default) | No keyword match |
| "Container für die API" | infrastructure | infrastructure | Works (keyword match) |
| "Das System soll skalieren" | infrastructure | helix (default) | No keyword match |
| "Datenbank Performance" | database | database | Works (keyword match) |

#### 3.2 No Context Awareness

- Only analyzes the current request text
- Ignores conversation history
- Cannot detect implicit domain references

#### 3.3 Primitive Scoring

```python
if trigger_lower in words:
    score += 2  # exact match
elif trigger_lower in request_lower:
    score += 1  # substring match
```

- Binary scoring (match/no match)
- No semantic relevance weighting
- False positives on partial matches (e.g., "bom" in "Bombastisch")

### Classification

| Element | Classification | Reasoning |
|---------|----------------|-----------|
| Keyword scoring | **PARTIALLY CARGO-CULT** | Could be hints, not mandatory |
| Trigger lists | **KEEP AS HINTS** | Useful starting point for LLM |
| Expert configs | **KEEP** | Good domain structure |
| Default fallback to "helix" | **KEEP** | Reasonable fallback |

---

## 4. Summary of Problematic Code Locations

### High Priority (Remove/Simplify)

| File | Lines | Function/Block | Issue |
|------|-------|----------------|-------|
| `session_manager.py` | 374-410 | Trigger detection + index logic | Overrides LLM intelligence |
| `session.md.j2` | 115-351 | `{% if step == %}` branches | Rigid, template-driven flow |

### Medium Priority (Refactor)

| File | Lines | Function/Block | Issue |
|------|-------|----------------|-------|
| `expert_manager.py` | 227-273 | `select_experts()` | Keyword-only, no semantics |

### Keep (Useful Code)

| File | Lines | Function/Block | Reason |
|------|-------|----------------|--------|
| `session_manager.py` | 343-359 | `original_request` extraction | Basic metadata |
| `session_manager.py` | 202-244 | `create_session()` | Directory structure |
| `session.md.j2` | 1-114 | Header/context sections | Good LLM context |
| `expert_manager.py` | 72-175 | Expert definitions | Domain knowledge |

---

## 5. Recommended Changes for Phase 02

### 5.1 Simplify `extract_state_from_messages()`

**Before** (80+ lines):
```python
def extract_state_from_messages(self, messages: list[dict]) -> dict[str, Any]:
    # Complex trigger detection, index logic, answer indicators...
```

**After** (~15 lines):
```python
def extract_state_from_messages(self, messages: list[dict]) -> dict[str, Any]:
    """Extract basic conversation metadata.

    NOTE: Step detection is done by the LLM, not by this function.
    """
    state = {
        "original_request": "",
        "message_count": len(messages),
    }
    user_messages = [m for m in messages if m.get('role') == 'user']
    if user_messages:
        state["original_request"] = user_messages[0].get('content', '')
    return state
```

### 5.2 Add `extract_step_from_response()`

**New function** to extract step marker from LLM output:
```python
def extract_step_from_response(self, response_text: str) -> str | None:
    """Extract step marker from LLM response.

    The LLM sets: <!-- STEP: what|why|constraints|generate|finalize|done -->
    """
    import re
    match = re.search(r'<!--\s*STEP:\s*(\w+)\s*-->', response_text)
    return match.group(1) if match else None
```

### 5.3 Template Refactoring (Phase 03)

Replace all step branches with a unified template that explains the entire flow, letting the LLM choose what's relevant.

---

## 6. Conclusion

The current implementation exhibits classic "cargo-cult programming" patterns where complex Python logic attempts to replicate what the LLM naturally understands. The refactoring in ADR-034 will:

1. **Remove** ~100 lines of fragile state-detection code
2. **Simplify** the template to a unified, flexible format
3. **Trust** the LLM to manage conversation flow naturally
4. **Enable** backtracking, multi-topic, and freeform conversations
5. **Improve** observability by extracting step from LLM output instead of guessing

**Risk**: LLM may occasionally set incorrect step markers, but since step is now only for observability (not flow control), this is acceptable.

---

*Analysis completed: 2025-12-30*
*Phase 01 Output: `phases/01/output/ANALYSIS.md`*
