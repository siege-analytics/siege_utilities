# Epic: CRM Integrations

**Date:** 2026-06-03
**Status:** IN PROGRESS
**Package:** `siege_utilities.connectors`
**GitHub Label:** `epic:crm-integrations`
**Issues:** #1011–#1033

## Issue Index

| # | Ticket | Title | Size | Depends On |
|---|--------|-------|------|------------|
| #1011 | WS1-T1 | Connector Protocol definition | M | — |
| #1012 | WS1-T2 | Shared CRM data models (Contact, Account, Opportunity, Activity) | M | #1011 |
| #1013 | WS1-T3 | connectors/ package scaffold + lazy loading | S | #1011 |
| #1014 | WS1-T4 | OAuthProvider enum extension (HubSpot, Zoho, Dynamics) | S | — |
| #1015 | WS2-T1 | Salesforce OAuth + connection management | M | #1011, #1014 |
| #1016 | WS2-T2 | Salesforce read: Contacts, Accounts, Opportunities, Leads | L | #1015 |
| #1017 | WS2-T3 | Salesforce SOQL query builder | M | #1015 |
| #1018 | WS2-T4 | Salesforce write-back (create/update/upsert) | L | #1016 |
| #1019 | WS2-T5 | Salesforce Bulk API for large datasets | M | #1016 |
| #1020 | WS3-T1 | HubSpot OAuth + connection management | M | #1011, #1014 |
| #1021 | WS3-T2 | HubSpot read: Contacts, Companies, Deals, Activities | L | #1020 |
| #1022 | WS3-T3 | HubSpot write-back + association handling | L | #1021 |
| #1023 | WS4-T1 | Zoho CRM OAuth + connection management | M | #1011, #1014 |
| #1024 | WS4-T2 | Zoho read: Leads, Contacts, Accounts, Deals | L | #1023 |
| #1025 | WS4-T3 | Zoho write-back + custom module support | L | #1024 |
| #1026 | WS5-T1 | Dynamics 365 MSAL/OAuth + Dataverse connection | M | #1011, #1014 |
| #1027 | WS5-T2 | Dynamics 365 read: Contacts, Accounts, Opportunities | L | #1026 |
| #1028 | WS5-T3 | Dynamics 365 write-back via Web API | L | #1027 |
| #1029 | WS6-T1 | CRM DataFrame adapters for reporting primitives | M | #1012, any WS2-5 read |
| #1030 | WS6-T2 | Sales pipeline chart type registration | S | #1029 |
| #1031 | WS6-T3 | Cross-CRM dedup pipeline via identifiers/ | M | #1012, #1029 |
| #1032 | WS6-T4 | Notebook: CRM → dedup → enrich → report | L | #1029, #1031 |
| #1033 | WS6-T5 | Notebook: sales tables → charts → PDF | M | #1029, #1030 |

## Goal

Give siege_utilities read/write access to the four dominant commercial CRMs
(Salesforce, HubSpot, Zoho, Microsoft Dynamics 365) through a unified
connector protocol. CRM data flows into the existing analytics pipeline —
normalize via `identifiers/`, enrich via `geo/`, visualize via `reporting/` —
and enriched results write back.

Anchor use cases:
1. Pull contacts from multiple CRMs, deduplicate via `normalize_name_v1` + `uuid5_from_seed`, enrich with geo/demographics, push consolidated profiles back
2. Pull sales/opportunity tables, generate charts and PDF reports using existing `reporting/` primitives
3. Unify donor/customer records across systems without manual review

## Dependency Graph

```
WS1 (Protocol + Foundation)  — independent, must go first
WS2 (Salesforce)             — depends on WS1-T1, WS1-T4
WS3 (HubSpot)               — depends on WS1-T1, WS1-T4
WS4 (Zoho)                  — depends on WS1-T1, WS1-T4
WS5 (Dynamics 365)           — depends on WS1-T1, WS1-T4

WS6 (Reporting + Pipeline)  — depends on WS1-T2 + at least one
                               WS2-5 read ticket completed
```

Recommended execution order: WS1 first, then WS2-5 (fully parallelizable), WS6 last.

## Key Design Decisions

1. **New `connectors/` package** — not extending `analytics/`; creates migration path for existing connectors
2. **Protocol over ABC** — per CLAUDE.md tactical principle 1
3. **Scope boundary:** connectors are primitives (pull/push records). No sync scheduling, no CDC, no conflict resolution beyond dedup.
4. **Write-back:** create/update/upsert — not real-time sync

## Risks

| Risk | Mitigation |
|------|------------|
| API versioning churn | Version-pin endpoints; test against sandbox instances |
| Rate limiting | Explicit handling with backoff; never silently return partial results (SU-1) |
| OAuth complexity | Leverage existing CredentialManager + OAuthIntegration model |
| Scope creep into ETL | Connectors are primitives; transformation lives in identifiers/, geo/, reporting/ |
