"""API errors."""

from __future__ import annotations

from typing import Optional

import grpc


class BotApiException(Exception):
    """Raised for failed BotsApi / InteractionsApi calls (never raw RpcError)."""

    def __init__(self, status_code: grpc.StatusCode, detail: str, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.__cause__ = cause

    @classmethod
    def from_rpc_error(cls, error: grpc.RpcError) -> BotApiException:
        code = error.code() if hasattr(error, "code") else grpc.StatusCode.UNKNOWN
        details = error.details() if hasattr(error, "details") else str(error)
        return cls(code, details or str(error), cause=error)
