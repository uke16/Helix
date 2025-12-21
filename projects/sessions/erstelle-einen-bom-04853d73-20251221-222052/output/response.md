## Projektplan erstellt!

**BOM Excel Export** - CLI-Tool zum Export von Multi-Level BOMs

Ich habe die Spezifikation und den Phasen-Plan basierend auf unserer Diskussion erstellt.

### Zusammenfassung

| Aspekt | Details |
|--------|---------|
| **Felder** | Artikelnummer, Beschreibung, Menge, Status |
| **Format** | XLSX (Excel) |
| **Tiefe** | Multi-Level mit allen Unterebenen (max. 5) |
| **Interface** | CLI Tool |
| **Datenquelle** | PostgreSQL via REST API |

### Phasen

1. **API & Datenstruktur Analyse**
   - REST API Endpunkte identifizieren
   - BOM-Datenmodell dokumentieren

2. **Implementation**
   - REST API Client
   - Multi-Level BOM Resolver
   - Excel Export mit openpyxl
   - CLI Interface

3. **Testing & Dokumentation**
   - Unit Tests
   - README mit Nutzungsanleitung

---

Sag **"Starte!"** wenn du bereit bist, das Projekt zu beginnen.
