"""SEC data and OpenFIGI reference lookups. No EDGAR filing-submission API."""

import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import TypedDict

import httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ..config import Settings
from .http import ProviderError, Response, fetch


def cik_value(value: str | int) -> str:
    token = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,10}", token) or int(token) <= 0:
        raise ValueError("CIK must be a positive 1-10 digit identifier")
    return token.zfill(10)


class SecProvider:
    provider_name = "SEC EDGAR"
    capabilities = ["test", "submissions", "company_facts", "backfill"]

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings, self.transport = settings, transport

    @property
    def configured(self) -> bool:
        agent = self.settings.sec_user_agent or ""
        return (
            len(agent) <= 250
            and bool(re.search(r"\S+\s+[^\s@]+@[^\s@]+\.[^\s@]+", agent))
            and not any(c in agent for c in "\r\n")
        )

    async def read(self, cik: str | int, kind: str = "submissions") -> Response:
        if not self.configured:
            raise ProviderError(
                "SEC_USER_AGENT requires an organization and contact email", "NOT_CONFIGURED"
            )
        cik = cik_value(cik)
        if kind not in {"submissions", "company_facts"}:
            raise ValueError("Unknown SEC dataset")
        path = (
            f"submissions/CIK{cik}.json"
            if kind == "submissions"
            else f"api/xbrl/companyfacts/CIK{cik}.json"
        )
        response = await fetch(
            self.provider_name,
            "https://data.sec.gov/" + path,
            headers={
                "User-Agent": self.settings.sec_user_agent or "",
                "Accept": "application/json",
            },
            transport=self.transport,
        )
        if (
            not isinstance(response.payload, dict)
            or str(response.payload.get("cik", "")).zfill(10) != cik
        ):
            raise ProviderError("SEC response CIK does not match request")
        return response

    async def test(self) -> Response:
        return await self.read("320193")


class FilingRow(TypedDict):
    cik: str
    accession: str
    filing_date: str
    form: str
    document: str
    url: str


def filing_rows(payload: JsonValue) -> list[FilingRow]:
    if not isinstance(payload, dict):
        raise ProviderError("SEC response must be an object")
    filings = payload.get("filings")
    recent = filings.get("recent") if isinstance(filings, dict) else None
    if not isinstance(recent, dict):
        raise ProviderError("SEC filing columns are missing or have unequal lengths")
    required = ("accessionNumber", "filingDate", "form", "primaryDocument")
    columns: list[list[str]] = []
    for key in required:
        values = recent.get(key)
        if not isinstance(values, list):
            raise ProviderError("SEC filing columns are missing or have unequal lengths")
        strings: list[str] = []
        for value in values:
            if not isinstance(value, str):
                raise ProviderError("SEC filing columns must contain strings")
            strings.append(value)
        columns.append(strings)
    if len({len(column) for column in columns}) != 1:
        raise ProviderError("SEC filing columns are missing or have unequal lengths")
    cik_raw = payload.get("cik")
    if not isinstance(cik_raw, (str, int)):
        raise ProviderError("SEC response CIK is missing or invalid")
    cik = cik_value(cik_raw)
    result: list[FilingRow] = []
    for i, accession in enumerate(columns[0]):
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
            raise ProviderError("SEC accession identifier is invalid")
        document = columns[3][i]
        try:
            date.fromisoformat(columns[1][i])
        except (ValueError, TypeError) as exc:
            raise ProviderError("SEC filing date is invalid") from exc
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", document or "") or ".." in document:
            raise ProviderError("SEC document filename is invalid")
        result.append(
            {
                "cik": cik,
                "accession": accession,
                "filing_date": columns[1][i],
                "form": columns[2][i],
                "document": document,
                "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{document}",
            }
        )
    return result


class MappingJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idType: str = Field(pattern=r"^[A-Z0-9_]{2,60}$")
    idValue: str = Field(min_length=1, max_length=160)
    exchCode: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]{1,12}$")
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    micCode: str | None = Field(default=None, pattern=r"^[A-Z0-9]{4}$")
    marketSecDes: str | None = Field(default=None, max_length=60)
    securityType2: str | None = Field(default=None, max_length=60)


class OpenFigiProvider:
    provider_name = "OpenFIGI"
    capabilities = ["test", "mapping", "review_mapping"]
    configured = True

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings, self.transport = settings, transport

    async def mapping(self, jobs: Sequence[Mapping[str, object]]) -> Response:
        maximum = 100 if self.settings.openfigi_api_key else 10
        if not 1 <= len(jobs) <= maximum:
            raise ValueError(f"OpenFIGI allows 1-{maximum} mapping jobs per request")
        headers = {"Content-Type": "application/json"}
        if self.settings.openfigi_api_key:
            headers["X-OPENFIGI-APIKEY"] = self.settings.openfigi_api_key
        response = await fetch(
            self.provider_name,
            "https://api.openfigi.com/v3/mapping",
            headers=headers,
            body=[MappingJob.model_validate(job).model_dump(exclude_none=True) for job in jobs],
            interval=0.25 if self.settings.openfigi_api_key else 2.5,
            transport=self.transport,
        )
        if not isinstance(response.payload, list) or len(response.payload) != len(jobs):
            raise ProviderError("OpenFIGI response count does not match requested jobs")
        for item in response.payload:
            if not isinstance(item, dict) or not any(
                key in item for key in ("data", "error", "warning")
            ):
                raise ProviderError("OpenFIGI mapping result is malformed")
            if "data" in item and (
                not isinstance(item["data"], list)
                or any(
                    not isinstance(candidate, dict)
                    or not re.fullmatch(r"BBG[A-Z0-9]{9}", str(candidate.get("figi", "")))
                    for candidate in item["data"]
                )
            ):
                raise ProviderError("OpenFIGI mapping candidates are malformed")
        return response

    async def test(self) -> Response:
        return await self.mapping([{"idType": "ID_BB_GLOBAL", "idValue": "BBG000B9XRY4"}])
