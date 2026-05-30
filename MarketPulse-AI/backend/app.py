"""
MarketPulse Flask API — Production-ready
Phases: Search Intelligence, Caching, Error Handling, Security, Scalability
"""
import json
import time
import hashlib
import logging
import traceback
import os
from functools import lru_cache
from flask import Flask, request, jsonify
from flask_cors import CORS
from pipeline import MarketPulsePipeline
from agent import MarketIntelligenceAgent

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("marketpulse")

app = Flask(__name__)

# CORS — allow both port 3000 and 3001 (React dev server can use either)
# Also allow 127.0.0.1 variants. In production, set ALLOWED_ORIGINS env var.
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
).split(",")
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=False)

# ---------------------------------------------------------------------------
# Phase 4 — In-memory response cache (TTL = 10 minutes)
# Keyed by normalised keyword. Prevents redundant scrape+AI calls.
# ---------------------------------------------------------------------------
_CACHE: dict = {}          # { cache_key: {"ts": float, "data": dict} }
CACHE_TTL_SECONDS = 600    # 10 minutes

def _cache_key(keyword: str) -> str:
    return hashlib.md5(keyword.lower().strip().encode()).hexdigest()

def _cache_get(keyword: str):
    key = _cache_key(keyword)
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL_SECONDS:
        log.info(f"[CACHE HIT] '{keyword}'")
        return entry["data"]
    return None

def _cache_set(keyword: str, data: dict):
    key = _cache_key(keyword)
    _CACHE[key] = {"ts": time.time(), "data": data}
    # Phase 9 — Evict oldest entries if cache grows too large
    if len(_CACHE) > 200:
        oldest = sorted(_CACHE.items(), key=lambda x: x[1]["ts"])[:50]
        for k, _ in oldest:
            _CACHE.pop(k, None)

# ---------------------------------------------------------------------------
# Phase 3 — Search Intelligence Engine
# Normalises queries, expands synonyms, classifies intent.
# ---------------------------------------------------------------------------
_QUERY_SYNONYMS = {
    # Product synonyms
    "fridge":           "refrigerator",
    "ac":               "air conditioner",
    "tv":               "television",
    "mobile":           "smartphone",
    "cell phone":       "smartphone",
    "earphones":        "earbuds",
    "headset":          "headphones",
    "notebook":         "laptop",
    "macbook":          "laptop apple",
    "iphone":           "smartphone apple",
    "pixel":            "smartphone google",
    "galaxy":           "smartphone samsung",
    # Industry / concept synonyms
    "ai":               "artificial intelligence",
    "ml":               "machine learning",
    "ev":               "electric vehicles",
    "evs":              "electric vehicles",
    "cloud":            "cloud computing",
    "saas":             "software as a service",
    "fintech":          "financial technology",
    "edtech":           "education technology",
    "healthtech":       "healthcare technology",
    "iot":              "internet of things",
}

# Queries that are industry/concept searches (not product searches)
# These get a different scraping strategy (broader terms)
_INDUSTRY_KEYWORDS = {
    "artificial intelligence", "machine learning", "electric vehicles",
    "cloud computing", "data science", "stock market", "digital marketing",
    "healthcare", "insurance", "fintech", "blockchain", "cryptocurrency",
    "renewable energy", "solar energy", "5g", "metaverse", "cybersecurity",
    "software as a service", "internet of things", "autonomous vehicles",
    "space technology", "biotechnology", "nanotechnology",
}

def normalise_query(raw: str) -> dict:
    """
    Phase 3 — Normalise and classify the user's search query.
    Returns: { keyword, original, is_industry, search_terms }
    """
    cleaned = raw.strip().lower()
    # Apply synonym expansion
    expanded = _QUERY_SYNONYMS.get(cleaned, cleaned)
    # Classify intent
    is_industry = expanded in _INDUSTRY_KEYWORDS or any(
        ind in expanded for ind in _INDUSTRY_KEYWORDS
    )
    # For industry searches, append "market" to get better product results
    search_terms = expanded if not is_industry else f"{expanded} products"
    return {
        "keyword":      raw.strip(),
        "normalised":   expanded,
        "is_industry":  is_industry,
        "search_terms": search_terms,
    }

# ---------------------------------------------------------------------------
# Phase 8 — Input validation
# ---------------------------------------------------------------------------
def _validate_keyword(keyword: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if not keyword or not keyword.strip():
        return False, "Keyword is required."
    if len(keyword) > 200:
        return False, "Keyword too long. Maximum 200 characters."
    # Phase 8 — Basic prompt injection protection
    injection_patterns = [
        "ignore previous", "ignore all", "system prompt", "jailbreak",
        "act as", "you are now", "forget your", "disregard",
    ]
    kw_lower = keyword.lower()
    for pattern in injection_patterns:
        if pattern in kw_lower:
            return False, "Invalid search query."
    return True, ""

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.route("/api/analyze", methods=["POST"])
def analyze_market():
    start_time = time.time()
    try:
        body = request.get_json(silent=True)
        if not body:
            return jsonify({"status": "error", "message": "Invalid JSON body."}), 400

        raw_keyword = (body.get("keyword") or "").strip()

        # Phase 8 — Input validation
        valid, err = _validate_keyword(raw_keyword)
        if not valid:
            return jsonify({"status": "error", "message": err}), 400

        # Phase 3 — Query normalisation
        query_info = normalise_query(raw_keyword)
        keyword      = query_info["keyword"]
        search_terms = query_info["search_terms"]
        is_industry  = query_info["is_industry"]

        log.info(f"→ Analyze: '{keyword}' | normalised='{search_terms}' | industry={is_industry}")

        # Phase 4 — Cache check
        cached = _cache_get(search_terms)
        if cached:
            cached["_cached"] = True
            cached["_response_ms"] = round((time.time() - start_time) * 1000)
            return jsonify(cached)

        pipeline = MarketPulsePipeline()
        agent    = MarketIntelligenceAgent()

        # Scrape
        raw_data = pipeline.fetch_live_data(search_terms)
        cleaned_data = pipeline.process_and_clean_data(raw_data)

        log.info(f"   Scraped: {len(raw_data)} raw → {len(cleaned_data)} valid")

        if not cleaned_data:
            # Phase 5 — Graceful no-data response
            response = {
                "status":   "no_data",
                "keyword":  keyword,
                "category": "General",
                "message":  (
                    f"No product data found for '{keyword}'. "
                    "The scrapers returned empty results. "
                    "Try a more specific product name or check back later."
                ),
                "source_counts":     getattr(pipeline, "source_counts", {}),
                "raw_product_count": len(raw_data),
                "_response_ms":      round((time.time() - start_time) * 1000),
            }
            return jsonify(response)

        # AI intelligence
        strategy = agent.generate_strategy(cleaned_data, keyword)
        category = strategy.pop("category", "General")

        brand_chart_data = _aggregate_brands(cleaned_data)
        source_counts    = getattr(pipeline, "source_counts", {})

        response = {
            "status":        "success",
            "keyword":       keyword,
            "category":      category,
            "product_count": len(cleaned_data),
            "source_counts": source_counts,
            "market_data":   cleaned_data,
            "brand_chart":   brand_chart_data,
            "ai_strategy":   strategy,
            "_cached":       False,
            "_response_ms":  round((time.time() - start_time) * 1000),
        }

        # Phase 4 — Cache successful response
        _cache_set(search_terms, response)

        log.info(f"✅ Done in {response['_response_ms']}ms | "
                 f"products={len(cleaned_data)} | category={category}")
        return jsonify(response)

    except Exception as e:
        # Phase 5 — Never expose stack traces to client
        log.error(f"❌ Analyze error: {e}\n{traceback.format_exc()}")
        return jsonify({
            "status":  "error",
            "message": "An internal error occurred. Please try again.",
        }), 500


@app.route("/api/raw", methods=["POST"])
def raw_scrape():
    """Verification/debug endpoint — raw scraped JSON without Gemini."""
    try:
        body = request.get_json(silent=True)
        if not body:
            return jsonify({"status": "error", "message": "Invalid JSON body."}), 400

        keyword = (body.get("keyword") or "").strip()
        valid, err = _validate_keyword(keyword)
        if not valid:
            return jsonify({"status": "error", "message": err}), 400

        query_info = normalise_query(keyword)
        pipeline   = MarketPulsePipeline()
        raw_data   = pipeline.fetch_live_data(query_info["search_terms"])
        cleaned    = pipeline.process_and_clean_data(raw_data)

        return jsonify({
            "keyword":       keyword,
            "search_terms":  query_info["search_terms"],
            "is_industry":   query_info["is_industry"],
            "raw_count":     len(raw_data),
            "valid_count":   len(cleaned),
            "source_counts": getattr(pipeline, "source_counts", {}),
            "products":      cleaned,
        })
    except Exception as e:
        log.error(f"❌ Raw scrape error: {e}")
        return jsonify({"status": "error", "message": "Scrape failed. Please try again."}), 500


@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    """Admin endpoint to clear the response cache."""
    _CACHE.clear()
    return jsonify({"status": "ok", "message": "Cache cleared."})


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status":       "healthy",
        "cache_entries": len(_CACHE),
        "version":      "2.0.0",
    })


# ---------------------------------------------------------------------------
# Brand aggregation for chart data
# ---------------------------------------------------------------------------
def _aggregate_brands(products: list) -> list:
    brand_map = {}
    for p in products:
        brand = p.get("brand") or "Unknown"
        if brand not in brand_map:
            brand_map[brand] = {
                "brand":         brand,
                "prices":        [],
                "ratings":       [],
                "review_counts": [],
                "product_count": 0,
            }
        brand_map[brand]["prices"].append(p.get("clean_price") or 0)
        brand_map[brand]["product_count"] += 1
        if p.get("rating") is not None:
            brand_map[brand]["ratings"].append(p["rating"])
        if p.get("review_count") is not None:
            brand_map[brand]["review_counts"].append(p["review_count"])

    result = []
    for brand, d in brand_map.items():
        prices  = d["prices"]
        ratings = d["ratings"]
        result.append({
            "brand":         brand,
            "avg_price":     round(sum(prices) / len(prices)) if prices else 0,
            "avg_rating":    round(sum(ratings) / len(ratings), 1) if ratings else None,
            "total_reviews": sum(d["review_counts"]) if d["review_counts"] else None,
            "product_count": d["product_count"],
        })

    result.sort(key=lambda x: x["avg_price"], reverse=True)
    return result


if __name__ == "__main__":
    log.info("🚀 MarketPulse Backend starting on port 5000...")
    # host='0.0.0.0' binds to all interfaces (IPv4 + IPv6) so both
    # http://localhost:5000 and http://127.0.0.1:5000 work from the browser.
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5000, threaded=True)
