"""
MarketPulse Pipeline — Production-grade scraper
Issues fixed: Flipkart 400, fake reviews, brand extraction,
              review count K+ parsing, source transparency, diagnostics.
"""
import re
import hashlib
import requests
import urllib3
import concurrent.futures
from collections import Counter
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# ISSUE 2 — Promotional / non-review text patterns to reject
# ---------------------------------------------------------------------------
_PROMO_PATTERNS = re.compile(
    r'(free delivery|amazon pay|icici|hdfc|sbi|axis bank|cashback|\bemi\b|no cost emi|'
    r'bought in past|people bought|bought last|delivery by|arrives by|'
    r'ships from|sold by|fulfilled by|\bprime\b|sponsored|\bad\b|advertisement|'
    r'get it by|fastest delivery|extra \d+%|bank offer|instant discount|'
    r'coupon|promo|deal of the day|lightning deal|limited time|'
    r'save \d+|off on|% off|\d+ off|flat \d+|'
    # Issue 1 — Additional non-review patterns (stock, install, setup, metadata)
    r'only \d+ left|left in stock|\bin stock\b|out of stock|coming soon|'
    r'\bservice\s*:|brand installation|installation included|device setup|'
    r'setup included|sold by|dispatched by|fulfilled by amazon|'
    r'add to cart|buy now|check price|see details|'
    r'technical details|product description|about this item|'
    r'what\'s in the box|in the box|package contents|'
    r'warranty|guarantee|return policy|exchange policy|'
    r'model number|model no|part number|asin\b|'
    r'seller:|ships from:|brand:|colour:|color:|size:|weight:|'
    r'compatible with|works with|designed for)',
    re.IGNORECASE
)

_MIN_REVIEW_LENGTH = 25   # raised from 20 — short texts are rarely genuine reviews
_MAX_REVIEW_LENGTH = 500

# Issue 1 — Opinion words that must appear in a genuine review
_OPINION_WORDS = re.compile(
    r'\b(good|great|bad|poor|excellent|terrible|amazing|awful|love|hate|'
    r'recommend|worth|value|quality|works|broke|issue|issues|problem|problems|'
    r'perfect|disappointed|satisfied|happy|unhappy|fast|slow|easy|difficult|'
    r'comfortable|uncomfortable|durable|fragile|nice|horrible|best|worst|'
    r'reliable|unreliable|sturdy|flimsy|accurate|inaccurate|responsive|'
    r'loud|quiet|bright|dim|heavy|light|smooth|rough|solid|weak|'
    r'impressive|disappointing|overpriced|affordable|cheap|expensive|'
    r'worth it|not worth|highly recommend|do not recommend|waste of money|'
    r'value for money|good buy|bad buy|regret|happy with|unhappy with)\b',
    re.IGNORECASE
)

def is_genuine_review(text: str) -> bool:
    """
    Issue 1 — Strict review validation.
    Accept only genuine customer feedback. Reject all marketplace metadata,
    stock messages, installation info, product specs, and seller text.
    """
    if not text:
        return False
    text = text.strip()

    # Length bounds
    if len(text) < _MIN_REVIEW_LENGTH or len(text) > _MAX_REVIEW_LENGTH:
        return False

    # Reject promotional/metadata/stock/install patterns
    if _PROMO_PATTERNS.search(text):
        return False

    # Must contain at least 4 alphabetic words of length >= 3
    words = re.findall(r'[a-zA-Z]{3,}', text)
    if len(words) < 4:
        return False

    # Must contain at least one opinion/sentiment word
    if not _OPINION_WORDS.search(text):
        return False

    # Reject if it looks like a product spec (high ratio of numbers/units)
    spec_pattern = re.compile(
        r'\b(\d+\s*(gb|tb|mb|mhz|ghz|inch|cm|mm|kg|g|w|v|mah|rpm|hz|mp|fps|ms)\b)',
        re.IGNORECASE
    )
    spec_matches = len(spec_pattern.findall(text))
    if spec_matches >= 3:  # 3+ spec units = likely a product description
        return False

    return True

# ---------------------------------------------------------------------------
# ISSUE 3 — Brand normalisation map (extended with tech/IoT brands)
# ---------------------------------------------------------------------------
BRAND_NORMALISATION = {
    # IoT / microcontrollers — ESP32 titles start with chip names, not brand names
    "esp32":            "Espressif",
    "esp8266":          "Espressif",
    "esp-wroom":        "Espressif",
    "esp-wrover":       "Espressif",
    "nodemcu":          "NodeMCU",
    "arduino":          "Arduino",
    "raspberry":        "Raspberry Pi",
    "raspberry pi":     "Raspberry Pi",
    "stm32":            "STMicroelectronics",
    "atmega":           "Microchip",
    "pic":              "Microchip",
    # Fashion / apparel
    "the indian garage": "The Indian Garage Co",
    "indian garage":    "The Indian Garage Co",
    "u turn":           "U TURN",
    "uturn":            "U TURN",
    "w for woman":      "W For Woman",
    "biba":             "BIBA",
    "fabindia":         "FabIndia",
    "raymond":          "Raymond",
    "peter england":    "Peter England",
    "van heusen":       "Van Heusen",
    "allen solly":      "Allen Solly",
    "louis philippe":   "Louis Philippe",
    "arrow":            "Arrow",
    "park avenue":      "Park Avenue",
    # Electronics
    "hp":               "HP",
    "dell":             "Dell",
    "lenovo":           "Lenovo",
    "asus":             "ASUS",
    "acer":             "Acer",
    "apple":            "Apple",
    "samsung":          "Samsung",
    "sony":             "Sony",
    "lg":               "LG",
    "mi":               "Xiaomi",
    "xiaomi":           "Xiaomi",
    "realme":           "Realme",
    "oneplus":          "OnePlus",
    "one plus":         "OnePlus",
    "oppo":             "OPPO",
    "vivo":             "Vivo",
    "motorola":         "Motorola",
    "nokia":            "Nokia",
    "boat":             "boAt",
    "boAt":             "boAt",
    "noise":            "Noise",
    "fire-boltt":       "Fire-Boltt",
    "fireboltt":        "Fire-Boltt",
    "fastrack":         "Fastrack",
    "zebronics":        "Zebronics",
    "ptron":            "pTron",
    "jbl":              "JBL",
    "bose":             "Bose",
    "sennheiser":       "Sennheiser",
    "skullcandy":       "Skullcandy",
    "anker":            "Anker",
    "logitech":         "Logitech",
    "razer":            "Razer",
    "corsair":          "Corsair",
    "intel":            "Intel",
    "amd":              "AMD",
    "nvidia":           "NVIDIA",
    "wd":               "Western Digital",
    "western digital":  "Western Digital",
    "seagate":          "Seagate",
    "kingston":         "Kingston",
    "sandisk":          "SanDisk",
    "tp-link":          "TP-Link",
    "tplink":           "TP-Link",
    "netgear":          "Netgear",
    "d-link":           "D-Link",
    # Appliances
    "whirlpool":        "Whirlpool",
    "godrej":           "Godrej",
    "voltas":           "Voltas",
    "daikin":           "Daikin",
    "havells":          "Havells",
    "philips":          "Philips",
    "bajaj":            "Bajaj",
    "prestige":         "Prestige",
    "pigeon":           "Pigeon",
    # Beauty
    "lakme":            "Lakmé",
    "maybelline":       "Maybelline",
    "loreal":           "L'Oréal",
    "l'oreal":          "L'Oréal",
    "nivea":            "Nivea",
    "dove":             "Dove",
    "himalaya":         "Himalaya",
    "mamaearth":        "Mamaearth",
    "biotique":         "Biotique",
    # Food
    "lays":             "Lay's",
    "lay's":            "Lay's",
    "haldiram":         "Haldiram's",
    "haldirams":        "Haldiram's",
    "britannia":        "Britannia",
    "amul":             "Amul",
    "nestle":           "Nestlé",
    "maggi":            "Maggi",
    "parle":            "Parle",
    "cadbury":          "Cadbury",
    "pringles":         "Pringles",
    "doritos":          "Doritos",
    # Misc brands seen in Indian e-commerce
    "f ferons":         "F FERONS",
    "ferons":           "F FERONS",
    "gemfly":           "GEMFLY",
    "caidea":           "Caidea",
    "triggr":           "TRIGGR",
    "goboult":          "GOBOULT",
    "marvik":           "MARVIK",
    "bouncefit":        "Bouncefit",
    "ultra":            "Ultra",
    "fire-boltt":       "Fire-Boltt",
    # Laptop brands not previously in map
    "msi":              "MSI",
    "gigabyte":         "Gigabyte",
    "huawei":           "Huawei",
    "honor":            "Honor",
    "infinix":          "Infinix",
    "avita":            "AVITA",
    "chuwi":            "CHUWI",
    "primebook":        "Primebook",
    "wings":            "Wings",
    "motorola":         "Motorola",
}

MULTI_WORD_BRANDS = sorted(
    [k for k in BRAND_NORMALISATION if " " in k],
    key=lambda x: -len(x)
)

# Fix 1 — Generic words that are NOT brands.
# IMPORTANT: Only include words that are NEVER a brand name.
# Do NOT include words like "ultra", "smart", "wireless", "pro", "mini", "max",
# "plus", "digital", "bluetooth" — these appear as real brand names in product titles.
_BRAND_BLACKLIST = {
    "add", "coming", "new", "latest", "best", "premium",
    "offer", "sale", "top",
    "buy", "get", "the", "a", "an", "for", "with", "and", "or",
    "imported", "generic", "unbranded", "local", "china",
    "combo", "pack", "set", "kit", "bundle", "deal",
    "easy", "simple", "basic", "standard", "classic",
    "original", "genuine", "official", "certified",
    "budget", "affordable", "cheap", "expensive", "luxury", "economy",
    "type", "model", "version", "edition", "generation",
    "updated", "upgraded", "improved", "enhanced",
    "quality", "value", "hot", "cool", "fast", "quick",
}

# ---------------------------------------------------------------------------
# Unicode Mathematical Bold decoder
# ---------------------------------------------------------------------------
def _decode_mathematical_bold(text: str) -> str:
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x1D400 <= cp <= 0x1D419:
            result.append(chr(cp - 0x1D400 + ord('A')))
        elif 0x1D41A <= cp <= 0x1D433:
            result.append(chr(cp - 0x1D41A + ord('a')))
        elif 0x1D468 <= cp <= 0x1D481:
            result.append(chr(cp - 0x1D468 + ord('A')))
        elif 0x1D482 <= cp <= 0x1D49B:
            result.append(chr(cp - 0x1D482 + ord('a')))
        elif 0x1D5D4 <= cp <= 0x1D5ED:
            result.append(chr(cp - 0x1D5D4 + ord('A')))
        elif 0x1D5EE <= cp <= 0x1D607:
            result.append(chr(cp - 0x1D5EE + ord('a')))
        elif 0x1D63C <= cp <= 0x1D655:
            result.append(chr(cp - 0x1D63C + ord('A')))
        elif 0x1D656 <= cp <= 0x1D66F:
            result.append(chr(cp - 0x1D656 + ord('a')))
        else:
            result.append(ch)
    return "".join(result)

# ---------------------------------------------------------------------------
# ISSUE 3 — Robust brand extraction
# ---------------------------------------------------------------------------
def extract_brand(title: str) -> str:
    if not title:
        return "Unknown"

    NON_BRAND_PREFIXES = {
        "refurbished", "renewed", "certified", "new", "used", "open",
        "box", "pre-owned", "preowned", "imported", "original", "genuine",
        "official", "brand", "combo", "pack", "set", "buy",
    }

    # Step 1: Strip Mathematical Bold unicode
    title_clean = re.sub(r'[\U0001D400-\U0001D7FF]', '', title).strip()
    if len(title_clean) < len(title) * 0.3:
        title_clean = title

    title_lower = title_clean.lower().strip()
    words = title_lower.split()
    while words and words[0] in NON_BRAND_PREFIXES:
        words = words[1:]
    if not words:
        return "Unknown"
    stripped_lower = " ".join(words)

    # Step 2: Multi-word prefix match
    for prefix in MULTI_WORD_BRANDS:
        if stripped_lower.startswith(prefix):
            return BRAND_NORMALISATION[prefix]

    # Step 3: Single-word normalisation
    first_word = words[0]
    if first_word in BRAND_NORMALISATION:
        return BRAND_NORMALISATION[first_word]

    # Step 4: Scan first 5 words
    for w in words[:5]:
        if w in BRAND_NORMALISATION:
            return BRAND_NORMALISATION[w]

    # Step 5: Decode Mathematical Bold and retry
    decoded = _decode_mathematical_bold(title)
    decoded_lower = decoded.lower().strip()
    decoded_words = decoded_lower.split()
    while decoded_words and decoded_words[0] in NON_BRAND_PREFIXES:
        decoded_words = decoded_words[1:]
    if decoded_words:
        decoded_stripped = " ".join(decoded_words)
        for prefix in MULTI_WORD_BRANDS:
            if decoded_stripped.startswith(prefix):
                return BRAND_NORMALISATION[prefix]
        first_decoded = decoded_words[0]
        if first_decoded in BRAND_NORMALISATION:
            return BRAND_NORMALISATION[first_decoded]
        # Prefix match: "hpelitebookmodel" starts with "hp"
        for brand_key in sorted(BRAND_NORMALISATION, key=len, reverse=True):
            if first_decoded.startswith(brand_key):
                return BRAND_NORMALISATION[brand_key]
        for w in decoded_words[:5]:
            if w in BRAND_NORMALISATION:
                return BRAND_NORMALISATION[w]

    # Step 6: Fallback — first non-prefix word, cleaned
    orig_words = title_clean.split()
    skip = 0
    for w in orig_words:
        if w.lower() in NON_BRAND_PREFIXES:
            skip += 1
        else:
            break
    original_first = orig_words[skip] if skip < len(orig_words) else (orig_words[0] if orig_words else "Unknown")
    original_first = re.sub(r'[^\x20-\x7E\u0900-\u097F]', '', original_first).strip()

    # Issue 2 — Reject generic/blacklisted words as brand names
    # Also reject single characters (e.g. "F" from "F FERONS") — not a useful brand label
    if (not original_first
            or original_first.lower() in _BRAND_BLACKLIST
            or len(original_first) <= 1):
        return "Unknown Brand"

    return original_first


def is_refurbished(title: str) -> bool:
    keywords = ["refurb", "renewed", "open box", "open-box", "second hand",
                "pre-owned", "preowned", "used", "reconditioned", "refab"]
    return any(k in title.lower() for k in keywords)


# ---------------------------------------------------------------------------
# ISSUE 5 — Parse review counts including K+ notation
# ---------------------------------------------------------------------------
def parse_review_count(text: str) -> int | None:
    """
    Parse review/rating counts including:
      "4,532 ratings" → 4532
      "1K+ ratings"   → 1000
      "4K+"           → 4000
      "10K+"          → 10000
      "12,000"        → 12000
    """
    if not text:
        return None
    text = text.strip()
    # K+ notation: "4K+", "1.5K", "10K+"
    m = re.search(r'([\d.]+)\s*[Kk]\+?', text)
    if m:
        try:
            return int(float(m.group(1)) * 1000)
        except ValueError:
            pass
    # Plain number with commas
    m = re.search(r'([\d,]+)', text)
    if m:
        try:
            return int(m.group(1).replace(',', ''))
        except ValueError:
            pass
    return None


class MarketPulsePipeline:
    def __init__(self):
        self.brd_username = "brd-customer-hl_726e4b2c-zone-web_unlocker1"
        self.brd_password = "m8m9yijgj02c"
        self.proxy_url = f"http://{self.brd_username}:{self.brd_password}@brd.superproxy.io:33335"
        self.proxies = {"http": self.proxy_url, "https": self.proxy_url}
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        # ISSUE 8 — Track per-source counts for transparency
        self.source_counts = {}

    # ------------------------------------------------------------------
    # PUBLIC ENTRY POINT
    # ------------------------------------------------------------------
    def fetch_live_data(self, keyword: str):
        print(f"🌐 [BRIGHT DATA] Launching multi-platform spiders for: '{keyword}'...")
        self.source_counts = {}
        combined = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f_amazon   = ex.submit(self.scrape_amazon,   keyword)
            f_flipkart = ex.submit(self.scrape_flipkart, keyword)
            amazon_products   = f_amazon.result()
            flipkart_products = f_flipkart.result()

        combined.extend(amazon_products)
        combined.extend(flipkart_products)
        self.source_counts["Amazon"]   = len(amazon_products)
        self.source_counts["Flipkart"] = len(flipkart_products)
        print(f"🎯 Raw products collected: {len(combined)} "
              f"(Amazon={len(amazon_products)}, Flipkart={len(flipkart_products)})")
        return combined

    # ------------------------------------------------------------------
    # SPIDER 1 — AMAZON
    # ------------------------------------------------------------------
    def scrape_amazon(self, keyword):
        url = f"https://www.amazon.in/s?k={keyword.replace(' ', '+')}"
        products = []
        try:
            print("🕷️ [SPIDER-1] Crawling Amazon.in...")
            resp = requests.get(url, headers=self.headers, proxies=self.proxies,
                                verify=False, timeout=25)
            soup = BeautifulSoup(resp.content, "html.parser")
            results = soup.find_all("div", {"data-component-type": "s-search-result"})
            print(f"   Amazon raw cards found: {len(results)}")
            for item in results[:10]:
                product = self._parse_amazon_card(item)
                if product:
                    products.append(product)
        except Exception as e:
            print(f"⚠️ [SPIDER-1] Amazon error: {e}")
        print(f"   Amazon products extracted: {len(products)}")
        return products

    def _parse_amazon_card(self, item):
        title_tag = item.find("h2")
        if not title_tag:
            return None
        title = title_tag.get_text(strip=True)
        if not title or len(title) < 5:
            return None

        price_whole = item.find("span", {"class": "a-price-whole"})
        if not price_whole:
            return None
        price_text = price_whole.get_text(strip=True).replace(",", "").replace(".", "")
        try:
            price_val = int(price_text)
        except ValueError:
            return None
        if price_val <= 0:
            return None

        brand = extract_brand(title)

        img = item.find("img", {"class": "s-image"})
        image_url = img["src"] if img and img.get("src") else None

        # Rating
        rating = None
        rating_tag = item.find("span", {"class": "a-icon-alt"})
        if rating_tag:
            m = re.search(r"([\d.]+)\s+out of", rating_tag.get_text())
            if m:
                try:
                    rating = float(m.group(1))
                except ValueError:
                    pass

        # ISSUE 5 — Review count with K+ parsing
        review_count = None
        rc_tag = item.find("span", {"class": "a-size-base", "dir": "auto"})
        if not rc_tag:
            rc_tag = item.find("a", {"class": "a-link-normal"},
                               href=re.compile(r"#customerReviews"))
        if rc_tag:
            review_count = parse_review_count(rc_tag.get_text(strip=True))

        # ISSUE 2 — Extract only genuine review snippets
        reviews = self._extract_amazon_card_reviews(item)

        return {
            "product_name": title,
            "brand":        brand,
            "price":        f"₹{price_val:,}",
            "clean_price":  price_val,
            "rating":       rating,
            "review_count": review_count,
            "reviews":      reviews,
            "platform":     "Amazon",
            "image_url":    image_url,
            "discount":     None,
            "refurbished":  is_refurbished(title),
        }

    def _extract_amazon_card_reviews(self, item) -> list:
        """ISSUE 2 — Extract only genuine customer review snippets."""
        snippets = []
        for cls in ["a-size-base a-color-secondary", "a-size-small a-color-secondary",
                    "s-line-clamp-2", "s-line-clamp-3", "a-text-italic"]:
            for tag in item.find_all(attrs={"class": re.compile(cls.replace(" ", r"\s"))}):
                text = tag.get_text(strip=True)
                if is_genuine_review(text) and text not in snippets:
                    snippets.append(text)
                if len(snippets) >= 3:
                    break
            if len(snippets) >= 3:
                break
        return snippets[:3]

    # ------------------------------------------------------------------
    # SPIDER 2 — FLIPKART
    # ISSUE 1 — Flipkart returns 400 because the proxy zone blocks it.
    # Fix: use a different request approach with full browser headers,
    # retry with a session, and handle 400/non-200 gracefully.
    # ------------------------------------------------------------------
    def scrape_flipkart(self, keyword):
        url = f"https://www.flipkart.com/search?q={keyword.replace(' ', '+')}"
        products = []
        try:
            print("🕷️ [SPIDER-2] Crawling Flipkart.com...")
            # Use a requests Session with full browser-like headers
            session = requests.Session()
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            })

            resp = session.get(url, proxies=self.proxies, verify=False, timeout=25)
            print(f"   Flipkart HTTP status: {resp.status_code}, size: {len(resp.content)} bytes")

            # ISSUE 1 — If 400, retry once without proxy (direct)
            if resp.status_code == 400:
                print("   ⚠️ Flipkart 400 via proxy — retrying direct (no proxy)...")
                resp = session.get(url, verify=False, timeout=25)
                print(f"   Flipkart direct status: {resp.status_code}, size: {len(resp.content)} bytes")

            if resp.status_code != 200:
                print(f"⚠️ [SPIDER-2] Flipkart unavailable (HTTP {resp.status_code}). Skipping.")
                return products

            soup = BeautifulSoup(resp.content, "html.parser")
            cards = self._find_flipkart_cards(soup)
            print(f"   Flipkart raw cards found: {len(cards)}")

            if cards:
                first_classes = []
                for tag in cards[0].find_all(True):
                    first_classes.extend(tag.get("class", []))
                top = Counter(first_classes).most_common(10)
                print(f"   Flipkart first-card classes: {[c for c, _ in top]}")

            for card in cards[:10]:
                product = self._parse_flipkart_card(card)
                if product:
                    products.append(product)

        except Exception as e:
            print(f"⚠️ [SPIDER-2] Flipkart error: {e}")

        print(f"   Flipkart products extracted: {len(products)}")
        return products

    def _find_flipkart_cards(self, soup) -> list:
        strategies = [
            # Strategy 1: data-id (most reliable)
            lambda s: [d for d in s.find_all("div", {"data-id": True})
                       if d.find("img") and d.find(string=re.compile(r'₹'))],
            # Strategy 2: known 2024-2025 grid classes
            lambda s: s.find_all("div", class_=re.compile(r"^(RGLWAk|tUxRFH|_1YokD2|_3pLy-c)$")),
            # Strategy 3: product link containers
            lambda s: [a.parent for a in s.find_all("a", href=re.compile(r"/p/"))
                       if a.parent and a.parent.find(string=re.compile(r'₹'))],
            # Strategy 4: div with image + price
            lambda s: [d for d in s.find_all("div")
                       if d.find("img") and d.find(string=re.compile(r'₹[\d,]+'))
                       and 30 < len(d.get_text()) < 2000],
            # Strategy 5: legacy classes
            lambda s: (s.find_all("div", class_=re.compile(r"_1AtVbE")) or
                       s.find_all("div", class_=re.compile(r"_2kHMtA")) or
                       s.find_all("div", class_=re.compile(r"CXW8mj"))),
        ]
        for i, strategy in enumerate(strategies):
            try:
                result = strategy(soup)
                if result and len(result) >= 2:
                    print(f"   Flipkart selector strategy {i+1} matched: {len(result)} cards")
                    seen, unique = set(), []
                    for c in result:
                        if id(c) not in seen:
                            seen.add(id(c))
                            unique.append(c)
                    return unique[:12]
            except Exception as e:
                print(f"   Strategy {i+1} error: {e}")
        print("   ⚠️ All Flipkart selector strategies failed")
        return []

    def _parse_flipkart_card(self, card):
        title = self._extract_flipkart_title(card)
        if not title or len(title) < 5:
            return None
        price_val = self._extract_flipkart_price(card)
        if not price_val or price_val <= 0:
            return None

        brand = extract_brand(title)
        img = card.find("img")
        image_url = None
        if img:
            image_url = img.get("data-src") or img.get("src")

        rating = self._extract_flipkart_rating(card)
        review_count = self._extract_flipkart_review_count(card)
        reviews = self._extract_flipkart_reviews(card)

        return {
            "product_name": title,
            "brand":        brand,
            "price":        f"₹{price_val:,}",
            "clean_price":  price_val,
            "rating":       rating,
            "review_count": review_count,
            "reviews":      reviews,
            "platform":     "Flipkart",
            "image_url":    image_url,
            "discount":     None,
            "refurbished":  is_refurbished(title),
        }

    def _extract_flipkart_title(self, card) -> str:
        title_classes = [
            "KzDlHZ", "_4rR01T", "IRpwTa", "s1Q9rs", "wjcEIp", "_2WkVRV",
            "B_NuCI", "WKTcLC", "yafNZb", "lymLuz",
        ]
        for cls in title_classes:
            t = card.find(attrs={"class": re.compile(r'\b' + re.escape(cls) + r'\b')})
            if t:
                txt = t.get_text(strip=True)
                if len(txt) > 8:
                    return self._clean_flipkart_title(txt)
        for a in card.find_all("a", href=re.compile(r"/p/")):
            txt = a.get_text(strip=True)
            if len(txt) > 8:
                return self._clean_flipkart_title(txt)
        best = ""
        for a in card.find_all("a"):
            txt = a.get_text(strip=True)
            if len(txt) > len(best) and len(txt) < 300:
                best = txt
        return self._clean_flipkart_title(best) if len(best) > 8 else ""

    @staticmethod
    def _clean_flipkart_title(title: str) -> str:
        """
        Flipkart cards often prepend UI text like 'Add to Compare' to the title.
        Strip it and any trailing spec/price noise.
        """
        if not title:
            return title
        # Remove leading "Add to Compare" (case-insensitive)
        title = re.sub(r'^Add\s+to\s+Compare\s*', '', title, flags=re.IGNORECASE).strip()
        # Truncate at the first occurrence of spec noise patterns
        # e.g. "ASUS Vivobook 15 Intel Core i3 13th Gen - (8 GB/512 GB SSD/Windows 11..."
        # We keep everything up to the first parenthesis or rating pattern
        # but only if the title is very long (>120 chars) — short titles are fine
        if len(title) > 120:
            # Cut at first occurrence of rating pattern like "4.3815 Ratings"
            m = re.search(r'\d+\.\d+\s*\d+\s*Ratings', title)
            if m:
                title = title[:m.start()].strip()
            # Also cut at "₹" price if it appears mid-title
            m2 = re.search(r'₹[\d,]+', title)
            if m2 and m2.start() > 20:
                title = title[:m2.start()].strip()
        return title.strip()

    def _extract_flipkart_price(self, card) -> int:
        price_classes = [
            "_30jeq3", "Nx9bqj", "_1_WHN1", "hl05au", "_25b18c",
            "CEmiEU", "aBzdBX", "_16Jk6d", "UOCQB1",
        ]
        for cls in price_classes:
            p = card.find(attrs={"class": re.compile(r'\b' + re.escape(cls) + r'\b')})
            if p:
                raw = p.get_text(strip=True).replace("₹", "").replace(",", "").strip()
                m = re.search(r'(\d+)', raw)
                if m:
                    try:
                        val = int(m.group(1))
                        if val > 0:
                            return val
                    except ValueError:
                        pass
        for tag in card.find_all(string=re.compile(r'₹\s*[\d,]+')):
            raw = re.sub(r'[^\d]', '', str(tag))
            if raw:
                try:
                    val = int(raw)
                    if 10 < val < 10_000_000:
                        return val
                except ValueError:
                    pass
        return 0

    def _extract_flipkart_rating(self, card):
        rating_classes = ["_3LWZlK", "XQDdHH", "gUuXy-", "Y1HWO0", "ipqd2A"]
        for cls in rating_classes:
            r = card.find(attrs={"class": re.compile(r'\b' + re.escape(cls) + r'\b')})
            if r:
                m = re.search(r'(\d+\.\d+|\d+)', r.get_text(strip=True))
                if m:
                    try:
                        val = float(m.group(1))
                        if 0 < val <= 5:
                            return val
                    except ValueError:
                        pass
        return None

    def _extract_flipkart_review_count(self, card):
        """ISSUE 5 — Parse review counts including K+ notation."""
        rc_classes = ["_2_R_DZ", "Wphh3N", "_13vcmD", "JOpGWq"]
        for cls in rc_classes:
            rc = card.find(attrs={"class": re.compile(r'\b' + re.escape(cls) + r'\b')})
            if rc:
                val = parse_review_count(rc.get_text(strip=True))
                if val is not None:
                    return val
        return None

    def _extract_flipkart_reviews(self, card) -> list:
        """ISSUE 2 — Only genuine review snippets."""
        snippets = []
        for tag in card.find_all(attrs={"class": re.compile(r'(review|comment|snippet)', re.IGNORECASE)}):
            txt = tag.get_text(strip=True)
            if is_genuine_review(txt):
                snippets.append(txt)
            if len(snippets) >= 3:
                break
        return snippets[:3]

    # ------------------------------------------------------------------
    # ISSUE 7 — Validation layer
    # ------------------------------------------------------------------
    def validate_and_clean(self, raw_data):
        if not raw_data:
            return []
        seen_titles = set()
        valid = []
        for p in raw_data:
            title = (p.get("product_name") or "").strip()
            if not title or len(title) < 5:
                continue

            # Clean unicode garbage from title
            title_clean = re.sub(r'[\U0001D400-\U0001D7FF]', '', title).strip()
            if title_clean and len(title_clean) >= 5:
                p["product_name"] = title_clean
                title = title_clean

            # Deduplicate
            key = hashlib.md5(title.lower().encode()).hexdigest()
            if key in seen_titles:
                continue
            seen_titles.add(key)

            # Valid price
            cp = p.get("clean_price")
            if not cp or cp <= 0:
                continue

            # Validate rating
            rating = p.get("rating")
            if rating is not None and not (0.0 <= rating <= 5.0):
                p["rating"] = None

            # Validate review count
            rc = p.get("review_count")
            if rc is not None and (not isinstance(rc, int) or rc < 0):
                p["review_count"] = None

            # Validate image URL
            img = p.get("image_url") or ""
            if img and not img.startswith("http"):
                p["image_url"] = None

            # Validate brand
            brand = p.get("brand") or ""
            if len(brand) < 1 or re.match(r'^[\W\d]+$', brand):
                p["brand"] = extract_brand(title)

            # ISSUE 2 — Filter reviews: keep only genuine snippets
            raw_reviews = p.get("reviews") or []
            if not isinstance(raw_reviews, list):
                raw_reviews = []
            p["reviews"] = [r for r in raw_reviews if is_genuine_review(r)]

            valid.append(p)

        print(f"✅ [VALIDATION] {len(raw_data)} raw → {len(valid)} valid products")
        return valid

    def process_and_clean_data(self, raw_data):
        cleaned = self.validate_and_clean(raw_data)
        if not cleaned:
            return []
        prices = [p["clean_price"] for p in cleaned]
        avg = sum(prices) / len(prices) if prices else 0
        for p in cleaned:
            p["market_position"] = "Premium Tier" if p["clean_price"] > avg else "Budget Tier"
            p["discount"]     = None
            p["discount_pct"] = 0
        self._log_diagnostics(cleaned)
        return cleaned

    def _log_diagnostics(self, products: list):
        n = len(products)
        sources = {}
        ratings_found = reviews_found = images_found = 0
        missing_rating = missing_rc = missing_img = 0
        snippet_count = refurb_count = 0
        for p in products:
            src = p.get("platform", "Unknown")
            sources[src] = sources.get(src, 0) + 1
            if p.get("rating") is not None:
                ratings_found += 1
            else:
                missing_rating += 1
            if p.get("review_count") is not None:
                reviews_found += 1
            else:
                missing_rc += 1
            if p.get("image_url"):
                images_found += 1
            else:
                missing_img += 1
            snippet_count += len(p.get("reviews") or [])
            if p.get("refurbished"):
                refurb_count += 1

        print("\n" + "─" * 55)
        print("📊 DIAGNOSTICS REPORT")
        print(f"   Total valid products  : {n}")
        for src, count in sources.items():
            print(f"   Source [{src:10s}]  : {count} products")
        print(f"   Ratings found         : {ratings_found}/{n}")
        print(f"   Review counts found   : {reviews_found}/{n}")
        print(f"   Genuine review snippets: {snippet_count}")
        print(f"   Images found          : {images_found}/{n}")
        print(f"   Refurbished tagged    : {refurb_count}")
        print(f"   Missing rating        : {missing_rating}")
        print(f"   Missing review count  : {missing_rc}")
        print(f"   Missing image         : {missing_img}")
        print("─" * 55 + "\n")
