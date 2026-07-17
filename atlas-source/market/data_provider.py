from abc import ABC, abstractmethod


class DataProvider(ABC):

    @abstractmethod
    def get_price_history(self, ticker):
        pass

    @abstractmethod
    def get_latest_price(self, ticker):
        pass

    @abstractmethod
    def get_supported_tickers(self):
        pass
