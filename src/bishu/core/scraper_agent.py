"""Web Scraper Agent for reading raw URLs, scraping table links, and extracting page paragraphs."""

import re
import json
import ssl
import urllib.request
import urllib.parse


class WebScraperAgent:
    """Agent for fetching web pages, extracting table links, and parsing page text paragraphs."""

    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def read_raw_url(self, url: str) -> str:
        """Fetch raw HTML/text content from given URL."""
        if not url.startswith("http"):
            url = "https://" + url

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10, context=self.ssl_ctx) as resp:
                raw_html = resp.read().decode('utf-8', errors='ignore')
                clean_text = re.sub(r'<script.*?</script>|<style.*?</style>', '', raw_html, flags=re.DOTALL)
                clean_text = re.sub(r'<.*?>', ' ', clean_text)
                return ' '.join(clean_text.split())[:3000]
        except Exception as e:
            return f"Failed to fetch URL '{url}': {e}"

    def scrape_table_links(self, url: str) -> list:
        """Parse HTML tables from URL and extract table links and data."""
        if not url.startswith("http"):
            url = "https://" + url

        table_data = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10, context=self.ssl_ctx) as resp:
                raw_html = resp.read().decode('utf-8', errors='ignore')

            # Find all table blocks
            tables = re.findall(r'<table.*?>(.*?)</table>', raw_html, re.DOTALL | re.IGNORECASE)
            for t_idx, tbl in enumerate(tables):
                links = re.findall(r'href=["\'](.*?)["\']', tbl)
                cells = re.findall(r'<td.*?>(.*?)</td>', tbl, re.DOTALL | re.IGNORECASE)
                clean_cells = [re.sub(r'<.*?>', '', c).strip() for c in cells if c.strip()]
                table_data.append({
                    "table_index": t_idx + 1,
                    "cell_sample": clean_cells[:10],
                    "extracted_links": links[:10]
                })

            return table_data if table_data else [{"info": "No <table> tags found on page."}]
        except Exception as e:
            return [{"error": f"Scrape table error: {e}"}]

    def extract_paragraphs(self, url: str) -> list:
        """Extract clean text paragraphs from <p> tags on page."""
        if not url.startswith("http"):
            url = "https://" + url

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10, context=self.ssl_ctx) as resp:
                raw_html = resp.read().decode('utf-8', errors='ignore')

            p_tags = re.findall(r'<p.*?>(.*?)</p>', raw_html, re.DOTALL | re.IGNORECASE)
            clean_paragraphs = []
            for p in p_tags:
                clean_p = re.sub(r'<.*?>', '', p).strip()
                if len(clean_p) > 25:
                    clean_paragraphs.append(clean_p)

            return clean_paragraphs[:15] if clean_paragraphs else ["No paragraph text found."]
        except Exception as e:
            return [f"Extract paragraphs error: {e}"]
