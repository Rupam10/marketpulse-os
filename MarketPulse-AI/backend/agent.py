"""
MarketPulse Agent — Production-grade Gemini intelligence.
Phases: Data quality, hallucination prevention, review validation,
        confidence scoring, field validation, error handling.
"""
import google.generativeai as genai
import json
import re
import time
import logging

log = logging.getLogger("marketpulse.agent")


class MarketIntelligenceAgent:
    def __init__(self):
        self.api_key = "AIzaSyC6A_0VNqCT5EIYMGE5WBuK_wSzGdNj0aU"
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    # ------------------------------------------------------------------
    # Gemini call with rate-limit retry + timeout guard
    # ------------------------------------------------------------------
    def _call_gemini(self, prompt: str, retries: int = 2) -> str:
        for attempt in range(retries + 1):
            try:
                resp = self.model.generate_content(prompt)
                return resp.text.strip()
            except Exception as e:
                err = str(e)
                if "429" in err and attempt < retries:
                    wait = 15 * (attempt + 1)
                    log.warning(f"[GEMINI] Rate limited. Waiting {wait}s (attempt {attempt+1})...")
                    time.sleep(wait)
                elif "timeout" in err.lower() and attempt < retries:
                    log.warning(f"[GEMINI] Timeout. Retrying (attempt {attempt+1})...")
                    time.sleep(5)
                else:
                    raise
        raise RuntimeError("Gemini retries exhausted")

    # ------------------------------------------------------------------
    # Issue 4 — Confidence score using spec formula exactly
    # confidence = (completeness * 0.35 + review * 0.25 + source * 0.20 + brand * 0.20)
    # Scaled to realistic ranges based on product count.
    # ------------------------------------------------------------------
    def _compute_confidence(self, cleaned_data: list) -> str:
        if not cleaned_data:
            return "0%"
        n = len(cleaned_data)

        # Base range by product count
        if n < 10:
            base, ceiling = 60, 75
        elif n < 25:
            base, ceiling = 70, 85
        elif n < 50:
            base, ceiling = 80, 90
        else:
            base, ceiling = 90, 98

        # Completeness score: how many products have all key fields
        complete = sum(
            1 for p in cleaned_data
            if p.get("rating") is not None
            and p.get("review_count") is not None
            and p.get("image_url")
            and p.get("brand") not in (None, "Unknown", "Unknown Brand")
        )
        completeness_score = complete / n

        # Review score: products with genuine review snippets
        with_reviews = sum(
            1 for p in cleaned_data
            if isinstance(p.get("reviews"), list) and len(p["reviews"]) > 0
        )
        review_score = with_reviews / n

        # Source score: diversity of platforms (1 source = 0.6, 2+ = 1.0)
        platforms = {p.get("platform") for p in cleaned_data if p.get("platform")}
        source_score = 1.0 if len(platforms) >= 2 else 0.6

        # Brand score: ratio of known (non-Unknown) brands
        known_brands = sum(
            1 for p in cleaned_data
            if p.get("brand") and p["brand"] not in ("Unknown", "Unknown Brand")
        )
        brand_score = known_brands / n

        # Spec formula
        raw = (
            completeness_score * 0.35
            + review_score      * 0.25
            + source_score      * 0.20
            + brand_score       * 0.20
        )

        # Map 0–1 raw score into the base–ceiling range
        total = round(base + raw * (ceiling - base))
        total = max(base, min(total, ceiling))
        return f"{total}%"

    # ------------------------------------------------------------------
    # Sanitise opportunity_score ("610/10" → "6.1/10")
    # ------------------------------------------------------------------
    @staticmethod
    def _sanitize_opportunity_score(raw: str) -> str:
        if not raw or raw == "N/A":
            return raw
        m = re.search(r"(\d+(?:\.\d+)?)", str(raw))
        if not m:
            return raw
        val = float(m.group(1))
        if val > 10:
            s = str(int(val))
            val = float(s[0] + "." + s[1:]) if len(s) > 1 else float(s)
        val = max(0.0, min(val, 10.0))
        formatted = f"{val:.1f}" if val != int(val) else f"{int(val)}"
        return f"{formatted}/10"

    # ------------------------------------------------------------------
    # Phase 1 — Insufficient data gate
    # ------------------------------------------------------------------
    @staticmethod
    def _has_sufficient_data(cleaned_data: list) -> tuple:
        """Returns (sufficient: bool, reason: str)."""
        if not cleaned_data:
            return False, "No products were scraped."
        valid_priced = [p for p in cleaned_data if (p.get("clean_price") or 0) > 0]
        if len(valid_priced) < 3:
            return False, (
                f"Only {len(valid_priced)} valid product(s) found. "
                "Insufficient data available for reliable analysis."
            )
        return True, ""

    # ------------------------------------------------------------------
    # Phase 6 — Validate every AI output field
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_strategy_fields(strategy: dict) -> dict:
        """Replace None/empty fields with honest fallbacks. Never blank UI."""
        fallback = "Insufficient data available for reliable analysis."
        for field in ["executive_summary", "pricing_strategy", "pricing_analysis",
                      "market_opportunities", "risks", "competitive_insights",
                      "customer_sentiment", "opportunities"]:
            val = strategy.get(field)
            if not val or (isinstance(val, str) and len(val.strip()) < 10):
                strategy[field] = fallback
        for lf in ["actionable_steps", "trends", "reasoning"]:
            val = strategy.get(lf)
            if not val or not isinstance(val, list) or len(val) == 0:
                strategy[lf] = [fallback]
        # Issue 3 — live_alerts gets its own honest fallback
        alerts = strategy.get("live_alerts")
        if not alerts or not isinstance(alerts, list) or len(alerts) == 0:
            strategy["live_alerts"] = ["No significant market alerts detected."]
        mh = strategy.get("market_health") or {}
        if mh.get("competition") not in ("HIGH", "MEDIUM", "LOW"):
            mh["competition"] = "N/A"
        if mh.get("trend_momentum") not in ("STRONG", "STABLE", "WEAK"):
            mh["trend_momentum"] = "N/A"
        strategy["market_health"] = mh
        return strategy

    # ------------------------------------------------------------------
    # Phase 1 — Strip hallucinated future-dated content
    # ------------------------------------------------------------------
    @staticmethod
    def _strip_hallucinations(strategy: dict) -> dict:
        future_pat = re.compile(r'\b20(2[6-9]|[3-9]\d)\b')

        def clean(text: str) -> str:
            if not text or not future_pat.search(text):
                return text
            sentences = re.split(r'(?<=[.!?])\s+', text)
            cleaned = [s for s in sentences if not future_pat.search(s)]
            return " ".join(cleaned).strip() or text

        for field in ["executive_summary", "pricing_strategy", "pricing_analysis",
                      "market_opportunities", "risks", "competitive_insights",
                      "customer_sentiment", "opportunities"]:
            if strategy.get(field):
                strategy[field] = clean(strategy[field])

        for lf in ["trends", "live_alerts", "reasoning", "actionable_steps"]:
            if isinstance(strategy.get(lf), list):
                strategy[lf] = [clean(t) for t in strategy[lf]
                                 if t and not future_pat.search(t)]
        return strategy

    # ------------------------------------------------------------------
    # Issue 3 — Filter fake market alerts (inventory/stock messages)
    # ------------------------------------------------------------------
    _FAKE_ALERT_PATTERNS = re.compile(
        r'(only \d+ left|left in stock|\bin stock\b|out of stock|coming soon|'
        r'limited stock|low stock|hurry|selling fast|almost gone|'
        r'only few left|last \d+ items?|order soon|'
        r'delivery|shipping|dispatch|arrives?|'
        r'service:|installation|setup|warranty|guarantee)',
        re.IGNORECASE
    )

    @classmethod
    def _filter_live_alerts(cls, alerts: list) -> list:
        """
        Issue 3 — Remove inventory/stock/delivery messages from market alerts.
        Keep only genuine market intelligence alerts.
        If nothing remains, return the honest fallback.
        """
        if not alerts or not isinstance(alerts, list):
            return ["No significant market alerts detected."]

        genuine = []
        for alert in alerts:
            if not alert or not isinstance(alert, str):
                continue
            if cls._FAKE_ALERT_PATTERNS.search(alert):
                continue
            # Must be a real market observation (price, competition, trend)
            if len(alert.strip()) < 15:
                continue
            genuine.append(alert.strip())

        return genuine if genuine else ["No significant market alerts detected."]

    # ------------------------------------------------------------------
    # Phase 2 — Review intelligence: only genuine snippets
    # ------------------------------------------------------------------
    @staticmethod
    def _build_review_intelligence(cleaned_data: list, gemini_ri: dict) -> dict:
        from pipeline import is_genuine_review
        all_snippets = []
        for p in cleaned_data:
            reviews = p.get("reviews") or []
            if isinstance(reviews, list):
                all_snippets.extend(r for r in reviews if is_genuine_review(r))

        if not all_snippets:
            return {
                "top_complaints": [],
                "top_praises":    [],
                "snippets":       [],
                "note": "Customer review data unavailable from source data.",
            }
        return {
            "top_complaints": gemini_ri.get("top_complaints") or [],
            "top_praises":    gemini_ri.get("top_praises") or [],
            "snippets":       all_snippets[:10],
            "note":           gemini_ri.get("note") or "",
        }

    # ------------------------------------------------------------------
    # Main strategy generation
    # ------------------------------------------------------------------
    def generate_strategy(self, cleaned_data: list, keyword: str) -> dict:
        log.info(f"[GEMINI] Generating intelligence for '{keyword}' ({len(cleaned_data)} products)")

        ai_confidence = self._compute_confidence(cleaned_data)

        _empty = {
            "category":            "General",
            "executive_summary":   None,
            "customer_sentiment":  None,
            "pricing_strategy":    None,
            "pricing_analysis":    None,
            "market_opportunities": None,
            "risks":               None,
            "competitive_insights": None,
            "opportunities":       None,
            "actionable_steps":    [],
            "market_health": {
                "ai_confidence":    "0%",
                "opportunity_score": "N/A",
                "competition":      "N/A",
                "trend_momentum":   "N/A",
            },
            "live_alerts":  [],
            "trends":       [],
            "reasoning":    [],
            "review_intelligence": {
                "top_complaints": [],
                "top_praises":    [],
                "snippets":       [],
                "note": "Customer review data unavailable from source data.",
            },
        }

        # Phase 1 — Insufficient data gate
        sufficient, reason = self._has_sufficient_data(cleaned_data)
        if not sufficient:
            log.warning(f"[GEMINI] Insufficient data: {reason}")
            result = dict(_empty)
            result["executive_summary"] = f"Insufficient data available for reliable analysis. {reason}"
            result["market_health"]["ai_confidence"] = ai_confidence
            return result

        # Build data summary
        product_summaries, all_reviews, scraped_brands = [], [], set()
        for p in cleaned_data:
            brand = p.get("brand") or "Unknown"
            scraped_brands.add(brand.lower())
            product_summaries.append({
                "title":        p.get("product_name"),
                "brand":        brand,
                "price":        p.get("price"),
                "clean_price":  p.get("clean_price"),
                "rating":       p.get("rating"),
                "review_count": p.get("review_count"),
                "platform":     p.get("platform"),
                "refurbished":  p.get("refurbished", False),
            })
            reviews = p.get("reviews") or []
            if isinstance(reviews, list):
                all_reviews.extend(reviews)

        review_note = (
            json.dumps(all_reviews[:15]) if all_reviews
            else "No review snippets available. Do NOT invent reviews."
        )
        scraped_brand_list = ", ".join(sorted(scraped_brands))

        # Issues 3, 5, 6 — Anti-hallucination + evidence-based + no fake alerts
        prompt = f"""
You are a B2B Market Intelligence AI. Analyze ONLY the data below.

STRICT RULES — VIOLATIONS WILL INVALIDATE THE ANALYSIS:
1. ONLY reference brands present in: {scraped_brand_list}
2. ONLY reference products in the scraped list below.
3. Do NOT use future years (2026+). Reference only current data.
4. If reviews are empty: set customer_sentiment to "Customer review data unavailable from source data."
5. Every insight MUST cite specific data: product count, average price, average rating, or review count.
   BAD: "HP shows strong market presence."
   GOOD: "HP appears in 4 products with average rating 4.2 and 2,200 total reviews."
6. Do NOT fabricate trends, prices, ratings, or market conditions.
7. opportunity_score format: "X.X/10" (e.g. "7.2/10"). Never "610/10".
8. live_alerts must ONLY contain genuine market intelligence:
   - Significant price changes, new competitor appearances, unusual market movements.
   - NEVER include: stock levels, inventory messages, "only X left", "coming soon",
     delivery info, installation info, or any ecommerce metadata.
   - If no real alert exists, return: ["No significant market alerts detected."]

Keyword: "{keyword}"
Products ({len(product_summaries)} scraped):
{json.dumps(product_summaries, indent=2)}

Reviews (real scraped text only):
{review_note}

Return ONLY a raw JSON object — no markdown, no code fences:

{{
  "category": "Single short category label",
  "executive_summary": "2-3 sentences citing specific product counts, prices, and ratings from the data.",
  "customer_sentiment": "From reviews only. If none: 'Customer review data unavailable from source data.'",
  "pricing_strategy": "2 sentences citing the actual min/max/avg price range from the data.",
  "pricing_analysis": "Describe the actual price distribution with specific price points from the data.",
  "market_opportunities": "1-2 sentences citing specific gaps or underserved segments visible in the data.",
  "risks": "1-2 sentences citing specific risks with data evidence (e.g. price concentration, brand dominance).",
  "competitive_insights": "1-2 sentences citing specific brand counts, ratings, and review volumes from the data.",
  "opportunities": "One-line opportunity citing a specific data observation.",
  "actionable_steps": ["Step citing data 1", "Step citing data 2", "Step citing data 3"],
  "market_health": {{
    "opportunity_score": "X.X/10",
    "competition": "HIGH or MEDIUM or LOW",
    "trend_momentum": "STRONG or STABLE or WEAK"
  }},
  "live_alerts": ["Real market alert from data only — NO stock/inventory/delivery messages"],
  "trends": ["Trend visible in the scraped data 1", "Trend visible in the scraped data 2"],
  "reasoning": ["Data-backed reason 1", "Data-backed reason 2", "Data-backed reason 3"],
  "review_intelligence": {{
    "top_complaints": [],
    "top_praises": [],
    "note": "State if review data was unavailable."
  }}
}}
"""

        try:
            text = self._call_gemini(prompt)
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            strategy = json.loads(text)

            # Phase 1 — Strip hallucinations
            strategy = self._strip_hallucinations(strategy)

            # Issue 3 — Filter fake market alerts (stock/inventory messages)
            strategy["live_alerts"] = self._filter_live_alerts(
                strategy.get("live_alerts", [])
            )

            # Inject computed confidence
            if "market_health" not in strategy:
                strategy["market_health"] = {}
            strategy["market_health"]["ai_confidence"] = ai_confidence
            strategy["market_health"]["opportunity_score"] = self._sanitize_opportunity_score(
                strategy["market_health"].get("opportunity_score", "N/A")
            )

            # Phase 2 — Build review intelligence from real snippets only
            gemini_ri = strategy.get("review_intelligence") or {}
            strategy["review_intelligence"] = self._build_review_intelligence(
                cleaned_data, gemini_ri)

            # Priority 3 — If no real review snippets exist, override customer_sentiment
            # regardless of what Gemini generated (it may have hallucinated sentiment)
            if not strategy["review_intelligence"]["snippets"]:
                strategy["customer_sentiment"] = "Customer review text unavailable from source data."

            # Phase 6 — Validate all fields are populated
            strategy = self._validate_strategy_fields(strategy)

            log.info(f"[GEMINI] Done. confidence={ai_confidence}, "
                     f"score={strategy['market_health']['opportunity_score']}, "
                     f"snippets={len(strategy['review_intelligence']['snippets'])}")
            return strategy

        except json.JSONDecodeError as e:
            log.error(f"[GEMINI] JSON parse error: {e}")
            result = dict(_empty)
            result["executive_summary"] = "AI analysis temporarily unavailable. Please try again."
            result["market_health"]["ai_confidence"] = ai_confidence
            return result
        except Exception as e:
            log.error(f"[GEMINI] Error: {e}")
            result = dict(_empty)
            result["executive_summary"] = "AI analysis temporarily unavailable. Please try again."
            result["market_health"]["ai_confidence"] = ai_confidence
            return result
