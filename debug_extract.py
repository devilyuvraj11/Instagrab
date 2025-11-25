# debug_extract.py
import httpx, re, json, sys
USER_AGENTS = {
  "desktop": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
  "mobile": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile"
}

def save(path, text):
    with open(path, "w", encoding="utf8") as f:
        f.write(text)
    print("[saved]", path)

def try_ld(html):
    return re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html, re.S|re.I)

def try_shared(html):
    m = re.search(r'window\._sharedData\s*=\s*(\{.*?\});', html, re.S)
    return (m.group(1) if m else None)

def try_a1(url, headers):
    u = url if url.endswith("/") else url + "/"
    u = u + "?__a=1&__d=dis"
    try:
        r = httpx.get(u, headers=headers, timeout=12.0)
    except Exception as e:
        return None, f"error: {e}"
    if r.status_code != 200:
        return None, f"status {r.status_code}"
    try:
        return r.json(), "ok"
    except Exception as e:
        return None, f"json error: {e}"

def inspect(url):
    print("URL:", url)
    html = None
    headers_used = None
    for name, ua in USER_AGENTS.items():
        hdr = {"User-Agent": ua, "Accept-Language":"en-US"}
        print("Fetching with UA:", name)
        try:
            r = httpx.get(url, headers=hdr, timeout=20.0)
        except Exception as e:
            print(" fetch error:", e); continue
        print(" status:", r.status_code)
        if r.status_code==200 and len(r.text)>1000:
            html = r.text; headers_used=hdr; save("page_fetched.html", html); break
    if not html:
        print("No usable HTML fetched.")
        return
    print("ld+json blocks:", len(try_ld(html)))
    shared = try_shared(html)
    print("window._sharedData present:", bool(shared))
    if shared:
        try:
            sd = json.loads(shared)
            # quick probe for keys
            print("Top keys in entry_data:", list(sd.get("entry_data",{}).keys()))
        except Exception as e:
            print("sharedData parse error:", e)
    js, note = try_a1(url, headers_used or {"User-Agent":USER_AGENTS["desktop"]})
    print("?__a=1 result:", note)
    if js and isinstance(js, dict):
        print("Top-level keys in ?__a=1 JSON:", list(js.keys())[:10])
    # brute force search
    m = re.search(r'"video_url"\s*:\s*"([^"]+)"', html)
    print("brute-force video_url found:", bool(m))
    if m: print(" example:", m.group(1)[:120])
    print("Done. Inspect page_fetched.html for full HTML.")
    
if __name__=="__main__":
    if len(sys.argv)<2:
        print("usage: python debug_extract.py <instagram_post_url>")
    else:
        inspect(sys.argv[1])
