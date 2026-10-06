"""
Unit tests for web scrapers parsing logic with mock HTML fixtures.
Tests are completely offline and do not rely on live websites.
"""
import pytest

from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper


MOCK_BOOKS_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="page-header action">
        <h1>Poetry</h1>
    </div>
    <ol class="row">
        <li>
            <article class="product_pod">
                <div class="image_container">
                    <a href="catalogue/a-light-in-the-attic_1000/index.html"><img src="media/cache/test.jpg" alt="A Light in the Attic"/></a>
                </div>
                <p class="star-rating Three">
                    <i class="icon-star"></i>
                </p>
                <h3><a href="catalogue/a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light in the ...</a></h3>
                <div class="product_price">
                    <p class="price_color">£51.77</p>
                    <p class="instock availability"><i class="icon-ok"></i> In stock</p>
                </div>
            </article>
        </li>
    </ol>
    <ul class="pager">
        <li class="next"><a href="catalogue/page-2.html">next</a></li>
    </ul>
</body>
</html>
"""

MOCK_MALFORMED_BOOKS_HTML = """
<!DOCTYPE html>
<html>
<body>
    <ol class="row">
        <li>
            <!-- Broken pod without h3 link -->
            <article class="product_pod">
                <p class="price_color">£19.99</p>
            </article>
        </li>
    </ol>
</body>
</html>
"""

MOCK_QUOTES_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="quote">
        <span class="text">“The world as we have created it is a process of our thinking.”</span>
        <span>by <small class="author">Albert Einstein</small>
        <a href="/author/Albert-Einstein">(about)</a>
        </span>
        <div class="tags">
            Tags:
            <a class="tag" href="/tag/change/page/1/">change</a>
            <a class="tag" href="/tag/thinking/page/1/">thinking</a>
        </div>
    </div>
    <ul class="pager">
        <li class="next"><a href="/page/2/">Next</a></li>
    </ul>
</body>
</html>
"""


class TestScraperParsing:
    def test_books_parser_extracts_correct_fields(self):
        scraper = BooksScraper()
        records, next_url = scraper.parse_page(MOCK_BOOKS_HTML, "https://books.toscrape.com/")
        
        assert len(records) == 1
        book = records[0]
        assert book["name_or_title"] == "A Light in the Attic"
        assert book["category"] == "Poetry"
        assert book["price"] == "£51.77"
        assert book["rating"] == "Three"
        assert book["source"] == "Books to Scrape"
        assert book["source_url"] == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
        assert book["availability"] == "In stock"
        assert next_url == "https://books.toscrape.com/catalogue/page-2.html"

    def test_books_parser_handles_malformed_html_safely(self):
        scraper = BooksScraper()
        records, next_url = scraper.parse_page(MOCK_MALFORMED_BOOKS_HTML, "https://books.toscrape.com/")
        # Malformed pod is safely skipped without raising an exception
        assert len(records) == 0
        assert next_url is None

    def test_quotes_parser_extracts_correct_fields(self):
        scraper = QuotesScraper()
        records, next_url = scraper.parse_page(MOCK_QUOTES_HTML, "https://quotes.toscrape.com/")

        assert len(records) == 1
        quote = records[0]
        assert "The world as we have created it" in quote["name_or_title"]
        assert quote["author"] == "Albert Einstein"
        assert quote["category"] is None
        assert "change" in quote["tags"]
        assert "thinking" in quote["tags"]
        assert quote["source"] == "Quotes to Scrape"
        assert "https://quotes.toscrape.com/page/1/#quote-1" in quote["source_url"] or "#quote-1" in quote["source_url"]
        assert next_url == "https://quotes.toscrape.com/page/2/"
