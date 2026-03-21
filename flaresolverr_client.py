import requests
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

FLARESOLVERR_URL = "http://localhost:8191/v1"
DEFAULT_TIMEOUT = 60000  # 60 seconds in milliseconds

class FlareSolverrSession:
    """
    Persistent FlareSolverr session wrapper.
    Reuses the same Cloudflare session ID to avoid solving challenge on every request.
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, flaresolverr_url: str = FLARESOLVERR_URL):
        self.timeout = timeout
        self.flaresolverr_url = flaresolverr_url
        self._session_id: Optional[str] = None
        self._last_used = 0

    def _ensure_session(self):
        """Create a session if one doesn't exist."""
        if not self._session_id:
            try:
                self.create_session()
            except Exception as e:
                logger.warning(f"Failed to auto-create FlareSolverr session: {e}")

    def create_session(self) -> Optional[str]:
        """Create a new persistent session in FlareSolverr."""
        try:
            resp = requests.post(
                self.flaresolverr_url, 
                json={"cmd": "sessions.create"},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("status") == "ok":
                self._session_id = data["session"]
                self._last_used = time.time()
                logger.info(f"Created FlareSolverr session: {self._session_id}")
                return self._session_id
            else:
                error_msg = data.get("message", "Unknown error")
                logger.error(f"FlareSolverr session creation failed: {error_msg}")
                return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Could not connect to FlareSolverr at {self.flaresolverr_url}: {e}")
            logger.info("💡 Make sure FlareSolverr is running. Try: python start_flaresolverr.py")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to FlareSolverr failed: {e}")
            return None

    def destroy_session(self) -> None:
        """Destroy the current session."""
        if self._session_id:
            try:
                resp = requests.post(
                    self.flaresolverr_url,
                    json={"cmd": "sessions.destroy", "session": self._session_id},
                    timeout=10
                )
                resp.raise_for_status()
                logger.info(f"Destroyed FlareSolverr session: {self._session_id}")
            except Exception as e:
                logger.warning(f"Failed to destroy session {self._session_id}: {e}")
            finally:
                self._session_id = None
                self._last_used = 0

    def get(self, url: str, **kwargs):
        """
        Execute a GET request via FlareSolverr.
        Returns a FakeSolverrResponse object compatible with requests.Response.
        """
        # Ensure we have a session
        if not self._session_id:
            if not self.create_session():
                raise ConnectionError(
                    "FlareSolverr is not running see README.md for setup instructions.\n"
                    "💡 Quick start: python start_flaresolverr.py\n"
                    "Or start it manually: python FlareSolverr/src/flaresolverr.py"
                )

        payload = {
            "cmd": "request.get",
            "url": url,
            "session": self._session_id,
            "maxTimeout": self.timeout,
        }

        try:
            # We use a longer timeout for the actual HTTP call to FS
            request_timeout = kwargs.get('timeout', 120)
            resp = requests.post(self.flaresolverr_url, json=payload, timeout=request_timeout)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                # If session is invalid, try to recreate it once
                error_msg = str(data.get("message", "")).lower()
                if "session does not exist" in error_msg or "session not found" in error_msg:
                    logger.warning("Session invalid, recreating...")
                    self._session_id = None
                    if self.create_session():
                        # Retry the request
                        payload["session"] = self._session_id
                        resp = requests.post(self.flaresolverr_url, json=payload, timeout=request_timeout)
                        resp.raise_for_status()
                        data = resp.json()
                
                if data.get("status") != "ok":
                    error_detail = data.get('message', 'Unknown error')
                    raise ConnectionError(f"FlareSolverr error: {error_detail}")

            self._last_used = time.time()
            return FakeSolverrResponse(data["solution"])

        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"FlareSolverr is not reachable at {self.flaresolverr_url}. "
                f"Confirm it is running on port 8191. Error: {e}"
            )
        except requests.exceptions.Timeout as e:
            raise TimeoutError(
                f"FlareSolverr request timed out after {request_timeout}s. "
                f"The site might be very slow or FlareSolverr is overloaded."
            )

class FakeSolverrResponse:
    """Mimics requests.Response using FlareSolverr output."""

    def __init__(self, solution: dict):
        self.text = solution.get("response", "")
        self.content = self.text.encode('utf-8') if isinstance(self.text, str) else self.text
        self.status_code = solution.get("status", 200)
        self.url = solution.get("url", "")
        
        # Parse cookies if available
        self.cookies = {}
        cookies_list = solution.get("cookies", [])
        if isinstance(cookies_list, list):
            for cookie in cookies_list:
                if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                    self.cookies[cookie["name"]] = cookie["value"]
        
        self.ok = 200 <= self.status_code < 400
        self.headers = solution.get("headers", {})
        self.reason = solution.get("statusText", "")

    def raise_for_status(self) -> None:
        """Raise HTTPError if status code indicates an error."""
        if not self.ok:
            raise requests.HTTPError(
                f"{self.status_code} {self.reason or 'Error'} for url: {self.url}",
                response=self
            )
    
    def json(self):
        """Parse JSON response."""
        import json
        if not self.text:
            raise ValueError("No JSON content to parse")
        return json.loads(self.text)

def is_flaresolverr_running(flaresolverr_url: str = FLARESOLVERR_URL) -> bool:
    """Quick health check to see if FlareSolverr is running."""
    try:
        health_url = flaresolverr_url.replace('/v1', '') + '/health'
        r = requests.get(health_url, timeout=2)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False
