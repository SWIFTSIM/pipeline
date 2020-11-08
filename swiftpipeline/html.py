"""
Functions that aid in the production of the HTML webpages.
"""

from swiftpipeline import __version__ as pipeline_version
from swiftpipeline.config import Config

from swiftsimio import SWIFTDataset

from velociraptor import __version__ as velociraptor_version
from velociraptor.autoplotter.metadata import AutoPlotterMetadata

from jinja2 import Environment, PackageLoader, FileSystemLoader, select_autoescape
from time import strftime
from typing import List

import unyt


def format_number(number):
    """
    Formats a number from float (with or without units) to a latex-like number.
    """

    try:
        units = f"\\; {number.units.latex_repr}"
    except:
        units = ""

    try:
        mantissa, exponent = ("%.3g" % number).split("e+")
        exponent = f" \\times 10^{{{int(exponent)}}}"
    except:
        mantissa = "%.3g" % number
        exponent = ""

    return f"\\({mantissa}{exponent}{units}\\)"


def get_if_present_float(dictionary, value: str, input_unit=None, output_unit=None):
    """
    A replacement for .get() that also formats the number if present.
    
    Assumes data should be a float.
    """

    try:
        value = float(dictionary[value])

        if input_unit is not None:
            value = unyt.unyt_quantity(value, input_unit)

            if output_unit is not None:
                value.convert_to_units(output_unit)

        return format_number(value)
    except KeyError:
        return ""


def get_if_present_int(dictionary, value: str, input_unit=None, output_unit=None):
    """
    A replacement for .get() that also formats the number if present.
    
    Assumes data should be an integer.
    """

    try:
        value = int(dictionary[value])

        if input_unit is not None:
            value = unyt.unyt_quantity(value, input_unit)

            if output_unit is not None:
                value.convert_to_units(output_unit)

        return format_number(value)
    except KeyError:
        return ""


class WebpageCreator(object):
    """
    Creates webpages based on the information that is provided in
    the plots metadata through the autoplotter and the additional
    plotting interface provided through the pipeline.
    """

    environment: Environment
    loader: PackageLoader

    variables: dict
    html: str

    auto_plotter_metadata: AutoPlotterMetadata
    config: Config

    def __init__(self):
        """
        Sets up the ``jinja`` templating system.
        """

        self.loader = PackageLoader("swiftpipeline", "templates")
        self.environment = Environment(
            loader=self.loader, autoescape=select_autoescape(["js"])
        )

        # Initialise empty variables dictionary, with the versions of
        # this package and the velociraptor package used.
        self.variables = dict(
            pipeline_version=pipeline_version,
            velociraptor_version=velociraptor_version,
            creation_date=strftime(r"%Y-%m-%d"),
            sections={},
            runs=[],
        )

        return

    def render_webpage(self, template: str = "plot_viewer.html") -> str:
        """
        Renders a webpage based on the internal variables stored in
        the ``variables`` dictionary.

        Parameters
        ----------

        template: str
            The name of the template that you wish to use. Defaults to
            "plot_viewer.html".

        Returns
        -------

        html: str
            The resulting HTML. This is also stored in ``.html``.
        """

        self.html = self.environment.get_template(template, parent="base.html").render(
            **self.variables
        )

        return self.html

    def add_metadata(self, page_name: str):
        """
        Add additional metadata to the page.

        Parameters
        ----------

        page_name: str
            Name to put in the page title.
        """

        self.variables.update(dict(page_name=page_name))

    def add_auto_plotter_metadata(self, auto_plotter_metadata: AutoPlotterMetadata):
        """
        Adds the auto plotter metadata to the section / plot metadata.

        Parameters
        ----------

        auto_plotter_metadata: AutoPlotterMetadata
            The complete instance of ``AutoPlotterMetadata`` after running the
            ``velociraptor`` ``AutoPlotter``.
        """

        self.auto_plotter_metadata = auto_plotter_metadata

        # Unique sections
        sections = {plot.section for plot in auto_plotter_metadata.metadata}

        for section in sections:
            plots = [
                dict(
                    filename=f"{plot.filename}.{auto_plotter_metadata.file_extension}",
                    title=plot.title,
                    caption=plot.caption,
                    hash=abs(hash(plot.caption + plot.title)),
                )
                for plot in auto_plotter_metadata.metadata
                if plot.section == section and plot.show_on_webpage
            ]

            current_section_plots = (
                self.variables["sections"].get(section, {"plots": []}).get("plots", [])
            )

            self.variables["sections"][section] = dict(
                title=section,
                plots=plots + current_section_plots,
                id=abs(hash(section)),
            )

        return

    def add_config_metadata(self, config: Config, is_comparison: bool = False):
        """
        Adds the section metadata from the additional plots
        defined under ``config.yml::scripts``.

        Parameters
        ----------

        config: Config
            Configuration object from ``swift-pipeline``.

        is_comparison: bool, optional
            Is this webpage being created for a comparison? Default: False.
        """

        self.config = config

        # Unique sections
        sections = {script.section for script in config.scripts}

        scripts_to_use = config.comparison_scripts if is_comparison else config.scripts

        for section in sections:
            plots = [
                dict(
                    filename=script.output_file,
                    title=script.title,
                    caption=script.caption,
                    hash=abs(hash(script.caption + script.title)),
                )
                for script in scripts_to_use
                if script.section == section and script.show_on_webpage
            ]

            current_section_plots = (
                self.variables["sections"].get(section, {"plots": []}).get("plots", [])
            )

            self.variables["sections"][section] = dict(
                title=section,
                plots=plots + current_section_plots,
                id=abs(hash(section)),
            )

        return

    def add_run_metadata(self, config: Config, snapshots: List[SWIFTDataset]):
        """
        Adds the "run" metadata (using the user-defined description.html).

        Parameters
        ----------

        config: Config
            Configuration object from ``swift-pipeline``.

        snapshots: List[SWIFTDataset].
            SWIFT Datasets used to generate the HTML with.
        """

        loader = FileSystemLoader(config.config_directory)
        environment = Environment(loader=loader)

        environment.filters["format_number"] = format_number
        environment.filters["get_if_present_float"] = get_if_present_float
        environment.filters["get_if_present_int"] = get_if_present_int

        if config.description_template is not None:
            self.variables["runs"] = [
                dict(
                    description=environment.get_template(
                        config.description_template
                    ).render(data=data),
                )
                for data in snapshots
            ]

        if config.custom_css is not None:
            self.variables["custom_css"] = environment.get_template(
                config.custom_css
            ).render()

        return

    def save_html(self, filename: str):
        """
        Saves the html in ``self.html`` to the filename provided.

        Parameters
        ----------

        filename: str
            Full filename (including file path) to save the HTML as.
        """

        with open(filename, "w") as handle:
            handle.write(self.html)
