# Parsons license-compatibility analysis

**Purpose:** verify that `siege_utilities` can depend on TMC's [Parsons](https://github.com/move-coop/parsons) library without contaminating siege's dual-license (AGPL-3.0-only OR commercial), and determine what obligation flows to end users of `siege_utilities[parsons-*]` extras.

**Closes P0-1 of parent epic:** [#1148 Epic: TMC Parsons integration](https://github.com/siege-analytics/siege_utilities/issues/1148).

## Facts

### Parsons license

Parsons is [Apache License 2.0](https://github.com/move-coop/parsons/blob/main/LICENSE.md) with an **additional NOTICE under Section 4(d)**. The NOTICE requires downstream distributors to preserve an author-attribution values statement (ending discrimination and violence based on protected classes, economic equality, reproductive rights, environmental protection, firearm safety and gun-violence prevention, etc.). Verbatim from `LICENSE.md` lines 1–3:

> Parsons: a Python library of connectors for the progressive community.
> Copyright 2019-2026 The Movement Cooperative
> Licensed under the Apache License, Version 2.0 (the "License"); you may not use this library except in compliance with the License, with the Additional NOTICE under Section 4(d) to include preserving the following author attribution statement:

The full NOTICE follows in the LICENSE.md; every distributor that ships Parsons or a derivative that reproduces "the Work in any Derivative Work" (Apache-2.0 §4(d) language) must preserve that NOTICE.

### siege_utilities license

`siege_utilities` is dual-licensed:

- **AGPL-3.0-only** (see [`LICENSES/AGPL-3.0.txt`](../LICENSES/AGPL-3.0.txt)) for open-source use.
- **Commercial license** ([`LICENSES/Siege-Commercial.txt`](../LICENSES/Siege-Commercial.txt)) under separate agreement.

SPDX identifier on top of [`LICENSE`](../LICENSE): `AGPL-3.0-only OR LicenseRef-Siege-Commercial`. Effective date: March 6, 2026. Attribution is required in both paths. See [`docs/LICENSE_MODEL.md`](LICENSE_MODEL.md).

## Analysis

### Can siege_utilities depend on Parsons via `pip install`?

**Yes.** Apache License 2.0 is a permissive license explicitly compatible with GPLv3 and AGPLv3 in the "downstream" direction: an AGPL-licensed work may consume an Apache-2.0-licensed dependency. This is confirmed by the [FSF's license compatibility list](https://www.gnu.org/licenses/license-list.html#apache2) ("This is a free software license, compatible with version 3 of the GNU GPL"). The reverse (Apache-2.0 consuming AGPL) would raise questions; that is not the direction here.

A pip-installed dependency is a runtime dependency, not vendored source. siege's distribution ships no Parsons code; end users who install `siege_utilities[parsons-*]` pull Parsons from PyPI themselves. This is the standard shape for Python library dependencies and is unambiguously permitted.

**Verdict:** PASS. Dependency permitted without re-license.

### Can siege_utilities vendor Parsons source?

**Not recommended.** Vendoring (copying Parsons source into `siege_utilities/vendor/parsons/`) would:

1. Trigger Apache-2.0 §4(d) NOTICE obligations on siege as a distributor — the NOTICE must be preserved in the vendored copy AND in any user-facing distribution artifact that reproduces it.
2. Create a maintenance burden (upstream tracking, security patches).
3. Not provide any material benefit over pip-depending, since Parsons is on PyPI and stable.

**Verdict:** vendoring is FORBIDDEN by this policy. All integration goes through the `parsons` PyPI dependency.

### Can siege_utilities re-export Parsons symbols from `siege_utilities.integrations.parsons.*`?

**Yes, with a caveat.** Wrapping (as in `SiegeVAN(parsons.VAN)`) or re-exporting (`from parsons import VAN`) does not itself trigger vendoring. The wrapper code we write is siege-authored and lives under siege's AGPL/commercial dual-license. The underlying Parsons class stays under Apache-2.0 and its NOTICE.

**Caveat:** if a wrapper's docstring reproduces material verbatim from Parsons docs (e.g., long API descriptions copied over), that reproduced text carries Apache-2.0 obligations. Best practice: write our own docstrings, reference Parsons docs by URL for detailed API behavior.

**Verdict:** wrapping and re-exporting PASS. Verbatim doc reproduction should be avoided in wrapper source.

### What obligation flows to end users of `siege_utilities[parsons-*]`?

End users who install `pip install siege-utilities[parsons-van]` receive:

- The siege wrapper code under **AGPL-3.0-only OR LicenseRef-Siege-Commercial** (their choice per siege's dual-license terms).
- The `parsons` package under **Apache-2.0 with §4(d) NOTICE** as an installed dependency.

Consumers who redistribute their own work built on top of `siege_utilities[parsons-*]` MUST:

1. Comply with siege's chosen license path (AGPL-3.0-only obligations if the AGPL path is chosen, or the commercial-license terms if signed).
2. Preserve the Parsons §4(d) NOTICE if they redistribute Parsons or a work reproducing it (per Apache-2.0 §4(d)).

Consumers who use `siege_utilities[parsons-*]` internally (SaaS, private applications, non-distributed use) still trigger AGPL-3.0's network-copyleft clause if their service exposes siege's functionality over a network, unless they hold a commercial license.

### Legal-review flag

**Commercial-license reviewer sign-off recommended before Phase 5 (public documentation) lands.** The reasoning:

1. The §4(d) NOTICE is unusual — most Apache-2.0 works do not carry appended NOTICE clauses. Downstream commercial customers who license siege under `LicenseRef-Siege-Commercial` may have policies about political-values statements attached to their dependency graph. Better to flag proactively than to answer post-hoc.
2. The commercial-license terms in [`LICENSES/Siege-Commercial.txt`](../LICENSES/Siege-Commercial.txt) may need a clause acknowledging that Parsons's NOTICE flows through regardless of the commercial-license path (since Parsons is a third-party dependency, not siege's own IP).

Legal review is NOT required to unblock Phase 1 substrate work (P1-1..P1-4) or Phase 2 (VAN connector) — those ship under the existing dual-license and don't distribute Parsons. Legal review IS a prerequisite for Phase 5 public docs and for any commercial-license customer questions.

## Required NOTICE surface language

Per Apache-2.0 §4(d), any distribution reproducing Parsons's work must preserve the NOTICE. Since siege pip-depends on Parsons rather than distributing it, the strictest read is that the NOTICE obligation flows to end users who install Parsons. However, best practice for wrapper libraries is to surface the upstream NOTICE proactively so users know what they're pulling in.

The following language MUST appear in [`docs/parsons_integration.md`](parsons_integration.md) (published in Phase 5, P5-2):

> **Third-party NOTICE — TMC Parsons.** `siege_utilities[parsons-*]` depends on
> [TMC Parsons](https://github.com/move-coop/parsons), licensed under the Apache License 2.0
> with an additional NOTICE under Section 4(d). The NOTICE requires downstream distributors
> to preserve The Movement Cooperative's author-attribution statement of values. If you
> redistribute Parsons or a derivative thereof — including as part of a redistribution of
> `siege_utilities[parsons-*]` — you must preserve TMC's NOTICE alongside the Apache-2.0
> license text. See [Parsons LICENSE.md](https://github.com/move-coop/parsons/blob/main/LICENSE.md)
> for the exact NOTICE text.

The README's "Getting Started by Use Case" table (P5-1) should include a brief pointer to `docs/parsons_integration.md` for the license note when adding the "Campaign/Advocacy Data" row.

## Falsification

Per epic Fact Sheet claim #1: this analysis is falsified if Parsons's `LICENSE.md` on `main` no longer contains "Apache License, Version 2.0" or the §4(d) NOTICE is removed. If a future audit finds either condition, this file must be revised before Phase 5 (public docs) ships.

Additional falsification: if a competent open-source licensing reviewer reads this document and rejects the "PASS" verdict in writing (comment on #1149), the epic dies — close #1148 with a rationale comment referencing the rejection.

## Decision summary

| Question | Verdict |
|---|---|
| Depend on Parsons via PyPI | **YES** — permitted, no re-license required |
| Vendor Parsons source into siege tree | **NO** — forbidden by this policy |
| Wrap / re-export Parsons symbols | **YES** — write our own docstrings, avoid verbatim reproduction |
| End-user obligation surface | Documented above; must appear in `docs/parsons_integration.md` (Phase 5) |
| Commercial-license legal review needed | Recommended before Phase 5 (public docs); not blocking for Phase 1/2 |

## References

- Parsons LICENSE: <https://github.com/move-coop/parsons/blob/main/LICENSE.md>
- siege LICENSE: [`../LICENSE`](../LICENSE)
- siege license model: [`LICENSE_MODEL.md`](LICENSE_MODEL.md)
- FSF Apache-2.0 compatibility statement: <https://www.gnu.org/licenses/license-list.html#apache2>
- Parent epic: [#1148](https://github.com/siege-analytics/siege_utilities/issues/1148)
- This ticket: [#1149](https://github.com/siege-analytics/siege_utilities/issues/1149)
