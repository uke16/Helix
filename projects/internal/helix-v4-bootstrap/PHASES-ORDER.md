# HELIX v4 Bootstrap - Phase Execution Order

## Corrected Order

| Order | Phase | Description | Depends On |
|-------|-------|-------------|------------|
| 1 | 01-foundation | Core Python modules | - |
| 2 | 02-consultant | Meeting system | 01 |
| 3 | 03-observability | Logging & metrics | 01 |
| 4 | 04-cli | Command line interface | 01, 02, 03 |
| 5 | 05-templates | Jinja2 templates | 01 |
| 6 | 06-config | YAML configurations | 01 |
| 7 | 07-unit-tests | pytest for modules | 01-06 |
| 8 | 08-integration-tests | System tests | 07 |
| 9 | 09-review | Architecture review | 08 |
| 10 | **11-documentation** | Skills & docs | 09 |
| 11 | **10-e2e-test** | Full system test | 11 (docs!) |
| 12 | 12-api | REST API + Docker | 10 |

## Rationale

Documentation (Phase 11) must come BEFORE E2E Test (Phase 10) because:
- E2E test starts a real HELIX project
- Consultant needs skills/knowledge to discuss features
- Without documentation, consultant cannot answer questions
- Skills folder must be populated before testing
