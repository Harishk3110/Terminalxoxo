from pathlib import Path

import pytest
from app import models
from app.data_mapping import (
    filename_metadata,
    normalize,
    parse_file,
    seed_profiles,
    suggest_mapping,
)
from sqlalchemy import select

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"


@pytest.mark.parametrize(
    ("filename", "profile_code", "count"),
    [
        ("positions.csv", "GENERIC_POSITIONS", 1),
        ("transactions.csv", "GENERIC_PORTFOLIO_TRANSACTIONS", 3),
        ("prices.csv", "GENERIC_OHLCV", 2),
        ("fx.csv", "GENERIC_FX_HISTORY", 2),
        ("options_chain.csv", "GENERIC_OPTIONS_CHAIN", 2),
        ("fundamentals_long.csv", "GENERIC_FUNDAMENTALS_LONG", 3),
        ("fundamentals_wide.csv", "GENERIC_FUNDAMENTALS_WIDE", 1),
    ],
)
def test_fictional_template_validates_with_its_registered_profile(
    ledger_session, filename, profile_code, count
):
    seed_profiles(ledger_session)
    security = models.Instrument(
        id="template-security",
        symbol="SAMPLE_EQ",
        name="Fictional template security",
        currency="SGD",
        country="Test",
        asset_class="Equity",
        security_type="Common Stock",
        sector="Test",
    )
    ledger_session.add(security)
    ledger_session.flush()
    profile = ledger_session.scalar(
        select(models.MappingProfile).where(models.MappingProfile.code == profile_code)
    )
    rows, columns = parse_file((TEMPLATES / filename).read_bytes(), filename)
    mapping = suggest_mapping(columns, profile)
    normalized, report = normalize(
        rows, mapping, profile, [security], filename_metadata(filename), {}
    )
    assert report["valid"], report["errors"]
    assert len(normalized) == report["validated_rows"] == count
    assert not profile.approved
    assert report["point_in_time"] == "UNVERIFIED"
    if filename == "positions.csv":
        assert any("reconciliation references only" in warning for warning in report["warnings"])
