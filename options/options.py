from __future__ import annotations

import pandas as pd
import yfinance as yf


class OptionPrices:

    def __init__(self, ticker):
        self.ticker = ticker
        self.get_option_chains()
        self.get_options()
        self.get_relative_prices()

    def get_option_chains(self):
        self.asset = yf.Ticker(self.ticker)
        self.expirations = self.asset.options
        self.call_chain = {
            expiration: self.asset.option_chain(expiration).calls for expiration in self.expirations
        }
        self.put_chain = {
            expiration: self.asset.option_chain(expiration).puts for expiration in self.expirations
        }

    def get_options(self, price_estimate="avg"):
        self.calls = self.construct_option_matrix(
            self.call_chain, option_type="call", price_estimate=price_estimate
        )
        self.puts = self.construct_option_matrix(
            self.put_chain, option_type="put", price_estimate=price_estimate
        )

    def get_relative_prices(self):
        self.spotPrice = (self.asset.info["bid"] + self.asset.info["ask"]) / 2
        self.calls["profitChange"] = (self.calls.profitPrice - self.spotPrice) / self.spotPrice
        self.puts["profitChange"] = (self.puts.profitPrice - self.spotPrice) / self.spotPrice

    def construct_option_matrix(self, option_chain, option_type, price_estimate):
        option_matrix = []
        for expiration, option_series in option_chain.items():
            options = pd.DataFrame(option_series.contractSymbol)
            options["expirationDate"] = expiration
            options["strikePrice"] = option_series.strike
            options["bidPrice"] = option_series.bid
            options["askPrice"] = option_series.ask

            if price_estimate == "avg":
                options["optionPrice"] = (option_series.bid + option_series.ask) / 2
            else:
                options["optionPrice"] = option_series.lastPrice

            if option_type == "call":
                options["profitPrice"] = options.strikePrice + options.optionPrice
            else:
                options["profitPrice"] = options.strikePrice - options.optionPrice

            option_matrix.append(options)
        return pd.concat(option_matrix, ignore_index=True)
