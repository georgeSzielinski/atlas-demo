# News Research

## Purpose

Evaluate news intelligence systems for ticker-specific sentiment, catalyst
detection, event summaries, and evidence extraction.

## Candidate Technologies

- Fake offline provider baseline
- Yahoo Finance RSS baseline
- Financial news APIs
- FinBERT sentiment models
- Financial RoBERTa sentiment models
- BloombergGPT-style financial LLMs
- General LLM summarization with source citations
- Retrieval-augmented news pipelines
- Event extraction models

## Evaluation Criteria

- Source reliability and freshness
- Sentiment accuracy against later market reaction
- Catalyst detection precision
- Explainability and citation quality
- Cost and rate limits
- Failure behavior when sources are unavailable
- License and data-use constraints

## Current Survey

See `news_ai_survey.md` for the first Atlas comparison of FinBERT, Financial
RoBERTa, ProsusAI/finbert, BloombergGPT-style financial LLMs, and optional
OpenAI/LLM explainability summaries.

## Integration Status

Atlas now has a provider-based news foundation. `FakeNewsProvider` remains the
default deterministic offline provider, while `RSSNewsProvider` is optional and
failure-safe. Future NLP models should be evaluated behind the same provider
boundary before they influence recommendation behavior.
