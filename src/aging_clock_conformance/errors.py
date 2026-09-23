"""Stable failures at application boundaries; never include raw sample contents."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ValidationReport


class ACCError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ComputationBlocked(ACCError):
    def __init__(self, report: ValidationReport) -> None:
        super().__init__("ACC_COMPUTATION_BLOCKED", "Sample does not satisfy the scoring contract.")
        self.report = report
