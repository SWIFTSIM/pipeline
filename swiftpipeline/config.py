"""
Configuration object for the entire pipeline.
"""

import yaml
from typing import List, Union
import os
import glob

# Items to read directly from the yaml file with their defaults
direct_read = {
    "auto_plotter_registration": [],
    "auto_plotter_global_mask": None,
    "observational_data_directory": None,
    "matplotlib_stylesheet": "default",
    "description_template": None,
    "custom_css": None,
}

# Configuration options that are appendable lists
# If one of these is found in an extra configuration file, its value(s) is (are)
# added to the existing list.
appendable_config_keys = [
    "scripts",
    "special_modes",
    "auto_plotter_configs",
    "auto_plotter_registration",
]


class Script(object):
    """
    Object describing the core properties of a 'script'.
    """

    # Filename of the python script to be ran
    filename: str
    # Output file name(s)
    # List of strings if the script produces several plots; otherwise, string
    # If list, required to have the same size as caption and title
    output_file: Union[str, List[str]]
    # Caption(s) for displaying in a webpage, etc.
    # List of strings if the script produces several plots (one caption per plot); otherwise, string
    caption: Union[str, List[str]]
    # Section heading; used to classify this with similar figures
    # in the output.
    section: str
    # Plot title(s); written above the caption
    # List of strings if the script makes several plots (one title per plot); otherwise, string
    title: Union[str, List[str]]
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


class SpecialMode(object):
    """
  Special mode that runs a script to make changes to the catalogue between reading it and plotting it.
  """

    name: str
    script_file: str

    def __init__(self, name: str, script_file: str):
        self.name = name
        self.script_file = script_file

    def adapt_catalogue(self, catalogue):
        with open(self.script_file, "r") as handle:
            exec(handle.read())


class Config(object):
    """
    Configuration object containing the major parameters read from the
    yaml file.
    """

    # Raw config read directly from the file, before processing.
    raw_config: dict
    raw_scripts: List[Script]
    raw_specials: List[SpecialMode]

    # Set up the object.
    __slots__ = list(direct_read.keys()) + [
        "raw_scripts",
        "raw_specials",
        "config_directory",
        "raw_config",
        "auto_plotter_configs",
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
        self.__extract_specials()

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
        for key in appendable_config_keys:
            if key not in self.raw_config:
                self.raw_config[key] = []

        if "auto_plotter_registration" in self.raw_config:
            if not isinstance(self.raw_config["auto_plotter_registration"], list):
                self.raw_config["auto_plotter_registration"] = [
                    self.raw_config["auto_plotter_registration"]
                ]
        else:
            self.raw_config["auto_plotter_registration"] = []

        if "extra_config" in self.raw_config:
            for extra_config_file in self.raw_config["extra_config"]:
                extra_raw_config = None
                with open(
                    f"{self.config_directory}/{extra_config_file}", "r"
                ) as handle:
                    extra_raw_config = yaml.safe_load(handle)
                for key in extra_raw_config:
                    if key in appendable_config_keys:
                        # append additional items
                        extra_list = extra_raw_config[key]
                        if not isinstance(extra_list, list):
                            extra_list = [extra_list]
                        for extra_item in extra_list:
                            self.raw_config[key].append(extra_item)
                    else:
                        # if the key is not an appendable list, it must be a
                        # parameter that can only have one value
                        # overwrite the original value
                        self.raw_config[key] = extra_raw_config[key]

        return

    def __extract_to_variables(self):
        """
        Extracts items from the configuration dictionary to local variables.
        """

        for variable, default in direct_read.items():
            setattr(self, variable, self.raw_config.get(variable, default))

        self.auto_plotter_configs = []
        for auto_plotter_config in self.raw_config.get("auto_plotter_configs", []):
            auto_plotter_config = f"{self.config_directory}/{auto_plotter_config}"
            if os.path.isfile(auto_plotter_config):
                self.auto_plotter_configs.append(auto_plotter_config)
            else:
                self.auto_plotter_configs.extend(
                    reversed(glob.glob(f"{auto_plotter_config}/*.yml"))
                )
        # support legacy auto_plotter_directory variable
        if "auto_plotter_directory" in self.raw_config:
            self.auto_plotter_configs.extend(
                reversed(
                    glob.glob(
                        f"{self.config_directory}/{self.raw_config['auto_plotter_directory']}/*.yml"
                    )
                )
            )

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

    def __extract_specials(self):
        raw_specials = self.raw_config.get("special_modes", [])
        self.raw_specials = {
            sp["name"]: SpecialMode(
                sp["name"], f'{self.config_directory}/{sp["script"]}'
            )
            for sp in raw_specials
        }
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

    def get_special_mode(self, mode):
        if not mode in self.raw_specials:
            raise AttributeError(f"Unknown special mode: {mode}!")
        return self.raw_specials[mode]
