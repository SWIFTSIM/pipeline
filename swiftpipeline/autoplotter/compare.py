"""
Tools for creating comparison plots built out of the saved data.yml files.
"""

import matplotlib.pyplot as plt
import yaml
import unyt

from numpy import log10
from typing import Union, List, Dict, Optional, Tuple
from swiftpipeline.autoplotter.objects import AutoPlot, valid_line_types
from swiftpipeline.autoplotter.plot import decorate_axes

from swiftpipeline.autoplotter.objects import AutoPlotter
from swiftpipeline.autoplotter.metadata import AutoPlotterMetadata
from swiftpipeline.observations import load_observations


class FakeCatalogue:
    """
    Stores redshift and scale factor information for use in comparison plots.
    """

    def __init__(self, z=0.0, a=0.0):
        self.z = float(z)
        self.a = float(a)
        return


def load_yaml_line_data(
    paths: Union[str, List[str]], names: Union[str, List[str]]
) -> Dict[str, Dict]:
    """
    Load the ``yaml`` data from the files for lines.
    """

    if not isinstance(paths, list):
        paths = [paths]
        names = [names]

    data = {}

    for path, name in zip(paths, names):
        try:
            with open(path, "r") as handle:
                data[name] = yaml.load(handle, Loader=yaml.Loader)
        except (OSError, FileNotFoundError):
            data[name] = {}

    return data


def recreate_instances(
    config: Union[str, List[str]],
    paths: Union[str, List[str]],
    names: Union[str, List[str]],
    observational_data_directory: Optional[str] = None,
    file_extension: Optional[str] = None,
    correction_directory: Optional[str] = None,
) -> Tuple[AutoPlotter, AutoPlotterMetadata, Dict[str, Dict]]:
    """
    Recreates instances of required objects for passing to
    ``recreate_single_figure``.
    """

    auto_plotter = AutoPlotter(
        config,
        observational_data_directory=observational_data_directory,
        correction_directory=correction_directory,
    )

    file_extension = file_extension if file_extension is not None else "png"

    auto_plotter.file_extension = file_extension

    auto_plotter_metadata = AutoPlotterMetadata(auto_plotter=auto_plotter)

    line_data = load_yaml_line_data(paths=paths, names=names)

    return auto_plotter, auto_plotter_metadata, line_data


def recreate_single_figure(
    plot: AutoPlot,
    line_data: Dict[str, Dict],
    output_directory: str,
    file_type: str,
) -> None:
    """
    Recreates a single figure using the data in ``line_data`` and the metadata in
    ``plot``.
    """

    try:
        first_line_metadata = line_data[list(line_data.keys())[0]]["metadata"]
        fake_catalogue = FakeCatalogue(
            z=first_line_metadata["redshift"], a=first_line_metadata["scale_factor"]
        )
    except KeyError:
        fake_catalogue = FakeCatalogue()

    fig, ax = plt.subplots()

    # Add simulation data
    for line_type in valid_line_types:
        line = getattr(plot, f"{line_type}_line", None)
        if line is not None:
            for color, (name, data) in enumerate(line_data.items()):
                color_name = f"C{color}"

                try:
                    this_plot = data[plot.filename]
                    this_line_dict = this_plot["lines"][line_type]
                except KeyError:
                    continue

                if (
                    this_line_dict.get("centers", []) == []
                    and this_line_dict.get("additional_points_x", []) == []
                ):
                    continue

                centers = unyt.unyt_array(this_line_dict["centers"], units=plot.x_units)
                heights = unyt.unyt_array(this_line_dict["values"], units=plot.y_units)
                errors = unyt.unyt_array(this_line_dict["scatter"], units=plot.y_units)

                ax.set_xlabel(this_plot.get("x_label", ax.get_xlabel()))
                ax.set_ylabel(this_plot.get("y_label", ax.get_ylabel()))

                additional_x = unyt.unyt_array(
                    this_line_dict.get("additional_points_x", []), units=plot.x_units
                )
                additional_y = unyt.unyt_array(
                    this_line_dict.get("additional_points_y", []), units=plot.y_units
                )

                if line.scatter == "errorbar":
                    ax.errorbar(
                        centers, heights, yerr=errors, label=name, color=color_name
                    )
                elif line.scatter == "shaded":
                    ax.plot(centers, heights, label=name, color=color_name)

                    if errors.shape[0]:
                        if errors.ndim > 1:
                            down, up = errors
                        else:
                            up = errors
                            down = errors
                    else:
                        up = 0
                        down = 0

                    ax.fill_between(
                        centers,
                        heights - down,
                        heights + up,
                        color=color_name,
                        alpha=0.3,
                        linewidth=0.0,
                    )

                else:
                    ax.plot(centers, heights, label=name)

                ax.scatter(additional_x, additional_y, c=color_name)

                if plot.y_lim is not None and len(additional_x) > 0:
                    line.highlight_data_outside_domain(
                        ax,
                        additional_x.value,
                        additional_y.value,
                        color_name,
                        (plot.x_lim[0].value, plot.x_lim[1].value),
                        (plot.y_lim[0].value, plot.y_lim[1].value),
                    )

    # Add observational data second to allow for colour precedence to go to runs
    observational_data_scale_factor_bracket = [
        10 ** (log10(fake_catalogue.a) + plot.observational_data_bracket_width),
        10 ** (log10(fake_catalogue.a) - plot.observational_data_bracket_width),
    ]

    observational_data_redshift_bracket = [
        (1 - x) / x for x in observational_data_scale_factor_bracket
    ]

    valid_observational_data = load_observations(
        plot.observational_data_filenames,
        redshift_bracket=observational_data_redshift_bracket,
    )

    for index, data in enumerate(valid_observational_data, start=1):
        data.x.convert_to_units(plot.x_units)
        data.y.convert_to_units(plot.y_units)
        data.plot_on_axes(
            ax, errorbar_kwargs=dict(zorder=-10, color=f"C{index + color}")
        )

    if plot.x_log:
        ax.set_xscale("log")
    if plot.y_log:
        ax.set_yscale("log")

    try:
        ax.set_xlim(*unyt.unyt_array(plot.x_lim, units=plot.x_units))
    except AttributeError:
        pass

    try:
        ax.set_ylim(*unyt.unyt_array(plot.y_lim, units=plot.y_units))
    except AttributeError:
        pass

    decorate_axes(
        ax,
        z=fake_catalogue.z,
        a=fake_catalogue.a,
        comment=plot.comment,
        legend_loc=plot.legend_loc,
        redshift_loc=plot.redshift_loc,
        comment_loc=plot.comment_loc,
    )

    fig.savefig(f"{output_directory}/{plot.filename}.{file_type}")
    plt.close(fig)
