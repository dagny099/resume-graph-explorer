"""
Google OAuth and Drive integration helpers.

This module centralizes OAuth URL generation, token exchange/persistence,
and lightweight download helpers for Google Drive files.
"""

import json
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, urlparse

import requests

from ..utils.logger import logger


@dataclass
class OAuthToken:
    """Represents a stored OAuth token set."""

    access_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    scope: Optional[str] = None
    token_type: str = "Bearer"
    id_token: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        data = asdict(self)
        data["expires_at"] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "OAuthToken":
        payload = data.copy()
        payload["expires_at"] = datetime.fromisoformat(payload["expires_at"])
        return cls(**payload)


class TokenStore:
    """Lightweight JSON-backed token storage keyed by session/user id."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.tokens_path = self.base_path / "oauth_tokens.json"
        self._tokens: Dict[str, OAuthToken] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not self.tokens_path.exists():
            return

        try:
            with open(self.tokens_path, "r") as f:
                raw = json.load(f)
            for session_id, token_data in raw.items():
                self._tokens[session_id] = OAuthToken.from_dict(token_data)
            logger.info("TokenStore loaded %d token sets", len(self._tokens))
        except Exception as exc:
            logger.error("Failed to load token store: %s", exc)
            self._tokens = {}

    def _save(self) -> None:
        try:
            serializable = {key: token.to_dict() for key, token in self._tokens.items()}
            with open(self.tokens_path, "w") as f:
                json.dump(serializable, f, indent=2)
        except Exception as exc:
            logger.error("Failed to persist token store: %s", exc)

    def set_tokens(self, session_id: str, token: OAuthToken) -> None:
        with self._lock:
            self._tokens[session_id] = token
            self._save()

    def get_tokens(self, session_id: str) -> Optional[OAuthToken]:
        return self._tokens.get(session_id)

    def delete_tokens(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._tokens:
                self._tokens.pop(session_id)
                self._save()


class GoogleOAuthService:
    """Helper to build consent URLs and exchange authorization codes."""

    AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: str,
        token_store: TokenStore,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.token_store = token_store

    def build_consent_url(self, state: Optional[str] = None) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scopes,
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state

        return f"{self.AUTH_BASE}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> OAuthToken:
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        response = requests.post(self.TOKEN_ENDPOINT, data=data, timeout=15)
        if response.status_code != 200:
            logger.error(
                "Failed to exchange code: %s - %s", response.status_code, response.text
            )
            response.raise_for_status()

        payload = response.json()
        expires_in = payload.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return OAuthToken(
            access_token=payload.get("access_token", ""),
            refresh_token=payload.get("refresh_token"),
            expires_at=expires_at,
            scope=payload.get("scope"),
            token_type=payload.get("token_type", "Bearer"),
            id_token=payload.get("id_token"),
        )


class GoogleDriveClient:
    """Utility to parse Drive URLs and download/export files."""

    EXPORT_MIME = {
        "document": ("application/pdf", "pdf"),
        "spreadsheets": ("application/pdf", "pdf"),
        "presentation": ("application/pdf", "pdf"),
    }

    def __init__(self, token_store: TokenStore):
        self.token_store = token_store

    @staticmethod
    def parse_file_url(file_url: str) -> Tuple[str, str]:
        parsed = urlparse(file_url)
        path_parts = parsed.path.split("/")
        try:
            type_index = path_parts.index("d") - 1
            file_type = path_parts[type_index]
            file_id = path_parts[type_index + 1]
        except (ValueError, IndexError) as exc:
            logger.error("Unable to parse Google file URL: %s", exc)
            raise ValueError("Invalid Google Drive URL format") from exc

        return file_id, file_type

    def download_file(self, file_id: str, file_type: str, token: OAuthToken) -> Tuple[bytes, str]:
        headers = {"Authorization": f"Bearer {token.access_token}"}

        if file_type in self.EXPORT_MIME:
            mime_type, extension = self.EXPORT_MIME[file_type]
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
            params = {"mimeType": mime_type}
        else:
            extension = "bin"
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            params = {"alt": "media"}

        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            logger.error(
                "Google Drive download failed: %s - %s", response.status_code, response.text
            )
            response.raise_for_status()

        filename = f"{file_id}.{extension}"
        return response.content, filename
