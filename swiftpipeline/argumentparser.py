"""
Argument parsing wrapper for the additional scripts.
"""

import argparse as ap
from typing import List, Union, Tuple, Optional
from swiftpipeline.config import Config


class ScriptArgumentParser(object):
    """
    Script argument parser for ``swiftpipeline`` additional scripts.
    
    They must conform to the following command-line api:

    + ``-s``: List of snapshots (not including directory)
    + ``-c``: List of catalogues (not including directory)
    + ``-d``: List of input directories (both the snapshot and catalogue
              should be in there).
    + ``-n``: List of run names, optional, for use in legends.
    + ``-o``: Output directory for the figure.
    + ``-C``: Configuration directory (contains the ``config``.yml)
    """

    parser: ap.ArgumentParser
    description: str

    # List of snapshots that are to be processed.
    snapshot_list: List[str]
    # List of catalogues (in the same order as snapshots) to be processed.
    catalogue_list: List[str]
    # List of directories that contain the above snapshots and catalogues
    directory_list: List[str]
    # List of representative names for the snapshots; may be a list of Nones
    name_list: List[Optional[str]]
    # Directory to output the figure to
    output_directory: str
    # Configuration directory containing config.yml.
    config_directory: str

    # Number of inputs to the script.
    number_of_inputs: int

    # Config object containing all relevant information.
    config: Config

    def __init__(self, description):
        """
        Initialises the argument parser object and parses the args, as they say.
        """

        self.description = description

        self.__setup_parser()
        self.__parse_arguments()

        return

    def __setup_parser(self):
        """
        Set up the argument parser.
        """

        self.parser = ap.ArgumentParser(description=self.description)

        self.parser.add_argument(
            "-s",
            "--snapshots",
            help="Snapshot list. Do not include directory. Example: snapshot_0000.hdf5",
            type=str,
            required=True,
            nargs="*",
        )

        self.parser.add_argument(
            "-c",
            "--catalogues",
            help="Catalogue list. Do not include directory. Example: catalogue_0000.properties",
            type=str,
            required=True,
            nargs="*",
        )

        self.parser.add_argument(
            "-d",
            "--input-directories",
            help="Input directory list. Catalogue and snapshot are in this directory.",
            type=str,
            required=True,
            nargs="*",
        )

        self.parser.add_argument(
            "-n",
            "--run-names",
            help="Names of the runs for placement in legends.",
            type=str,
            required=False,
            nargs="*",
        )

        self.parser.add_argument(
            "-o",
            "--output-directory",
            help="Output directory for the produced figure.",
            type=str,
            required=True,
        )

        self.parser.add_argument(
            "-C",
            "--config",
            help="Config directory that contains config.yaml",
            type=str,
            required=True,
        )

        return

    def __parse_arguments(self):
        """
        Parses the arguments from the ``parser``.
        """

        args = self.parser.parse_args()

        self.number_of_inputs = len(args.snapshots)

        self.snapshot_list = args.snapshots
        self.catalogue_list = args.catalogues
        self.directory_list = args.input_directories
        self.name_list = (
            args.run_names
            if args.run_names is not None
            else [None] * self.number_of_inputs
        )
        self.output_directory = args.output_directory
        self.config_directory = args.config

        self.config = Config(config_directory=self.config_directory)

        return

    @property
    def stylesheet_location(self):
        return f"{self.config_directory}/{self.config.matplotlib_stylesheet}"
