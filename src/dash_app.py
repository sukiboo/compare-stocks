import json
from collections.abc import Sequence
from typing import Any

from dash import Dash, Input, Output, State, ctx, dcc, html, no_update
from plotly.graph_objects import Figure

from src.constants import (
    APP_DATE_START,
    APP_INITIAL_INTERVAL_DAYS,
    APP_INITIAL_TICKERS,
    APP_MAX_TICKERS,
)
from src.prices import Prices
from src.style_elements import (
    BUTTON_STYLE_ACTIVE,
    BUTTON_STYLE_INACTIVE,
    plot_prices,
    setup_interval_buttons,
    setup_ticker_selection,
)
from src.utils import (
    adjust_date_range,
    date_to_idx_range,
    get_date_range,
    normalize_ticker_symbol,
)

INTERVAL_LENGTH_TOLERANCE_DAYS = 2

_JS_HELPERS = """
    function _nearestIdx(tsMs, t) {
        let lo = 0, hi = tsMs.length - 1;
        if (t <= tsMs[lo]) return lo;
        if (t >= tsMs[hi]) return hi;
        while (lo < hi - 1) {
            const mid = (lo + hi) >> 1;
            if (tsMs[mid] < t) lo = mid; else hi = mid;
        }
        return (t - tsMs[lo] < tsMs[hi] - t) ? lo : hi;
    }
    function _msToDate(ms) {
        const d = new Date(ms);
        const y = d.getUTCFullYear();
        const m = String(d.getUTCMonth() + 1).padStart(2, '0');
        const day = String(d.getUTCDate()).padStart(2, '0');
        return y + '-' + m + '-' + day;
    }
    function _getDateRange(layout) {
        const r2 = layout && layout.xaxis2 && layout.xaxis2.range;
        if (r2 && r2[0] && r2[1]) return [String(r2[0]).slice(0, 10), String(r2[1]).slice(0, 10)];
        const r1 = layout && layout.xaxis && layout.xaxis.range;
        if (r1 && r1[0] && r1[1]) return [String(r1[0]).slice(0, 10), String(r1[1]).slice(0, 10)];
        return [null, null];
    }
    function _rescale(figure, rawPrices, d0, d1) {
        const tsMs = rawPrices.timestamps_ms;
        const tickers = rawPrices.tickers;
        const prices = rawPrices.prices;
        const N = tickers.length;
        if (!N) return figure;
        const idx0 = _nearestIdx(tsMs, Date.parse(d0));
        const idx1 = _nearestIdx(tsMs, Date.parse(d1));
        const newFig = Object.assign({}, figure);
        newFig.data = figure.data.slice();
        newFig.layout = Object.assign({}, figure.layout);
        newFig.layout.xaxis = Object.assign({}, figure.layout.xaxis, {range: [d0, d1]});
        newFig.layout.xaxis2 = Object.assign({}, figure.layout.xaxis2, {range: [d0, d1]});
        const y2 = Object.assign({}, figure.layout.yaxis2 || {}, {autorange: true});
        delete y2.range;
        newFig.layout.yaxis2 = y2;
        for (let i = 0; i < N; i++) {
            const p = prices[tickers[i]];
            if (!p) continue;
            const base = p[idx0];
            const y = new Array(p.length);
            const cd = new Array(p.length);
            for (let j = 0; j < p.length; j++) {
                const price = p[j];
                const priceStr = '$' + price.toLocaleString('en-US',
                    {minimumFractionDigits: 2, maximumFractionDigits: 2});
                if (j < idx0 || j > idx1) {
                    y[j] = null;
                    cd[j] = ['', priceStr];
                } else {
                    const yj = 100 * (price / base - 1);
                    y[j] = yj;
                    const pctStr = (yj >= 0 ? '+' : '') + yj.toFixed(2) + '%';
                    cd[j] = [pctStr, priceStr];
                }
            }
            newFig.data[N + i] = Object.assign({}, newFig.data[N + i], {y: y, customdata: cd});
        }
        return newFig;
    }
"""


class NormalizedAssetPricesApp:

    def __init__(
        self,
        initial_tickers: list[str] = APP_INITIAL_TICKERS,
        date_start: str = APP_DATE_START,
        initial_interval_days: int = APP_INITIAL_INTERVAL_DAYS,
    ) -> None:
        self.setup_env(initial_tickers, date_start, initial_interval_days)
        self.interval_buttons_html, self.interval_buttons_ids, self.interval_offsets = (
            setup_interval_buttons()
        )
        self.initial_active_btn = next(
            (
                bid
                for bid in self.interval_buttons_ids
                if bid != "btn-ytd" and self.interval_offsets[bid] == initial_interval_days
            ),
            None,
        )
        self.initial_tickers = initial_tickers
        self.ticker_selection = setup_ticker_selection(initial_tickers)
        self.setup_app()

    def setup_env(
        self, initial_tickers: list[str], date_start: str, initial_interval_days: int
    ) -> None:
        self.prices = Prices(initial_tickers, date_start)
        self.timestamps = self.prices.date_range
        self.idx_range = date_to_idx_range(
            self.timestamps,
            adjust_date_range(self.timestamps, initial_interval_days),
        )
        self.fig = plot_prices(
            self.timestamps,
            self.prices.prices_normalized,
            self.prices.prices_raw,
            self.prices.rolling_changes,
            self.idx_range,
        )

    def update_figure(
        self, tickers: list[str], date_range: Sequence[str | None] = [None, None]
    ) -> Figure:
        tickers_updated, range_updated = False, False

        if list(tickers) != self.prices.tickers:
            self.prices.update_tickers(tickers)
            tickers_updated = True
            print(f"tickers update: {', '.join(tickers) if tickers else 'None'}")

        idx_range = date_to_idx_range(self.timestamps, date_range)
        if idx_range != self.idx_range:
            self.idx_range = idx_range
            range_updated = True
            print(f"interval update: {date_range=}")

        if tickers_updated or range_updated:
            self.fig = plot_prices(
                self.timestamps,
                self.prices.prices_normalized,
                self.prices.prices_raw,
                self.prices.rolling_changes,
                idx_range,
            )

        return self.fig

    def _raw_prices_payload(self) -> dict[str, Any]:
        return {
            "timestamps_ms": (self.timestamps.astype("int64") // 10**6).tolist(),
            "tickers": list(self.prices.tickers),
            "prices": {t: self.prices.prices_raw[t].tolist() for t in self.prices.tickers},
        }

    def setup_app(self) -> None:
        self.app = Dash(__name__)
        self.app.layout = html.Div(
            [
                dcc.Graph(id="plotly-normalized-asset-prices", figure=self.fig),
                dcc.Store(id="debounced-relayout", data=None),
                dcc.Store(id="active-interval-btn", data=self.initial_active_btn),
                dcc.Store(id="raw-prices", data=self._raw_prices_payload()),
                self.interval_buttons_html,
                self.ticker_selection,
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

        button_ids_js = json.dumps(self.interval_buttons_ids)
        active_style_js = json.dumps(BUTTON_STYLE_ACTIVE)
        inactive_style_js = json.dumps(BUTTON_STYLE_INACTIVE)
        self.app.clientside_callback(
            f"""
            function (activeBtn) {{
                const ids = {button_ids_js};
                const active = {active_style_js};
                const inactive = {inactive_style_js};
                return ids.map(id => id === activeBtn ? active : inactive);
            }}
            """,
            [Output(button_id, "style") for button_id in self.interval_buttons_ids],
            Input("active-interval-btn", "data"),
        )

        @self.app.callback(
            [
                Output("ticker-selection", "options"),
                Output("ticker-selection", "value"),
                Output("ticker-input", "value"),
                Output("ticker-input", "placeholder"),
            ],
            [Input("ticker-input", "n_submit"), Input("ticker-selection", "value")],
            [State("ticker-input", "value"), State("ticker-selection", "value")],
            prevent_initial_call=True,
        )
        def update_tickers(
            n_submit: int,
            selected_tickers: list[str] | None,
            input_ticker: str,
            current_tickers: list[str] | None,
        ) -> tuple[list[dict[str, str]], list[str], str, str]:
            triggered_id = ctx.triggered_id
            tickers = current_tickers if current_tickers else []
            options = [{"label": t, "value": t} for t in tickers]

            if triggered_id == "ticker-input" and input_ticker.strip():
                ticker = normalize_ticker_symbol(input_ticker)
                if ticker in tickers:
                    return options, tickers, "", f"⚠️ `{ticker}` already added"
                elif not self.prices.is_valid_ticker(ticker):
                    return options, tickers, "", f"❌ `{ticker}` is not valid"
                elif len(tickers) >= APP_MAX_TICKERS:
                    return options, tickers, "", f"⛔ {APP_MAX_TICKERS} tickers max!"
                else:
                    tickers = tickers + [ticker]
                    options = [{"label": t, "value": t} for t in tickers]
                    return options, tickers, "", f"✅ `{ticker}` added"
            else:
                tickers = selected_tickers if selected_tickers else []
                options = [{"label": t, "value": t} for t in tickers]
                return options, tickers, input_ticker or "", "Enter ticker symbol..."

        offsets_js = json.dumps(self.interval_offsets)
        btn_ids_js_inner = json.dumps(self.interval_buttons_ids)
        self.app.clientside_callback(
            f"""
            function (...args) {{
                {_JS_HELPERS}
                const btnIds = {btn_ids_js_inner};
                const offsets = {offsets_js};
                const nBtns = btnIds.length;
                const rawPrices = args[nBtns];
                const currentFigure = args[nBtns + 1];
                const ctx = window.dash_clientside.callback_context;
                const triggeredId = ctx && ctx.triggered_id;
                if (!triggeredId || !btnIds.includes(triggeredId) ||
                    !rawPrices || !currentFigure) {{
                    return [window.dash_clientside.no_update, window.dash_clientside.no_update];
                }}
                const tsMs = rawPrices.timestamps_ms;
                const first = tsMs[0];
                const last = tsMs[tsMs.length - 1];
                const offsetDays = offsets[triggeredId];
                let baseEndMs = last;
                if (triggeredId !== 'btn-ytd') {{
                    const range = _getDateRange(currentFigure.layout);
                    if (range[1]) {{
                        const parsed = Date.parse(range[1]);
                        if (!isNaN(parsed)) baseEndMs = parsed;
                    }}
                }}
                const startMs = Math.max(first, baseEndMs - offsetDays * 86400000);
                const d0 = _msToDate(startMs);
                const d1 = _msToDate(baseEndMs);
                const newFig = _rescale(currentFigure, rawPrices, d0, d1);
                return [newFig, triggeredId];
            }}
            """,
            [
                Output("plotly-normalized-asset-prices", "figure", allow_duplicate=True),
                Output("active-interval-btn", "data", allow_duplicate=True),
            ],
            [Input(bid, "n_clicks") for bid in self.interval_buttons_ids],
            [
                State("raw-prices", "data"),
                State("plotly-normalized-asset-prices", "figure"),
            ],
            prevent_initial_call=True,
        )

        tolerance_days = INTERVAL_LENGTH_TOLERANCE_DAYS
        self.app.clientside_callback(
            f"""
            function (debounced, rawPrices, currentFigure, activeBtn) {{
                {_JS_HELPERS}
                const offsets = {offsets_js};
                const tolerance = {tolerance_days};
                if (!debounced || !rawPrices || !currentFigure) {{
                    return [window.dash_clientside.no_update, window.dash_clientside.no_update];
                }}
                const range = _getDateRange(currentFigure.layout);
                if (!range[0] || !range[1]) {{
                    return [
                        window.dash_clientside.no_update,
                        activeBtn ? null : window.dash_clientside.no_update,
                    ];
                }}
                let newActive = activeBtn;
                if (activeBtn) {{
                    const lengthDays =
                        (Date.parse(range[1]) - Date.parse(range[0])) / 86400000;
                    const expected = offsets[activeBtn];
                    if (Math.abs(lengthDays - expected) > tolerance) {{
                        newActive = null;
                    }}
                }}
                const newFig = _rescale(currentFigure, rawPrices, range[0], range[1]);
                return [newFig, newActive];
            }}
            """,
            [
                Output("plotly-normalized-asset-prices", "figure", allow_duplicate=True),
                Output("active-interval-btn", "data", allow_duplicate=True),
            ],
            Input("debounced-relayout", "data"),
            [
                State("raw-prices", "data"),
                State("plotly-normalized-asset-prices", "figure"),
                State("active-interval-btn", "data"),
            ],
            prevent_initial_call=True,
        )

        @self.app.callback(
            [
                Output("plotly-normalized-asset-prices", "figure", allow_duplicate=True),
                Output("raw-prices", "data", allow_duplicate=True),
            ],
            Input("ticker-selection", "value"),
            State("plotly-normalized-asset-prices", "figure"),
            prevent_initial_call=True,
        )
        def on_tickers_change(
            tickers: list[str] | None,
            current_figure: dict[str, Any],
        ) -> tuple[Any, Any]:
            tickers = tickers or []
            if list(tickers) == self.prices.tickers:
                return no_update, no_update
            date_range = get_date_range(current_figure["layout"])
            fig = self.update_figure(tickers, date_range)
            return fig, self._raw_prices_payload()

    def run(self, **kwargs: Any) -> None:
        self.app.run_server(**kwargs)


def create_app() -> tuple[NormalizedAssetPricesApp, Any]:
    dash_app = NormalizedAssetPricesApp()
    server = dash_app.app.server
    return dash_app, server
