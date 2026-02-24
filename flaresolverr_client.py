import requests
import time
import logging

logger = logging.getLogger(__name__)

FLARESOLVERR_URL = "http://localhost:8191/v1"

class FlareSolverrSession:
    """
    Persistent FlareSolverr session wrapper.
    Reuses the same Cloudflare session ID to avoid solving challenge on every request.
    """

    def __init__(self, timeout=60000):
        self.timeout = timeout
        self._session_id = None

    def _ensure_session(self):
        """Create a session if one doesn't exist."""
        if not self._session_id:
            try:
                self.create_session()
            except Exception as e:
                logger.warning(f"Failed to auto-create FlareSolverr session: {e}")

    def create_session(self):
        """Create a new persistent session in FlareSolverr."""
        try:
            resp = requests.post(
                FLARESOLVERR_URL, 
                json={"cmd": "sessions.create"},
                timeout=30
            )
            data = resp.json()
            if data.get("status") == "ok":
                self._session_id = data["session"]
                logger.info(f"Created FlareSolverr session: {self._session_id}")
                return self._session_id
            else:
                logger.error(f"FlareSolverr session creation failed: {data}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Could not connect to FlareSolverr: {e}")
            return None

    def destroy_session(self):
        """Destroy the current session."""
        if self._session_id:
            try:
                requests.post(
                    FLARESOLVERR_URL,
                    json={"cmd": "sessions.destroy", "session": self._session_id},
                    timeout=10
                )
                logger.info(f"Destroyed FlareSolverr session: {self._session_id}")
            except Exception:
                pass
            self._session_id = None

    def get(self, url, **kwargs):
        """
        Execute a GET request via FlareSolverr.
        Returns a FakeSolverrResponse object compatible with requests.Response.
        """
        # Ensure we have a session
        if not self._session_id:
            if not self.create_session():
                raise ConnectionError(
                    "FlareSolverr is not running see README.md for setup instructions.\n"
                    "Start it with: python FlareSolverr/src/flaresolverr.py"
                )

        payload = {
            "cmd": "request.get",
            "url": url,
            "session": self._session_id,
            "maxTimeout": self.timeout,
        }

        try:
            # We use a longer timeout for the actual HTTP call to FS
            resp = requests.post(FLARESOLVERR_URL, json=payload, timeout=kwargs.get('timeout', 120))
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                # If session is invalid, try to recreate it once
                if "session does not exist" in str(data.get("message", "")).lower():
                    logger.warning("Session invalid, recreating...")
                    self._session_id = None
                    if self.create_session():
                        # Retry the request
                        payload["session"] = self._session_id
                        resp = requests.post(FLARESOLVERR_URL, json=payload, timeout=kwargs.get('timeout', 120))
                        data = resp.json()
                
                if data.get("status") != "ok":
                    raise ConnectionError(f"FlareSolverr error: {data.get('message')}")

            return FakeSolverrResponse(data["solution"])

        except requests.exceptions.ConnectionError:
             raise ConnectionError(
                "FlareSolverr is not reachable. Confirm it is running on port 8191."
            )

class FakeSolverrResponse:
    """Mimics requests.Response using FlareSolverr output."""

    def __init__(self, solution):
        self.text = solution.get("response", "")
        self.content = self.text.encode('utf-8')
        self.status_code = solution.get("status", 200)
        self.url = solution.get("url", "")
        self.cookies = {} 
        # FS returns cookies as list of dicts, we could parse if needed
        # but for scraping HTML usually .text is enough.
        
        self.ok = 200 <= self.status_code < 400
        self.headers = solution.get("headers", {})

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"Status {self.status_code}")
    
    def json(self):
        import json
        return json.loads(self.text)

def is_flaresolverr_running():
    """Quick health check."""
    try:
        r = requests.get(f"{FLARESOLVERR_URL.replace('/v1', '')}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False
