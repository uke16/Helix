# Check: Migrations-Plan

> Prüft ob ADRs mit `change_scope: major` einen vollständigen Migrations-Plan haben.

---

## Wann ist dieser Check relevant?

Dieser Check ist **kritisch** wenn:

- `change_scope: major` im YAML-Header
- `classification: NEW` mit vielen neuen Dateien (>5)
- Content enthält "breaking change" oder "inkompatibel"

---

## Zu prüfende Kriterien

### 1. Migration-Section vorhanden

- [ ] Section `## Migration` oder `## Migrationsplan` existiert
- [ ] Section hat mindestens 100 Zeichen Inhalt

### 2. Migrations-Phasen definiert

Die Migration sollte in Phasen aufgeteilt sein:

- [ ] Mindestens 2 Phasen/Schritte definiert
- [ ] Jede Phase hat eine Beschreibung
- [ ] Phasen haben eine logische Reihenfolge

Typische Phasen-Bezeichnungen:
- "Phase 1", "Phase 2", ...
- "Tag 1-3", "Tag 4-5", ...
- "Schritt 1", "Schritt 2", ...
- "Step 1", "Step 2", ...

### 3. Rollback-Strategie

- [ ] Rollback wird erwähnt (Suchbegriffe: rollback, zurückrollen, revert, wiederherstellen)
- [ ] Es gibt einen konkreten Rollback-Plan oder Git-Tag-Referenz

### 4. Abhängigkeiten berücksichtigt

- [ ] Wenn `depends_on` nicht leer: Abhängige ADRs werden in Migration erwähnt
- [ ] Reihenfolge der Änderungen ist dokumentiert

### 5. Akzeptanzkriterien für Migration

- [ ] Mindestens ein Akzeptanzkriterium enthält "migration"
- [ ] Optional: Akzeptanzkriterium für "rollback"

---

## Severity-Mapping

| Kriterium | Severity |
|-----------|----------|
| Migration-Section fehlt bei major | **ERROR** |
| Migration-Section zu kurz (<100 Zeichen) | **ERROR** |
| Keine Phasen/Schritte definiert | WARNING |
| Rollback nicht erwähnt | WARNING |
| Kein Migration-Akzeptanzkriterium | WARNING |

---

## Beispiel für guten Migrations-Plan

```markdown
## Migration

### 14-Tage Implementationsplan

#### Phase 1: Foundation (Tag 1-3)
- [ ] Basis-Infrastruktur erstellen
- [ ] Unit Tests schreiben

#### Phase 2: Core Implementation (Tag 4-7)
- [ ] Hauptlogik implementieren
- [ ] Integration Tests

#### Phase 3: Integration (Tag 8-10)
- [ ] In bestehende Systeme integrieren
- [ ] E2E Tests

#### Phase 4: Rollout (Tag 11-14)
- [ ] Staging-Deployment
- [ ] Produktion-Deployment

### Rollback-Strategie

Falls kritische Fehler auftreten:
1. Git tag `pre-feature-x` wiederherstellen
2. Deployment rückgängig machen
3. Datenbank-Migration revertieren (falls vorhanden)
```

---

## Beispiel-Findings

### Error: Migration fehlt

```json
{
  "severity": "error",
  "check": "migration",
  "message": "change_scope=major aber keine Migration-Section vorhanden",
  "location": "YAML header: change_scope"
}
```

### Warning: Rollback fehlt

```json
{
  "severity": "warning",
  "check": "migration",
  "message": "Rollback-Strategie nicht dokumentiert",
  "location": "Migration"
}
```

---

## Prüfanleitung

1. **Prüfe change_scope** im YAML-Header
2. **Wenn major**: Suche nach Migration-Section
3. **Prüfe Inhalt** der Migration-Section
4. **Suche nach Phasen/Schritten**
5. **Suche nach Rollback**
6. **Prüfe Akzeptanzkriterien** auf Migration-Bezug
7. **Dokumentiere Findings**

---

## Kontext: Warum ist das wichtig?

Bei ADR-014 (Documentation Architecture) wurde ein 14-Tage-Migrationsplan
im Konzept definiert, aber beim ADR vergessen. Das führte zu:

- Unklarheit über Implementierungsreihenfolge
- Fehlende Rollback-Strategie
- Keine messbaren Migrations-Meilensteine

Dieser Check verhindert solche Informationsverluste.
