"""
Final production validation — brand attribution, hallucination guards,
review intelligence, confidence scoring.
"""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from pipeline import extract_brand, is_genuine_review, _BRAND_BLACKLIST, BRAND_NORMALISATION
from agent import MarketIntelligenceAgent

agent = MarketIntelligenceAgent()
total_pass = total_fail = 0

def chk(label, got, expected):
    global total_pass, total_fail
    ok = (got == expected)
    if ok: total_pass += 1
    else:  total_fail += 1
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok:
        print(f"         got      = {got!r}")
        print(f"         expected = {expected!r}")

print("=" * 60)
print("1. BRAND ATTRIBUTION")
print("-" * 60)

brand_cases = [
    ("HP Victus AMD Ryzen 7 Gaming Laptop",          "HP"),
    ("ASUS Vivobook 15 Intel Core i3",               "ASUS"),
    ("Dell Inspiron 15 3000 Intel Core i5",          "Dell"),
    ("Lenovo IdeaPad Slim 3 AMD Ryzen 5",            "Lenovo"),
    ("Samsung Galaxy Book2 Pro 360",                 "Samsung"),
    ("Apple MacBook Air M2 13 inch",                 "Apple"),
    ("boAt Rockerz 480 RGB Headphones",              "boAt"),
    ("Fire-Boltt Ninja Call Pro Smart Watch",        "Fire-Boltt"),
    ("Sony WH-CH520 Wireless Headphones",            "Sony"),
    ("Acer Aspire 3 Laptop Intel Celeron",           "Acer"),
    ("Ultra Smartwatch Bluetooth Calling T800",      "Ultra"),
    ("MARVIK Smart Watch for Kids",                  "MARVIK"),
    ("GOBOULT Fluid X Headphones",                   "GOBOULT"),
    ("Bouncefit D20 Y68 Fitness Band",               "Bouncefit"),
    ("TRIGGR Punkheadz Z1 Headphones",               "TRIGGR"),
    ("Caidea CNB100 Hiphop Headphones",              "Caidea"),
    ("PTron Studio Pro Headphones",                  "pTron"),
    ("Refurbished HP Elitebook 840 G3",              "HP"),
    ("Renewed Apple iPhone 13 128GB",                "Apple"),
    ("Premium Quality Wireless Earbuds",             "Unknown Brand"),
    ("Coming Soon New Smartwatch",                   "Unknown Brand"),
    ("Best Budget Laptop Under 30000",               "Unknown Brand"),
    ("F FERONS Wireless Headphone",                  "F FERONS"),
]

b_pass = b_fail = 0
for title, expected in brand_cases:
    got = extract_brand(title)
    ok = (got == expected)
    if ok: b_pass += 1; total_pass += 1
    else:  b_fail += 1; total_fail += 1
    status = "PASS" if ok else "FAIL"
    safe = title.encode('ascii', 'replace').decode('ascii')[:50]
    print(f"  [{status}] {got:25s} <- {safe}")
    if not ok:
        print(f"         expected = {expected!r}")
print(f"\n  Brand: {b_pass} pass, {b_fail} fail")

print()
print("2. FAKE REVIEW REJECTION")
print("-" * 60)

r_pass = r_fail = 0
review_cases = [
    ("Service: Device Setup",                        False),
    ("Only 2 left in stock",                         False),
    ("Coming soon",                                  False),
    ("Brand Installation included",                  False),
    ("FREE delivery by tomorrow",                    False),
    ("Amazon Pay ICICI card: 5% cashback",           False),
    ("Only 1 left in stock - order soon",            False),
    ("16GB RAM, 512GB SSD, 15.6 inch FHD display",  False),
    ("Warranty: 1 year manufacturer",                False),
    ("Great product, works perfectly as expected",   True),
    ("Battery life is excellent, very happy",        True),
    ("Poor build quality, broke after 2 weeks",      True),
    ("Comfortable to wear, good value for money",    True),
    ("Connectivity issues after 3 months, disappointed", True),
]
for text, expected in review_cases:
    got = is_genuine_review(text)
    ok = (got == expected)
    if ok: r_pass += 1; total_pass += 1
    else:  r_fail += 1; total_fail += 1
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] genuine={str(got):5s} <- {text[:55]}")
print(f"\n  Reviews: {r_pass} pass, {r_fail} fail")

print()
print("3. NO FAKE SENTIMENT WHEN NO REVIEWS")
print("-" * 60)

ri_empty = agent._build_review_intelligence(
    [{"reviews": []}, {"reviews": None}], {}
)
chk("No snippets -> top_complaints empty",   ri_empty["top_complaints"], [])
chk("No snippets -> top_praises empty",      ri_empty["top_praises"],    [])
chk("No snippets -> snippets empty",         ri_empty["snippets"],       [])
chk("No snippets -> note contains unavailable",
    "unavailable" in ri_empty["note"].lower(), True)

data_no_reviews = [
    {"product_name": "HP Laptop", "brand": "HP", "price": "Rs50000",
     "clean_price": 50000, "rating": 4.2, "review_count": 100,
     "reviews": [], "platform": "Amazon", "image_url": "http://x.com/img.jpg",
     "refurbished": False}
    for _ in range(5)
]
fake_strategy = {
    "customer_sentiment": "Customers love this product and rate it highly.",
    "review_intelligence": {"snippets": [], "top_complaints": [], "top_praises": [], "note": ""},
    "market_health": {"ai_confidence": "70%", "opportunity_score": "7/10",
                      "competition": "HIGH", "trend_momentum": "STRONG"},
    "executive_summary": "Test", "pricing_strategy": "Test pricing",
    "pricing_analysis": "Test analysis", "market_opportunities": "Test opp",
    "risks": "Test risks", "competitive_insights": "Test comp",
    "opportunities": "Test opp", "actionable_steps": ["Step 1"],
    "live_alerts": ["Alert 1"], "trends": ["Trend 1"], "reasoning": ["Reason 1"],
}
gemini_ri = fake_strategy.get("review_intelligence") or {}
fake_strategy["review_intelligence"] = agent._build_review_intelligence(data_no_reviews, gemini_ri)
if not fake_strategy["review_intelligence"]["snippets"]:
    fake_strategy["customer_sentiment"] = "Customer review text unavailable from source data."

chk("Hallucinated sentiment overridden when no snippets",
    fake_strategy["customer_sentiment"],
    "Customer review text unavailable from source data.")

print()
print("4. CONFIDENCE SCORING")
print("-" * 60)

conf_cases = [
    (5,  True,  True,  True,  True,  1, (60, 75)),
    (10, True,  True,  True,  True,  1, (70, 85)),
    (10, True,  True,  True,  True,  2, (70, 85)),
    (25, True,  True,  True,  True,  2, (80, 90)),
    (50, True,  True,  True,  True,  2, (90, 98)),
    (8,  False, False, True,  True,  1, (60, 75)),
]
for n, has_r, has_rc, has_img, has_brand, n_plat, (lo, hi) in conf_cases:
    platforms = ["Amazon"] * n if n_plat == 1 else ["Amazon"] * (n//2) + ["Flipkart"] * (n - n//2)
    data = [
        {
            "rating":       4.0 if has_r else None,
            "review_count": 100 if has_rc else None,
            "image_url":    "http://x.com/img.jpg" if has_img else None,
            "brand":        "HP" if has_brand else "Unknown Brand",
            "reviews":      [],
            "platform":     platforms[i],
        }
        for i in range(n)
    ]
    conf = agent._compute_confidence(data)
    val = int(conf.replace("%", ""))
    ok = lo <= val <= hi
    total_pass += ok; total_fail += (not ok)
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] n={n:2d} rated={has_r} rc={has_rc} plat={n_plat} -> {conf} (expected {lo}-{hi}%)")

print()
print("5. HALLUCINATION GUARDS")
print("-" * 60)

fake_alerts = ["Only 2 left in stock", "Coming Soon", "Delivery by tomorrow",
               "Service: Brand Setup", "Only few left"]
real_alerts = ["HP dominates with 5 of 8 products in mid-range segment",
               "Price clustering between Rs50000-55000 signals intense competition"]

filtered_fake = agent._filter_live_alerts(fake_alerts)
chk("All fake alerts removed -> fallback",
    filtered_fake, ["No significant market alerts detected."])

filtered_real = agent._filter_live_alerts(real_alerts)
chk("Real alerts preserved", len(filtered_real) == 2, True)

filtered_mixed = agent._filter_live_alerts(fake_alerts + real_alerts)
chk("Mixed: only real alerts kept", len(filtered_mixed) == 2, True)

strat_with_future = {
    "executive_summary": "In 2027 HP will dominate. Currently HP has 4 products.",
    "trends": ["AI laptops will grow in 2028", "Battery life improving now"],
    "live_alerts": ["By 2029 market will shift"],
    "pricing_strategy": "Price competitively.", "pricing_analysis": "Prices vary.",
    "market_opportunities": "Gap exists.", "risks": "Competition high.",
    "competitive_insights": "HP leads.", "customer_sentiment": "Good.",
    "opportunities": "Enter mid-range.",
}
cleaned = agent._strip_hallucinations(strat_with_future)
chk("Future year stripped from executive_summary",
    "2027" not in cleaned["executive_summary"], True)
chk("Future year stripped from trends",
    all("2028" not in t for t in cleaned["trends"]), True)

print()
print("6. VALIDATE STRATEGY FIELDS FALLBACKS")
print("-" * 60)

sparse = {"market_health": {"competition": "HIGH", "trend_momentum": "STRONG"}}
filled = agent._validate_strategy_fields(sparse)
chk("executive_summary fallback set",
    filled.get("executive_summary") == "Insufficient data available for reliable analysis.", True)
chk("live_alerts fallback set",
    filled.get("live_alerts") == ["No significant market alerts detected."], True)
chk("actionable_steps fallback set",
    isinstance(filled.get("actionable_steps"), list) and len(filled["actionable_steps"]) > 0, True)

print()
print("=" * 60)
print(f"TOTAL: {total_pass} passed, {total_fail} failed out of {total_pass + total_fail}")
if total_fail == 0:
    print("ALL VALIDATION TESTS PASSED")
else:
    print(f"WARNING: {total_fail} test(s) failed")
