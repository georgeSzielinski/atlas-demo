from abc import ABC, abstractmethod


class FundamentalProvider(ABC):

    @abstractmethod
    def get_company_profile(self, ticker):
        pass

    @abstractmethod
    def get_fundamentals(self, ticker):
        pass

    @abstractmethod
    def health_check(self):
        pass

    @abstractmethod
    def provider_name(self):
        pass
