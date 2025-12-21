# BOM Structure (Stücklisten)

## Types

### Single-Level BOM
Direct children only:
```
Product A
├── Component B (qty: 2)
├── Component C (qty: 1)
└── Component D (qty: 4)
```

### Multi-Level BOM
Full hierarchy:
```
Product A
├── Assembly B
│   ├── Part B1
│   └── Part B2
├── Component C
└── Assembly D
    ├── Part D1
    └── Part D2
```

## BOM Operations

### Explosion
Top-down: Show all components of a product

### Implosion (Where-Used)
Bottom-up: Show all products using a component

### Comparison
Show differences between BOM revisions

## Export Formats

- CSV (flat)
- XML (hierarchical)
- SAP IDoc (integration)
- JSON (API)
