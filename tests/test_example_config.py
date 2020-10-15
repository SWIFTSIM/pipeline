"""
Tests that loading the config works and does not crash.
"""

from swiftpipeline.config import Config


def test_config(path="tests/test_config"):
    """
    Tests loading a config doesn't induce a crash, and
    that we have valid data.
    """

    config = Config(config_directory=path)
