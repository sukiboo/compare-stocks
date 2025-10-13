import re
from datetime import timedelta

import numpy as np
import pandas as pd
from dateutil import parser  # type: ignore


def normalize_ticker_symbol(ticker_input):
    """Remove all non-alphanumeric characters from ticker input, return uppercase."""
    return re.sub(r"[^A-Z0-9]", "", ticker_input.upper())


def get_available_tickers():
    """This list is too limited, I opted for any input + validation in the app."""
    nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    nyse_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
    nasdaq_tickers = pd.read_csv(nasdaq_url, sep="|")["Symbol"].dropna().tolist()[:-1]
    nyse_tickers = pd.read_csv(nyse_url, sep="|")["ACT Symbol"].dropna().tolist()[:-1]
    all_tickers = sorted(set(nasdaq_tickers + nyse_tickers))  # type: ignore
    return all_tickers


def date_to_idx_range(timestamps, date_range):
    idx_range = (
        timestamps.get_indexer(date_range, method="nearest").tolist()
        if all(date_range)
        else [0, -1]
    )
    return idx_range


def get_date_range(figure_layout):
    date_range = [None, None]
    # check xaxis2 first
    if "xaxis2" in figure_layout and figure_layout["xaxis2"].get("range"):
        date_range = figure_layout["xaxis2"]["range"]
    # if not found, check xaxis1
    elif "xaxis1" in figure_layout and figure_layout["xaxis1"].get("range"):
        date_range = figure_layout["xaxis1"]["range"]
    # else:
    #     print(figure_layout)
    return date_range


def adjust_date_range(timestamps, offset_days, triggered_id="btn-1y", date_range=None):
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


def normalize_prices(prices, date_range):
    date0, date1 = date_range
    prices_normalized = np.nan * prices
    prices_normalized.loc[date0:date1] = prices[date0:date1] / prices.loc[date0] - 1
    return prices_normalized
