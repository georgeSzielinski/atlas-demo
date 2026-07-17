# Financial News AI Survey

This survey compares candidate systems for financial news sentiment and event
intelligence. It is documentation only. No production engine changes are
implied.

## Summary Recommendation

Start with a two-layer benchmark: use a small local classifier for article-level
sentiment, then evaluate an optional LLM explainability layer for source-grounded
summaries and event extraction. FinBERT and Financial RoBERTa are the practical
first candidates. BloombergGPT-style systems should inform architecture, but
not be treated as immediately available Atlas dependencies.

## Candidate Comparison

| Candidate | Purpose | Input Format | License If Found | Integration Difficulty | Pros | Cons | Atlas Fit | Risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FinBERT | Financial-domain BERT family for sentiment or tone analysis on financial text. | Short financial text snippets, sentences, headlines, or article excerpts; outputs positive, negative, or neutral sentiment probabilities depending on checkpoint. | Varies by implementation. The ProsusAI repository is Apache-2.0. Some academic/Hugging Face checkpoints do not clearly expose a license on the model card and need per-artifact review. | Medium. Easy inference API through Transformers, but Atlas needs headline/article chunking, source metadata, confidence calibration, and stale-news behavior. | Purpose-built for financial language; small enough for local CPU/GPU tests; clear labels; widely used baseline. | Sentence-level models can miss event context; older checkpoints may depend on older libraries; license and dataset terms vary. | Strong first baseline for ticker-level sentiment evidence. | False confidence on ambiguous headlines, source duplication, stale article reuse, and license ambiguity for individual checkpoints. Sources: [FinBERT paper](https://arxiv.org/abs/1908.10063), [yiyanghkust model card](https://huggingface.co/yiyanghkust/finbert-tone). |
| Financial RoBERTa | RoBERTa or DistilRoBERTa models fine-tuned for financial news sentiment classification. | Financial news sentences or headlines; common output labels are positive, negative, and neutral. | Example: `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis` lists Apache-2.0 on Hugging Face. | Low to medium. Transformers pipeline integration is straightforward; Atlas still needs provenance, freshness, and confidence mapping. | Lightweight compared with full LLMs; Apache-2.0 example exists; DistilRoBERTa model card reports 82M parameters and strong Financial PhraseBank evaluation accuracy. | Training data is small and may not generalize to all current market news; sentence-level sentiment is not full event intelligence. | Strong candidate for first local news classifier benchmark. | Overfitting to Financial PhraseBank style, weak event detection, and poor handling of sarcasm, guidance nuance, or macro context. Source: [Hugging Face model card](https://huggingface.co/mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis). |
| ProsusAI/finbert | Specific FinBERT implementation/checkpoint for financial sentiment analysis. | Financial text passed to a text-classification pipeline; model returns softmax outputs for positive, negative, and neutral. | Apache-2.0 repository license. Hugging Face model card links to the FinBERT paper and describes Financial PhraseBank fine-tuning. | Low to medium. Existing Transformers support makes a proof-of-concept simple; production use needs model packaging and score normalization. | Clear open-source baseline; widely downloaded model card; direct financial sentiment output. | Repository notes older Hugging Face dependency history; model is sentiment-only, not a source-grounded event extractor. | Best first FinBERT checkpoint for Atlas benchmark if license review passes. | May overweight short-term sentiment; model confidence may not equal investment relevance. Sources: [GitHub](https://github.com/ProsusAI/finBERT), [Hugging Face](https://huggingface.co/ProsusAI/finbert). |
| BloombergGPT-style financial LLMs | Large financial-domain LLM architecture for broad NLP tasks such as sentiment, named entity recognition, question answering, summarization, and classification. | Long-form financial documents, news, filings, transcripts, and mixed prompts depending on model design. | BloombergGPT itself is not an open Atlas dependency. The paper describes a 50B parameter model; public open alternatives such as FinGPT exist with their own licenses and terms. | High. Requires model access, cost controls, prompt/evaluation design, and strict provenance rules. | Shows that finance-specialized LLMs can outperform general models on financial tasks; useful architecture reference for future domain LLM strategy. | BloombergGPT is closed-source as a practical dependency; 50B-class models are expensive; hallucination and source attribution remain risks. | Research reference only for now. Atlas should not depend on a proprietary financial LLM for core sentiment. | Vendor lock-in, opaque data, high cost, hallucinated summaries, and compliance concerns. Sources: [BloombergGPT paper](https://arxiv.org/abs/2303.17564), [FinGPT paper](https://arxiv.org/abs/2307.10485). |
| OpenAI/LLM Summaries | Optional explainability layer for summarizing trusted articles, extracting events, and producing source-grounded notes after retrieval. | Curated source text snippets with ticker, source, URL, publication time, and explicit summarization/extraction instructions. | API/service terms apply rather than a model-weight license. Review current provider terms before production use. | Medium. Easier than hosting large domain LLMs, but requires strict prompt contracts, citation/provenance handling, cost limits, and fallback behavior. | Strong natural-language summaries; can extract catalysts, risks, and cross-article themes; useful for user-facing explanations. | Not a primary sentiment classifier; can hallucinate if not source-grounded; cost and latency vary; requires privacy and data-use review. | Good optional explanation layer after deterministic source retrieval and classifier scoring. | Hallucinated facts, missing citations, stale source text, prompt drift, cost spikes, and overexplaining weak evidence. Source: [OpenAI platform docs](https://platform.openai.com/docs). |

## Trusted Source Rules

- Prefer primary company sources, SEC filings, exchange notices, earnings releases, and investor relations pages for company-specific material events.
- Prefer reputable financial news outlets, wire services, and official index/provider publications for market news.
- Treat blogs, social media, forums, scraped reposts, and low-reputation aggregators as low-trust unless corroborated.
- Record source name, URL, publication timestamp, retrieval timestamp, ticker mapping, and headline for every item.
- Deduplicate syndicated stories so one wire article does not appear as many independent signals.
- Do not use a source when terms of use or redistribution rights are unclear for the intended Atlas feature.

## Freshness Rules

- Intraday market-moving news should be considered fresh for the current trading day only unless the event remains unresolved.
- Earnings, SEC filings, and official company announcements may remain relevant for 30 to 90 days depending on topic.
- Analyst rating changes and price-target updates should decay quickly unless supported by new fundamentals.
- Macro news should be tagged separately and not forced onto a single ticker unless the link is explicit.
- Store publication time and retrieval time separately so Atlas can detect stale feeds.
- If publication time is missing, treat the item as stale unless a trusted source provides a clear date elsewhere.

## Provenance Requirements

Every future news intelligence record should include:

- ticker
- source name
- source type
- source URL
- headline
- author or publisher when available
- publication timestamp
- retrieval timestamp
- content snippet or summary input hash
- model/tool name
- sentiment label
- confidence
- extracted event type when available
- cited evidence text or sentence reference
- stale flag
- missing-data flag

LLM summaries must reference source records already captured by Atlas. They
should not introduce uncited facts.

## Stale Or Missing News Handling

- If no trusted fresh news is available, return neutral sentiment, zero or low confidence, and an explicit "No fresh trusted news found" note.
- If only stale news is available, mark the item stale and exclude it from strong BUY/AVOID evidence weighting.
- If sources fail, keep Atlas usable and report a source failure instead of fabricating sentiment.
- If articles conflict, preserve both sides and lower confidence rather than forcing a single narrative.
- If source provenance is incomplete, use the item for display only after review, not for scoring.

## Atlas Research Status

No new model integration is active. The next step is to build an offline news
benchmark using fixed tickers, trusted article sets, event labels, freshness
metadata, and validation against later price/recommendation outcomes.
