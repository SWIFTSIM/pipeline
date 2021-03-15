"""
Tests the HTML generation code, with mocked up example scripts.
"""

from swiftpipeline.html import WebpageCreator


def test_basic():
    """
    Tests if we can make a basic page without crashing. Essentially
    tests that all of the templating code is linked up correctly.
    """

    creator = WebpageCreator()
    plots = [dict(title="Test Plot", caption="Test Caption", filename="test.png")]
    creator.variables["sections"] = {
        "A": dict(title="Test Section", id=abs(hash("Test Section")), plots=plots)
    }
    creator.add_metadata(page_name="Test Page")
    creator.render_webpage()

    return
