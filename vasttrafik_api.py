import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class VasttrafikAPI:
    """Client for Västtrafik API with OAuth2 authentication."""

    def __init__(self):
        self.client_id = os.getenv('VASTTRAFIK_CLIENT_ID')
        self.client_secret = os.getenv('VASTTRAFIK_CLIENT_SECRET')
        self.token_url = "https://ext-api.vasttrafik.se/token"
        self.api_base = "https://ext-api.vasttrafik.se/pr/v4"
        self.access_token = None
        self.token_expires = None

        if not self.client_id or not self.client_secret:
            raise ValueError("Missing API credentials. Please set VASTTRAFIK_CLIENT_ID and VASTTRAFIK_CLIENT_SECRET in .env file")

    def get_access_token(self):
        """Get OAuth2 access token using client credentials flow."""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token

        auth = (self.client_id, self.client_secret)
        data = {
            'grant_type': 'client_credentials'
        }

        response = requests.post(self.token_url, auth=auth, data=data)
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data['access_token']
        # Set expiry slightly before actual expiry to avoid edge cases
        expires_in = token_data.get('expires_in', 3600)
        self.token_expires = datetime.now() + timedelta(seconds=expires_in - 60)

        return self.access_token

    def _make_request(self, endpoint, params=None):
        """Make authenticated request to Västtrafik API."""
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}'
        }

        url = f"{self.api_base}/{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        return response.json()

    def search_stop(self, query):
        """Search for stops by name."""
        params = {'q': query}
        return self._make_request('locations/by-text', params=params)

    def get_departures(self, stop_gid, limit=10):
        """Get departures for a specific stop.

        Args:
            stop_gid: Stop global ID (e.g., '9021014001960000')
            limit: Maximum number of departures to return
        """
        params = {
            'limit': limit,
            'timeSpan': 60  # Look ahead 60 minutes
        }

        endpoint = f'stop-areas/{stop_gid}/departures'
        return self._make_request(endpoint, params=params)
