# Pydantic Model Constraints Reference

This document provides a comprehensive reference for all Pydantic field constraints used in siege_utilities configuration models. Use this when constructing configurations to ensure your values pass validation.

---

## Table of Contents

- [Person](#person)
- [User](#user)
- [Client](#client)
- [Collaborator](#collaborator)
- [Organization](#organization)
- [Collaboration](#collaboration)
- [Credential](#credential)
- [OnePasswordCredential](#onepasswordcredential)
- [DatabaseConnection](#databaseconnection)
- [OAuthIntegration](#oauthintegration)

---

## Person

Base person/actor model with common capabilities.

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `person_id` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `name` | str | Yes | 1-100 chars | - |
| `email` | str | Yes | Must match `^[^@]+@[^@]+\.[^@]+$` | - |
| `phone` | str | No | Max 20 chars, 10-15 digits (extracted) | None |
| `address` | str | No | Max 200 chars | None |
| `website` | str | No | Must match `^https?://[^\s/$.?#].[^\s]*$` | None |
| `linkedin` | str | No | Must match `^https?://(www\.)?linkedin\.com/(in\|company)/[a-zA-Z0-9-]+/?$` | None |
| `credentials` | List[Credential] | No | - | [] |
| `oauth_integrations` | List[OAuthIntegration] | No | - | [] |
| `database_connections` | List[DatabaseConnection] | No | - | [] |
| `onepassword_credentials` | List[OnePasswordCredential] | No | - | [] |
| `organizations` | List[str] | No | Must be unique | [] |
| `primary_organization` | str | No | - | None |
| `collaborations` | List[str] | No | Must be unique | [] |
| `created_date` | datetime | No | - | now() |
| `last_updated` | datetime | No | - | now() |
| `status` | str | No | `active \| inactive \| suspended \| archived` | "active" |
| `notes` | str | No | Max 1000 chars | None |

---

## User

User actor - Siege/Masai team members and internal users. Extends Person.

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `username` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `github_login` | str | No | Max 50 chars, pattern: `^[a-zA-Z0-9_-]+$` | None |
| `role` | str | No | `analyst \| manager \| developer \| admin \| collaborator` | "analyst" |
| `permissions` | List[str] | No | Must be unique | [] |
| `preferred_download_directory` | Path | No | - | ~/Downloads/siege_utilities |
| `default_output_format` | str | No | `pdf \| pptx \| html` | "pdf" |
| `preferred_map_style` | str | No | `open-street-map \| carto-positron \| carto-darkmatter \| stamen-terrain \| stamen-toner \| stamen-watercolor \| satellite \| terrain` | "open-street-map" |
| `default_color_scheme` | str | No | `YlOrRd \| viridis \| plasma \| inferno \| Blues \| Greens \| Reds \| Purples` | "YlOrRd" |
| `default_dpi` | int | No | 72-600 | 300 |
| `default_figure_size` | tuple[int, int] | No | - | (10, 8) |
| `enable_logging` | bool | No | - | True |
| `log_level` | str | No | `DEBUG \| INFO \| WARNING \| ERROR \| CRITICAL` | "INFO" |
| `google_analytics_key` | str | No | Max 100 chars | "" |
| `facebook_business_key` | str | No | Max 100 chars | "" |
| `census_api_key` | str | No | Max 100 chars | "" |
| `default_database` | str | No | `postgresql \| mysql \| sqlite \| duckdb` | "postgresql" |
| `postgresql_connection` | str | No | Max 500 chars | "" |
| `duckdb_path` | str | No | Max 500 chars | "" |

---

## Client

Client actor - External client organizations. Extends Person.

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `client_code` | str | Yes | 2-10 chars, pattern: `^[A-Z0-9]+$`, must be uppercase, reserved codes: `{DEFAULT, ADMIN, SYSTEM, TEST}` | - |
| `industry` | str | Yes | 1-50 chars | - |
| `project_count` | int | Yes | >= 0 | - |
| `client_status` | str | Yes | `active \| inactive \| archived` | - |
| `branding_config` | Dict[str, Any] | No | - | None |
| `report_preferences` | Dict[str, Any] | No | - | None |

---

## Collaborator

Collaborator actor - External collaborators. Extends Person.

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `external_organization` | str | Yes | 1-100 chars, cannot be empty/whitespace | - |
| `collaboration_level` | str | No | `read \| write \| admin` | "read" |
| `access_expires` | datetime | No | Must be in the future | None |
| `invitation_sent` | datetime | No | - | None |
| `invitation_accepted` | datetime | No | - | None |
| `allowed_services` | List[str] | No | Must be unique | [] |
| `restricted_credentials` | List[str] | No | Must be unique | [] |

---

## Organization

Organization model for companies (Siege, Masai, Hillcrest).

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `org_id` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `name` | str | Yes | 1-100 chars | - |
| `org_type` | str | Yes | `vendor \| client \| partner \| internal` | - |
| `primary_email` | str | Yes | Must match `^[^@]+@[^@]+\.[^@]+$` | - |
| `phone` | str | No | Max 20 chars | None |
| `address` | str | No | Max 200 chars | None |
| `website` | str | No | - | None |
| `members` | List[str] | No | Must be unique | [] |
| `primary_contact` | str | No | - | None |
| `created_date` | datetime | No | - | now() |
| `last_updated` | datetime | No | - | now() |
| `status` | str | No | `active \| inactive \| archived` | "active" |
| `notes` | str | No | Max 1000 chars | None |

---

## Collaboration

Collaboration model for joint projects between organizations.

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `collab_id` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `name` | str | Yes | 1-100 chars | - |
| `description` | str | No | Max 500 chars | None |
| `organizations` | List[str] | No | Must be unique | [] |
| `clients` | List[str] | No | Must be unique | [] |
| `participants` | List[str] | No | Must be unique | [] |
| `status` | str | No | `planning \| active \| on_hold \| completed \| cancelled` | "planning" |
| `start_date` | datetime | No | - | now() |
| `end_date` | datetime | No | Must be in the future | None |
| `shared_credentials` | List[str] | No | - | [] |
| `shared_databases` | List[str] | No | - | [] |
| `created_date` | datetime | No | - | now() |
| `last_updated` | datetime | No | - | now() |
| `notes` | str | No | Max 1000 chars | None |

---

## Credential

Credential management with comprehensive validation.

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `name` | str | Yes | 1-100 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `credential_type` | CredentialType | Yes | `api_key \| oauth_token \| username_password \| ssh_key \| certificate \| secret` | - |
| `service` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `username` | str | No | Max 100 chars | None |
| `password` | str | No | Max 500 chars, min 8 chars if provided | None |
| `api_key` | str | No | Max 500 chars, min 10 chars if provided | None |
| `token` | str | No | Max 1000 chars | None |
| `secret` | str | No | Max 500 chars | None |
| `status` | CredentialStatus | No | `active \| expired \| revoked \| pending` | "active" |
| `created_date` | datetime | No | - | now() |
| `expires_at` | datetime | No | Must be in the future | None |
| `last_used` | datetime | No | - | None |
| `metadata` | Dict[str, Any] | No | - | {} |
| `notes` | str | No | Max 1000 chars | None |

---

## OnePasswordCredential

Specialized credential model for 1Password integration.

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `vault_id` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `item_id` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `title` | str | Yes | 1-100 chars | - |
| `credential_name` | str | Yes | 1-100 chars | - |
| `service` | str | Yes | 1-50 chars | - |
| `last_synced` | datetime | No | - | now() |
| `auto_sync` | bool | No | - | True |

---

## DatabaseConnection

Database connection configuration with comprehensive validation.

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `name` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `connection_type` | str | Yes | `postgresql \| mysql \| sqlite \| duckdb` | - |
| `host` | str | Yes | 1-255 chars, pattern: `^[a-zA-Z0-9.-]+$` | - |
| `port` | int | Yes | 1-65535 | - |
| `database` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z][a-zA-Z0-9_-]*$` (must start with letter) | - |
| `username` | str | Yes | 1-50 chars | - |
| `password` | str | Yes | **8-100 chars, requires: uppercase + lowercase + number** | - |
| `ssl_enabled` | bool | No | - | True |
| `connection_timeout` | int | No | 1-300 seconds | 30 |
| `max_connections` | int | No | 1-100 | 10 |

### Password Validation Rules

The `password` field has strict validation:
- Minimum 8 characters
- Maximum 100 characters
- Must contain at least one uppercase letter (`A-Z`)
- Must contain at least one lowercase letter (`a-z`)
- Must contain at least one number (`0-9`)
- Cannot be common weak passwords (`password`, `12345678`, `qwerty123`)

**Valid example:** `Dessert123!`
**Invalid examples:** `dessert` (too short, no uppercase/number), `PASSWORD123` (no lowercase)

---

## OAuthIntegration

OAuth integration configuration with comprehensive validation.

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `name` | str | Yes | 1-100 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `provider` | OAuthProvider | Yes | `google \| microsoft \| github \| linkedin \| facebook \| twitter \| salesforce \| slack \| zoom \| custom` | - |
| `service` | str | Yes | 1-50 chars, pattern: `^[a-zA-Z0-9_-]+$` | - |
| `client_id` | str | Yes | 10-200 chars | - |
| `client_secret` | str | Yes | 10-200 chars | - |
| `redirect_uri` | str | Yes | Must match `^https?://[^\s/$.?#].[^\s]*$` | - |
| `scopes` | List[OAuthScope] | No | `read \| write \| admin \| profile \| email \| analytics \| files \| calendar \| contacts` | [] |
| `access_token` | str | No | Max 2000 chars | None |
| `refresh_token` | str | No | Max 2000 chars | None |
| `token_type` | str | No | - | "Bearer" |
| `expires_at` | datetime | No | Must be in the future | None |
| `is_active` | bool | No | - | True |
| `created_date` | datetime | No | - | now() |
| `last_used` | datetime | No | - | None |
| `last_refreshed` | datetime | No | - | None |
| `auto_refresh` | bool | No | - | True |
| `refresh_threshold` | int | No | 60-3600 seconds | 300 |
| `metadata` | Dict[str, Any] | No | - | {} |
| `notes` | str | No | Max 1000 chars | None |

---

## Quick Reference: Common Patterns

### ID Fields
All ID fields (`person_id`, `org_id`, `collab_id`, etc.):
- Pattern: `^[a-zA-Z0-9_-]+$`
- Length: 1-50 chars

### Email Fields
- Pattern: `^[^@]+@[^@]+\.[^@]+$`
- Example: `user@example.com`

### URL Fields (website, redirect_uri)
- Pattern: `^https?://[^\s/$.?#].[^\s]*$`
- Example: `https://example.com/callback`

### LinkedIn URLs
- Pattern: `^https?://(www\.)?linkedin\.com/(in|company)/[a-zA-Z0-9-]+/?$`
- Examples:
  - `https://linkedin.com/in/johndoe`
  - `https://www.linkedin.com/company/siege-analytics`

### Phone Numbers
- 10-15 digits (non-digit characters stripped during validation)
- Examples: `555-123-4567`, `+1 (555) 123-4567`

---

## Enums Reference

### CredentialType
```python
"api_key" | "oauth_token" | "username_password" | "ssh_key" | "certificate" | "secret"
```

### CredentialStatus
```python
"active" | "expired" | "revoked" | "pending"
```

### OAuthProvider
```python
"google" | "microsoft" | "github" | "linkedin" | "facebook" | "twitter" | "salesforce" | "slack" | "zoom" | "custom"
```

### OAuthScope
```python
"read" | "write" | "admin" | "profile" | "email" | "analytics" | "files" | "calendar" | "contacts"
```

---

## Model Inheritance

```
BaseModel
├── Person
│   ├── User
│   ├── Client
│   └── Collaborator
├── Organization
├── Collaboration
├── Credential
├── OnePasswordCredential
├── DatabaseConnection
└── OAuthIntegration
```

---

*Last updated: 2026-02-05*
