# Draft: Prompt Upscaling - Intelligente Prompt-Verbesserung

**Status:** Draft / Research
**Erstellt:** 2024-12-24

---

## Kontext

### Das Problem

User/Orchestrator gibt schlechten Prompt:
```
"Mach ein Tool"
```

Agent produziert schlechtes Ergebnis weil:
- Unklar WAS für ein Tool
- Unklar WARUM
- Keine Akzeptanzkriterien
- Kein Context

### Die Idee

Der Orchestrator verbessert Prompts BEVOR sie an den Agent gehen:

```
User-Prompt (schlecht)
    ↓
┌─────────────────────┐
│  PROMPT UPSCALER    │
│  ─────────────────  │
│  • Analysiert       │
│  • Ergänzt Context  │
│  • Fügt Struktur    │
│  • Startet Denken   │
└─────────────────────┘
    ↓
Enhanced-Prompt (gut)
    ↓
Agent
```

---

## Ansätze

### 1. Template-basiertes Upscaling

**Einfachster Ansatz:**
```python
def upscale_prompt(raw_prompt: str, context: dict) -> str:
    return f"""
# Aufgabe
{raw_prompt}

# Context
- Projekt: {context['project']}
- Domain: {context['domain']}
- Relevante Skills: {context['skills']}

# Erwarteter Output
- Datei in output/ Verzeichnis
- Valide Syntax
- Dokumentiert

# Bevor du fertig bist
1. Prüfe ob alle Anforderungen erfüllt sind
2. Rufe verify_phase_output auf
3. Korrigiere bei Fehlern
"""
```

**Pro:** Einfach, deterministisch
**Contra:** Nicht intelligent, keine echte Verbesserung

### 2. LLM-basiertes Upscaling (Meta-Prompt)

**Idee:** Ein kleines LLM verbessert den Prompt bevor das große LLM arbeitet.

```python
async def upscale_with_llm(raw_prompt: str) -> str:
    meta_prompt = f"""
Du bist ein Prompt-Verbesserer.

Analysiere diesen Prompt und verbessere ihn:
"{raw_prompt}"

Füge hinzu:
1. Klarstellung WAS genau gemeint ist
2. WARUM das wichtig ist (wenn ableitbar)
3. Konkrete Akzeptanzkriterien
4. Edge Cases die beachtet werden sollten

Gib NUR den verbesserten Prompt zurück.
"""
    
    # Günstiges Model für Meta-Task
    response = await call_llm(meta_prompt, model="claude-haiku")
    return response
```

**Pro:** Intelligent, kann Context verstehen
**Contra:** Extra API Call, Kosten, Latenz

### 3. Chain-of-Thought Injection

**Idee:** Denk-Prozesse in den Prompt einbauen.

```python
def inject_thinking(prompt: str) -> str:
    return f"""
{prompt}

Bevor du antwortest:

<thinking>
1. Was genau wird hier verlangt?
2. Welche Teile sind unklar?
3. Was sind sinnvolle Annahmen?
4. Welche Edge Cases gibt es?
5. Was ist der beste Ansatz?
</thinking>

Dann: Implementiere basierend auf deiner Analyse.
"""
```

**Pro:** Verbessert Reasoning, keine extra API Calls
**Contra:** Funktioniert nur bei Modellen die <thinking> unterstützen

### 4. Iterative Clarification

**Idee:** Bei unklaren Prompts erst Rückfragen stellen.

```
User: "Mach ein Tool"
    ↓
Orchestrator erkennt: "Zu vage"
    ↓
Orchestrator fragt: "Was für ein Tool? Für welchen Zweck?"
    ↓
User: "Ein CLI Tool das ADRs validiert"
    ↓
Orchestrator: "Jetzt klar genug" → Agent
```

**Pro:** Beste Qualität, User bleibt eingebunden
**Contra:** Nicht autonom, blockiert Workflow

### 5. Context-Aware Enrichment

**Idee:** Automatisch relevanten Context laden basierend auf Keywords.

```python
async def enrich_prompt(prompt: str) -> str:
    # Keywords extrahieren
    keywords = extract_keywords(prompt)  # ["tool", "adr", "validiert"]
    
    # Relevante Dateien finden
    relevant_files = find_relevant_files(keywords)
    # → ["src/helix/tools/adr_tool.py", "adr/012-adr-single-source.md"]
    
    # Code-Snippets extrahieren
    snippets = extract_snippets(relevant_files, keywords)
    
    return f"""
{prompt}

# Relevanter bestehender Code
{snippets}

# Verwandte ADRs
{list_related_adrs(keywords)}
"""
```

**Pro:** Automatisch, kontextreich
**Contra:** Kann irrelevantes laden, Token-intensiv

---

## Kombinierter Ansatz

Optimal wäre eine Kombination:

```
Raw Prompt
    ↓
[1] Template-Struktur hinzufügen
    ↓
[2] Keywords extrahieren → Context laden
    ↓
[3] Chain-of-Thought injizieren
    ↓
[4] Optional: LLM-Verbesserung (nur bei sehr vagen Prompts)
    ↓
Enhanced Prompt
    ↓
Agent
```

### Entscheidungslogik

```python
def should_llm_upscale(prompt: str) -> bool:
    """Entscheide ob LLM-Upscaling nötig ist."""
    # Zu kurz?
    if len(prompt.split()) < 10:
        return True
    
    # Keine konkreten Substantive?
    if not has_concrete_nouns(prompt):
        return True
    
    # Fragezeichen aber keine klare Frage?
    if "?" in prompt and not is_clear_question(prompt):
        return True
    
    return False
```

---

## Implementation Skizze

```python
# src/helix/orchestrator/prompt_upscaler.py

class PromptUpscaler:
    """Verbessert Prompts bevor sie an Agents gehen."""
    
    def __init__(self, context_loader: ContextLoader):
        self.context_loader = context_loader
    
    async def upscale(self, raw_prompt: str, phase_context: dict) -> str:
        """Hauptmethode für Prompt-Verbesserung."""
        
        # 1. Basis-Template
        prompt = self._apply_template(raw_prompt, phase_context)
        
        # 2. Context laden
        keywords = self._extract_keywords(raw_prompt)
        context = await self.context_loader.load_relevant(keywords)
        prompt = self._inject_context(prompt, context)
        
        # 3. Thinking injizieren
        prompt = self._inject_thinking(prompt)
        
        # 4. Optional: LLM-Verbesserung
        if self._needs_llm_upscale(raw_prompt):
            prompt = await self._llm_upscale(prompt)
        
        return prompt
    
    def _needs_llm_upscale(self, prompt: str) -> bool:
        """Heuristik ob LLM-Upscaling nötig."""
        word_count = len(prompt.split())
        has_structure = any(x in prompt for x in ["##", "1.", "-", "*"])
        
        return word_count < 15 and not has_structure
```

---

## Metriken

Wie messen wir Erfolg?

1. **Gate Pass Rate**
   - Vorher: X% der Outputs bestehen Gate beim ersten Mal
   - Nachher: Y% bestehen beim ersten Mal
   
2. **Retry Count**
   - Vorher: Durchschnittlich N Retries
   - Nachher: Durchschnittlich M Retries

3. **User Satisfaction**
   - Qualitative Bewertung der Outputs
   - "War das was du wolltest?" Score

4. **Token Efficiency**
   - Upscaling-Kosten vs. eingesparte Retry-Kosten

---

## Offene Fragen

1. **Wann ist Upscaling Counter-Produktiv?**
   - Experten-User mit präzisen Prompts brauchen kein Upscaling
   - Over-Engineering kann den Intent verfälschen

2. **Wie viel Context ist optimal?**
   - Zu wenig: Agent fehlt Information
   - Zu viel: Agent wird verwirrt / Kosten steigen

3. **Wer kontrolliert das Upscaling?**
   - Automatisch? User-konfigurierbar?
   - Phase-spezifisch?

---

## Verwandte Konzepte

- **Anthropic's "Constitutional AI"** - Selbst-Korrektur durch Prinzipien
- **Chain-of-Thought Prompting** - Denken vor Antworten
- **Retrieval-Augmented Generation (RAG)** - Context aus Datenbank
- **Meta-Prompting** - Prompts die Prompts verbessern

---

## Nächste Schritte

- [ ] POC: Template-basiertes Upscaling implementieren
- [ ] Messen: Gate Pass Rate vorher/nachher
- [ ] POC: Keyword-basiertes Context Loading
- [ ] Entscheiden: LLM-Upscaling ja/nein und wann
- [ ] User-Feedback: Ist Upscaling hilfreich oder störend?

---

## Verwandte ADRs

- ADR-004: Escalation System (Retry-Logik)
- ADR-005: Consultant Topology
- ADR-011: Post-Phase Verification
- Draft: Sub-Agent Enhancement
