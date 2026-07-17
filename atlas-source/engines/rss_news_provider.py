from urllib.parse import quote
from urllib.request import urlopen
from xml.etree import ElementTree

from engines.news_provider import NewsProvider


class RSSNewsProvider(NewsProvider):

    def __init__(self, timeout=5):
        self.timeout = timeout
        self.last_error = ""

    def get_headlines(self, ticker):
        try:
            headlines = self._fetch_headlines(ticker)
            self.last_error = ""

            return headlines
        except Exception as error:
            self.last_error = str(error)

            return []

    def get_provider_name(self):
        return "rss"

    def health_check(self):
        return {
            "provider": self.get_provider_name(),
            "healthy": True,
            "message": "RSS provider is optional and failure-safe.",
        }

    def _fetch_headlines(self, ticker):
        encoded_ticker = quote(str(ticker).upper())
        url = (
            "https://feeds.finance.yahoo.com/rss/2.0/headline"
            f"?s={encoded_ticker}&region=US&lang=en-US"
        )

        with urlopen(url, timeout=self.timeout) as response:
            feed = response.read()

        root = ElementTree.fromstring(feed)
        headlines = []

        for item in root.findall("./channel/item"):
            title = item.findtext("title")

            if title:
                headlines.append(title.strip())

            if len(headlines) == 5:
                break

        return headlines
