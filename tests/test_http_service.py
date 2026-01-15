from infracrawl.services.http_service import HttpService
from infracrawl.exceptions import HttpFetchError
from unittest.mock import Mock
import requests


def test_fetch_success():
    mock_http_client = Mock()
    mock_http_client.return_value.status_code = 200
    mock_http_client.return_value.text = 'hello world'
    http = HttpService(user_agent='TestAgent', http_client=mock_http_client)
    response = http.fetch('http://example.com')
    assert response.status_code == 200
    assert response.text == 'hello world'


def test_fetch_robots_success():
    mock_http_client = Mock()
    mock_http_client.return_value.status_code = 200
    mock_http_client.return_value.text = 'User-agent: *\nDisallow: /private'
    http = HttpService(user_agent='TestAgent', http_client=mock_http_client)
    response = http.fetch_robots('http://example.com/robots.txt')
    assert response.status_code == 200
    assert 'Disallow' in response.text


def test_fetch_wraps_requests_exception():
    mock_http_client = Mock()
    mock_http_client.side_effect = requests.exceptions.Timeout("timed out")
    http = HttpService(user_agent='TestAgent', http_client=mock_http_client)

    try:
        http.fetch('http://example.com')
        assert False, "expected HttpFetchError"
    except HttpFetchError as e:
        assert "http://example.com" in str(e)
