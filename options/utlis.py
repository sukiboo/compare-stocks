from __future__ import annotations

import warnings

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
from plotly.colors import sample_colorscale

sns.set_theme(style="darkgrid", palette="muted", font="monospace", font_scale=1.0)
warnings.filterwarnings("ignore", message=".*constrained_layout not applied.*")


def plot_option_matrix(opt, option_type="calls"):
    option_matrix = opt.calls if option_type == "calls" else opt.puts
    cmap = "GnBu" if option_type == "calls" else "PuRd"
    color_palette = sample_colorscale(
        getattr(px.colors.sequential, cmap), np.linspace(0, 0.9, len(opt.expirations))
    )

    fig = px.scatter(
        option_matrix,
        x="optionPrice",
        y="profitPrice",
        color="expirationDate",
        hover_data=["strikePrice", "contractSymbol"],
        color_discrete_sequence=color_palette,
    )

    fig.update_traces(
        marker={
            "size": 15,
            "line": {"width": 1, "color": "rgba(128, 128, 128, 0.5)"},
            "symbol": "triangle-up" if option_type == "calls" else "triangle-down",
            "opacity": 0.75,
        },
    )

    fig.update_layout(title=f"{opt.ticker} {option_type} prices")
    fig.show()


def plot_option_matrix_3d(opt, option_type="calls", uniform_dates=True, bid_ask_spread=True):
    option_matrix = opt.calls if option_type == "calls" else opt.puts
    marker = "^" if option_type == "calls" else "v"
    cmap = "PuBuGn" if option_type == "calls" else "PuRd"

    # colors based on expiration date
    colormap = plt.colormaps[cmap](np.linspace(0.25, 1, len(opt.expirations)))
    date_to_color = {date: colormap[i] for i, date in enumerate(opt.expirations)}

    # opacity based on option price
    alpha_min = 0.2
    price_min, price_max = option_matrix["optionPrice"].min(), option_matrix["optionPrice"].max()
    get_opacity = lambda p: ((price_max - p) / (price_max - price_min) + alpha_min) / (
        1 + alpha_min
    )

    # plot option prices
    fig = plt.figure(figsize=(12, 8), constrained_layout=True)
    ax = fig.add_subplot(111, projection="3d")
    for _, contract in option_matrix.iterrows():
        x = contract["strikePrice"]
        y = (
            mdates.date2num(pd.to_datetime(contract["expirationDate"]))
            if not uniform_dates
            else opt.expirations.index(contract["expirationDate"])
        )
        z = contract["optionPrice"]
        color = date_to_color[contract["expirationDate"]]
        alpha = get_opacity(contract["optionPrice"])

        # plot estimated contract price
        ax.scatter(
            xs=x,
            ys=y,
            zs=z,
            marker=marker,
            s=50,
            color=color,
            alpha=alpha,
        )

        # plot bid-ask spread
        if bid_ask_spread:
            ax.plot(
                [x, x],
                [y, y],
                [contract["askPrice"], contract["bidPrice"]],
                color=color,
                linestyle="-",
                linewidth=2,
                alpha=alpha,
            )

    # configure axes
    if not uniform_dates:
        ax.yaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    else:
        ax.set_yticks(range(len(opt.expirations)))
        ax.set_yticklabels(opt.expirations)
    if option_type == "calls":
        plt.yticks(rotation=-30)
        ax.view_init(elev=20, azim=-60)
    else:
        plt.yticks(rotation=45)
        ax.view_init(elev=20, azim=-120)

    ax.set_title(f"{opt.ticker} {option_type} prices")
    ax.set_xlabel("strikePrice", labelpad=10)
    ax.set_ylabel("expirationDate", labelpad=30)
    ax.set_zlabel("optionPrice", labelpad=10)

    plt.show()
