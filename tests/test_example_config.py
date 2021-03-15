"""
Tests that loading the config works and does not crash.
"""

from swiftpipeline.config import Config
from swiftpipeline.imageconfig import ImageConfig


def test_config(path="tests/test_config"):
    """
    Tests loading a config doesn't induce a crash, and
    that we have valid data.
    """

    config = Config(config_directory=path)


def test_image_config(path="tests/test_config"):
    """
    Tests loading an image config doesn't induce a crash,
    and that we have valid data.
    """

    config = ImageConfig(config_directory=path)