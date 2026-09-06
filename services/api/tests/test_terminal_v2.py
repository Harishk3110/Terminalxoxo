import io
import math
import uuid

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy import delete

from app import models
from app.database import SessionLocal
from app.main import app, settings
from app.object_storage import ObjectStorage
from app.terminal_analytics import FUNCTIONS, portfolio_analytics, stress_result, valuation
from app.terminal_worker import execute_run, backtest_result

client = TestClient(app)


def test_registry_is_unique_and_bootstrap_matches():
    payload = client.get('/api/v1/terminal/bootstrap').json()
    assert len(FUNCTIONS) >= 100
    assert len({f['mnemonic'] for f in FUNCTIONS}) == len(FUNCTIONS)
    assert payload['functions'] == FUNCTIONS
    assert len(payload['scenarios']) == 16
    assert all(q['source'] and q['as_of'] and q['market_state'] == 'DEMO' for q in payload['quotes'])


def test_workspace_round_trip():
    configuration = {'tabs': [{'id': 'a', 'title': 'STRESS', 'route': '/stress-tests'}], 'tabStates': {'a': {'equity_shock': -17}}, 'sizes': [75, 25]}
    created = client.post('/api/v1/workspaces', json={'name': 'Test ' + str(uuid.uuid4()), 'configuration': configuration}).json()
    changed = client.post(f"/api/v1/workspaces/{created['id']}", json={'name': 'Renamed test', 'configuration': configuration})
    assert changed.status_code == 200
    saved = next(w for w in client.get('/api/v1/workspaces').json()['items'] if w['id'] == created['id'])
    assert saved['configuration'] == configuration
    assert saved['name'] == 'Renamed test'
    assert client.post(f"/api/v1/workspaces/{created['id']}/delete").status_code == 200


def test_risk_and_stress_are_recomputed_and_reconcile():
    with SessionLocal() as session:
        data = portfolio_analytics(session)
        a = stress_result(session, {'_portfolio': data, 'equity_shock': -10})
        b = stress_result(session, {'_portfolio': data, 'equity_shock': -20})
        fx = stress_result(session, {'_portfolio': data, 'equity_shock': 0, 'fx_shock': 5})
        assert a['loss'] != b['loss']
        assert a['loss'] == pytest.approx(sum(r['pnl'] for r in a['contributions']))
        assert a['post_nav'] == pytest.approx(a['pre_nav'] + a['loss'])
        assert b['loss'] == pytest.approx(2 * a['loss'], abs=.05)
        assert fx['loss'] > 0
        assert len(data['curve']) > 50
        assert all(math.isfinite(v) for v in data['risk'].values() if isinstance(v, (float, int)))
        with pytest.raises(ValueError):
            stress_result(session, {'_portfolio': data, 'equity_shock': float('nan')})


def test_run_lifecycle_and_immutable_inputs(monkeypatch):
    monkeypatch.setattr('app.terminal_api.launch_worker', lambda run_id: None)
    queued = client.post('/api/v1/terminal/runs', json={'kind': 'stress', 'name': 'Unit stress', 'parameters': {'equity_shock': -10}})
    assert queued.status_code == 202
    run = queued.json()
    assert run['status'] == 'QUEUED'
    assert '_portfolio' not in run['parameters']
    with SessionLocal() as session:
        frozen = session.get(models.AnalysisRun, run['id']).parameters['_portfolio']
    execute_run(run['id'])
    done = client.get(f"/api/v1/terminal/runs/{run['id']}").json()
    assert done['status'] == 'SUCCEEDED', done['error']
    assert [h['state'] for h in done['history']] == ['QUEUED', 'RUNNING', 'SUCCEEDED']
    assert done['result']['pre_nav'] == float(frozen['portfolio']['nav'])
    report = client.get(f"/api/v1/terminal/runs/{run['id']}/export").json()
    downloaded = client.get(report['download_url'])
    assert downloaded.status_code == 200
    book = load_workbook(io.BytesIO(downloaded.content), data_only=False)
    assert book['Summary']['C2'].value == '=A2+B2'


def test_cancelled_run_never_publishes_a_result(monkeypatch):
    monkeypatch.setattr('app.terminal_api.launch_worker', lambda run_id: None)
    run = client.post('/api/v1/terminal/runs', json={'kind': 'stress', 'name': 'Cancel test'}).json()
    assert client.post(f"/api/v1/terminal/runs/{run['id']}/cancel").status_code == 200
    execute_run(run['id'])
    assert client.get(f"/api/v1/terminal/runs/{run['id']}").json()['result'] is None


def test_upload_validation_import_and_backtest(monkeypatch):
    import pandas as pd
    dates = pd.date_range('2024-01-01', periods=240, freq='B')
    csv = 'day,px,open,high,low\n' + '\n'.join(f'{d.date()},{100 + .1*i + 10*math.sin(i/8)},{100 + .1*i + 10*math.sin(i/8)},{102 + .1*i + 10*math.sin(i/8)},{98 + .1*i + 10*math.sin(i/8)}' for i, d in enumerate(dates))
    preview = client.post('/api/v1/uploads/preview', files={'file': ('fixture.csv', csv, 'text/csv')})
    assert preview.status_code == 200, preview.text
    upload = preview.json()
    payload = {'upload_id': upload['upload_id'], 'name': 'Unit fixture', 'mapping': {'date': 'day', 'close': 'px', 'open': 'open', 'high': 'high', 'low': 'low'}, 'licence': 'Self-created test data'}
    assert client.post('/api/v1/uploads/validate', json=payload).json()['valid']
    imported = client.post('/api/v1/uploads/import', json=payload)
    assert imported.status_code == 200, imported.text
    dataset = imported.json()
    monkeypatch.setattr('app.terminal_api.launch_worker', lambda run_id: None)
    queued = client.post('/api/v1/terminal/runs', json={'kind': 'backtest', 'name': 'Uploaded data test', 'parameters': {'dataset_id': dataset['dataset_id'], 'base_currency': 'USD', 'fast': 5, 'slow': 15}})
    assert queued.status_code == 202, queued.text
    run = queued.json()
    execute_run(run['id'])
    result = client.get(f"/api/v1/terminal/runs/{run['id']}").json()
    assert result['status'] == 'SUCCEEDED', result['error']
    assert result['result']['quality'] == 'USER PROVIDED'
    assert result['parameters']['dataset_version_id'] == dataset['version_id']
    assert len(result['result']['equity_curve']) == 240
    assert result['result']['metrics']['trade_count'] > 0


def test_invalid_upload_cannot_be_imported():
    response = client.post('/api/v1/uploads/preview', files={'file': ('bad.csv', 'date,close\ninvalid,-20', 'text/csv')})
    payload = {'upload_id': response.json()['upload_id'], 'name': 'Invalid', 'mapping': {'date': 'date', 'close': 'close'}, 'licence': 'Self-created'}
    assert not client.post('/api/v1/uploads/validate', json=payload).json()['valid']
    assert client.post('/api/v1/uploads/import', json=payload).status_code == 422


@pytest.mark.parametrize('filename,body', [('bad.json', '[1,2]'), ('bad.json', 'false'), ('bad.xlsx', 'not a workbook')])
def test_malformed_files_return_validation_error(filename, body):
    assert client.post('/api/v1/uploads/preview', files={'file': (filename, body)}).status_code == 422


def test_valuation_changes_and_rejects_invalid_discount_rate():
    with SessionLocal() as session:
        low = valuation(session, 'AAPL', wacc=.08)
        high = valuation(session, 'AAPL', wacc=.15)
        assert low['fair_value'] > high['fair_value']
        assert low['quality'] == 'DEMO DATA'
        with pytest.raises(ValueError):
            valuation(session, 'AAPL', wacc=.02, terminal_growth=.03)


def test_concurrent_first_load_of_synthetic_financials():
    from concurrent.futures import ThreadPoolExecutor
    with SessionLocal() as session:
        key = session.scalar(select(models.Instrument.id).where(models.Instrument.symbol == 'NVDA'))
        session.execute(delete(models.FundamentalSnapshot).where(models.FundamentalSnapshot.instrument_id == key))
        session.commit()
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.get('/api/v1/fundamentals/NVDA'), range(4)))
    assert all(response.status_code == 200 for response in responses)
    assert all(response.json()['items'] == responses[0].json()['items'] for response in responses)


def test_oversell_is_rejected():
    response = client.post('/api/v1/portfolios/default/transactions', json={'transaction_type': 'SELL', 'trade_date': '2026-09-05', 'symbol': 'AAPL', 'quantity': 999999, 'price': 200, 'currency': 'USD', 'fx_rate_to_base': 1.3})
    assert response.status_code == 400


def test_storage_rejects_path_traversal():
    with pytest.raises(ValueError):
        ObjectStorage().get_bytes('../config.py')


@pytest.mark.parametrize('environment', ['local-demo', 'production-paper'])
def test_private_api_requires_authentication_in_every_environment(monkeypatch, environment):
    monkeypatch.setattr(settings, 'knk_env', environment)
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/v1/terminal/portfolio').status_code == 401
        assert anonymous.get('/api/v1/workspaces').status_code == 401
    assert client.get('/api/v1/public/content').status_code == 404


def test_backtest_costs_affect_results():
    with SessionLocal() as session:
        cheap = backtest_result(session, {'symbol': 'SPY', 'base_currency': 'USD', 'fast': 5, 'slow': 15, 'fee_bps': 0, 'slippage_bps': 0})
        costly = backtest_result(session, {'symbol': 'SPY', 'base_currency': 'USD', 'fast': 5, 'slow': 15, 'fee_bps': 50, 'slippage_bps': 20})
        assert cheap['final_equity'] != costly['final_equity']
        assert len(cheap['equity_curve']) >= 80
