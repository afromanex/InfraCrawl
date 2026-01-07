import requests

class HttpService:
    def __init__(self, user_agent: str, timeout: int = 10):
        self.user_agent = user_agent
        self.timeout = timeout

    def fetch(self, url: str):
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        return resp.status_code, resp.text

    def fetch_robots(self, robots_url: str):
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(robots_url, headers=headers, timeout=self.timeout)
        return resp.status_code, resp.text
