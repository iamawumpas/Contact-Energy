"""Minimal Contact Energy API client for validation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class ContactEnergyApi:
	"""Async API client supporting login and account validation only."""

	def __init__(self, hass: HomeAssistant, email: str, password: str) -> None:
		self._email = email
		self._password = password
		self._api_token: str = ""
		self._url_base = "https://api.contact-digital-prod.net"
		# Embedded API key provided by upstream mobile client
		self._api_key = "z840P4lQCH9TqcjC9L2pP157DZcZJMcr5tVQCvyx"
		self._session = async_get_clientsession(hass)
		self._login_lock = asyncio.Lock()

	def _headers(self, include_token: bool = True) -> dict[str, str]:
		headers = {"x-api-key": self._api_key}
		if include_token and self._api_token:
			headers["session"] = self._api_token
		return headers

		async def _request(self, method: str, url: str, **kwargs: Any) -> Any:
			"""HTTP request with retry/backoff for 5xx and robust error mapping."""
			max_retries = kwargs.pop("_retries", 2)
			backoff = 1
			attempt = 0
			while True:
				attempt += 1
				try:
					async with async_timeout.timeout(30):
						async with self._session.request(method, url, **kwargs) as resp:
							_LOGGER.debug("%s %s -> %s", method, url, resp.status)
							if resp.status == 200:
								ct = resp.headers.get("content-type", "")
								if "application/json" in ct:
									return await resp.json()
								return await resp.text()
							if resp.status == 401:
								raise InvalidAuth("Unauthorized (401)")
							text = await resp.text()
							# Retry on server errors
							if 500 <= resp.status <= 599 and attempt <= (max_retries + 1):
								_LOGGER.warning(
									"Server error %s on %s; retrying in %ss (attempt %s/%s)",
									resp.status,
									url,
									backoff,
									attempt,
									max_retries + 1,
								)
								await asyncio.sleep(backoff)
								backoff *= 2
								continue
							raise CannotConnect(f"Unexpected status {resp.status}: {text}")
				except asyncio.TimeoutError as e:
					_LOGGER.error("Timeout calling %s: %s", url, e)
					if attempt <= (max_retries + 1):
						await asyncio.sleep(backoff)
						backoff *= 2
						continue
					raise CannotConnect("Timeout") from e
				except aiohttp.ClientError as e:
					_LOGGER.error("Client error calling %s: %s", url, e)
					if attempt <= (max_retries + 1):
						await asyncio.sleep(backoff)
						backoff *= 2
						continue
					raise CannotConnect("Client error") from e
				except InvalidAuth:
					# Do not retry invalid auth
					raise
				except Exception as e:  # noqa: BLE001
					_LOGGER.exception("Unexpected error calling %s: %s", url, e)
					if attempt <= (max_retries + 1):
						await asyncio.sleep(backoff)
						backoff *= 2
						continue
					raise UnknownError("Unexpected error") from e

	async def async_login(self) -> bool:
		"""Login and store token."""
		async with self._login_lock:
			if self._api_token:
				return True
			data = {"username": self._email, "password": self._password}
			try:
				result = await self._request(
					"POST",
					f"{self._url_base}/login/v2",
					json=data,
					headers=self._headers(include_token=False),
				)
				if isinstance(result, dict) and result.get("token"):
					self._api_token = result["token"]
					_LOGGER.debug("Login successful for %s", self._email)
					return True
				_LOGGER.error("Login failed: unexpected response: %s", result)
				return False
			except InvalidAuth:
				_LOGGER.error("Invalid credentials for %s", self._email)
				return False

	async def async_validate_account(self) -> bool:
		"""Validate account access by fetching accounts summary."""
		if not self._api_token:
			ok = await self.async_login()
			if not ok:
				return False
		try:
			data = await self._request(
				"GET",
				f"{self._url_base}/accounts/v2",
				headers=self._headers(),
			)
			if isinstance(data, dict) and data.get("accountDetail"):
				return True
			_LOGGER.error("Account validation failed: missing accountDetail in response")
			return False
		except InvalidAuth:
			_LOGGER.warning("Token invalid during validation; retrying login")
			if await self.async_login():
				return await self.async_validate_account()
			return False


class InvalidAuth(Exception):
	"""Invalid authentication error."""


class CannotConnect(Exception):
	"""Connectivity error."""


class UnknownError(Exception):
	"""Unknown error."""

