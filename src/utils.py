import re
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd
from dateutil import parser  # type: ignore

from src.constants import APP_PORTFOLIO


def normalize_ticker_symbol(ticker_input: str) -> str:
    """Remove all non-alphanumeric characters from ticker input, return uppercase."""
    return re.sub(r"[^A-Z0-9]", "", ticker_input.upper())


def get_available_tickers() -> list[str]:
    """This list is too limited, I opted for any input + validation in the app."""
    nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    nyse_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
    nasdaq_tickers = pd.read_csv(nasdaq_url, sep="|")["Symbol"].dropna().tolist()[:-1]
    nyse_tickers = pd.read_csv(nyse_url, sep="|")["ACT Symbol"].dropna().tolist()[:-1]
    all_tickers = sorted(set(nasdaq_tickers + nyse_tickers))  # type: ignore
    return all_tickers


def date_to_idx_range(timestamps: pd.DatetimeIndex, date_range: Sequence[Any]) -> list[int]:
    idx_range = (
        timestamps.get_indexer(date_range, method="nearest").tolist()
        if all(date_range)
        else [0, -1]
    )
    return idx_range


def get_date_range(figure_layout: dict[str, Any]) -> Sequence[str | None]:
    date_range: Sequence[str | None] = [None, None]
    # check xaxis2 first
    if "xaxis2" in figure_layout and figure_layout["xaxis2"].get("range"):
        date_range = figure_layout["xaxis2"]["range"]
    # if not found, check xaxis1
    elif "xaxis1" in figure_layout and figure_layout["xaxis1"].get("range"):
        date_range = figure_layout["xaxis1"]["range"]
    # else:
    #     print(figure_layout)
    return date_range


def adjust_date_range(
    timestamps: pd.DatetimeIndex,
    offset_days: int,
    triggered_id: str = "btn-1y",
    date_range: Sequence[str | None] | None = None,
) -> Sequence[str]:
    if not date_range or triggered_id == "btn-ytd":
        start_date = timestamps[0].strftime("%Y-%m-%d")
        end_date = timestamps[-1].strftime("%Y-%m-%d")
    else:
        start_date, end_date = date_range
    start_date = max(
        parser.parse(end_date) - timedelta(days=offset_days),
        timestamps[0],
    ).strftime("%Y-%m-%d")
    return [start_date, end_date]


def normalize_prices(
    prices: pd.DataFrame, prices_copy: pd.DataFrame, date_range: Sequence[Any]
) -> pd.DataFrame:
    date0, date1 = date_range
    prices_normalized = np.nan * prices
    prices_normalized.loc[date0:date1] = prices[date0:date1] / prices.loc[date0] - 1

    # tickers = list(APP_PORTFOLIO.keys())
    weights = list(APP_PORTFOLIO.values())
    prices_normalized_copy = np.nan * prices_copy
    prices_normalized_copy.loc[date0:date1] = prices_copy[date0:date1] / prices_copy.loc[date0] - 1
    portfolio_normalized = prices_normalized_copy.mul(weights, axis=1).sum(axis=1)
    prices_normalized.insert(0, "Portfolio", portfolio_normalized)

    return prices_normalized
