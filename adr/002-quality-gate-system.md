# ADR-002: Quality Gate System

**Status:** Proposed  
**Datum:** 2025-12-21  
**Bezug:** ADR-000, ADR-001  
**Migriert von:** HELIX v3 ADR-094, ADR-095

---

## Kontext

Quality Gates sind deterministische Prüfungen zwischen Workflow-Phasen.
Sie ersetzen LLM-basierte Validierung durch einfache Python-Checks.

---

## Entscheidung

### Quality Gate Architektur

```
Phase 1          QG1          Phase 2          QG2          Phase 3
┌──────────┐   ┌─────┐      ┌──────────┐   ┌─────┐      ┌──────────┐
│Consultant│──▶│PASS?│─YES─▶│Developer │──▶│PASS?│─YES─▶│ Reviewer │
│ Meeting  │   └──┬──┘      │          │   └──┬──┘      │          │
└──────────┘      │         └──────────┘      │         └──────────┘
                  │NO                         │NO
                  ▼                           ▼
            ┌──────────┐                ┌──────────┐
            │  Retry   │                │Escalation│
            │  oder    │                │ Meeting  │
            │  Abort   │                └──────────┘
            └──────────┘
```

### Gate Definitionen

```python
# src/helix/quality_gates/gates.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import subprocess

@dataclass
class GateResult:
    gate: str
    passed: bool
    message: str
    details: dict = None
    
    def __bool__(self):
        return self.passed


class QualityGate:
    """Base class für Quality Gates."""
    
    name: str = "base"
    
    def check(self, context: dict) -> GateResult:
        raise NotImplementedError


class SpecCompletenessGate(QualityGate):
    """QG1: Ist die Implementation Spec vollständig?"""
    
    name = "QG1_SPEC_COMPLETE"
    
    REQUIRED_FIELDS = [
        "meta.domain",
        "request.original",
        "implementation.files_to_create",
        "implementation.acceptance_criteria"
    ]
    
    def check(self, context: dict) -> GateResult:
        spec = context.get("spec", {})
        missing = []
        
        for field in self.REQUIRED_FIELDS:
            parts = field.split(".")
            value = spec
            for part in parts:
                value = value.get(part, {}) if isinstance(value, dict) else None
                if value is None:
                    missing.append(field)
                    break
        
        if missing:
            return GateResult(
                gate=self.name,
                passed=False,
                message=f"Spec unvollständig: {len(missing)} Felder fehlen",
                details={"missing_fields": missing}
            )
        
        # Check: Mindestens eine Datei definiert?
        files = spec.get("implementation", {}).get("files_to_create", [])
        if not files:
            return GateResult(
                gate=self.name,
                passed=False,
                message="Keine Dateien in Spec definiert"
            )
        
        return GateResult(
            gate=self.name,
            passed=True,
            message=f"Spec vollständig mit {len(files)} Dateien"
        )


class FilesCreatedGate(QualityGate):
    """QG2: Wurden alle erwarteten Dateien erstellt?"""
    
    name = "QG2_FILES_CREATED"
    
    def check(self, context: dict) -> GateResult:
        spec = context.get("spec", {})
        project_path = Path(context.get("project_path", "."))
        
        expected = spec.get("implementation", {}).get("files_to_create", [])
        
        missing = []
        created = []
        
        for file_def in expected:
            # file_def kann string oder dict sein
            path = file_def if isinstance(file_def, str) else file_def.get("path")
            full_path = project_path / path
            
            if full_path.exists():
                created.append(path)
            else:
                missing.append(path)
        
        if missing:
            return GateResult(
                gate=self.name,
                passed=False,
                message=f"{len(missing)} von {len(expected)} Dateien fehlen",
                details={"missing": missing, "created": created}
            )
        
        return GateResult(
            gate=self.name,
            passed=True,
            message=f"Alle {len(expected)} Dateien erstellt"
        )


class SyntaxCheckGate(QualityGate):
    """QG2b: Haben Python-Dateien valide Syntax?"""
    
    name = "QG2B_SYNTAX_CHECK"
    
    def check(self, context: dict) -> GateResult:
        project_path = Path(context.get("project_path", "."))
        
        python_files = list(project_path.rglob("*.py"))
        errors = []
        
        for py_file in python_files:
            result = subprocess.run(
                ["python3", "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                errors.append({
                    "file": str(py_file),
                    "error": result.stderr
                })
        
        if errors:
            return GateResult(
                gate=self.name,
                passed=False,
                message=f"{len(errors)} Dateien mit Syntax-Fehlern",
                details={"errors": errors}
            )
        
        return GateResult(
            gate=self.name,
            passed=True,
            message=f"{len(python_files)} Python-Dateien OK"
        )


class ReviewApprovedGate(QualityGate):
    """QG3: Hat der Reviewer approved?"""
    
    name = "QG3_REVIEW_APPROVED"
    
    def check(self, context: dict) -> GateResult:
        review = context.get("review_result", {})
        
        status = review.get("status", "pending")
        
        if status == "approved":
            return GateResult(
                gate=self.name,
                passed=True,
                message="Review approved"
            )
        elif status == "changes_requested":
            return GateResult(
                gate=self.name,
                passed=False,
                message="Changes requested",
                details={"feedback": review.get("feedback", [])}
            )
        else:
            return GateResult(
                gate=self.name,
                passed=False,
                message=f"Review status: {status}"
            )


class DocumentationCompleteGate(QualityGate):
    """QG4: Ist die Dokumentation geschrieben?"""
    
    name = "QG4_DOCS_COMPLETE"
    
    def check(self, context: dict) -> GateResult:
        spec = context.get("spec", {})
        project_path = Path(context.get("project_path", "."))
        
        # Erwartete Doku-Dateien aus Spec
        expected_docs = []
        for file_def in spec.get("implementation", {}).get("files_to_create", []):
            path = file_def if isinstance(file_def, str) else file_def.get("path")
            if path and path.endswith(".md"):
                expected_docs.append(path)
        
        # Auch docs/ Verzeichnis prüfen
        docs_dir = project_path / "docs"
        if docs_dir.exists():
            # Mindestens eine .md Datei?
            md_files = list(docs_dir.rglob("*.md"))
            if not md_files and not expected_docs:
                return GateResult(
                    gate=self.name,
                    passed=False,
                    message="Keine Dokumentation gefunden"
                )
        
        missing_docs = []
        for doc in expected_docs:
            if not (project_path / doc).exists():
                missing_docs.append(doc)
        
        if missing_docs:
            return GateResult(
                gate=self.name,
                passed=False,
                message=f"{len(missing_docs)} Doku-Dateien fehlen",
                details={"missing": missing_docs}
            )
        
        return GateResult(
            gate=self.name,
            passed=True,
            message="Dokumentation vollständig"
        )
```

### Gate Runner

```python
# src/helix/quality_gates/runner.py

class GateRunner:
    """Führt Quality Gates aus."""
    
    PHASE_GATES = {
        "after_consultant": [SpecCompletenessGate()],
        "after_developer": [FilesCreatedGate(), SyntaxCheckGate()],
        "after_reviewer": [ReviewApprovedGate()],
        "after_documentation": [DocumentationCompleteGate()]
    }
    
    def run_gates(self, phase: str, context: dict) -> list[GateResult]:
        """Führt alle Gates für eine Phase aus."""
        gates = self.PHASE_GATES.get(phase, [])
        results = []
        
        for gate in gates:
            result = gate.check(context)
            results.append(result)
            
            # Bei Failure abbrechen
            if not result.passed:
                break
        
        return results
    
    def all_passed(self, results: list[GateResult]) -> bool:
        return all(r.passed for r in results)
```

---

## Verwendung im Orchestrator

```python
async def run_workflow(self, request: str, domain: str):
    gate_runner = GateRunner()
    
    # Phase 1: Consultant Meeting
    spec = await self.consultant_meeting(domain, request)
    
    results = gate_runner.run_gates("after_consultant", {"spec": spec})
    if not gate_runner.all_passed(results):
        return {"error": "QG1 failed", "details": results}
    
    # Phase 2: Developer
    dev_result = await self.developer_phase(spec)
    
    results = gate_runner.run_gates("after_developer", {
        "spec": spec,
        "project_path": dev_result["project_path"]
    })
    if not gate_runner.all_passed(results):
        # Escalation Meeting statt hartem Abort
        return await self.escalation_meeting(spec, dev_result, results)
    
    # ... weitere Phasen
```

---

## Konsequenzen

### Positiv
- Deterministische Prüfungen (kein LLM-Zufall)
- Schnell (keine API-Calls)
- Einfach zu testen
- Klare Pass/Fail Semantik

### Negativ
- Weniger "intelligent" als LLM-Review
- Muss manuell erweitert werden

---

## Referenzen

- HELIX v3 ADR-094: Plan Validator
- HELIX v3 ADR-095: Completion Validators

