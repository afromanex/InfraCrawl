"""
Test for run.py main() function with dependency injection.
Demonstrates that the DIP refactoring enables integration testing.
"""
from unittest.mock import Mock, patch
from run import main
from infracrawl.container import Container


def test_container_creates_dependencies():
    """Test that the container creates all required dependencies."""
    container = Container()
    container.config.database_url.from_value(None)
    container.config.user_agent.from_value("TestBot/1.0")
    container.config.http_timeout.from_value(10)
    
    # Verify repositories can be created
    pages_repo = container.pages_repository()
    links_repo = container.links_repository()
    configs_repo = container.configs_repository()
    
    assert pages_repo is not None
    assert links_repo is not None
    assert configs_repo is not None


def test_container_creates_services():
    """Test that the container creates service instances."""
    container = Container()
    container.config.database_url.from_value(None)
    container.config.user_agent.from_value("TestBot/1.0")
    container.config.http_timeout.from_value(10)
    container.config.crawl_delay.from_value(1.0)
    
    # Verify services can be created
    http_service = container.http_service()
    robots_service = container.robots_service()
    config_service = container.config_service()
    crawler = container.crawler()
    
    assert http_service is not None
    assert robots_service is not None
    assert config_service is not None
    assert crawler is not None


def test_main_accepts_injected_container():
    """Test that main() can accept an injected container for testing."""
    # Create a test container with mocked dependencies
    container = Container()
    container.config.database_url.from_value(None)
    container.config.user_agent.from_value("TestBot/1.0")
    container.config.http_timeout.from_value(10)
    container.config.crawl_delay.from_value(1.0)
    
    # Override specific providers with mocks
    container.config_service.override(Mock(sync_configs_with_disk=Mock()))
    
    # Mock uvicorn.run to prevent server startup
    with patch('run.uvicorn.run') as mock_uvicorn:
        # Call main with injected container
        main(container=container)
        
        # Verify server would have started
        assert mock_uvicorn.called
