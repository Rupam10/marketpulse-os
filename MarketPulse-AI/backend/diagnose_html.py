"""
HTML STRUCTURE DIAGNOSTIC
Fetches real HTML from Amazon and Flipkart via Bright Data.
Prints element structures to identify correct CSS selectors.
"""
import requests
import urllib3
import sys
import io
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BRD_USER = "brd-customer-hl_726e4b2c-zone-web_unlocker1"
BRD_PASS = "m8m9yijgj02c"
PROXY = f"http://{BRD_USER}:{BRD_PASS}@brd.superproxy.io:33335"
PROXIES = {"http": PROXY, "https": PROXY}

# ========================
# AMAZON DIAGNOSTIC
# ========================
print("=" * 80)
print("AMAZON.IN DIAGNOSTIC — keyword: laptop")
print("=" * 80)

try:
    resp = requests.get("https://www.amazon.in/s?k=laptop", proxies=PROXIES, verify=False, timeout=20)
    soup = BeautifulSoup(resp.content, 'html.parser')
    results = soup.find_all('div', {'data-component-type': 's-search-result'})
    print(f"Total search result divs found: {len(results)}")
    
    for i, item in enumerate(results[:3]):
        print(f"\n--- AMAZON RESULT {i+1} ---")
        
        # Title
        h2 = item.find('h2')
        print(f"  TITLE h2: {h2.text.strip()[:60] if h2 else 'NOT FOUND'}...")
        
        # Product link
        h2_link = h2.find('a') if h2 else None
        href = h2_link.get('href', '') if h2_link else ''
        print(f"  PRODUCT URL: {'https://www.amazon.in' + href[:80] if href else 'NOT FOUND'}...")
        
        # Price
        price = item.find('span', {'class': 'a-price-whole'})
        print(f"  PRICE: {price.text.strip() if price else 'NOT FOUND'}")
        
        # Original price (MRP)
        orig_price = item.find('span', {'class': 'a-price a-text-price'})
        if orig_price:
            orig_offscreen = orig_price.find('span', {'class': 'a-offscreen'})
            print(f"  ORIGINAL PRICE: {orig_offscreen.text.strip() if orig_offscreen else 'NOT FOUND'}")
        else:
            print(f"  ORIGINAL PRICE: NOT FOUND")
        
        # Rating - method 1: a-icon-alt
        rating_alt = item.find('span', {'class': 'a-icon-alt'})
        print(f"  RATING (a-icon-alt): {rating_alt.text.strip() if rating_alt else 'NOT FOUND'}")
        
        # Rating - method 2: aria-label on star icon
        star_icon = item.find('i', {'class': 'a-icon-star-small'})
        if star_icon:
            star_span = star_icon.find('span', {'class': 'a-icon-alt'})
            print(f"  RATING (star-small > alt): {star_span.text.strip() if star_span else 'NOT FOUND'}")
        
        # Review count - method 1: a-size-base s-underline-text
        review_link = item.find('span', {'class': 'a-size-base s-underline-text'})
        print(f"  REVIEWS (a-size-base): {review_link.text.strip() if review_link else 'NOT FOUND'}")
        
        # Review count - method 2: look for link with #customerReviews
        rev_a = item.find('a', href=lambda h: h and '#customerReviews' in h if h else False)
        if rev_a:
            rev_span = rev_a.find('span')
            print(f"  REVIEWS (#customerReviews link): {rev_span.text.strip() if rev_span else rev_a.text.strip()}")
        
        # Discount percentage
        discount_span = item.find('span', string=lambda t: t and '% off' in t if t else False)
        if not discount_span:
            discount_span = item.find('span', {'class': 'a-letter-space'})
            if discount_span:
                discount_span = discount_span.find_next_sibling('span')
        print(f"  DISCOUNT: {discount_span.text.strip() if discount_span else 'NOT FOUND'}")
        
        # Image
        img = item.find('img', {'class': 's-image'})
        print(f"  IMAGE: {img['src'][:80] if img else 'NOT FOUND'}...")

except Exception as e:
    print(f"AMAZON ERROR: {e}")

# ========================
# FLIPKART DIAGNOSTIC
# ========================
print("\n\n" + "=" * 80)
print("FLIPKART DIAGNOSTIC — keyword: laptop")
print("=" * 80)

try:
    resp = requests.get("https://www.flipkart.com/search?q=laptop", proxies=PROXIES, verify=False, timeout=20)
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    # Try many known Flipkart container classes
    selector_attempts = [
        ('div._1sdMkc', soup.find_all('div', {'class': '_1sdMkc'})),
        ('div.cPHDOP', soup.find_all('div', {'class': 'cPHDOP'})),
        ('div._1AtVbE', soup.find_all('div', {'class': '_1AtVbE'})),
        ('div.tUxRFH', soup.find_all('div', {'class': 'tUxRFH'})),
        ('div.slAVV4', soup.find_all('div', {'class': 'slAVV4'})),
        ('a.CGtC98', soup.find_all('a', {'class': 'CGtC98'})),
        ('div.KzDlHZ', soup.find_all('div', {'class': 'KzDlHZ'})),
        ('div._75nlfW', soup.find_all('div', {'class': '_75nlfW'})),
        ('div.yKfJKb', soup.find_all('div', {'class': 'yKfJKb'})),
    ]
    
    print("\nSELECTOR SCAN:")
    for name, elems in selector_attempts:
        print(f"  {name}: {len(elems)} found")
    
    # Also try data-id attribute
    data_id_divs = soup.find_all('div', attrs={'data-id': True})
    print(f"  div[data-id]: {len(data_id_divs)} found")
    
    # Find ALL divs that contain both a product title-like text and a price
    # Look for common price pattern ₹
    all_price_divs = soup.find_all(string=lambda t: t and '₹' in t if t else False)
    print(f"\n  Elements containing ₹: {len(all_price_divs)}")
    
    # Print first few parent structures with prices
    print("\n--- FLIPKART: ELEMENTS WITH ₹ (first 5 unique parents) ---")
    seen_parents = set()
    count = 0
    for price_text in all_price_divs:
        parent = price_text.parent
        if parent and id(parent) not in seen_parents and count < 5:
            seen_parents.add(id(parent))
            classes = parent.get('class', [])
            tag = parent.name
            print(f"\n  TAG: <{tag}> CLASS: {classes}")
            print(f"  TEXT: {parent.text.strip()[:100]}")
            # Look up 3 levels for a product card container
            grandparent = parent.parent
            if grandparent:
                gp_classes = grandparent.get('class', [])
                print(f"  PARENT TAG: <{grandparent.name}> CLASS: {gp_classes}")
                great_gp = grandparent.parent
                if great_gp:
                    ggp_classes = great_gp.get('class', [])
                    print(f"  GRANDPARENT TAG: <{great_gp.name}> CLASS: {ggp_classes}")
            count += 1
    
    # Try to find product cards by looking for elements with rating patterns
    rating_divs = soup.find_all('div', string=lambda t: t and len(t.strip()) <= 4 and '.' in t.strip() if t else False)
    print(f"\n--- FLIPKART: Possible rating elements: {len(rating_divs)} ---")
    for rd in rating_divs[:5]:
        classes = rd.get('class', [])
        print(f"  <div class='{classes}'> text='{rd.text.strip()}'")
    
    # Try span ratings too
    rating_spans = soup.find_all('span', string=lambda t: t and len(t.strip()) <= 4 and '.' in t.strip() if t else False)
    print(f"\n--- FLIPKART: Possible rating spans: {len(rating_spans)} ---")
    for rs in rating_spans[:5]:
        classes = rs.get('class', [])
        print(f"  <span class='{classes}'> text='{rs.text.strip()}'")
    
    # Find all <a> tags that look like product links
    product_links = soup.find_all('a', href=lambda h: h and '/p/' in h if h else False)
    print(f"\n--- FLIPKART: Product links (/p/ pattern): {len(product_links)} ---")
    for pl in product_links[:3]:
        classes = pl.get('class', [])
        title_text = pl.get('title', pl.text.strip()[:60])
        print(f"  <a class='{classes}' title='{title_text}'>")
        print(f"    href: {pl['href'][:80]}...")
    
    # Try finding by img tags with product images
    imgs = soup.find_all('img', {'class': lambda c: c and any(x in str(c) for x in ['DByuf4', '_396cs4', 'DByuf4'])}) 
    if not imgs:
        imgs = soup.find_all('img', src=lambda s: s and 'rukminim' in s if s else False)
    print(f"\n--- FLIPKART: Product images (rukminim): {len(imgs)} ---")
    for im in imgs[:3]:
        classes = im.get('class', [])
        print(f"  <img class='{classes}' src='{im.get('src', '')[:80]}'>")
    
    # Save raw HTML for deeper inspection if needed
    with open('flipkart_debug.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify()[:50000])
    print("\n[Saved first 50KB of Flipkart HTML to flipkart_debug.html]")

except Exception as e:
    print(f"FLIPKART ERROR: {e}")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
