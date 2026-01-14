from infracrawl.services.http_service import HttpService
from unittest.mock import Mock


def test_fetch_success():
    mock_http_client = Mock()
    mock_http_client.return_value.status_code = 200
    mock_http_client.return_value.text = 'hello world'
    http = HttpService(user_agent='TestAgent', http_client=mock_http_client)
    status, text = http.fetch('http://example.com')
    assert status == 200
    assert text == 'hello world'


def test_fetch_robots_success():
    mock_http_client = Mock()
    mock_http_client.return_value.status_code = 200
    mock_http_client.return_value.text = 'User-agent: *\nDisallow: /private'
    http = HttpService(user_agent='TestAgent', http_client=mock_http_client)
    status, text = http.fetch_robots('http://example.com/robots.txt')
    assert status == 200
    assert 'Disallow' in text
