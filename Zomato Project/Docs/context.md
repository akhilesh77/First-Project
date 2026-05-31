# Project context: AI-powered restaurant recommendation (Zomato use case)

This file captures the full intent and scope of the problem statement so collaborators and tooling can align without re-reading the raw statement.

## One-line summary

Build a service that combines a real Zomato-style restaurant dataset with an LLM to filter, rank, and explain personalized restaurant recommendations from structured user preferences.

## Source

- Original problem statement: `Docs/problemstatement.txt`
- Reference dataset (Hugging Face): `https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation`

## Business objective

Deliver **intelligent, personalized suggestions** that feel human and useful—not only a filtered list—by pairing **structured restaurant data** with **LLM reasoning and natural-language output**.

## Functional requirements (what the system must do)

1. **Accept user preferences** as inputs to drive filtering and ranking.
2. **Use a real-world restaurant dataset** (the Hugging Face Zomato recommendation dataset above).
3. **Invoke an LLM** to turn filtered candidates into ranked, explained recommendations.
4. **Present results** in a clear, scannable UI or API response.

## User inputs (explicit)

| Preference | Role |
|------------|------|
| Location | e.g. Delhi, Bangalore—geo or city scope |
| Budget | discrete band: low / medium / high |
| Cuisine | e.g. Italian, Chinese |
| Minimum rating | floor for acceptable venues |
| Additional preferences | free-form or tagged constraints (e.g. family-friendly, quick service) |

## Data layer expectations

- **Ingest** the Hugging Face dataset.
- **Preprocess** as needed for the app (cleaning, typing, normalization).
- **Extract** fields that support matching and display, including at minimum: restaurant name, location, cuisine, cost, rating, and other fields needed for filtering and explanations.

## Integration layer (between data and LLM)

- **Filter** the dataset to a relevant subset from user preferences.
- **Prepare structured payloads** for the model (e.g. JSON or tabular summaries of candidates).
- **Prompt design** so the LLM can **reason** and **rank** options—not only paraphrase the list.

## Recommendation engine (LLM responsibilities)

- **Rank** restaurants among the filtered set.
- **Explain** why each pick fits the user (alignment with budget, cuisine, rating, and extra preferences).
- **Optionally** summarize the overall shortlist or trade-offs.

## Output contract (what the user sees)

For each top recommendation, surface at least:

- Restaurant name  
- Cuisine  
- Rating  
- Estimated cost  
- **AI-generated explanation** (why this restaurant matches)

Presentation should be **user-friendly** (clear hierarchy, readable copy, no raw dump of model internals unless useful for debugging).

## Implicit non-functional hints

- **Traceability**: explanations should map to observable fields (rating, cost, cuisine, location) where possible.
- **Grounding**: recommendations should be grounded in the dataset subset passed to the LLM to reduce hallucinated venues.
- **Separation of concerns**: deterministic filtering vs. probabilistic ranking/explanation keeps behavior testable and tunable.

## Glossary

- **Structured data**: rows/fields from the dataset used for filtering and display.
- **LLM**: model used for ranking rationale, explanations, and optional summarization after structured narrowing.

---

*Generated from `problemstatement.txt` to preserve project context in one place.*
