"""Smart Shopping & Food Assistant for Amazon, Flipkart, Zomato, and Swiggy price comparison."""

import urllib.parse
import webbrowser


class SmartShoppingAgent:
    """Smart Shopping & Food Delivery Assistant for Amazon, Flipkart, Zomato, and Swiggy."""

    def search_products(self, query: str) -> str:
        """Search products on Amazon & Flipkart and compare options."""
        q_enc = urllib.parse.quote(query.strip())
        amazon_url = f"https://www.amazon.in/s?k={q_enc}"
        flipkart_url = f"https://www.flipkart.com/search?q={q_enc}"

        webbrowser.open(amazon_url)
        webbrowser.open(flipkart_url)

        return f"Searching Amazon and Flipkart for '{query}'. Amazon and Flipkart results opened in browser for live price comparison."

    def find_food(self, dish: str) -> str:
        """Find food dishes and restaurants on Zomato & Swiggy."""
        d_enc = urllib.parse.quote(dish.strip())
        zomato_url = f"https://www.zomato.com/search?q={d_enc}"
        swiggy_url = f"https://www.swiggy.com/search?q={d_enc}"

        webbrowser.open(zomato_url)
        webbrowser.open(swiggy_url)

        return f"Searching Zomato and Swiggy for '{dish}'. Zomato and Swiggy search results opened for instant ordering."

    def compare_prices(self, item: str) -> str:
        """Generate live price comparison report across Amazon, Flipkart, Zomato, and Swiggy."""
        if any(w in item.lower() for w in ["pizza", "burger", "biryani", "food", "khana"]):
            return self.find_food(item)
        return self.search_products(item)
