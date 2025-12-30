---
adr_id: "034"
title: "Consultant Flow Refactoring - LLM-Native statt State-Machine"
status: Proposed

project_type: helix_internal
component_type: PROCESS
classification: REFACTOR
change_scope: major

files:
  create: []
  modify:
    - src/helix/api/session_manager.py
    - src/helix/api/routes/openai.py
    - templates/consultant/session.md.j2
    - src/helix/consultant/expert_manager.py
  docs:
    - docs/ARCHITECTURE-MODULES.md

depends_on:
  - ADR-029  # Session Persistence
---

# ADR-034: Consultant Flow Refactoring - LLM-Native statt State-Machine

## Status

Proposed

---

## Kontext

### Das Problem

Bei der Nutzung des HELIX Consultants wurde eine **fundamental kaputte State-Machine** entdeckt. Der aktuelle Code versucht, den Konversationsfluss mit einer starren, index-basierten Logik zu steuern - anstatt dem LLM zu vertrauen, die Konversation natuerlich zu fuehren.

### Analyse der Problemstellen

#### 1. `extract_state_from_messages()` in `session_manager.py:331-412`

Diese Funktion ist das Herzproblem. Sie versucht, den "step" (what/why/constraints/generate/finalize/execute) aus Messages zu extrahieren:

```python
# Problematische index-basierte Logik
if len(user_messages) >= 2:
    all_followup_content = " ".join(
        m.get('content', '') for m in user_messages[1:]
    )
    state["answers"]["what"] = all_followup_content

# ... spaeter ...
if len(user_messages) >= 4:
    state["step"] = "generate"
elif len(user_messages) >= 3:
    state["step"] = "constraints"
else:
    state["step"] = "why"
```

**Probleme:**
- **Index-Logik ist fragil:** "Nach 4 Messages = generate" ist Cargo-Cult
- **Substring-Matching fuer Trigger:** `'adr' in last_msg and any(word in last_msg for word in ['erstelle', 'create', ...])`
- **Keine semantische Analyse:** Der Code zaehlt Messages statt Inhalt zu verstehen
- **Ueberschreibt LLM-Intelligenz:** Das Template sagt dem LLM was zu tun ist, dann ueberschreibt Python die Entscheidung

#### 2. Trigger-Listen in `session_manager.py:374-399`

```python
# ADR/Finalize triggers - use word-based detection
has_adr_request = (
    'adr' in last_msg and
    any(word in last_msg for word in ['erstelle', 'create', 'mach', 'schreib', 'generier'])
)

finalize_exact = [
    'finalisiere', 'finalize', 'leg das ab', 'adr schreiben',
]

# Execute triggers - user confirms to start execution
elif any(word in last_msg for word in ['start', 'starte', 'los', 'go']):
    state["step"] = "execute"

# Answer indicators
answer_indicators = [
    '1.', '2.', '3.', 'option', 'antwort', 'answer',
    'mount', 'auth', 'oauth', 'intern', 'extern',
    'ja', 'nein', 'yes', 'no', 'richtig', 'korrekt',
]
```

**Probleme:**
- **Hardcodierte Woerter:** Deutsche + englische Mischung, unvollstaendig
- **False Positives:** "Ich starte gerade VS Code" -> step = "execute"
- **False Negatives:** "Bitte das ADR jetzt generieren" matcht nicht (kein exakter Trigger)
- **Wartungshoelle:** Jedes neue Szenario braucht neue Trigger-Woerter

#### 3. Template-Branches in `session.md.j2:115-351`

Das Template hat massive `{% if step == "X" %}` Bloecke:

```jinja2
{% if step == "what" %}
### Phase: Anforderungsklaerung (WAS)
...
{% elif step == "why" %}
### Phase: Bedarfsanalyse (WARUM)
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

**Probleme:**
- **Template-driven Flow:** Python entscheidet Step -> Template zeigt nur diesen Step -> LLM kann nur das tun
- **Kein Backtracking:** Wenn User zurueck will ("warte, doch nicht so"), geht nicht
- **Keine Flexibilitaet:** User muss den vordefinierten Pfad gehen

#### 4. Expert-Selection in `expert_manager.py:227-273`

```python
def select_experts(self, request: str) -> list[str]:
    """Select experts based on keywords in the request."""
    request_lower = request.lower()
    request_normalized = re.sub(r'[^\w\s]', ' ', request_lower)
    words = set(request_normalized.split())

    for expert_id, expert in experts.items():
        for trigger in expert.triggers:
            # Check for exact word match
            if trigger_lower in words:
                score += 2
            # Check for partial match (substring)
            elif trigger_lower in request_lower:
                score += 1
```

**Probleme:**
- **Keyword-basiert statt semantisch:** "Docker Container" aktiviert infrastructure-Expert, aber "wie deploye ich das?" nicht
- **Keine Context-Awareness:** Betrachtet nur Request, nicht Konversationsverlauf
- **Primitive Scoring:** Woerter zaehlen statt Relevanz verstehen

### Was ist Cargo-Cult, was ist notwendig?

| Element | Status | Begruendung |
|---------|--------|-------------|
| Index-basierte Step-Detection | CARGO-CULT | LLM kann selbst erkennen wo Konversation steht |
| Substring-Trigger-Matching | CARGO-CULT | LLM versteht Intent semantisch |
| Template-Branches per Step | CARGO-CULT | Ein einheitliches Template mit allen Infos reicht |
| SessionState.step Field | NOTWENDIG | Fuer Logging/Debugging/Status-API nuetzlich |
| Session-Verzeichnis-Struktur | NOTWENDIG | Persistenz, Output-Organisation |
| Message-History-Speicherung | NOTWENDIG | Kontext fuer LLM |
| Expert-Triggers | TEILWEISE | Kann bleiben als Hint, sollte nicht mandatory sein |

---

## Entscheidung

### Wir entscheiden uns fuer:

**Die State-Machine komplett entfernen und dem LLM vertrauen.**

### Diese Entscheidung beinhaltet:

1. **`extract_state_from_messages()` entfernen/vereinfachen**
   - Step-Detection komplett raus
   - LLM entscheidet selbst wo die Konversation steht

2. **Template vereinfachen**
   - Alle Step-Branches entfernen
   - Ein einheitliches Template das ALLE Phasen erklaert
   - LLM waehlt selbst was relevant ist

3. **Step-Field behalten fuer Observability**
   - LLM schreibt Step in Output
   - Python extrahiert Step aus LLM-Output (nicht aus User-Messages!)

4. **Expert-Selection optional machen**
   - Bleiben als Hints im Template
   - LLM entscheidet welche Skills relevant sind

### Warum diese Loesung?

- **LLM > Regex:** Claude versteht "Bitte erstell mir jetzt das ADR" ohne Trigger-Liste
- **Flexibler Flow:** User kann jederzeit zurueck, vorwaerts, abbrechen
- **Weniger Code:** State-Machine-Logik faellt komplett weg
- **Wartungsfrei:** Keine Trigger-Listen mehr pflegen
- **Robust:** Kein False-Positive/Negative bei Keyword-Detection

---

## Implementation

### Phase 1: `extract_state_from_messages()` entfernen

**Vorher (session_manager.py:331-412):**
```python
def extract_state_from_messages(self, messages: list[dict]) -> dict[str, Any]:
    # 80+ Zeilen komplexe Logik mit Substring-Matching
    ...
```

**Nachher:**
```python
def extract_state_from_messages(self, messages: list[dict]) -> dict[str, Any]:
    """Extract basic conversation metadata.

    NOTE: Step detection is done by the LLM, not by this function.
    This function only extracts the original request and message count.
    """
    state = {
        "original_request": "",
        "message_count": len(messages),
        # Step wird vom LLM in output/response.md gesetzt, nicht hier!
    }

    user_messages = [m for m in messages if m.get('role') == 'user']
    if user_messages:
        state["original_request"] = user_messages[0].get('content', '')

    return state
```

### Phase 2: Template vereinfachen

**Vorher (session.md.j2):** 450+ Zeilen mit {% if step == "X" %} Branches

**Nachher:** Ein einheitliches Template:

```jinja2
# HELIX v4 Consultant Session

Du bist der **HELIX Meta-Consultant**.

## Session
- **ID**: `{{ session_id }}`
- **Erstellt**: {{ created_at }}

## Urspruengliche Anfrage
{{ original_request }}

{% if context %}
## Bisherige Konversation
{% for key, value in context.items() %}
### {{ key }}
{{ value }}
{% endfor %}
{% endif %}

---

## Deine Aufgabe

Fuehre ein natuerliches Gespraech mit dem User, um seine Anfrage zu verstehen und umzusetzen.

### Typischer Flow (aber flexibel!):
1. **Verstehen**: Was genau soll gebaut werden?
2. **Klaeren**: Warum? Welche Constraints?
3. **Planen**: ADR erstellen wenn genug Information
4. **Bestaetigen**: User bestaetigt ADR
5. **Finalisieren**: ADR in adr/ verschieben

Du entscheidest selbst, wann du genug Information hast.
Der User kann jederzeit zurueck, Fragen stellen, oder abbrechen.

### Output
Schreibe deine Antwort nach `output/response.md`.

Am Ende jeder Antwort, setze einen Step-Marker:
<!-- STEP: what|why|constraints|generate|finalize|done -->

Dieser Marker wird fuer Status-Tracking verwendet, nicht fuer Flow-Control.
```

### Phase 3: Step aus LLM-Output extrahieren

**Neue Funktion in session_manager.py:**

```python
def extract_step_from_response(self, response_text: str) -> str | None:
    """Extract step marker from LLM response.

    The LLM sets the step marker at the end of its response:
    <!-- STEP: what -->

    This is used for observability, NOT for flow control.
    """
    import re
    match = re.search(r'<!--\s*STEP:\s*(\w+)\s*-->', response_text)
    if match:
        return match.group(1)
    return None
```

**Integration in openai.py:**

```python
# Nach LLM-Response lesen
if response_file.exists():
    response_text = response_file.read_text()

    # Extract step for observability (not for control!)
    step = session_manager.extract_step_from_response(response_text)
    if step:
        session_manager.update_state(session_id, step=step)
```

### Phase 4: Expert-Selection vereinfachen

**Vorher:** Komplexes Keyword-Scoring in expert_manager.py

**Nachher:** Experts als Hints im Template, LLM entscheidet

```jinja2
## Verfuegbare Domain-Experten (optional)

Falls relevant, kannst du diese Skills einbeziehen:
- **helix**: HELIX Architektur, ADRs
- **pdm**: Produktdaten, Stuecklisten
- **encoder**: POSITAL Encoder
- **infrastructure**: Docker, CI/CD
- **database**: PostgreSQL, Neo4j

Du entscheidest selbst, welche relevant sind.
```

---

## Migration

### Schritt 1: Parallel-Betrieb
- Neues Template als `session-v2.md.j2`
- Feature-Flag `HELIX_USE_LLM_FLOW=true` zum Aktivieren
- Alte Logik bleibt vorerst als Fallback

### Schritt 2: Validation
- A/B-Test mit echten Consultant-Sessions
- Vergleich: Erfolgsrate, User-Zufriedenheit, Fehlerrate

### Schritt 3: Vollstaendige Migration
- Alte extract_state_from_messages() Logik entfernen
- session-v2.md.j2 wird session.md.j2
- Feature-Flag entfernen

---

## Akzeptanzkriterien

### Flow ohne State-Machine
- [ ] extract_state_from_messages() enthaelt keine Trigger-Detection mehr
- [ ] Template hat keine {% if step == "X" %} Branches mehr
- [ ] LLM-Antworten enthalten Step-Marker <!-- STEP: X -->
- [ ] Step wird aus LLM-Output extrahiert (nicht aus User-Messages)

### Natuerlicher Konversationsfluss
- [ ] User kann jederzeit "zurueck" gehen (LLM versteht das)
- [ ] User kann ADR anfordern ohne exakte Trigger-Woerter
- [ ] User kann Fragen stellen ohne Flow zu unterbrechen
- [ ] Mehrere Themen in einer Session funktionieren

### Backward Compatibility
- [ ] Alte Sessions bleiben lesbar
- [ ] status.json Format unveraendert
- [ ] API-Responses unveraendert

### Observability
- [ ] Step wird weiterhin in status.json geloggt
- [ ] Step kommt jetzt vom LLM, nicht von Python
- [ ] Debugging zeigt welchen Step LLM gewaehlt hat

---

## Konsequenzen

### Positiv

1. **Natuerlicherer Flow:** User kann frei mit dem Consultant sprechen
2. **Weniger False Positives:** "Starte VS Code" != step=execute
3. **Keine Trigger-Wartung:** Neue Features brauchen keine neuen Keywords
4. **Robuster:** LLM versteht Kontext, Regex nicht
5. **Einfacherer Code:** 80+ Zeilen State-Detection fallen weg

### Negativ

1. **LLM-Abhaengigkeit:** Wenn LLM falsche Step-Marker setzt, ist Status falsch
2. **Weniger deterministisch:** Flow ist nicht mehr vorhersagbar
3. **Debugging:** Schwieriger nachzuvollziehen warum LLM X gewaehlt hat

### Risiken & Mitigation

| Risiko | Mitigation |
|--------|------------|
| LLM vergisst Step-Marker | Template erinnert am Ende daran, Fallback auf "unknown" |
| LLM waehlt falschen Step | Step ist nur fuer Logging, nicht fuer Control |
| User vermisst strikte Fuehrung | Template erklaert typischen Flow, User kann fragen |
| A/B-Test zeigt schlechtere Ergebnisse | Rollback auf alte Logik moeglich via Feature-Flag |

---

## Referenzen

- [ADR-029: Session Persistence](029-open-webui-session-persistence---x-conversation-id.md)
- [ADR-005: Consultant Topology](005-consultant-topology-agentic-meetings.md)
- session_manager.py:331-412 (aktuelle problematische Implementierung)
- session.md.j2 (aktuelles Template mit Step-Branches)
