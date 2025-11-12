"""Minimal Contact Energy API client for validation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
	API_BASE_URL,
	API_KEY,
	API_TIMEOUT_DEFAULT,
	API_TIMEOUT_USAGE,
	API_MAX_RETRIES,
	API_BACKOFF_INITIAL,
)

_LOGGER = logging.getLogger(__name__)


class ContactEnergyApi:
	"""Async API client supporting login and account validation only."""

	def __init__(self, hass: HomeAssistant, email: str, password: str) -> None:
		self._email = email
		self._password = password
		self._api_token: str = ""
		self._url_base = API_BASE_URL
		self._api_key = API_KEY
		self._session = async_get_clientsession(hass)
		self._login_lock = asyncio.Lock()

	def _headers(self, include_token: bool = True) -> dict[str, str]:
		"""Build request headers with optional session token."""
		headers = {"x-api-key": self._api_key}
		if include_token and self._api_token:
			headers["session"] = self._api_token
		return headers

	async def _handle_retry(self, attempt: int, max_retries: int, backoff: float, error_context: str) -> float:
		"""Handle retry logic with exponential backoff."""
		if attempt <= max_retries:
			_LOGGER.debug("%s; retrying in %ss (attempt %s/%s)", error_context, backoff, attempt, max_retries + 1)
			await asyncio.sleep(backoff)
			return backoff * 2
		return backoff

	async def _request(self, method: str, url: str, **kwargs: Any) -> Any:
		"""HTTP request with retry/backoff for 5xx and robust error mapping."""
		max_retries = kwargs.pop("_retries", API_MAX_RETRIES)
		backoff = API_BACKOFF_INITIAL
		attempt = 0
		last_server_error = None
		
		while True:
			attempt += 1
			try:
				# Use longer timeout for usage requests which can be slow
				timeout_duration = API_TIMEOUT_USAGE if "/usage/" in url else API_TIMEOUT_DEFAULT
				async with async_timeout.timeout(timeout_duration):
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
							last_server_error = (resp.status, url)
							backoff = await self._handle_retry(
								attempt, max_retries, backoff,
								f"Server error {resp.status} on {url}"
							)
							continue
						
						# Log exhausted retries
						if last_server_error:
							_LOGGER.debug(
								"Contact Energy API returned server error %s after %s retries for %s",
								last_server_error[0], max_retries, last_server_error[1]
							)
						raise CannotConnect(f"Server error {resp.status}" if last_server_error else f"Unexpected status {resp.status}")
						
			except asyncio.TimeoutError as e:
				_LOGGER.debug("Timeout calling %s (attempt %s/%s)", url, attempt, max_retries + 1)
				if attempt <= (max_retries + 1):
					backoff = await self._handle_retry(attempt, max_retries, backoff, f"Timeout calling {url}")
					continue
				_LOGGER.warning("Timeout calling %s after %s retries", url, max_retries)
				raise CannotConnect("Timeout") from e
				
			except aiohttp.ClientError as e:
				_LOGGER.debug("Client error calling %s (attempt %s/%s): %s", url, attempt, max_retries + 1, e)
				if attempt <= (max_retries + 1):
					backoff = await self._handle_retry(attempt, max_retries, backoff, f"Client error calling {url}: {e}")
					continue
				_LOGGER.warning("Client error calling %s after %s retries: %s", url, max_retries, e)
				raise CannotConnect("Client error") from e
				
			except InvalidAuth:
				# Do not retry invalid auth
				raise
				
			except Exception as e:  # noqa: BLE001
				_LOGGER.debug("Unexpected error calling %s (attempt %s/%s): %s", url, attempt, max_retries + 1, e)
				if attempt <= (max_retries + 1):
					backoff = await self._handle_retry(attempt, max_retries, backoff, f"Unexpected error calling {url}: {e}")
					continue
				# Log 502 errors at debug level since they're common and expected from Contact Energy API
				if "502" in str(e):
					_LOGGER.debug("Server error 502 calling %s after %s retries (API temporarily unavailable)", url, max_retries)
				else:
					_LOGGER.warning("Unexpected error calling %s after %s retries: %s", url, max_retries, e)
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
		if not self._api_token and not await self.async_login():
			return False
			
		try:
			data = await self._request("GET", f"{self._url_base}/accounts/v2", headers=self._headers())
			if isinstance(data, dict) and data.get("accountDetail"):
				return True
			_LOGGER.error("Account validation failed: missing accountDetail in response")
			return False
		except InvalidAuth:
			_LOGGER.warning("Token invalid during validation; retrying login")
			if await self.async_login():
				return await self.async_validate_account()
			return False

	async def async_get_usage(self, year: str, month: str, day: str, account_id: str, contract_id: str) -> Any:
		"""Get usage data for a specific date using the correct endpoint pattern."""
		if not self._api_token and not await self.async_login():
			return None

		date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
		url = f"{self._url_base}/usage/v2/{contract_id}?ba={account_id}&interval=hourly&from={date_str}&to={date_str}"
		
		_LOGGER.debug("Getting usage data for %s using correct endpoint", date_str)
		
		try:
			data = await self._request("POST", url, headers=self._headers())
			if data:
				_LOGGER.debug("Successfully fetched usage data for %s: %d data points", date_str, len(data) if isinstance(data, list) else 1)
				return data
			_LOGGER.debug("No usage data available for %s", date_str)
			return None
		except InvalidAuth:
			_LOGGER.debug("Token expired during usage fetch, attempting to login again")
			if await self.async_login():
				return await self.async_get_usage(year, month, day, account_id, contract_id)
			return None
		except (CannotConnect, UnknownError) as error:
			_LOGGER.debug("Could not fetch usage data for %s: %s", date_str, error)
			return None
		except Exception as error:
			_LOGGER.warning("Unexpected error fetching usage data for %s: %s", date_str, error)
			return None

	async def async_get_account_details(self) -> Any:
		"""Get account details from the accounts/v2 endpoint."""
		if not self._api_token and not await self.async_login():
			raise CannotConnect("Failed to authenticate")

		try:
			data = await self._request("GET", f"{self._url_base}/accounts/v2", headers=self._headers())
			return data
		except InvalidAuth:
			_LOGGER.debug("Token expired during account fetch, attempting to login again")
			if await self.async_login():
				return await self.async_get_account_details()
			raise InvalidAuth("Failed to re-authenticate")
		except (CannotConnect, InvalidAuth):
			raise
		except Exception as error:
			_LOGGER.error("Failed to fetch account details: %s", error)
			raise UnknownError(f"Failed to fetch account details: {error}") from error


class InvalidAuth(Exception):
	"""Invalid authentication error."""


class CannotConnect(Exception):
	"""Connectivity error."""


class UnknownError(Exception):
	"""Unknown error."""

