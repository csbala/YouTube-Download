"""The `doctor` command: checks everything a download needs, each with its fix.

Pattern: Template Method. SetupCheck.run() is the fixed skeleton (probe the machine, look for a
problem, otherwise describe what's fine); each check fills in those steps.
"""

from __future__ import annotations

import importlib.metadata
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Generic, Protocol, TypeVar

from . import tools
from .settings import MIN_YT_DLP_VERSION, AppSettings, get_settings
from .tools import ToolLocator

COOKIE_MAX_AGE_DAYS = 30
SECONDS_PER_DAY = 86400

Finding = TypeVar("Finding")


class CheckStatus(Enum):
    OK = "OK"
    WARN = "WARN"  # works, but risky
    MISSING = "MISSING"  # blocks a download


@dataclass(frozen=True)
class CheckResult:
    status: CheckStatus
    message: str

    @property
    def blocks_download(self) -> bool:
        return self.status is CheckStatus.MISSING

    def __str__(self) -> str:
        return f"[{self.status.value}] {self.message}"


def pip_upgrade_command() -> str:
    return f'"{sys.executable}" -m pip install -U "yt-dlp[default]"'


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".") if part.isdigit())


class SetupCheck(ABC, Generic[Finding]):
    def run(self) -> CheckResult:
        finding = self.probe()
        problem = self.find_problem(finding)
        return problem or CheckResult(CheckStatus.OK, self.describe_ok(finding))

    @abstractmethod
    def probe(self) -> Finding:
        """Look at the machine."""

    @abstractmethod
    def find_problem(self, finding: Finding) -> CheckResult | None:
        """A WARN or MISSING result, or None when everything's fine."""

    @abstractmethod
    def describe_ok(self, finding: Finding) -> str: ...


class YtDlpVersionCheck(SetupCheck[str | None]):
    def probe(self) -> str | None:
        try:
            return importlib.metadata.version("yt-dlp")
        except importlib.metadata.PackageNotFoundError:
            return None

    def find_problem(self, finding: str | None) -> CheckResult | None:
        if finding is None:
            return CheckResult(CheckStatus.MISSING, f"yt-dlp is not installed for this Python. Fix: {pip_upgrade_command()}")
        if version_tuple(finding) < version_tuple(MIN_YT_DLP_VERSION):
            return CheckResult(
                CheckStatus.MISSING,
                f"yt-dlp {finding} is too old (this script needs {MIN_YT_DLP_VERSION} or newer). Fix: {pip_upgrade_command()}",
            )
        return None

    def describe_ok(self, finding: str | None) -> str:
        return f"yt-dlp {finding}"


class ChallengeSolverCheck(SetupCheck[bool]):
    def __init__(self, tool_locator: ToolLocator) -> None:
        self._tools = tool_locator

    def probe(self) -> bool:
        return self._tools.ejs_installed()

    def find_problem(self, finding: bool) -> CheckResult | None:
        if finding:
            return None
        return CheckResult(
            CheckStatus.WARN,
            "yt-dlp-ejs is not installed, so the YouTube challenge solver is fetched from GitHub "
            f"on every run. Fix: {pip_upgrade_command()}",
        )

    def describe_ok(self, finding: bool) -> str:
        return "yt-dlp-ejs (YouTube challenge solver)"


class NodeCheck(SetupCheck[str | None]):
    def __init__(self, tool_locator: ToolLocator) -> None:
        self._tools = tool_locator

    def probe(self) -> str | None:
        return self._tools.node_path()

    def find_problem(self, finding: str | None) -> CheckResult | None:
        if finding:
            return None
        return CheckResult(
            CheckStatus.MISSING,
            "Node.js not found (yt-dlp uses it to solve YouTube's JS challenge). Fix: winget install -e --id OpenJS.NodeJS.LTS",
        )

    def describe_ok(self, finding: str | None) -> str:
        return f"Node.js at {finding}"


class FfmpegCheck(SetupCheck[str | None]):
    def __init__(self, tool_locator: ToolLocator) -> None:
        self._tools = tool_locator

    def probe(self) -> str | None:
        return self._tools.ffmpeg_dir()

    def find_problem(self, finding: str | None) -> CheckResult | None:
        if finding:
            return None
        return CheckResult(
            CheckStatus.MISSING, "ffmpeg not found (needed for mp3; webm still works without it). Fix: winget install -e --id Gyan.FFmpeg"
        )

    def describe_ok(self, finding: str | None) -> str:
        return f"ffmpeg in {finding}"


@dataclass(frozen=True)
class CookiesFinding:
    exists: bool
    is_netscape_format: bool = False
    age_days: int = 0


class CookiesCheck(SetupCheck[CookiesFinding]):
    """Never reads past the first line of cookies.txt, and never shows it: it's the user's login."""

    def __init__(self, cookies_file: str) -> None:
        self._cookies_file = cookies_file

    def probe(self) -> CookiesFinding:
        if not os.path.isfile(self._cookies_file):
            return CookiesFinding(exists=False)
        with open(self._cookies_file, encoding="utf-8", errors="replace") as file:
            header = file.readline()
        age_days = int((datetime.now().timestamp() - os.path.getmtime(self._cookies_file)) / SECONDS_PER_DAY)
        return CookiesFinding(exists=True, is_netscape_format="HTTP Cookie File" in header, age_days=age_days)

    def find_problem(self, finding: CookiesFinding) -> CheckResult | None:
        if not finding.exists:
            return CheckResult(
                CheckStatus.WARN,
                f"cookies.txt not found at {self._cookies_file}. Public videos usually work; "
                "age-restricted ones and 'confirm you're not a bot' blocks will fail. "
                "Fix: export YouTube cookies with the 'Get cookies.txt LOCALLY' browser extension "
                "and save them as cookies.txt next to downloader.py.",
            )
        if not finding.is_netscape_format:
            return CheckResult(
                CheckStatus.WARN,
                "cookies.txt isn't in Netscape format (its first line should mention "
                "'HTTP Cookie File'). Re-export it with 'Get cookies.txt LOCALLY'.",
            )
        if finding.age_days > COOKIE_MAX_AGE_DAYS:
            return CheckResult(
                CheckStatus.WARN,
                f"cookies.txt is {finding.age_days} days old and may have expired. "
                "Re-export it if downloads fail with a sign-in or bot error.",
            )
        return None

    def describe_ok(self, finding: CookiesFinding) -> str:
        return f"cookies.txt ({finding.age_days} days old)"


class RunnableCheck(Protocol):
    """What the doctor needs from a check, whatever its Finding type."""

    def run(self) -> CheckResult: ...


def setup_checks(tool_locator: ToolLocator, settings: AppSettings) -> list[RunnableCheck]:
    return [
        YtDlpVersionCheck(),
        ChallengeSolverCheck(tool_locator),
        NodeCheck(tool_locator),
        FfmpegCheck(tool_locator),
        CookiesCheck(settings.cookies_file),
    ]


def diagnose(tool_locator: ToolLocator | None = None, settings: AppSettings | None = None) -> list[CheckResult]:
    """Run every setup check, in the order they're printed."""
    checks = setup_checks(tool_locator or tools.default_tool_locator(), settings or get_settings())
    return [check.run() for check in checks]
