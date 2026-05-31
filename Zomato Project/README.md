# Zomato AI Restaurant Recommendation

AI-powered restaurant recommendations using the Hugging Face Zomato dataset and an LLM (later phases).

## Documentation

| Doc | Purpose |
|-----|---------|
| [Docs/context.md](Docs/context.md) | Product scope |
| [Docs/architecture.md](Docs/architecture.md) | System design |
| [Docs/implementation-plan.md](Docs/implementation-plan.md) | Phased delivery |
| [Docs/edge-case.md](Docs/edge-case.md) | Edge-case handling |
| [Docs/data-dictionary.md](Docs/data-dictionary.md) | Phase 1 schema and mappings |

## Prerequisites

- Python 3.9+
- Network access (first ingest downloads ~574 MB from Hugging Face)

## Setup

```powershell
cd "c:\Users\Nisha\OneDrive\Documents\Next Leap\SD\Zomato Project"
py -m pip install -e .
copy .env.example .env
```

## Phase 1: Ingest dataset

```powershell
py -m scripts.ingest -v
```

Options:

- `--dataset` — override Hugging Face dataset id
- `--db path\to\file.db` — override SQLite path
- `--report data\ingest-report.json` — save JSON report
- `--no-samples` — skip sample query output

Default database: `data/restaurants.db` (see `.env.example`).

## Project layout

```
src/app/
  config.py          # Environment / paths
  filter/
    models.py        # UserPreferences, FilterResult
    service.py       # PreferenceFilter (hard filter + rank)
    scoring.py       # Soft keyword scoring
  api/
    routes.py        # POST /v1/recommendations, GET /health
    schemas.py       # Request/response models
    service.py       # Filter + Grok or stub
  llm/
    client.py        # xAI Grok HTTP client
    prompts.py       # Prompt builder
    engine.py        # rank_and_explain
  validation/
    merger.py        # Parse JSON, validate IDs, merge rows
  main.py            # FastAPI app
  data/
    budget.py        # Budget band thresholds
    constants.py     # Raw column names
    transform.py     # Clean + canonical mapping
    repository.py    # SQLite + indexes
    ingest.py        # Pipeline orchestration
scripts/
  ingest.py          # CLI
data/
  restaurants.db     # Generated (gitignored)
```

## Verify ingestion

The ingest command prints row counts, null rating/cost stats, budget distribution, top cities, and sample query results. See [Docs/data-dictionary.md](Docs/data-dictionary.md) for manual SQL examples.

## Phase 2: Filter by preferences

Requires ingested `data/restaurants.db`.

```powershell
py -m scripts.filter --location Bengaluru --budget medium --cuisine "North Indian" --min-rating 4.0
py -m scripts.filter --location Bangalore --budget medium --cuisine "North Indian" --min-rating 4.0 --additional "family-friendly" --top 10
```

Returns JSON with `candidates` (bounded list of `restaurant_id` + display fields), `total_matched`, and optional `message` when empty.

## Phase 3: Recommendation API

Requires ingested `data/restaurants.db`.

```powershell
py -m pip install -e ".[dev]"
py -m scripts.serve
```

Server: http://127.0.0.1:8000 — interactive docs at http://127.0.0.1:8000/docs

### Health check

```powershell
curl http://127.0.0.1:8000/health
```

### Get recommendations (stub explanations)

```powershell
curl -X POST http://127.0.0.1:8000/v1/recommendations `
  -H "Content-Type: application/json" `
  -d "{\"location\":\"Bengaluru\",\"budget\":\"medium\",\"cuisine\":\"North Indian\",\"min_rating\":4.0,\"top_k\":5}"
```

**Example request**

```json
{
  "location": "Bengaluru",
  "budget": "medium",
  "cuisine": "North Indian",
  "min_rating": 4.0,
  "additional_preferences": "family-friendly",
  "top_k": 5
}
```

**Example response**

```json
{
  "recommendations": [
    {
      "restaurant_id": "e25dc32d6d3f3c6f",
      "name": "House Of Commons",
      "cuisine": "Continental, Asian, North Indian",
      "rating": 4.8,
      "estimated_cost": 1000.0,
      "location": "Bangalore (Koramangala 5th Block)",
      "explanation": "House Of Commons serves ... matched by your filters (AI ranking coming in a later release)."
    }
  ],
  "summary": null,
  "message": null,
  "metadata": {
    "candidates_considered": 1432,
    "model": "stub",
    "latency_ms": 42
  }
}
```

Optional: set `API_KEY` in `.env` and send header `X-API-Key: your-secret-key`.

## Phase 4: Grok (xAI) ranking and explanations

Set your xAI API key in `.env` (not OpenAI):

```env
XAI_API_KEY=your-xai-key
LLM_MODEL=grok-3
LLM_BASE_URL=https://api.x.ai/v1
LLM_ENABLED=true
```

When `LLM_ENABLED=true` and a key is set, `POST /v1/recommendations` calls **Grok** to rank filtered candidates and write explanations. On failure, the API falls back to stub text (`model` suffix `-degraded`).

Disable Grok for local filter-only testing:

```env
LLM_ENABLED=false
```

Other Grok model ids: `grok-2-1212`, `grok-3-mini`, `grok-4.3` (see [xAI models](https://docs.x.ai/developers/models)).
