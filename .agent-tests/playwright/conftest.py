import pytest
from playwright.sync_api import Error as PlaywrightError


@pytest.fixture(scope="session")
def browser(playwright, browser_type_launch_args):
    """Launch chromium; skip (not fail) when the host lacks system libraries."""
    try:
        b = playwright.chromium.launch(**browser_type_launch_args)
    except PlaywrightError as exc:
        pytest.skip("chromium cannot start in this environment: %s" % str(exc).splitlines()[0])
    yield b
    b.close()
