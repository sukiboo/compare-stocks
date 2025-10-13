from datetime import date

import pandas as pd
import yfinance as yf

from src.constants import (
    PRICES_EPS,
    PRICES_RETRIEVAL_INTERVAL,
    PRICES_ROLLING_MIN_PERIOD,
    PRICES_ROLLING_WINDOW,
)


class Prices:
    """Retrieve historical prices and compute relevant metrics."""

    def __init__(self, initial_tickers, date_start):
        self.tickers = list(initial_tickers)
        self.date_range = pd.date_range(start=date_start, end=date.today(), freq="B")
        self.get_retrieve_prices(initial_tickers)

    def __str__(self):
        return f"Prices(tickers={self.tickers})"

    def get_historical_prices(self, tickers):
        data = yf.download(
            tickers,
            interval=PRICES_RETRIEVAL_INTERVAL,
            start=self.date_range[0],
            end=self.date_range[-1],
            auto_adjust=False,
            progress=False,
        )

        if data is None or data.empty:
            raise ValueError(f"No data retrieved for tickers: {tickers}")

        df = data.Close.reindex(index=self.date_range).bfill().ffill()
        return df

    def get_retrieve_prices(self, tickers):
        self.prices_raw = self.get_historical_prices(tickers).reindex(columns=tickers)
        self.prices_normalized = self.prices_raw / self.prices_raw.iloc[0]
        self.percentage_changes = (
            self.prices_normalized / (self.prices_normalized.shift(1) + PRICES_EPS) - 1
        ).fillna(0)
        self.rolling_changes = self.percentage_changes.rolling(
            window=PRICES_ROLLING_WINDOW, min_periods=PRICES_ROLLING_MIN_PERIOD
        ).sum()

    def update_tickers(self, tickers):
        selected_tickers = list(tickers)
        for ticker in self.tickers[:]:
            if ticker not in selected_tickers:
                self.remove_ticker(ticker)
        for ticker in selected_tickers:
            if ticker not in self.tickers:
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
        self.tickers.append(ticker)
        ticker_df = self.get_historical_prices(ticker)
        self.prices_raw[ticker] = ticker_df
        self.prices_normalized[ticker] = ticker_df / ticker_df.iloc[0]
        self.percentage_changes[ticker] = (
            self.prices_normalized[ticker] / (self.prices_normalized[ticker].shift(1) + PRICES_EPS)
            - 1
        ).fillna(0)
        self.rolling_changes[ticker] = (
            self.percentage_changes[ticker]
            .rolling(window=PRICES_ROLLING_WINDOW, min_periods=PRICES_ROLLING_MIN_PERIOD)
            .sum()
        )
