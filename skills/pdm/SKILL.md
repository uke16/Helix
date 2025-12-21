# PDM - Product Data Management

## Overview

PDM at FRABA manages product lifecycle data including:
- Article master data
- Bill of Materials (BOM/Stücklisten)
- Revisions and versions
- Document management
- Engineering changes

## Key Concepts

### Articles (Artikel)
Products with unique identifiers, descriptions, and attributes.

### Bill of Materials (BOM)
Hierarchical structure showing:
- Parent article
- Child components
- Quantities
- Positions

### Revisions
Version control for articles:
- Revision number (A, B, C...)
- Status (Draft, Released, Obsolete)
- Effective dates

## Integration Points

- **ERP/SAP**: Material master sync
- **Webshop**: Product catalog
- **Engineering**: CAD drawings
- **Production**: Manufacturing orders

## Common Operations

1. Create/modify articles
2. Build/explode BOMs
3. Release revisions
4. Export to SAP
5. Generate reports

## Data Structures

```
Article
├── ID
├── Description
├── Category
├── Status
└── BOM[]
    ├── Position
    ├── Child Article
    ├── Quantity
    └── Unit
```

*Note: FRABA-specific field names and structures to be added.*
