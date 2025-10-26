from datetime import date

import numpy as np
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
        self.get_relative_prices(initial_tickers)

    def __str__(self):
        return f"Prices(tickers={self.tickers})"

    def get_historical_prices(self, tickers):
        data = yf.download(
            tickers,
            interval=PRICES_RETRIEVAL_INTERVAL,
            start=self.date_range[0],
            end=self.date_range[-1],
            auto_adjust=True,  # account for dividends
            progress=False,
        )

        if data is None or data.empty:
            raise ValueError(f"No data retrieved for tickers: {tickers}")

        df = data.Close.reindex(index=self.date_range).bfill().ffill()

        # add yield for securities without dividends (e.g. bonds, money market funds)
        ticker_list = [tickers] if isinstance(tickers, str) else tickers
        if ticker_list:
            days_elapsed = (self.date_range - self.date_range[0]).days
            for ticker in ticker_list:
                try:
                    ticker_obj = yf.Ticker(ticker)
                    if ticker_obj.dividends.empty:
                        annual_yield = ticker_obj.info.get("yield", 0.0)
                        if annual_yield > 0:
                            continuous_rate = np.log(1 + annual_yield)
                            cumulative_factor = np.exp(continuous_rate * days_elapsed / 365.25)
                            df[ticker] = df[ticker] * cumulative_factor
                except Exception as e:
                    print(f"Could not adjust yield for {ticker}: {e}")

        return df

    def get_relative_prices(self, tickers):
        self.prices_raw = self.get_historical_prices(tickers).reindex(columns=tickers)
        self.prices_normalized = self.prices_raw / self.prices_raw.iloc[0]
        self.percentage_changes = (
            self.prices_normalized / (self.prices_normalized.shift(1) + PRICES_EPS) - 1
        ).fillna(0)
        self.rolling_changes = self.percentage_changes.rolling(
            window=PRICES_ROLLING_WINDOW, min_periods=PRICES_ROLLING_MIN_PERIOD
        ).sum()

    def update_tickers(self, tickers):
        for ticker in self.tickers[:]:
            if ticker not in tickers:
                self.remove_ticker(ticker)
        for ticker in tickers:
            if ticker not in self.tickers:
                self.add_ticker(ticker)

        # reorder tickers
        if self.tickers != tickers:
            self.tickers = list(tickers)
            self.prices_raw = self.prices_raw[tickers]
            self.prices_normalized = self.prices_normalized[tickers]
            self.percentage_changes = self.percentage_changes[tickers]
            self.rolling_changes = self.rolling_changes[tickers]

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
        ticker_df = self.get_historical_prices(ticker)
        self.tickers.append(ticker)
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

    def is_valid_ticker(self, ticker):
        try:
            data = yf.download(ticker, period="5d", progress=False, auto_adjust=False)
            return data is not None and not data.empty
        except Exception:
            return False
