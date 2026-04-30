"""
LLM Refiner Service — uses Google Gemini (gemini-1.5-flash) to polish:
  1. suggested_question  → clear, specific, answerable research question
  2. supporting_evidence → coherent 2-3 sentence summary paragraph

Falls back gracefully to raw values if:
  - GEMINI_API_KEY is not set in .env
  - The API call fails for any reason (network, quota, etc.)
"""
import json
import logging
import re

logger = logging.getLogger(__name__)

# Module-level Gemini client (lazy-initialised once)
_gemini_model = None
_gemini_tried = False


def _get_gemini(api_key: str):
    """Return a configured Gemini GenerativeModel, or None if unavailable."""
    global _gemini_model, _gemini_tried
    if _gemini_tried:
        return _gemini_model
    _gemini_tried = True

    if not api_key:
        logger.info("GEMINI_API_KEY not set — LLM refinement disabled, using template questions.")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.4,
                "top_p": 0.9,
                "max_output_tokens": 512,
            },
        )
        logger.info("Gemini LLM refiner initialised ✓")
    except Exception as e:
        logger.warning("Gemini setup failed — LLM refinement disabled: %s", e)
        _gemini_model = None

    return _gemini_model


def refine_gap(
    keywords: list[str],
    domain: str,
    raw_question: str,
    raw_evidence: list[str],
    gap_score: float,
    s_struct: float,
    s_sem: float,
    s_temp: float,
    api_key: str = "",
) -> dict:
    """
    Use Gemini to refine the suggested research question and supporting evidence
    for a single research gap.

    Returns:
        {
            "refined_question": str,   # clear, specific research question
            "refined_evidence": str,   # 2-3 sentence coherent evidence summary
            "llm_used": bool           # True if LLM was successfully used
        }
    """
    model = _get_gemini(api_key)

    # ── Fallback: no LLM available ──────────────────────────────────────────
    if model is None:
        return {
            "refined_question": raw_question,
            "refined_evidence": _simple_evidence_summary(raw_evidence),
            "llm_used": False,
        }

    # ── Determine dominant gap dimension ────────────────────────────────────
    gap_type_map = {
        "citation sparsity (the topic has very few citations)": s_struct,
        "semantic novelty (the topic is significantly different from the rest of the literature)": s_sem,
        "temporal recency (the topic has emerged very recently)": s_temp,
    }
    dominant_gap_type = max(gap_type_map, key=gap_type_map.get)  # type: ignore

    # ── Build prompt ────────────────────────────────────────────────────────
    evidence_text = (
        "\n".join(f"- {e}" for e in raw_evidence[:5])
        if raw_evidence
        else "No direct evidence sentences available."
    )

    prompt = f"""You are an expert academic research advisor. Your task is to refine the following automatically generated research gap analysis into clear, professional, and easily understandable language.

## Research Gap Information
- **Topic / Domain**: {domain}
- **Key Concepts**: {", ".join(keywords[:6])}
- **Gap Score**: {gap_score:.2f} (scale 0–1, higher = stronger gap)
- **Primary Gap Type**: {dominant_gap_type}
- **Citation Sparsity Score**: {s_struct:.2f}
- **Semantic Novelty Score**: {s_sem:.2f}
- **Temporal Recency Score**: {s_temp:.2f}

## Raw Research Question (needs refinement)
{raw_question}

## Raw Evidence Sentences from Papers
{evidence_text}

## Your Task
Produce a JSON response with exactly these two keys:

1. **"question"**: A single, well-formed research question that:
   - Is specific, clear, and directly answerable through future research
   - Naturally incorporates the key concepts
   - Reflects the dominant gap type ({dominant_gap_type})
   - Reads like a genuine academic research question (not robotic)
   - Is between 20 and 50 words long

2. **"evidence"**: A 2-3 sentence paragraph that:
   - Summarises WHY this is a research gap using the evidence provided
   - Explains what is missing or underexplored in plain English
   - Is coherent, flows naturally, and is easy for a non-expert to understand
   - Does NOT use bullet points — must be flowing prose

Respond with ONLY valid JSON. No markdown. No explanation outside the JSON.
Example format: {{"question": "...", "evidence": "..."}}"""

    # ── Call Gemini ─────────────────────────────────────────────────────────
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Strip markdown code fences if present
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

        parsed = json.loads(raw_text)
        refined_question = str(parsed.get("question", raw_question)).strip()
        refined_evidence_text = str(parsed.get("evidence", "")).strip()

        if not refined_question:
            refined_question = raw_question
        if not refined_evidence_text:
            refined_evidence_text = _simple_evidence_summary(raw_evidence)

        logger.info("LLM refined gap: domain='%s'", domain)
        return {
            "refined_question": refined_question,
            "refined_evidence": refined_evidence_text,
            "llm_used": True,
        }

    except Exception as e:
        logger.warning("Gemini refinement failed for domain '%s': %s", domain, e)
        return {
            "refined_question": raw_question,
            "refined_evidence": _simple_evidence_summary(raw_evidence),
            "llm_used": False,
        }


def _simple_evidence_summary(evidence: list[str]) -> str:
    """
    Fallback: join raw evidence sentences into a readable paragraph
    when the LLM is not available.
    """
    if not evidence:
        return "No supporting evidence sentences were found in the uploaded papers for this topic cluster."

    # Take up to 3 sentences, strip whitespace, join with spaces
    sentences = [s.strip().rstrip(".") for s in evidence[:3] if s.strip()]
    if not sentences:
        return "Supporting evidence could not be extracted from the papers."

    return ". ".join(sentences) + "."
