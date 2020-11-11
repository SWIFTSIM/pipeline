"""
Configuration object for the entire pipeline.
"""

import yaml
from typing import List

# Items to read directly from the yaml file with their defaults
direct_read = {
    "auto_plotter_directory": None,
    "auto_plotter_registration": None,
    "observational_data_directory": None,
    "matplotlib_stylesheet": "default",
    "description_template": None,
    "custom_css": None,
}


class Script(object):
    """
    Object describing the core properties of a 'script'.
    """

    # Filename of the python script to be ran
    filename: str
    # Caption for displaying in a webpage, etc.
    caption: str
    # Output file name; required to match up the caption and file in
    # postprocessing
    output_file: str
    # Section heading; used to classify this with similar figures
    # in the output.
    section: str
    # Plot title; written above the caption
    title: str
    # Show on webpage; Defaults to True but used to disable webpage plotting
    # in the config file if required.
    show_on_webpage: bool
    # additional arguments to be fed to a given script
    additional_arguments: dict
    # Use in the case where we have comparisons? The scripts may be disabled
    # in comparison cases for performance reasons.
    use_for_comparison: bool

    def __init__(self, script_dict: dict):
        """
        Takes the dictionary and extracts it to inner variables.
        """

        self.filename = script_dict.get("filename", "")
        self.caption = script_dict.get("caption", "")
        self.output_file = script_dict.get("output_file", "")
        self.section = script_dict.get("section", "")
        self.title = script_dict.get("title", "")
        self.show_on_webpage = script_dict.get("show_on_webpage", True)
        self.additional_arguments = script_dict.get("additional_arguments", {})
        self.use_for_comparison = script_dict.get("use_for_comparison", True)
        return

    def __str__(self):
        return (
            f"Script: {self.filename}, produces {self.filename} in {self.section} "
            f"described as {self.caption}"
        )

    def __repr__(self):
        return f"Script object describing the {self.filename} script."

    @property
    def additional_argument_list(self):
        """
        Gets a list of additional arguments, with --key, value ordering.
        """

        additional_arguments = []

        for key, value in self.additional_arguments.items():
            additional_arguments.append(f"--{key}")
            additional_arguments.append(f"{value}")

        return additional_arguments


class Config(object):
    """
    Configuration object containing the major parameters read from the
    yaml file.
    """

    # Raw config read directly from the file, before processing.
    raw_config: dict
    raw_scripts: List[Script]

    # Set up the object.
    __slots__ = list(direct_read.keys()) + [
        "raw_scripts",
        "config_directory",
        "raw_config",
    ]

    def __init__(self, config_directory: str):
        """
        Set up and load the config to this object.

        Parameters
        ----------

        config_directory: str
            Directory containing the configuration ``config.yml``.
        """

        self.config_directory = config_directory

        self.__read_config()
        self.__extract_to_variables()
        self.__extract_scripts()

        return

    def __str__(self):
        return f"Configuration file object describing {self.config_directory}"

    def __repr__(self):
        return self.__str__()

    def __read_config(self):
        """
        Read the ``config.yml`` and store the basic contents in
        ``self.raw_config``.
        """

        with open(f"{self.config_directory}/config.yml", "r") as handle:
            self.raw_config = yaml.safe_load(handle)

        return

    def __extract_to_variables(self):
        """
        Extracts items from the configuration dictionary to local variables.
        """

        for variable, default in direct_read.items():
            setattr(self, variable, self.raw_config.get(variable, default))

        return

    def __extract_scripts(self):
        """
        Extracts the items in the scripts section to their own
        list with objects describing each script.
        """

        raw_scripts = self.raw_config.get("scripts", [])
        self.raw_scripts = [
            Script(script_dict=script_dict) for script_dict in raw_scripts
        ]

        return

    @property
    def scripts(self):
        """
        Gets all of the scripts defined in the parameter file.
        """
        return self.raw_scripts

    @property
    def comparison_scripts(self):
        """
        Gets the scripts only to be used in comparisons from the parameter
        file.
        """
        return [script for script in self.raw_scripts if script.use_for_comparison]
