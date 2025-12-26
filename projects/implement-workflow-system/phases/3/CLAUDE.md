# Phase 3: Consultant Workflow-Wissen (ADR-024)

Du bist ein Claude Code Entwickler der dem Consultant beibringt, Workflows zu starten.

---

## 🎯 Ziel

Erweitere das Consultant Template damit er:
1. Weiß welche Workflows existieren
2. Den richtigen Workflow wählen kann (intern/extern, leicht/komplex)
3. Workflows via HELIX API starten kann

---

## 📚 Zuerst lesen

1. `templates/consultant/session.md.j2` - Aktuelles Template
2. `output/` von Phase 2 - Die neuen Workflow-Templates
3. `src/helix/api/routes/helix.py` - API Endpoints
4. `docs/ROADMAP-CONSULTANT-WORKFLOWS.md` - Entscheidungen

---

## 📋 Aufgaben

### 1. ADR-024 erstellen

Erstelle `output/adr/024-consultant-workflow-knowledge.md`

### 2. Consultant Template erweitern

Ergänze `templates/consultant/session.md.j2` mit neuem Abschnitt:

```markdown
## 🚀 Workflows starten

### Verfügbare Workflows

| Projekt-Typ | Workflow | Wann nutzen |
|-------------|----------|-------------|
| Intern + Leicht | `intern-simple` | HELIX Feature, klar definiert |
| Intern + Komplex | `intern-complex` | HELIX Feature, unklar/groß |
| Extern + Leicht | `extern-simple` | Externes Tool, klar definiert |
| Extern + Komplex | `extern-complex` | Externes Tool, unklar/groß |

### Workflow wählen

1. **Intern vs Extern?**
   - Intern: Ändert HELIX selbst (src/helix/, adr/, skills/)
   - Extern: Separates Projekt (projects/external/)
   - *Wenn unklar: Frage den User*

2. **Leicht vs Komplex?**
   - Leicht: Scope ist klar, <5 Files, 1-2 Sessions
   - Komplex: Scope unklar, braucht Feasibility/Planning
   - *User kann es sagen, oder du schätzt*

### Workflow starten

```bash
# Projekt erstellen
mkdir -p projects/{internal|external}/{name}/phases

# phases.yaml aus Template kopieren
cp templates/workflows/{workflow}.yaml projects/.../phases.yaml

# Via API starten
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/.../", "phase": 1}'

# Status prüfen
curl http://localhost:8001/helix/jobs
```

### Phase Reset

Falls eine Phase fehlschlägt und du sie neu starten willst:

```bash
# Phase zurücksetzen
curl -X POST http://localhost:8001/helix/execute \
  -d '{"project_path": "...", "phase": N, "reset": true}'
```
```

### 3. Workflow-Guide erstellen

Erstelle `output/templates/consultant/workflow-guide.md`:
- Detaillierte Anleitung
- Beispiel-Dialoge
- Troubleshooting

---

## 📁 Output

| Datei | Beschreibung |
|-------|--------------|
| `output/adr/024-consultant-workflow-knowledge.md` | ADR |
| `output/templates/consultant/session.md.j2` | Erweitertes Template |
| `output/templates/consultant/workflow-guide.md` | Detaillierter Guide |

---

## ✅ Quality Gate

- [ ] ADR-024 valide
- [ ] Jinja2 Syntax valide in session.md.j2
- [ ] Workflow-Referenzen korrekt (alle 4 Typen)
- [ ] API Endpoints dokumentiert
- [ ] Phase Reset dokumentiert

---

## 🔗 Entscheidungen (Q4, Q5)

- **Intern vs Extern**: Wenn User nicht sagt → Consultant fragt
- **Leicht vs Komplex**: User sagt es ODER Consultant schätzt
