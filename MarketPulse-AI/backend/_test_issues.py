"""Targeted tests for the 6 critical bug fixes."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pipeline import is_genuine_review, extract_brand
from agent import MarketIntelligenceAgent

a = MarketIntelligenceAgent()
total_pass = total_fail = 0

def check(label, got, expected):
    global total_pass, total_fail
    ok = got == expected
    if ok: total_pass += 1
    else:  total_fail += 1
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok:
        print(f"         got={got!r}")
        print(f"         exp={expected!r}")

# -----------------------------------------------------------------------
print("=" * 60)
print("ISSUE 1: Fake Review Filtering")
print("-" * 60)

# Must reject
check("Service: Device Setup",
      is_genuine_review("Service: Device Setup"), False)
check("Only 2 left in stock",
      is_genuine_review("Only 2 left in stock"), False)
check("Coming soon",
      is_genuine_review("Coming soon"), False)
check("Brand Installation included",
      is_genuine_review("Brand Installation included"), False)
check("Model Number: XYZ-123-ABC",
      is_genuine_review("Model Number: XYZ-123-ABC"), False)
check("Seller: TechStore India",
      is_genuine_review("Seller: TechStore India"), False)
check("Delivery by Monday",
      is_genuine_review("Delivery by Monday"), False)
check("Only 1 left in stock - order soon",
      is_genuine_review("Only 1 left in stock - order soon"), False)
check("16GB RAM, 512GB SSD, 15.6 inch FHD display",
      is_genuine_review("16GB RAM, 512GB SSD, 15.6 inch FHD display"), False)

# Must accept
check("Great product, works perfectly as expected",
      is_genuine_review("Great product, works perfectly as expected"), True)
check("Battery life is excellent, very happy with purchase",
      is_genuine_review("Battery life is excellent, very happy with purchase"), True)
check("Poor build quality, broke after 2 weeks of use",
      is_genuine_review("Poor build quality, broke after 2 weeks of use"), True)
check("Comfortable to wear, good value for money",
      is_genuine_review("Comfortable to wear, good value for money"), True)
check("Connectivity issues after 3 months, disappointed",
      is_genuine_review("Connectivity issues after 3 months, disappointed"), True)

# -----------------------------------------------------------------------
print()
print("ISSUE 2: Fake Brand Blacklist")
print("-" * 60)

check("'Add' -> Unknown Brand",
      extract_brand("Add to Cart Samsung Galaxy"), "Samsung")
check("'Coming' -> not a brand",
      extract_brand("Coming Soon New Smartwatch"), "Unknown Brand")
check("'Electric' -> not a brand",
      extract_brand("Electric Scooter 250W Motor"), "Unknown Brand")
check("'New' -> not a brand",
      extract_brand("New Latest Bluetooth Speaker"), "Unknown Brand")
check("'Premium' -> not a brand",
      extract_brand("Premium Quality Wireless Earbuds"), "Unknown Brand")
check("'Best' -> not a brand",
      extract_brand("Best Budget Laptop Under 30000"), "Unknown Brand")
check("Real brand HP still works",
      extract_brand("HP Elitebook 840 G3 Laptop"), "HP")
check("Real brand Samsung still works",
      extract_brand("Samsung Galaxy S24 Ultra 5G"), "Samsung")
check("Real brand boAt still works",
      extract_brand("boAt Rockerz 480 Headphones"), "boAt")

# -----------------------------------------------------------------------
print()
print("ISSUE 3: Fake Market Alert Filtering")
print("-" * 60)

fake_alerts = [
    "Only 2 left in stock",
    "Only few left",
    "Coming Soon",
    "Delivery by tomorrow",
    "Installation included",
    "Service: Brand Setup",
]
real_alerts = [
    "HP dominates with 5 out of 8 products in the mid-range segment",
    "Price clustering between Rs 50,000-55,000 indicates intense competition",
    "New budget entrants from Acer and Lenovo gaining market share",
]

filtered_fake = a._filter_live_alerts(fake_alerts)
check("All fake alerts removed -> fallback",
      filtered_fake, ["No significant market alerts detected."])

filtered_real = a._filter_live_alerts(real_alerts)
check("Real alerts preserved",
      len(filtered_real) == 3, True)

filtered_mixed = a._filter_live_alerts(fake_alerts + real_alerts)
check("Mixed: only real alerts kept",
      len(filtered_mixed) == 3, True)

filtered_empty = a._filter_live_alerts([])
check("Empty list -> fallback",
      filtered_empty, ["No significant market alerts detected."])

# -----------------------------------------------------------------------
print()
print("ISSUE 4: Confidence Score Formula")
print("-" * 60)

# 8 products, all rated, all have review_count, all have images, known brands, no snippets
data_good = [
    {"rating": 4.0, "review_count": 100, "image_url": "http://x.com/img.jpg",
     "brand": "HP", "reviews": [], "platform": "Amazon"}
    for _ in range(8)
]
conf = a._compute_confidence(data_good)
val = int(conf.replace("%", ""))
check(f"8 products, good data -> {conf} in range 60-75%", 60 <= val <= 75, True)

# 15 products
data_15 = data_good * 2  # 16 products
conf15 = a._compute_confidence(data_15)
val15 = int(conf15.replace("%", ""))
check(f"16 products -> {conf15} in range 70-85%", 70 <= val15 <= 85, True)

# 0 products
check("0 products -> 0%", a._compute_confidence([]), "0%")

# Two sources increases source_score
data_two_sources = [
    {"rating": 4.0, "review_count": 100, "image_url": "http://x.com/img.jpg",
     "brand": "HP", "reviews": [], "platform": "Amazon" if i < 4 else "Flipkart"}
    for i in range(8)
]
conf_two = a._compute_confidence(data_two_sources)
conf_one = a._compute_confidence(data_good)  # all Amazon
check("Two sources gives higher confidence than one",
      int(conf_two.replace("%","")) >= int(conf_one.replace("%","")), True)

# -----------------------------------------------------------------------
print()
print("ISSUE 5: Evidence-based insights (prompt check)")
print("-" * 60)
# We can't run Gemini in tests, but we verify the prompt contains the citation requirement
import inspect
src = inspect.getsource(a.generate_strategy)
check("Prompt requires data citations",
      "cite specific" in src or "citing specific" in src or "citing data" in src, True)
check("Prompt forbids stock alerts",
      "only X left" in src or "stock/inventory" in src or "NO stock" in src, True)
check("Prompt requires evidence for insights",
      "product count" in src or "average rating" in src or "review count" in src, True)

# -----------------------------------------------------------------------
print()
print("ISSUE 6: Response quality — no hallucination fallbacks")
print("-" * 60)
check("_validate_strategy_fields sets live_alerts fallback",
      "No significant market alerts detected" in str(
          a._validate_strategy_fields({"market_health": {}})
      ), True)
check("_build_review_intelligence returns honest note when no snippets",
      "unavailable" in a._build_review_intelligence(
          [{"reviews": []}], {}
      )["note"].lower(), True)

# -----------------------------------------------------------------------
print()
print("=" * 60)
print(f"TOTAL: {total_pass} passed, {total_fail} failed out of {total_pass+total_fail}")
if total_fail == 0:
    print("ALL TESTS PASSED")
else:
    print(f"WARNING: {total_fail} test(s) failed")
