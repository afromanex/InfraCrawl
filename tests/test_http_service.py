from infracrawl.services.http_service import HttpService
from infracrawl.exceptions import HttpFetchError
from unittest.mock import Mock, PropertyMock
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


def test_fetch_content_type_from_headers():
    mock_http_client = Mock()
    mock_http_client.return_value.status_code = 200
    mock_http_client.return_value.text = '<html>test</html>'
    mock_http_client.return_value.headers = {'Content-Type': 'text/html; charset=utf-8'}
    http = HttpService(user_agent='TestAgent', http_client=mock_http_client)
    response = http.fetch('http://example.com')
    assert response.status_code == 200
    assert response.content_type == 'text/html; charset=utf-8'


def test_fetch_missing_content_type():
    mock_http_client = Mock()
    mock_http_client.return_value.status_code = 200
    mock_http_client.return_value.text = 'data'
    mock_http_client.return_value.headers = {}
    http = HttpService(user_agent='TestAgent', http_client=mock_http_client)
    response = http.fetch('http://example.com')
    assert response.status_code == 200
    assert response.content_type is None


def test_fetch_bubbles_unexpected_exceptions():
    """Verify that non-requests exceptions from headers.get() are NOT swallowed."""
    mock_http_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = 'test'
    # Simulate headers.get() raising an exception
    mock_response.headers.get.side_effect = RuntimeError("Real bug in headers.get()")
    mock_http_client.return_value = mock_response
    http = HttpService(user_agent='TestAgent', http_client=mock_http_client)

    try:
        http.fetch('http://example.com')
        assert False, "expected RuntimeError to bubble up"
    except RuntimeError as e:
        assert "Real bug" in str(e)
