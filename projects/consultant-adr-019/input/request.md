# Problem: Dokumentation veraltet ohne Warnung

Unsere YAML-Dokumentation in docs/sources/*.yaml kann auf Code verweisen der nicht mehr existiert. Wenn jemand eine Klasse oder Methode löscht/umbenennt, merkt es niemand - die Doku bleibt falsch.

**Beispiel:**
```yaml
# docs/sources/debug.yaml
modules:
  - name: StreamParser
    module: "helix.debug.stream_parser"  # Was wenn diese Datei gelöscht wird?
    methods:
      - "parse_line(line: str)"          # Was wenn Methode umbenannt wird?
```

Wir brauchen eine Lösung die verhindert dass Dokumentation veraltet.

**Constraints:**
- Muss mit bestehendem docs_compiler.py funktionieren
- YAML-Format beibehalten
- Keine externen Services
