# Edge cases and handling guide

This document catalogs **known edge cases** for the AI-powered restaurant recommendation system and defines **expected behavior** for each. It complements [`context.md`](./context.md), [`architecture.md`](./architecture.md), and [`implementation-plan.md`](./implementation-plan.md).

Use this as a checklist during implementation and testing. Each entry maps to an owning component from the architecture.

---

## How to read this document

| Column | Meaning |
|--------|---------|
| **ID** | Stable reference for tests and issues |
| **Scenario** | What can go wrong or be unusual |
| **Owner** | Component responsible ([`architecture.md`](./architecture.md) §4) |
| **Handling** | Required system behavior |
| **HTTP / UX** | Client-facing outcome where applicable |
| **Test hint** | Suggested unit or integration test |

**Severity legend**

- **Critical** — Wrong data, security risk, or total failure without fallback
- **High** — Degraded experience; fallback required
- **Medium** — Handled gracefully; user may see limited results
- **Low** — Cosmetic or rare; log and continue

---

## 1. User input edge cases

Applies to: Client, Recommendation API ([`architecture.md`](./architecture.md) §4.1–4.2)

| ID | Scenario | Sev | Owner | Handling | HTTP / UX | Test hint |
|----|----------|-----|-------|----------|-----------|-----------|
| UI-01 | **Missing required field** (location, budget, cuisine, or min_rating) | High | API | Reject before orchestrator; return field-level validation errors | `400 Bad Request` with `{ "errors": { "location": "required" } }` | Submit empty body |
| UI-02 | **Empty string** after trim (`"   "`) | High | API | Treat as missing; same as UI-01 | `400` | `"location": "  "` |
| UI-03 | **Invalid budget** (not `low` \| `medium` \| `high`) | High | API | Reject with allowed enum list | `400` | `"budget": "cheap"` |
| UI-04 | **min_rating out of range** (e.g. `-1`, `6`, `NaN`) | High | API | Clamp or reject; document policy: reject if outside `[0, 5]` | `400` | `min_rating: 99` |
| UI-05 | **min_rating at boundary** (`0` or `5`) | Medium | Filter | Accept; filter uses `>=` correctly | `200` | Boundary values |
| UI-06 | **top_k missing** | Low | API | Default to `5` (or configured default) | `200` | Omit `top_k` |
| UI-07 | **top_k too large** (e.g. `1000`) | High | API | Cap at `top_k_max` (e.g. `10`); optionally warn in metadata | `200` with capped count | `top_k: 100` |
| UI-08 | **top_k zero or negative** | High | API | Reject or coerce to `1`; prefer reject for clarity | `400` | `top_k: 0` |
| UI-09 | **additional_preferences very long** (prompt injection / token blow-up) | Critical | API | Enforce max length (e.g. 500 chars); truncate with log or reject | `400` or truncated server-side | 10k-char string |
| UI-10 | **additional_preferences empty / omitted** | Low | Orchestrator | Skip soft scoring; LLM prompt omits or marks as none | `200` | Omit field |
| UI-11 | **Unicode / emoji in inputs** | Medium | API | Accept valid UTF-8; normalize NFC if needed | `200` | `"Delhi 🍕"` |
| UI-12 | **SQL / NoSQL injection patterns** in strings | Critical | Filter | Parameterized queries only; never interpolate raw user strings | `200` or `400`; no DB error leak | `"'; DROP TABLE--"` |
| UI-13 | **Prompt injection** in additional_preferences (“ignore instructions…”) | High | Prompt builder | Keep user text in a delimited block; system instructions separate; optional moderation strip | `200`; model may still misbehave—validator grounds output | Injection fixture strings |
| UI-14 | **Unknown JSON fields** in request body | Low | API | Ignore unknown keys (forward-compatible) or reject strict mode | Document choice | Extra `"foo": 1` |
| UI-15 | **Wrong Content-Type** or malformed JSON | High | API | `415` or `400` with clear message | No stack trace to client | Invalid JSON body |
| UI-16 | **Location typo** (“Delhii”, “Banglore”) | Medium | Filter | No match → empty results; optional fuzzy/alias suggest in message | `200` empty + helpful copy | Typo city name |
| UI-17 | **Location alias mismatch** (“Bengaluru” vs “Bangalore”) | Medium | Filter | Resolve via `city_alias` table ([`architecture.md`](./architecture.md) §5.3) | `200` if alias exists | Both spellings |
| UI-18 | **Cuisine not in dataset** (“Mexican” when none exist) | Medium | Filter | Zero candidates; do not call LLM | `200` empty + suggestion to relax filters | Obscure cuisine |
| UI-19 | **Over-constrained query** (all filters max strict) | Medium | Orchestrator | Zero candidates early exit | `200` `{ "recommendations": [], "message": "..." }` | Delhi + high + 5.0 + niche cuisine |
| UI-20 | **Duplicate concurrent requests** from same user | Low | API | Idempotent per request; optional short TTL cache ([`architecture.md`](./architecture.md) §7.4) | Same results | Parallel identical POSTs |

---

## 2. Dataset and ingestion edge cases

Applies to: Dataset store, ingestion pipeline ([`architecture.md`](./architecture.md) §4.5, §5.1)

| ID | Scenario | Sev | Owner | Handling | HTTP / UX | Test hint |
|----|----------|-----|-------|----------|-----------|-----------|
| DS-01 | **Hugging Face download fails** (network, rate limit) | Critical | Ingestion | Retry with backoff; fail ingest job with actionable error; app refuses start if DB empty | `503` on recommend if no data | Mock network failure |
| DS-02 | **Dataset schema changed** (column rename/remove) | Critical | Ingestion | Version pin dataset revision; validate expected columns; fail ingest with diff log | Block deploy until fixed | Fixture with wrong schema |
| DS-03 | **Missing restaurant_id** in raw data | High | Ingestion | Derive stable hash from name+city+address or row index; document algorithm | N/A | Strip id column |
| DS-04 | **Duplicate rows** (same name/city) | Medium | Ingestion | Dedupe policy: keep highest rating or first; log count removed | N/A | Duplicate fixture |
| DS-05 | **Null / missing rating** | High | Ingestion + Filter | Policy: **exclude from min_rating filter** OR treat as `0`—pick one and document ([`architecture.md`](./architecture.md) §4.4) | Users with high min_rating won't see null-rated rows | Rows with null rating |
| DS-06 | **Invalid rating string** (“4.5/5”, “-”, “New”) | Medium | Ingestion | Parse or set null; count parse failures in ingest report | N/A | Dirty rating values |
| DS-07 | **Missing cost / cost_for_two** | High | Ingestion | Exclude from budget filter OR assign default band `unknown`; never crash filter | Show “Cost unavailable” in UI | Null cost rows |
| DS-08 | **Cost format inconsistent** (“₹800”, “800 for two”, ranges) | Medium | Ingestion | Normalize to numeric; failed parse → null cost policy | N/A | Mixed formats |
| DS-09 | **Multi-label cuisines** (“Chinese, Thai, Seafood”) | Medium | Ingestion + Filter | Split on delimiter; tokenize; match if any token contains user cuisine | N/A | Multi-cuisine row |
| DS-10 | **Empty cuisine field** | Medium | Filter | Row fails cuisine hard filter; excluded | N/A | Blank cuisines |
| DS-11 | **City name casing / whitespace** (“ delhi ”, “DELHI”) | Medium | Ingestion | Normalize to canonical case-fold + trim at ingest and query | N/A | Case variants |
| DS-12 | **Special characters in restaurant name** | Low | Display | UTF-8 safe storage; escape on HTML render | N/A | Names with `&`, quotes |
| DS-13 | **Very long text fields** (descriptions) | Medium | Prompt builder | Truncate per-field char limit before LLM payload | N/A | 10k-char description |
| DS-14 | **Empty dataset after cleaning** | Critical | Ingestion | Fail ingest; do not start API | `503` | Aggressive filter in ingest |
| DS-15 | **Partial ingest failure** mid-load | Critical | Ingestion | Transactional load or blue-green swap; never serve half-loaded table | `503` until healthy | Kill process mid-insert |
| DS-16 | **Stale local DB** (ingest not re-run) | Low | Ops | Document one-time ingest; health check includes row count threshold | N/A | Empty DB file |

---

## 3. Filtering and query edge cases

Applies to: Preference filter ([`architecture.md`](./architecture.md) §4.4)

| ID | Scenario | Sev | Owner | Handling | HTTP / UX | Test hint |
|----|----------|-----|-------|----------|-----------|-----------|
| FL-01 | **Zero matching restaurants** | High | Orchestrator | Skip LLM; return empty list + actionable message (relax rating, budget, cuisine) | `200` empty + `message` | Impossible combo |
| FL-02 | **Exactly one candidate** | Medium | Orchestrator | Still valid; LLM ranks/explains one item OR skip LLM and use template | `200` with 1 item | Unique combo |
| FL-03 | **Candidates exceed N_max** (token budget) | High | Filter + Orchestrator | Pre-truncate deterministically: sort by rating desc, tie-break by id | `200`; metadata shows `candidates_considered` | Broad location only |
| FL-04 | **All candidates same rating** | Low | Filter | Stable secondary sort (cost, name, id) | N/A | Tie ratings |
| FL-05 | **Budget band boundary** (cost exactly on threshold) | Medium | Ingestion | Define inclusive/exclusive rules once; unit test boundaries | N/A | Cost at threshold |
| FL-06 | **User budget “low” but only “medium” exists in city** | Medium | Filter | Zero results; message suggests medium | `200` empty | Strict budget in expensive city |
| FL-07 | **Cuisine substring false positive** (“Indian” matches “Indo-Chinese”) | Low | Filter | Document behavior; optional word-boundary match | N/A | Substring collision |
| FL-08 | **additional_preferences keyword match none** | Low | Filter | No soft boost; hard filters still apply | `200` | Nonsense keywords |
| FL-09 | **additional_preferences matches all** equally | Low | Filter | Soft score tie → fall back to rating sort | N/A | Generic word “food” |
| FL-10 | **Location matches multiple cities** (ambiguous “New”) | Medium | Filter | Prefer exact match; if ambiguous, return disambiguation error or top city by row count | `400` or narrow list | `"New"` |
| FL-11 | **DB connection lost during query** | Critical | Data layer | Retry once; then `503` with safe message | `503` | Kill DB mid-request |
| FL-12 | **Query timeout** (slow unindexed scan) | High | Data layer | Indexes on filter columns; query timeout; log slow query | `504` or `503` | Large table no index |

---

## 4. LLM, prompt, and merge edge cases

Applies to: Prompt builder, LLM client, Validator/merger ([`architecture.md`](./architecture.md) §4.6–4.8)

| ID | Scenario | Sev | Owner | Handling | HTTP / UX | Test hint |
|----|----------|-----|-------|----------|-----------|-----------|
| LLM-01 | **LLM API key missing / invalid** | Critical | LLM client | Fail startup check OR degraded mode on request; never expose key in error | `503` “Recommendations temporarily unavailable” | Empty env var |
| LLM-02 | **LLM rate limit (429)** | High | LLM client | Retry with exponential backoff (max 2–3); then degraded mode | `200` with template explanations + flag in metadata | Mock 429 |
| LLM-03 | **LLM timeout** | High | LLM client | Abort; return deterministic ranked list + template explanation | `200` degraded | Short timeout mock |
| LLM-04 | **LLM provider outage (5xx)** | High | LLM client | Same as LLM-03; optional circuit breaker | `200` degraded | Mock 500 |
| LLM-05 | **Response not valid JSON** (markdown fences, prose only) | High | Validator | Strip code fences; retry parse; fallback degraded | `200` degraded | Raw prose fixture |
| LLM-06 | **JSON missing required keys** (no rankings array) | High | Validator | Degraded mode with filter order | `200` degraded | Partial JSON |
| LLM-07 | **Hallucinated restaurant_id** not in candidates | Critical | Validator | Drop invalid IDs; log count; pad from deterministic order if below top_k | `200`; never show fake venue | ID `"99999"` |
| LLM-08 | **Duplicate IDs in LLM ranking** | Medium | Validator | Dedupe keeping first occurrence; backfill from candidates | `200` | Duplicate ids in JSON |
| LLM-09 | **Fewer than top_k IDs returned** | Medium | Validator | Pad with next best from deterministic order; mark padded items optional in metadata | `200` | LLM returns 2 of 5 |
| LLM-10 | **More than top_k IDs returned** | Low | Validator | Trim to top_k preserving order | `200` | LLM returns 20 |
| LLM-11 | **Empty explanation string** for an ID | Medium | Validator | Substitute template: “Matches your preferences for {cuisine} in {location}.” | `200` | `""` explanation |
| LLM-12 | **Explanation contradicts facts** (wrong rating in text) | Medium | Merger | Display authoritative numbers from DB; explanation is narrative only | `200` | Mock wrong text |
| LLM-13 | **Model invents restaurant name in JSON** | Critical | Merger | **Always overwrite** name/cuisine/rating/cost from datastore ([`architecture.md`](./architecture.md) §4.8) | `200` correct facts | Model wrong name |
| LLM-14 | **Prompt exceeds context window** | High | Prompt builder | Reduce N_max; truncate descriptions; fail gracefully if still too large | `200` degraded or `503` | Huge candidate list |
| LLM-15 | **Unsafe / offensive model output** | High | Validator | Optional moderation pass; replace with generic explanation | `200` sanitized | Red-team prompts |
| LLM-16 | **Summary missing** when optional | Low | Merger | Omit summary field; UI hides block | `200` | No summary key |
| LLM-17 | **Summary present but empty** | Low | Merger | Treat as omitted | `200` | `"summary": ""` |
| LLM-18 | **Non-deterministic ranking** same input | Low | LLM client | Low temperature; document variance; optional cache | Acceptable variance | Run twice compare |
| LLM-19 | **Token usage spike** (verbose model) | Medium | LLM client | Cap max_output_tokens; monitor per request | N/A | Log token metrics |
| LLM-20 | **Retry succeeds after transient failure** | Low | LLM client | Single successful response; log retry count | `200` | Fail then succeed mock |

---

## 5. API and orchestration edge cases

Applies to: Recommendation API, Orchestrator ([`architecture.md`](./architecture.md) §4.2–4.3, §6.1)

| ID | Scenario | Sev | Owner | Handling | HTTP / UX | Test hint |
|----|----------|-----|-------|----------|-----------|-----------|
| OR-01 | **Unhandled exception in orchestrator** | Critical | API | Catch-all; log correlation id; `500` generic message | No stack trace in body | Force exception |
| OR-02 | **Partial failure after LLM success, merge throws** | High | Orchestrator | Degraded: return candidates with templates | `200` degraded | Break merger mock |
| OR-03 | **Request cancelled by client** | Low | API | Abort upstream LLM call if supported; stop processing | Client abort | Close connection |
| OR-04 | **Health check: DB down** | Critical | API | `GET /health` → `503` not ready | Deploy probe fails | Stop DB |
| OR-05 | **Health check: LLM optional** | Medium | API | Document: `/health` live if API+DB ok; `/ready` includes LLM ping optional | Split liveness/readiness | Config flag |
| OR-06 | **Rate limit exceeded** | High | API | `429` with `Retry-After` | User sees try again | Burst requests |
| OR-07 | **Payload too large** | High | API | `413` before parsing body | Clear message | Huge JSON |
| OR-08 | **CORS preflight failure** | Medium | API | Configure allowed origins for UI | Browser blocked | Wrong origin |
| OR-09 | **Idempotent empty vs error** | Medium | Orchestrator | Distinguish `200` empty (no matches) from `503` (system fault) in docs and UI | Different copy | Both paths |
| OR-10 | **Metadata latency_ms wrong** | Low | Orchestrator | Measure wall clock end-to-end; clamp negative | N/A | Clock skew |

---

## 6. Client and presentation edge cases

Applies to: Client ([`architecture.md`](./architecture.md) §4.1; [`context.md`](./context.md) §Output contract)

| ID | Scenario | Sev | Owner | Handling | HTTP / UX | Test hint |
|----|----------|-----|-------|----------|-----------|-----------|
| CL-01 | **Network error** (offline, DNS) | High | Client | Show retry button; no raw error object | Friendly banner | Offline mode |
| CL-02 | **Slow response** (>10s) | Medium | Client | Loading state; optional cancel | Spinner + cancel | Throttle API mock |
| CL-03 | **Empty recommendations array** | Medium | Client | Show empty state with tips from server `message` | Empty state UI | Zero results |
| CL-04 | **Null rating displayed** | Medium | Client | Show “Rating N/A” not `null` | Formatted display | Null in payload |
| CL-05 | **Null cost displayed** | Medium | Client | Show “Cost unavailable” | Formatted display | Null cost |
| CL-06 | **Very long explanation** | Low | Client | Clamp lines with “Read more” expand | Readable card | Long text |
| CL-07 | **XSS in restaurant name from DB** | Critical | Client | Escape on render; CSP headers | Safe HTML | `<script>` in name |
| CL-08 | **Double submit** (button spam) | Medium | Client | Disable button while loading | One request | Double click |
| CL-09 | **Stale results** (user changes form after response) | Low | Client | Clear results on input change or label “Results for …” | Clear UX | Edit after search |
| CL-10 | **Degraded mode flag in metadata** | Medium | Client | Optional badge: “AI summary unavailable; showing best matches” | User trust | `degraded: true` |

---

## 7. Security and abuse edge cases

Applies to: API, Prompt builder ([`architecture.md`](./architecture.md) §7.1, §9)

| ID | Scenario | Sev | Owner | Handling | HTTP / UX | Test hint |
|----|----------|-----|-------|----------|-----------|-----------|
| SEC-01 | **API key in client bundle** | Critical | Client + Ops | Keys server-side only | N/A | Static analysis |
| SEC-02 | **Secrets logged in prompts/errors** | Critical | All | Redact keys; log correlation id only | N/A | Log audit |
| SEC-03 | **Automated scraping / cost abuse** | High | API | Rate limit; optional API key | `429` | Load test |
| SEC-04 | **PII in additional_preferences** | Medium | API | Do not persist raw text unless required; redact logs | N/A | Email in string |
| SEC-05 | **LLM jailbreak attempts** | High | Prompt builder | Grounding + validator; no tool execution from user text | `200` grounded only | Injection corpus |

---

## 8. Operational and deployment edge cases

Applies to: Deployment, observability ([`architecture.md`](./architecture.md) §7–8)

| ID | Scenario | Sev | Owner | Handling | HTTP / UX | Test hint |
|----|----------|-----|-------|----------|-----------|-----------|
| OP-01 | **Cold start with empty SQLite path** | Critical | Ops | Init script runs ingest or fail fast | `503` | Fresh deploy |
| OP-02 | **Disk full during ingest** | Critical | Ingestion | Fail job; do not swap partial table | N/A | Simulate ENOSPC |
| OP-03 | **Wrong DATABASE_URL in prod** | Critical | Ops | Startup validation; clear log | `503` | Bad env |
| OP-04 | **Clock skew across replicas** | Low | Ops | Use monotonic timers for latency | N/A | N/A |
| OP-05 | **Log volume from debug prompts** | Medium | Ops | Debug flag off in prod; sample logs | N/A | High traffic |
| OP-06 | **Concurrent ingest + live queries** | High | Ops | Blue-green table swap or read lock during ingest | Brief `503` or stale read | Overlap jobs |

---

## 9. Decision register (policies to lock once)

Record chosen behavior in README or config so all components stay consistent.

| Topic | Options | Recommended default |
|-------|---------|---------------------|
| Null rating | Exclude vs treat as 0 | **Exclude** from min_rating queries |
| Null cost | Exclude vs `unknown` band | **`unknown`**; exclude from budget filter |
| Zero filter results | Message only vs suggest relaxations | **Suggest** relaxing rating or budget |
| top_k default / max | e.g. 5 / 10 | **5 / 10** |
| N_max candidates to LLM | e.g. 20–40 | **30** (tune to model context) |
| LLM failure | Empty vs degraded list | **Degraded list** ([`architecture.md`](./architecture.md) §2) |
| City matching | Exact vs alias table | **Exact + alias table** for common variants |
| Invalid LLM IDs | Drop vs fail whole request | **Drop + backfill** |
| additional_preferences max length | e.g. 500 | **500 characters** |

---

## 10. Behavior matrix (quick reference)

| Condition | Call LLM? | Response shape |
|-----------|-----------|----------------|
| Validation error | No | `400` |
| Zero candidates | No | `200` empty + message |
| 1..N candidates, LLM OK | Yes | `200` ranked + explanations |
| 1..N candidates, LLM fail | No (fallback) | `200` degraded + templates |
| DB unavailable | No | `503` |
| Rate limited | No | `429` |

---

## 11. Test coverage map

Map edge-case IDs to implementation phases ([`implementation-plan.md`](./implementation-plan.md)):

| Phase | Priority edge-case IDs |
|-------|------------------------|
| Phase 1 (Data) | DS-01–DS-16 |
| Phase 2 (Filter) | FL-01–FL-12, UI-17–UI-19 |
| Phase 3 (API) | UI-01–UI-15, OR-01, OR-06–OR-08 |
| Phase 4 (LLM) | LLM-01–LLM-20 |
| Phase 5 (Orchestrator) | OR-02, OR-09, behavior matrix |
| Phase 6 (Client) | CL-01–CL-10 |
| Phase 7 (Hardening) | SEC-01–SEC-05, OP-01–OP-06 |

---

## 12. Document map

| Document | Role |
|----------|------|
| [`context.md`](./context.md) | Requirements and output contract |
| [`architecture.md`](./architecture.md) | Components and fail-soft principles |
| [`implementation-plan.md`](./implementation-plan.md) | When to implement handlers |
| **This file** | Edge scenarios, policies, and expected behavior |

---

*Update this file when new edge cases are discovered in development or review.*
