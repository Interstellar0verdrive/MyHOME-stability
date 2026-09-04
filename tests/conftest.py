"""Shared pytest configuration for the MyHOME custom integration tests.

``pytest-homeassistant-custom-component`` provides the ``hass`` fixture family; the
autouse fixture below enables loading of ``custom_components/`` in every test.
Pure-python tests (e.g. ``test_validate.py``) do not need ``hass`` and simply ignore
these fixtures.
"""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for every test."""
    yield
