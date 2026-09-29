# siege_utilities

All-purpose data engineering and data science library by Siege Analytics
(focus on geospatial analysis).

## branch_integrity

Consumed by the develop-first promotion parity guard (branch-topology-check).
Model classification from the repo census (2026-09-29): develop is the
integration branch, main is production; promotion flows develop -> main.

```yaml
branch_integrity:
  model: develop-first
  integration: develop
  production: main
  staging: null
  promotion_order: [integration, staging, production]
```

Invariant: production is always an ancestor of integration (`main` subseteq
`develop`, i.e. `main..develop` behind_by == 0). Unpromoted forward work on
develop (ahead_by > 0) is normal; production carrying commits develop lacks is
the divergence the guard blocks.
