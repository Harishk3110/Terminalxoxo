"""Optional paper-account reader. No broker action endpoints or execution calls."""

import argparse
import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from agent import SERVICE, credential_backend, validate_endpoint
from ib_async import IB, ExecutionFilter, StartupFetch


def finite(value, positive=False):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or abs(number) > Decimal("1e16") or positive and number <= 0:
            return None
        return str(number)
    except Exception:
        return None


async def read_snapshot(args):
    if (
        args.host not in {"localhost", "127.0.0.1", "::1"}
        or args.port not in {7497, 4002}
        or not args.account.startswith("DU")
    ):
        raise ValueError(
            "Only loopback TWS/Gateway paper ports and an explicit DU paper account are allowed"
        )
    ib = IB()
    try:
        fields = StartupFetch.POSITIONS | StartupFetch.ACCOUNT_UPDATES | StartupFetch.EXECUTIONS
        await ib.connectAsync(
            args.host,
            args.port,
            clientId=args.client_id,
            timeout=10,
            readonly=True,
            account=args.account,
            fetchFields=fields,
        )
        if args.account not in ib.managedAccounts():
            raise ValueError("Configured paper account is not accessible")
        summary = await ib.accountSummaryAsync(args.account)
        navs = [
            r
            for r in summary
            if r.tag == "NetLiquidation" and r.currency in {args.currency, "BASE"}
        ]
        if not navs or finite(navs[0].value) is None:
            raise ValueError("No broker NAV in the explicitly configured base currency")
        values = ib.accountValues(args.account)
        fx = {
            v.currency: v.value
            for v in values
            if v.tag == "ExchangeRate" and len(v.currency) == 3 and finite(v.value, True)
        }
        fx[args.currency] = "1"
        cash = [
            {"currency": r.currency, "amount": r.value}
            for r in values
            if r.tag == "CashBalance"
            and r.currency != "BASE"
            and len(r.currency) == 3
            and finite(r.value) is not None
        ]
        positions = []
        for row in ib.portfolio(args.account):
            contract = row.contract
            multiplier = finite(contract.multiplier or 1, True)
            if multiplier is None:
                raise ValueError("Broker position multiplier unavailable")
            average = finite(Decimal(str(row.averageCost)) / Decimal(multiplier))
            if average is None:
                raise ValueError("Broker position average cost unavailable")
            positions.append(
                {
                    "symbol": contract.symbol
                    if contract.secType == "STK"
                    else contract.localSymbol,
                    "currency": contract.currency,
                    "quantity": str(row.position),
                    "average_cost": average,
                    "multiplier": multiplier,
                    "market_price": finite(row.marketPrice, True),
                }
            )
        fills = []
        for fill in await ib.reqExecutionsAsync(ExecutionFilter(acctCode=args.account)):
            execution, contract, commission = fill.execution, fill.contract, fill.commissionReport
            fills.append(
                {
                    "execution_id": execution.execId,
                    "symbol": contract.symbol
                    if contract.secType == "STK"
                    else contract.localSymbol,
                    "currency": contract.currency,
                    "contract_type": contract.secType,
                    "side": execution.side,
                    "quantity": str(execution.shares),
                    "price": str(execution.price),
                    "time": execution.time.astimezone(UTC).isoformat(),
                    "commission": finite(commission.commission),
                    "commission_currency": commission.currency or None,
                }
            )
        return {
            "account": args.account,
            "currency": args.currency,
            "as_of": datetime.now(UTC).isoformat(),
            "nav": navs[0].value,
            "cash": cash,
            "positions": positions,
            "fills": fills,
            "fx": fx,
        }
    finally:
        ib.disconnect()


async def run(args):
    url = validate_endpoint(args.url, args.allow_loopback_http)
    token = credential_backend().get_password(SERVICE, url)
    if not token:
        raise RuntimeError("Pair a token with read-only broker scope first")
    async with httpx.AsyncClient(
        base_url=url,
        headers={"Authorization": "Bearer " + token},
        timeout=30,
        follow_redirects=False,
    ) as client:
        while True:
            try:
                snapshot = await read_snapshot(args)
                response = await client.post("/agent/v1/broker-snapshots", json=snapshot)
                response.raise_for_status()
                print("Paper-account snapshot stored; fills require explicit ledger approval.")
            except (httpx.HTTPError, ConnectionError, TimeoutError, ValueError) as exc:
                print("Read-only synchronization failed:", type(exc).__name__)
                if args.once:
                    raise RuntimeError("Paper snapshot was not stored") from None
            if args.once:
                return
            await asyncio.sleep(30)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument(
        "--currency", required=True, help="Verified base currency of the paper account"
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7497)
    parser.add_argument("--client-id", type=int, default=3110)
    parser.add_argument("--allow-loopback-http", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
