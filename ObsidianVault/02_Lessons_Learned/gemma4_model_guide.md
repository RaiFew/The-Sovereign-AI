# Gemma 4 26B - Model Usage Guide

## Overview
Gemma 4 26B is an open-weight model from Google available both via local Ollama and Cloud API (Google AI Studio).

## Option 1: Local API (Ollama)
Suitable for Agent J (Compressor) and Agent F (Auditor) - local processing.

**Model Name:** `gemma4:26b`

**Pull Command:**
```bash
ollama pull gemma4:26b
```

**Benefits:**
- Free permanently - no request/token limits
- 100% Privacy - data never leaves your machine
- Works offline - no internet required
- Ideal for processing private Obsidian data

---

## Option 2: Cloud API (Google AI Studio / Vertex AI)
Higher speed, no local hardware requirements.

**Available Models:**
- Instruction Tuned (Recommended): `gemma-4-26b-it`
- Base Model: `gemma-4-26b`
- Cost-efficient (A4B): `gemma-4-26b-a4b-it`

**Free Tier Limits (2026):**
- 100-250 requests per day
- Limited requests per minute (RPM)
- ⚠️ **Privacy Trade-off**: Google may use your input/output data to train their models

**Paid Tier:**
- ~$0.06 per 1 million tokens
- 100% privacy - Google won't use your data for training
- No daily limits

---

## Recommendations for The Sovereign AI

| Use Case | Recommended Option |
|----------|-------------------|
| Agent J (Compressor) | Local Ollama `gemma4:26b` |
| Agent F (Auditor) | Local Ollama `gemma4:26b` |
| Agent K (Commander) | Cloud Gemini (faster) |
| Agent C (Hunter) | Cloud Gemini (research) |

---

## Important Notes
1. Gemma models are NOT listed in `gemini.list_models()` - they require separate Ollama setup for local use
2. For Cloud API, use the `gemma-4-26b-it` model name
3. Local Ollama models don't count against Gemini API quotas
4. Using local Gemma for sensitive data processing ensures complete privacy

---

<!-- Sovereign AI Metadata -->
```json
{
  "sovereign_metadata": {
    "topic": "ai_models",
    "subject": "gemma4_26b_guide",
    "last_researched_date": "2026-05-05",
    "route_used": "FULL",
    "version": 1
  }
}
```
