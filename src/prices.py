from datetime import date

import pandas as pd
import yfinance as yf


class Prices:
    """Retrieve historical prices and compute relevant metrics."""

    def __init__(self, initial_tickers, date_start):
        self.tickers = set(initial_tickers)
        # self.date_range = (date_start, date.today().strftime("%Y-%m-%d"))
        self.date_range = pd.date_range(start=date_start, end=date.today(), freq="B")
        self.prices_raw = self.get_historical_prices(initial_tickers)
        self.prices_normalized = self.prices_raw / self.prices_raw.iloc[0]
        self.percentage_changes = (
            self.prices_normalized / (self.prices_normalized.shift(1) + 1e-7) - 1
        ).fillna(0)
        self.rolling_changes = self.percentage_changes.rolling(window=251, min_periods=1).sum()

    def __str__(self):
        return f"Prices(tickers={self.tickers})"

    def get_historical_prices(self, tickers):
        df = (
            yf.download(
                tickers,
                interval="1d",
                start=self.date_range[0],
                end=self.date_range[-1],
                auto_adjust=False,
                progress=False,
            )
            .Close.reindex(self.date_range)
            .bfill()
            .ffill()
        )
        return df

    # TODO: what happens if tickers are empty?
    def update_tickers(self, tickers):
        selected_tickers = set(tickers)
        for ticker in self.tickers - selected_tickers:
            self.remove_ticker(ticker)
        for ticker in selected_tickers - self.tickers:
            self.add_ticker(ticker)

    def remove_ticker(self, ticker):
        self.tickers.remove(ticker)
        for df in [
            self.prices_raw,
            self.prices_normalized,
            self.percentage_changes,
            self.rolling_changes,
        ]:
            df.drop(ticker, axis=1, inplace=True)

    def add_ticker(self, ticker):
        self.tickers.add(ticker)
        ticker_df = self.get_historical_prices(ticker)
        self.prices_raw[ticker] = ticker_df
        self.prices_normalized[ticker] = ticker_df / ticker_df.iloc[0]
        self.percentage_changes[ticker] = (
            self.prices_normalized[ticker] / (self.prices_normalized[ticker].shift(1) + 1e-7) - 1
        ).fillna(0)
        self.rolling_changes[ticker] = (
            self.percentage_changes[ticker].rolling(window=251, min_periods=1)
        ).sum()
