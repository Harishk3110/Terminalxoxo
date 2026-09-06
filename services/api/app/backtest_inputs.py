"""Pin instruments and prior-published FX fixings before an offline run is queued."""

from datetime import UTC, datetime, time, timedelta

from sqlalchemy import select

from . import models
from .price_sources import FxRateResolver
from .quant_data import dataset_rows
from .research_inputs import ResearchInput, bars_frame, pin_input
from .terminal_analytics import instrument


def pin_backtest_inputs(session, params):
    symbols = params.get("symbols") or [params.get("symbol", "SPY")]
    if (
        not isinstance(symbols, list)
        or not 1 <= len(symbols) <= 12
        or any(not isinstance(symbol, str) for symbol in symbols)
        or len(set(symbols)) != len(symbols)
    ):
        raise ValueError("Select a unique list of one to twelve securities")
    base = params.get("base_currency", "SGD")
    if not isinstance(base, str) or len(base) != 3 or not base.isalpha():
        raise ValueError("A three-letter base currency is required")
    base = base.upper()
    pinned, fixings, sectors = {}, {}, {}
    resolver = FxRateResolver(session)
    for symbol in symbols:
        item = instrument(session, symbol)
        if item.asset_class not in ("Equity", "ETF"):
            raise ValueError("This offline simulator supports equity and ETF research only")
        sectors[symbol] = item.sector
        request = ResearchInput(
            **{
                key: params[key]
                for key in ResearchInput.model_fields
                if params.get(key) and key != "symbol"
            },
            symbol=symbol,
        )
        evidence = pin_input(session, request)
        rows, _ = dataset_rows(session, evidence["dataset_version_id"])
        frame = bars_frame(rows, symbol, request.start, request.end)
        currencies = {
            row.get("currency", evidence["schema"].get("currency", item.currency))
            for row in rows
            if row.get("symbol", symbol) == symbol
        }
        if currencies != {item.currency}:
            raise ValueError("Dataset and security currency do not agree")
        pinned[symbol] = evidence
        demo_fx = (
            session.scalars(
                select(models.FxRate)
                .where(
                    models.FxRate.base_currency == item.currency,
                    models.FxRate.quote_currency == base,
                    models.FxRate.provider == "DemoProvider",
                )
                .order_by(models.FxRate.date)
            ).all()
            if request.source_mode == "DEMO_RESEARCH"
            else []
        )
        daily = {}
        for day in frame.index:
            cutoff = datetime.combine(day.date(), time.min, UTC) - timedelta(microseconds=1)
            if item.currency == base:
                value, provenance = (
                    1,
                    {"source": "IDENTITY", "data_state": "CALCULATED", "as_of": cutoff.isoformat()},
                )
            elif request.source_mode == "DEMO_RESEARCH":
                prior = [row for row in demo_fx if row.date < day.date()]
                chosen = prior[-1] if prior else None
                if not chosen or (day.date() - chosen.date).days > 4:
                    raise ValueError(
                        f"Prior DEMO FX fixing missing for {item.currency}/{base} on {day.date()}"
                    )
                value, provenance = (
                    chosen.rate,
                    {
                        "source": chosen.provider,
                        "data_state": chosen.quality,
                        "as_of": chosen.date.isoformat(),
                        "id": chosen.id,
                    },
                )
            else:
                value, provenance = resolver.resolve(item.currency, base, cutoff)
                if value is None or provenance.get("stale"):
                    raise ValueError(
                        f"Prior published FX fixing missing or stale for {item.currency}/{base} on {day.date()}"
                    )
                if "DEMO" in provenance.get("data_state", "") and "DEMO" not in evidence["quality"]:
                    raise ValueError("Non-demo research cannot silently use synthetic FX")
            if float(value) <= 0:
                raise ValueError("FX fixings must be positive")
            daily[day.date().isoformat()] = {"rate": str(value), "provenance": provenance}
        fixings[symbol] = daily
    return {
        **params,
        "symbol": symbols[0],
        "symbols": symbols,
        "base_currency": base,
        "_datasets": pinned,
        "_fx": fixings,
        "_sectors": sectors,
        "dataset_version_id": pinned[symbols[0]]["dataset_version_id"],
        "dataset_id": pinned[symbols[0]]["dataset_id"],
    }
