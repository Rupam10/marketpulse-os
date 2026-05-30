"""
PHASE 1 VERIFICATION TEST
Calls scrapers directly. Prints raw product JSON before any Gemini analysis.
No data is modified or cleaned. This shows exactly what the scrapers return.
"""
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pipeline import MarketPulsePipeline

pipeline = MarketPulsePipeline()

queries = ["laptop", "headphone", "smartwatch"]

for keyword in queries:
    print("=" * 80)
    print(f"QUERY: {keyword}")
    print("=" * 80)
    
    raw_data = pipeline.fetch_live_data(keyword)
    
    print(f"\nTOTAL PRODUCTS SCRAPED: {len(raw_data)}")
    print("-" * 80)
    
    if len(raw_data) == 0:
        print(">>> NO PRODUCTS RETURNED. Scrapers returned empty. No fallback injected.")
    
    for i, product in enumerate(raw_data):
        print(f"\n--- PRODUCT {i+1} ---")
        print(f"  product_name : {product.get('product_name')}")
        print(f"  brand        : {product.get('brand')}")
        print(f"  price        : {product.get('price')}")
        print(f"  rating       : {product.get('rating')}")
        print(f"  discount     : {product.get('discount')}")
        print(f"  review_count : {product.get('review_count')}")
        print(f"  platform     : {product.get('platform')}")
        print(f"  image_url    : {product.get('image_url')}")
        print(f"  reviews      : {product.get('reviews')}")
    
    print(f"\n>>> RAW JSON DUMP:")
    print(json.dumps(raw_data, indent=2, ensure_ascii=False))
    print("\n")

print("=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
