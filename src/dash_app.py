import itertools

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html


class NormalizedAssetPricesApp:

    def __init__(self, prices):
        self.setup_env(prices)
        self.setup_app()

    def setup_env(self, prices):
        self.prices = prices / prices.iloc[0]
        self.percentage_changes = (self.prices / (self.prices.shift(1) + 1e-7) - 1).fillna(0)
        self.rolling_changes = self.percentage_changes.rolling(window=251, min_periods=1).sum()
        self.timestamps = self.prices.index
        self.idx_range = [None, None]
        self.fig = self.plot_prices()

    def normalize_prices(self):
        idx0, idx1 = self.idx_range
        date0, date1 = self.timestamps[idx0], self.timestamps[idx1]
        price = self.prices.loc[date0]
        self.prices_normalized = np.nan * self.prices
        self.prices_normalized.loc[date0:date1] = 100 * (self.prices[date0:date1] / price - 1)

    def plot_prices(self, date_range=[None, None]):
        idx_range = self.date_to_idx_range(date_range)
        # do not update the figure if the range is unchanged
        if idx_range == self.idx_range:
            return self.fig
        else:
            self.idx_range = idx_range
            self.normalize_prices()

        fig = go.Figure()

        # rangeslider plot
        colors = itertools.cycle(px.colors.qualitative.Set2)
        for asset in self.prices.columns:
            fig.add_trace(
                go.Scatter(
                    x=self.timestamps,
                    y=self.rolling_changes[asset],
                    line=dict(color=next(colors)),
                    xaxis="x1",
                    yaxis="y1",
                    showlegend=False,
                )
            )

        # main plot
        colors = itertools.cycle(px.colors.qualitative.Set2)
        for asset in self.prices_normalized.columns:
            fig.add_trace(
                go.Scatter(
                    x=self.timestamps,
                    y=self.prices_normalized[asset],
                    line=dict(width=3, color=next(colors)),
                    name=asset,
                    xaxis="x2",
                    yaxis="y2",
                )
            )

        # dummy traces to show ticks on the right
        for _ in self.prices_normalized.columns:
            fig.add_trace(
                go.Scatter(
                    x=[],
                    y=[],
                    xaxis="x2",
                    yaxis="y3",
                    showlegend=False,
                )
            )

        # configure axes
        xaxis1_dict = dict(rangeslider=dict(visible=True, thickness=0.1), tickangle=-30, nticks=20)
        xaxis2_dict = dict(matches="x1", showticklabels=False)
        if all(date_range):
            xaxis1_dict["range"] = date_range
            xaxis2_dict["range"] = date_range
        yaxis1_dict = dict(showticklabels=False)
        yaxis2_dict = dict(
            title="relative price change",
            nticks=12,
            tickformat=".0f",
            ticksuffix="%",
            ticks="outside",
        )
        yaxis3_dict = dict(
            matches="y2",
            overlaying="y2",
            side="right",
            nticks=12,
            tickformat=".0f",
            ticksuffix="%",
            ticks="outside",
        )

        fig.update_layout(
            xaxis1=xaxis1_dict,
            yaxis1=yaxis1_dict,
            xaxis2=xaxis2_dict,
            yaxis2=yaxis2_dict,
            yaxis3=yaxis3_dict,
            uirevision="constant",  # prevent resets from the xrange compression
            font=dict(family="Courier New, Monospace", size=14, weight="bold"),
            legend=dict(
                title=dict(text="assets: "),
                orientation="h",
                x=0.0,
                y=1.0,
                xanchor="left",
                yanchor="bottom",
            ),
            margin=dict(t=50, b=50),
            template="plotly",
            height=600,
        )

        return fig

    def date_to_idx_range(self, date_range):
        idx_range = (
            self.timestamps.get_indexer(date_range, method="nearest").tolist()
            if all(date_range)
            else [0, -1]
        )
        return idx_range

    def get_date_range(self, figure_layout):
        date_range = [None, None]
        # Check xaxis2 first
        if "xaxis2" in figure_layout and figure_layout["xaxis2"].get("range"):
            date_range = figure_layout["xaxis2"]["range"]
        # If not found, check xaxis1
        elif "xaxis1" in figure_layout and figure_layout["xaxis1"].get("range"):
            date_range = figure_layout["xaxis1"]["range"]
        return date_range

    def setup_app(self):
        self.app = Dash(__name__)

        self.app.layout = html.Div(
            [
                dcc.Graph(id="plotly-normalized-asset-prices", figure=self.fig),
                dcc.Store(id="debounced-relayout", data=None),
            ]
        )

        # wait 100ms between the updates, even though o1 insists that it's not a
        # "true debounce": https://chatgpt.com/share/677b0a08-712c-800c-8aa9-d4abdfa50f11
        self.app.clientside_callback(
            """
            function (relayoutData) {
                return new Promise((resolve) => {
                    setTimeout(function() {
                        resolve('Figure updated.');
                    }, 100);
                });
            }
            """,
            Output("debounced-relayout", "data"),
            Input("plotly-normalized-asset-prices", "relayoutData"),
            prevent_initial_call=True,
        )

        @self.app.callback(
            Output("plotly-normalized-asset-prices", "figure"),
            Input("debounced-relayout", "data"),
            State("plotly-normalized-asset-prices", "figure"),
            prevent_initial_call=True,
        )
        def update_figure_after_delay(relayout_data, current_figure):
            date_range = self.get_date_range(current_figure["layout"])
            fig = self.plot_prices(date_range)
            return fig

    def run(self, **kwargs):
        self.app.run_server(**kwargs)


def create_app(df):
    dash_app = NormalizedAssetPricesApp(df)
    server = dash_app.app.server
    return dash_app, server
