from abc import ABC, abstractmethod


class NewsProvider(ABC):

    @abstractmethod
    def get_headlines(self, ticker):
        pass

    @abstractmethod
    def get_provider_name(self):
        pass

    @abstractmethod
    def health_check(self):
        pass
