from infracrawl.services.http_service import HttpService
from unittest.mock import patch

@patch('requests.get')
def test_fetch_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = 'hello world'
    http = HttpService(user_agent='TestAgent')
    status, text = http.fetch('http://example.com')
    assert status == 200
    assert text == 'hello world'

@patch('requests.get')
def test_fetch_robots_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = 'User-agent: *\nDisallow: /private'
    http = HttpService(user_agent='TestAgent')
    status, text = http.fetch_robots('http://example.com/robots.txt')
    assert status == 200
    assert 'Disallow' in text
