"""A successful test process must also produce nonempty, unskipped results."""

import hashlib
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict, Field


class BrowserStats(BaseModel):
    model_config = ConfigDict(strict=True)
    expected: int = Field(gt=0)
    skipped: Literal[0]
    unexpected: Literal[0]
    flaky: Literal[0]


class BrowserResults(BaseModel):
    stats: BrowserStats
    errors: list[object] = Field(max_length=0)


def validate_results(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Test results are missing or indirect")
    content = path.read_bytes()
    if path.suffix == ".xml":
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            raise ValueError("Invalid test result XML") from None
        cases = list(root.iter("testcase"))
        if not cases or any(
            case.find(state) is not None
            for case in cases
            for state in ("failure", "error", "skipped")
        ):
            raise ValueError("Test results must be nonempty with no failures, errors or skips")
        suites = list(root.iter("testsuite"))
        if not suites or any(
            int(suite.get(state, "0")) != 0
            for suite in suites
            for state in ("failures", "errors", "skipped")
        ):
            raise ValueError("Test suite summary is not clean")
        if sum(int(suite.get("tests", "0")) for suite in suites) != len(cases):
            raise ValueError("Test suite count does not match executed cases")
    elif path.suffix == ".json":
        BrowserResults.model_validate_json(content)
    else:
        raise ValueError("Unsupported test result format")
    return hashlib.sha256(content).hexdigest()
