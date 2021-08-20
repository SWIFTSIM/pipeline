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
from typing import List, Dict
from pathlib import Path

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


def camel_to_title(string):
    return string.title().replace("_", " ")


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
        sections = {
            plot.section
            for plot in auto_plotter_metadata.metadata
            if plot.show_on_webpage
        }

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
        sections = {
            script.section for script in config.scripts if script.show_on_webpage
        }

        scripts_to_use = config.comparison_scripts if is_comparison else config.scripts

        for section in sections:

            plots: List[Dict] = []

            for script in scripts_to_use:
                if script.section == section and script.show_on_webpage:

                    # Check whether we expect more than one plot (output file) produced by the script
                    if isinstance(script.output_file, list):

                        # If so, check that each plot has its own title and caption
                        assert isinstance(script.title, list) and isinstance(
                            script.caption, list
                        ), (
                            f"Check the config parameters for '{script.filename}'. "
                            f"If 'output_file' is a list object, then 'title' and 'caption' must be too!"
                        )

                        # Check that the number of plots is the same as the number of their titles and captions
                        assert (
                            len(script.output_file)
                            == len(script.title)
                            == len(script.caption)
                        ), (
                            f"Check the config parameters for '{script.filename}'. "
                            f"Lists 'output_file', 'title' and 'caption' must have the same size!"
                        )

                        # Loop over plots made by the script
                        for output_file, title, caption in zip(
                            script.output_file, script.title, script.caption
                        ):

                            # Save everything into a dict
                            plot = dict(
                                filename=output_file,
                                title=title,
                                caption=caption,
                                hash=abs(hash(caption + output_file)),
                            )

                            # Add collect in a list
                            plots.append(plot)

                    # The script makes just a single plot
                    else:
                        plot = dict(
                            filename=script.output_file,
                            title=script.title,
                            caption=script.caption,
                            hash=abs(hash(script.caption + script.output_file)),
                        )
                        plots.append(plot)

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
        environment.filters["camel_to_title"] = camel_to_title
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


class ImageWebpageCreator(object):
    """
    Creates the webpages for the imaging system.
    """

    environment: Environment
    loader: PackageLoader

    variables: dict
    html: str

    config: Config

    def __init__(self, haloes, config):
        """
        Sets up the ``jinja`` templating system.
        """

        self.loader = PackageLoader("swiftpipeline", "templates")
        self.environment = Environment(
            loader=self.loader, autoescape=select_autoescape(["js"])
        )

        self.environment.filters["format_number"] = format_number
        self.environment.filters["camel_to_title"] = camel_to_title
        self.environment.filters["get_if_present_float"] = get_if_present_float
        self.environment.filters["get_if_present_int"] = get_if_present_int

        # Initialise empty variables dictionary, with the versions of
        # this package and the velociraptor package used.
        self.variables = dict(
            pipeline_version=pipeline_version,
            velociraptor_version=velociraptor_version,
            creation_date=strftime(r"%Y-%m-%d"),
            haloes=haloes,
            config=config,
            images=config.images,
        )

        return

    def render_gallery(self) -> str:
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

        self.html = self.environment.get_template(
            "image_gallery.html", parent="base.html"
        ).render(page_name="Image Gallery", **self.variables)

        return self.html

    def render_single_halo(self, halo) -> str:
        return self.environment.get_template(
            "image_halo.html", parent="base.html"
        ).render(page_name=f"Halo {halo.unique_id}", halo=halo, **self.variables)

    def save_html(self, output_path: Path):
        """
        Saves all the relevant HTML, to the output path.
        """

        gallery_html = self.render_gallery()
        gallery_filename = Path(output_path) / "index.html"

        with open(gallery_filename, "w") as handle:
            handle.write(gallery_html)

        for halo in self.variables["haloes"]:
            halo_html = self.render_single_halo(halo)
            halo_filename = Path(output_path) / f"halo_{halo.unique_id}/index.html"

            with open(halo_filename, "w") as handle:
                handle.write(halo_html)
