"""
Main objects for holding information relating to the autoplotter.
"""

from swiftpipeline.autoplotter.lines import AutoPlotterLine, valid_line_types
from swiftpipeline.autoplotter.box_size_correction import BoxSizeCorrection
from swiftpipeline.observations import load_observations

import swiftpipeline.autoplotter.plot as plot

from functools import reduce
from unyt import unyt_quantity, unyt_array, matplotlib_support
from unyt.exceptions import UnitConversionError
import numpy as np
from numpy import log10, linspace, logspace, array, logical_and, logical_not, ones
import unyt.dimensions

# Register mh (hydrogen atom mass) and mag (magnitude) as units
try:
    from unyt import unit_registry as _ur
    _ur.default_unit_registry.add("mh", float(unyt.mh.to("kg").value), unyt.dimensions.mass)
    _ur.default_unit_registry.add("mag", 1.0, unyt.dimensions.dimensionless)
except Exception:
    pass
from matplotlib.pyplot import Axes, Figure, close, subplots
from yaml import safe_load
from typing import Union, List, Dict, Tuple
from pathlib import Path

from os import path, mkdir
from collections import OrderedDict
import sys

valid_plot_types = [
    "scatter",
    "2dhistogram",
    "massfunction",
    "luminosityfunction",
    "histogram",
    "cumulative_histogram",
    "adaptivemassfunction",
]

matplotlib_support.label_style = "[]"


def _convert_units(arr, units):
    if hasattr(arr, "convert_to_physical"):
        arr.convert_to_physical(units)
    else:
        arr.convert_to_units(units)


class AutoPlotterError(Exception):
    def __init__(self, message):
        self.message = message


class AutoPlot(object):
    """
    Object representing a single figure of x against y.
    """

    # Forward declarations
    plot_type: str
    x: str
    y: str
    x_log: bool
    y_log: bool
    x_units: unyt_quantity
    y_units: unyt_quantity
    x_lim: List[Union[unyt_quantity, None]]
    y_lim: List[Union[unyt_quantity, None]]
    x_shade: List[Union[unyt_quantity, None]]
    y_shade: List[Union[unyt_quantity, None]]
    x_label: Union[None, str] = None
    y_label: Union[None, str] = None
    x_label_override: Union[None, str] = None
    y_label_override: Union[None, str] = None
    comment: Union[None, str]
    mean_line: Union[None, AutoPlotterLine]
    median_line: Union[None, AutoPlotterLine]
    mass_function_line: Union[None, AutoPlotterLine]
    luminosity_function_line: Union[None, AutoPlotterLine]
    adaptive_mass_function_line: Union[None, AutoPlotterLine]
    adaptive_luminosity_function_line: Union[None, AutoPlotterLine]
    histogram_line: Union[None, AutoPlotterLine]
    cumulative_histogram_line: Union[None, AutoPlotterLine]
    number_of_bins: int
    min_num_points_highlight: int
    reverse_cumsum: bool
    x_bins: unyt_array
    y_bins: unyt_array
    # Select centrals (True) or satellites (True), mutually exclusive
    select_centrals: bool
    select_satellites: bool
    structure_mask: Union[None, array]
    selection_mask: Union[None, array]
    correction_directory: str
    box_size_correction: Union[None, BoxSizeCorrection]
    legend_loc: str
    redshift_loc: str
    comment_loc: str
    observational_data_filenames: List[str]
    observational_data_bracket_width: float
    observational_data_directory: str
    global_mask: Union[None, array]

    def __init__(
        self,
        filename: str,
        data: Dict[str, Union[Dict, str]],
        observational_data_directory: str,
        correction_directory: str,
    ):
        self.filename = filename
        self.data = data
        self.observational_data_directory = observational_data_directory
        self.correction_directory = correction_directory

        self._parse_data()

        return

    def _parse_coordinate_quantity(self, coordinate: str) -> None:
        try:
            setattr(self, coordinate, self.data[coordinate]["quantity"])
            setattr(
                self,
                f"{coordinate}_units",
                unyt_quantity(1.0, units=self.data[coordinate]["units"]),
            )
        except KeyError:
            raise AutoPlotterError(
                f"You must provide an {coordinate}-quantity and units to plot for {self.filename}"
            )

        return

    def _parse_coordinate_quantity_units(self, coordinate: str) -> None:
        try:
            units = unyt_quantity(
                1.0, self.data[coordinate].get("units", "dimensionless")
            )
        except KeyError:
            units = unyt_quantity(1.0, units="dimensionless")

        setattr(self, f"{coordinate}_units", units)

        return

    def _set_coordinate_quantity_none(self, coordinate: str) -> None:
        setattr(self, coordinate, None)
        setattr(self, f"{coordinate}_units", unyt_quantity(1.0, units=None))

        return

    def _parse_coordinate_limit(self, coordinate: str) -> None:
        setattr(self, f"{coordinate}_lim", [None, None])

        try:
            getattr(self, f"{coordinate}_lim")[0] = unyt_quantity(
                float(self.data[coordinate]["start"]),
                units=self.data[coordinate]["units"],
            )
        except KeyError:
            pass

        try:
            getattr(self, f"{coordinate}_lim")[1] = unyt_quantity(
                float(self.data[coordinate]["end"]),
                units=self.data[coordinate]["units"],
            )
        except KeyError:
            pass

        return

    def _parse_coordinate_shade(self, coordinate: str) -> None:
        setattr(self, f"{coordinate}_shade", [None, None])

        try:
            getattr(self, f"{coordinate}_shade")[0] = unyt_quantity(
                float(self.data[coordinate]["shade"]["below"]),
                units=self.data[coordinate]["units"],
            )
        except KeyError:
            pass

        try:
            getattr(self, f"{coordinate}_shade")[1] = unyt_quantity(
                float(self.data[coordinate]["shade"]["above"]),
                units=self.data[coordinate]["units"],
            )
        except KeyError:
            pass

    def _parse_coordinate_log(self, coordinate: str) -> None:
        try:
            setattr(self, f"{coordinate}_log", bool(self.data[coordinate]["log"]))
        except KeyError:
            setattr(self, f"{coordinate}_log", True)

        return

    def _parse_coordinate_label_override(self, coordinate: str) -> None:
        try:
            setattr(
                self,
                f"{coordinate}_label_override",
                self.data[coordinate]["label_override"],
            )
        except KeyError:
            setattr(self, f"{coordinate}_label_override", None)

        return

    def _parse_line(self, line_type: str) -> None:
        try:
            setattr(
                self,
                f"{line_type}_line",
                AutoPlotterLine(line_type, self.data[line_type]),
            )
        except KeyError:
            setattr(self, f"{line_type}_line", None)

        self.min_num_points_highlight = self.data.get("min_num_points_highlight", 10)

        return

    def _parse_lines(self) -> None:
        for line_type in valid_line_types:
            self._parse_line(line_type)

        return

    def _parse_select_centrals(self) -> None:
        try:
            self.select_centrals = bool(self.data["select_centrals"])
        except KeyError:
            self.select_centrals = False

        self.structure_mask = None

        return

    def _parse_select_satellites(self) -> None:
        try:
            self.select_satellites = bool(self.data["select_satellites"])
        except KeyError:
            self.select_satellites = False

        self.structure_mask = None

        return

    def _parse_selection_mask(self) -> None:
        try:
            self.selection_mask = self.data["selection_mask"]
        except KeyError:
            self.selection_mask = None

        return

    def _parse_number_of_bins(self) -> None:
        try:
            self.number_of_bins = int(self.data["number_of_bins"])
        except KeyError:
            self.number_of_bins = 128

        return

    def _parse_comment(self) -> None:
        try:
            self.comment = str(self.data["comment"])
        except KeyError:
            self.comment = None

        return

    def _parse_loc(self) -> None:
        valid_locs = [
            "upper right",
            "upper left",
            "lower left",
            "lower right",
            "right",
            "lower center",
            "upper center",
            "center",
        ]

        try:
            self.legend_loc = str(self.data["legend_loc"])
            if self.legend_loc not in valid_locs:
                raise AutoPlotterError(
                    f"Choice of legend_loc {self.legend_loc} invalid. "
                    f"Choose from one of {valid_locs}"
                )
        except KeyError:
            self.legend_loc = "lower left"

        try:
            self.redshift_loc = str(self.data["redshift_loc"])
            if self.redshift_loc not in valid_locs:
                raise AutoPlotterError(
                    f"Choice of redshift_loc {self.redshift_loc} invalid. "
                    f"Choose from one of {valid_locs}"
                )
        except KeyError:
            replacements = OrderedDict(
                {
                    "upper": "lower",
                    "lower": "upper",
                    "left": "right",
                    "right": "left",
                    "center": "right",
                }
            )

            self.redshift_loc = " ".join(
                [b for a, b in replacements.items() if a in self.legend_loc.split(" ")]
            )

            self.redshift_loc = (
                "lower center" if self.redshift_loc == "left" else self.redshift_loc
            )

        try:
            self.comment_loc = str(self.data["comment_loc"])
            if self.comment_loc not in valid_locs:
                raise AutoPlotterError(
                    f"Choice of comment_loc {self.comment_loc} invalid. "
                    f"Choose from one of {valid_locs}"
                )
        except KeyError:
            replacements = OrderedDict(
                {
                    "upper": "upper",
                    "lower": "lower",
                    "left": "right",
                    "right": "left",
                    "center": "center",
                }
            )

            self.comment_loc = " ".join(
                [
                    b
                    for a, b in replacements.items()
                    if a in self.redshift_loc.split(" ")
                ]
            )

            self.comment_loc = (
                "upper center" if self.comment_loc == "left" else self.comment_loc
            )

        return

    def _parse_coordinate_histogram_bin(self, coordinate: str) -> None:
        start, end = getattr(self, f"{coordinate}_lim")

        if getattr(self, f"{coordinate}_log"):
            setattr(
                self,
                f"{coordinate}_bins",
                unyt_array(
                    logspace(log10(start), log10(end), self.number_of_bins + 1),
                    units=start.units,
                ),
            )
        else:
            setattr(
                self,
                f"{coordinate}_bins",
                linspace(start, end, self.number_of_bins + 1),
            )

        return

    def _parse_scatter(self) -> None:
        for coordinate in ["x", "y"]:
            self._parse_coordinate_quantity(coordinate)
            self._parse_coordinate_log(coordinate)
            self._parse_coordinate_limit(coordinate)
            self._parse_coordinate_label_override(coordinate)
            self._parse_coordinate_shade(coordinate)

        self._parse_loc()
        self._parse_comment()
        self._parse_lines()
        self._parse_select_centrals()
        self._parse_select_satellites()
        self._parse_selection_mask()

        return

    def _parse_2dhistogram(self) -> None:
        self._parse_scatter()
        self._parse_number_of_bins()

        for coordinate in ["x", "y"]:
            self._parse_coordinate_histogram_bin(coordinate)

        return

    def _parse_common_histogramtype(self) -> None:
        self._parse_coordinate_quantity("x")
        self._set_coordinate_quantity_none("y")
        self._parse_coordinate_quantity_units("y")

        for coordinate in ["x", "y"]:
            self._parse_coordinate_log(coordinate)
            self._parse_coordinate_limit(coordinate)
            self._parse_coordinate_label_override(coordinate)
            self._parse_coordinate_shade(coordinate)

        self._parse_number_of_bins()
        self._parse_coordinate_histogram_bin("x")
        self._parse_loc()
        self._parse_comment()
        self._parse_select_centrals()
        self._parse_select_satellites()
        self._parse_selection_mask()

        return

    def _parse_massfunction(self) -> None:
        self._parse_common_histogramtype()

        try:
            box_size_correction = str(self.data["box_size_correction"])
            self.box_size_correction = BoxSizeCorrection(
                box_size_correction, self.correction_directory
            )
        except KeyError:
            self.box_size_correction = None

        self.mass_function_line = AutoPlotterLine(
            line_type="mass_function",
            line_data=dict(
                plot=True,
                log=self.x_log,
                number_of_bins=self.number_of_bins,
                start=dict(value=self.x_lim[0].value, units=self.x_lim[0].units),
                end=dict(value=self.x_lim[1].value, units=self.x_lim[1].units),
            ),
            box_size_correction=self.box_size_correction,
        )

        return

    def _parse_adaptivemassfunction(self) -> None:
        self._parse_common_histogramtype()

        try:
            box_size_correction = str(self.data["box_size_correction"])
            self.box_size_correction = BoxSizeCorrection(
                box_size_correction, self.correction_directory
            )
        except KeyError:
            self.box_size_correction = None

        self.adaptive_mass_function_line = AutoPlotterLine(
            line_type="adaptive_mass_function",
            line_data=dict(
                plot=True,
                log=self.x_log,
                number_of_bins=self.number_of_bins,
                start=dict(value=self.x_lim[0].value, units=self.x_lim[0].units),
                end=dict(value=self.x_lim[1].value, units=self.x_lim[1].units),
                adaptive=True,
            ),
            box_size_correction=self.box_size_correction,
        )

        return

    def _parse_luminosityfunction(self) -> None:
        self._parse_common_histogramtype()

        self.luminosity_function_line = AutoPlotterLine(
            line_type="luminosity_function",
            line_data=dict(
                plot=True,
                log=self.x_log,
                number_of_bins=self.number_of_bins,
                start=dict(value=self.x_lim[0].value, units=self.x_lim[0].units),
                end=dict(value=self.x_lim[1].value, units=self.x_lim[1].units),
            ),
        )

        self.x_lim = self.x_lim[::-1]

        return

    def _parse_histogram(self) -> None:
        self._parse_common_histogramtype()

        self.histogram_line = AutoPlotterLine(
            line_type="histogram",
            line_data=dict(
                plot=True,
                log=self.x_log,
                number_of_bins=self.number_of_bins,
                start=dict(value=self.x_lim[0].value, units=self.x_lim[0].units),
                end=dict(value=self.x_lim[1].value, units=self.x_lim[1].units),
            ),
        )

        return

    def _parse_cumulative_histogram(self) -> None:
        self._parse_common_histogramtype()

        self.cumulative_histogram_line = AutoPlotterLine(
            line_type="cumulative_histogram",
            line_data=dict(
                plot=True,
                log=self.x_log,
                number_of_bins=self.number_of_bins,
                start=dict(value=self.x_lim[0].value, units=self.x_lim[0].units),
                end=dict(value=self.x_lim[1].value, units=self.x_lim[1].units),
            ),
        )

        return

    def _parse_data(self):
        try:
            self.plot_type = self.data["type"]
        except KeyError:
            self.plot_type = "scatter"

        if self.plot_type not in valid_plot_types:
            raise AutoPlotterError(
                f"Plot type {self.plot_type} is not valid. Please choose from {valid_plot_types}."
            )

        getattr(self, f"_parse_{self.plot_type}")()

        self._parse_observational_data()

        return

    def _parse_observational_data(self):
        self.observational_data_filenames = []

        try:
            obs_data = self.data["observational_data"]

            for data in obs_data:
                observational_data_file_path = self.observational_data_directory / Path(
                    data.get("filename", "")
                )

                if not path.exists(observational_data_file_path):
                    raise AutoPlotterError(
                        f"Unable to find file at {observational_data_file_path}."
                    )
                else:
                    self.observational_data_filenames.append(
                        observational_data_file_path
                    )

        except KeyError:
            pass

        self.observational_data_bracket_width = float(
            self.data.get("metadata", {}).get("observational_data_bracket_width", 0.1)
        )

        return

    def _add_shading_to_axes(self, ax: Axes) -> None:
        common_args = dict(zorder=-10, alpha=0.3, color="grey", linewidth=0)

        if self.x_shade[0] is not None:
            ax.axvspan(self.x_lim[0], self.x_shade[0], **common_args)

        if self.x_shade[1] is not None:
            ax.axvspan(self.x_shade[1], self.x_lim[1], **common_args)

        if self.y_shade[0] is not None:
            ax.axhspan(self.y_lim[0], self.y_shade[0], **common_args)

        if self.y_shade[1] is not None:
            ax.axhspan(self.y_shade[1], self.y_lim[1], **common_args)

        return

    def _add_lines_to_axes(self, ax: Axes, x: unyt_array, y: unyt_array) -> None:
        if self.median_line is not None:
            self.median_line.plot_line(
                ax=ax,
                x=x,
                y=y,
                label="Median",
                x_lim=self.x_lim,
                y_lim=self.y_lim,
                min_num_points_highlight=self.min_num_points_highlight,
            )
        if self.mean_line is not None:
            self.mean_line.plot_line(
                ax=ax,
                x=x,
                y=y,
                label="Mean",
                x_lim=self.x_lim,
                y_lim=self.y_lim,
                min_num_points_highlight=self.min_num_points_highlight,
            )

        return

    @staticmethod
    def _name_from_path(quantity: str) -> str:
        """
        Derive a display name from a dot-separated SOAP path, replicating the
        old velociraptor soap_catalogue behaviour of
        ``hdf5_path.replace("/", " ").replace("_", "")``.

        e.g. "exclusive_sphere_50kpc.stellar_mass" -> "ExclusiveSphere50kpc StellarMass"
        """
        return " ".join(
            "".join(word.capitalize() for word in part.split("_"))
            for part in quantity.split(".")
        )

    def get_quantity_from_soap_with_mask(self, quantity: str, soap) -> unyt_array:
        """
        Get a quantity from the SOAP catalogue using the mask.
        """

        x = reduce(getattr, quantity.split("."), soap)
        # swiftsimio auto-generated names contain "[Column"; replace those with
        # a path-derived name matching the old velociraptor soap_catalogue style.
        # Explicitly set names (derived quantities in registration.py) are kept.
        if "[Column" in x.name:
            name = self._name_from_path(quantity)
        else:
            name = x.name

        if self.structure_mask is not None:
            x_mask = logical_and(self.global_mask, self.structure_mask)
            x = x[x_mask]
            x.name = name
            return x

        self.structure_mask = ones(x.shape).astype(bool)

        if self.selection_mask is not None:
            self.structure_mask = reduce(
                getattr, self.selection_mask.split("."), soap
            ).astype(bool)

        if self.select_centrals and self.select_satellites:
            raise AutoPlotterError(
                "Cannot simultaneously select centrals and satellites"
            )
        if self.select_centrals:
            self.structure_mask = logical_and(
                self.structure_mask,
                soap.input_halos.is_central.astype(bool),
            )
        elif self.select_satellites:
            self.structure_mask = logical_and(
                self.structure_mask,
                logical_not(soap.input_halos.is_central.astype(bool)),
            )

        x_mask = logical_and(self.global_mask, self.structure_mask)
        x = x[x_mask]
        x.name = name
        return x

    def _make_plot_scatter(self, soap) -> Tuple[Figure, Axes]:
        x = self.get_quantity_from_soap_with_mask(self.x, soap)
        _convert_units(x, self.x_units)
        y = self.get_quantity_from_soap_with_mask(self.y, soap)
        _convert_units(y, self.y_units)
        # TODO: Remove (only needed for agreement with old pipeline)
        x = x.astype(np.float64)
        y = y.astype(np.float64)

        fig, ax = subplots()
        plot.scatter_x_against_y(ax=ax, x=x, y=y)
        self._add_lines_to_axes(ax=ax, x=x, y=y)

        return fig, ax

    def _make_plot_2dhistogram(self, soap) -> Tuple[Figure, Axes]:
        x = self.get_quantity_from_soap_with_mask(self.x, soap)
        _convert_units(x, self.x_units)
        y = self.get_quantity_from_soap_with_mask(self.y, soap)
        _convert_units(y, self.y_units)
        # TODO: Remove (only needed for agreement with old pipeline)
        x = x.astype(np.float64)
        y = y.astype(np.float64)

        self.x_bins.convert_to_units(self.x_units)
        self.y_bins.convert_to_units(self.y_units)

        fig, ax = plot.histogram_x_against_y(x, y, self.x_bins, self.y_bins)
        self._add_lines_to_axes(ax=ax, x=x, y=y)

        return fig, ax

    def _get_box_volume(self, soap):
        """
        Compute the comoving box volume from the SOAP metadata.
        """
        boxsize = soap.metadata.boxsize
        return boxsize[0] * boxsize[1] * boxsize[2]

    def _make_plot_massfunction(self, soap) -> Tuple[Figure, Axes]:
        x = self.get_quantity_from_soap_with_mask(self.x, soap)
        _convert_units(x, self.x_units)
        # TODO: Remove (only needed for agreement with old pipeline)
        x = x.astype(np.float64)

        mass_function_line = getattr(
            self,
            "mass_function_line",
            getattr(self, "adaptive_mass_function_line", None),
        )

        mass_function_line.create_line(
            x=x, y=None, box_volume=self._get_box_volume(soap)
        )

        self.x_bins = mass_function_line.bins

        mass_function_line.output[1].convert_to_units(self.y_units)
        mass_function_line.output[2].convert_to_units(self.y_units)

        fig, ax = plot.mass_function(
            x=x, x_bins=self.x_bins, mass_function=mass_function_line
        )

        return fig, ax

    def _make_plot_adaptivemassfunction(self, soap) -> Tuple[Figure, Axes]:
        return self._make_plot_massfunction(soap=soap)

    def _make_plot_luminosityfunction(self, soap) -> Tuple[Figure, Axes]:
        x = self.get_quantity_from_soap_with_mask(self.x, soap)
        _convert_units(x, self.x_units)
        # TODO: Remove (only needed for agreement with old pipeline)
        x = x.astype(np.float64)

        luminosity_function_line = getattr(
            self,
            "luminosity_function_line",
            getattr(self, "adaptive_luminosity_function_line", None),
        )

        luminosity_function_line.create_line(
            x=x, y=None, box_volume=self._get_box_volume(soap)
        )

        self.x_bins = luminosity_function_line.bins

        luminosity_function_line.output[1].convert_to_units(self.y_units)
        luminosity_function_line.output[2].convert_to_units(self.y_units)

        fig, ax = plot.luminosity_function(
            x=x, x_bins=self.x_bins, luminosity_function=luminosity_function_line
        )

        return fig, ax

    def _make_plot_histogram(self, soap) -> Tuple[Figure, Axes]:
        x = self.get_quantity_from_soap_with_mask(self.x, soap)
        _convert_units(x, self.x_units)
        # TODO: Remove (only needed for agreement with old pipeline)
        x = x.astype(np.float64)

        self.x_bins.convert_to_units(self.x_units)

        self.histogram_line.create_line(
            x=x, y=None, box_volume=self._get_box_volume(soap)
        )

        self.histogram_line.output[1].convert_to_units(self.y_units)

        fig, ax = plot.histogram(x=x, x_bins=self.x_bins, histogram=self.histogram_line)

        return fig, ax

    def _make_plot_cumulative_histogram(self, soap) -> Tuple[Figure, Axes]:
        self.reverse_cumsum = self.data.get("reverse_cumsum", False)

        assert (
            type(self.reverse_cumsum) == bool
        ), f"reverse_cumsum must be either true or false, not {self.reverse_cumsum}"

        x = self.get_quantity_from_soap_with_mask(self.x, soap)
        _convert_units(x, self.x_units)
        # TODO: Remove (only needed for agreement with old pipeline)
        x = x.astype(np.float64)

        self.x_bins.convert_to_units(self.x_units)

        self.cumulative_histogram_line.create_line(
            x=x,
            y=None,
            box_volume=self._get_box_volume(soap),
            reverse_cumsum=self.reverse_cumsum,
        )
        self.cumulative_histogram_line.output[1].convert_to_units(self.y_units)

        fig, ax = plot.histogram(
            x=x, x_bins=self.x_bins, histogram=self.cumulative_histogram_line
        )

        return fig, ax

    def make_plot(
        self,
        soap,
        directory: str,
        file_extension: str,
        no_plot: bool = False,
    ):
        """
        Federates out data parsing to individual functions based on the plot type.
        """

        a = float(soap.metadata.scale_factor)

        observational_data_scale_factor_bracket = [
            10 ** (log10(a) + self.observational_data_bracket_width),
            10 ** (log10(a) - self.observational_data_bracket_width),
        ]

        observational_data_redshift_bracket = [
            (1 - x) / x for x in observational_data_scale_factor_bracket
        ]

        valid_observational_data = load_observations(
            self.observational_data_filenames,
            redshift_bracket=observational_data_redshift_bracket,
        )

        with matplotlib_support:
            fig, ax = getattr(self, f"_make_plot_{self.plot_type}")(soap=soap)
            if self.x_log:
                ax.set_xscale("log")
            if self.y_log:
                ax.set_yscale("log")

            self._add_shading_to_axes(ax)

            for data in valid_observational_data:
                data.plot_on_axes(ax, errorbar_kwargs=dict(zorder=-10))

            try:
                ax.set_xlim(*self.x_lim)
                ax.set_ylim(*self.y_lim)
            except:
                pass

            plot.decorate_axes(
                ax=ax,
                z=float(soap.metadata.redshift),
                a=a,
                comment=self.comment,
                legend_loc=self.legend_loc,
                redshift_loc=self.redshift_loc,
                comment_loc=self.comment_loc,
            )

            self.x_label = ax.get_xlabel()
            self.y_label = ax.get_ylabel()

            if self.x_label_override is not None:
                self.x_label = self.x_label_override
            if self.y_label_override is not None:
                self.y_label = self.y_label_override

        if not no_plot:
            fig.savefig(f"{directory}/{self.filename}.{file_extension}")

        close(fig)

        return


class AutoPlotter(object):
    """
    Main autoplotter object; contains all of the AutoPlot objects
    and parsing code to turn the input yaml file into those.
    """

    filename: Union[str, List[str]]
    multiple_yaml_files: bool
    soap: object
    yaml: Dict[str, Union[Dict, str]]
    plots: List[AutoPlot]
    observational_data_directory: str
    correction_directory: str
    created_successfully: List[bool]
    global_mask: Union[None, array]

    def __init__(
        self,
        filename: Union[str, List[str]],
        observational_data_directory: Union[None, str] = None,
        correction_directory: Union[None, str] = None,
    ) -> None:
        self.filename = filename

        self.multiple_yaml_files = isinstance(filename, list)
        self.observational_data_directory = Path(
            observational_data_directory
            if observational_data_directory is not None
            else ""
        )
        self.correction_directory = Path(
            correction_directory if correction_directory is not None else ""
        )

        self.load_yaml()
        self.parse_yaml()

        return

    def load_yaml(self):
        if not self.multiple_yaml_files:
            with open(self.filename, "r") as handle:
                self.yaml = safe_load(handle)
        else:
            self.yaml = {}

            for filename in self.filename:
                with open(filename, "r") as handle:
                    self.yaml = {**self.yaml, **safe_load(handle)}

        return

    def parse_yaml(self):
        self.plots = [
            AutoPlot(
                filename,
                plot_data,
                self.observational_data_directory,
                self.correction_directory,
            )
            for filename, plot_data in self.yaml.items()
        ]

        return

    def link_catalogue(self, catalogue, global_mask_tag: Union[None, str]):
        """
        Links a SOAP catalogue with this object so that the plots can be created.
        The parameter is named 'catalogue' for backwards compatibility with the
        swift-pipeline entry point.
        """

        self.soap = catalogue

        if global_mask_tag is not None:
            self.global_mask = reduce(
                getattr, global_mask_tag.split("."), catalogue
            )
        else:
            self.global_mask = True
        return

    def create_plots(
        self,
        directory: str,
        file_extension: str = "pdf",
        debug: bool = False,
        no_plots: bool = False,
    ):
        self.file_extension = file_extension

        if not path.exists(directory):
            mkdir(directory)

        self.created_successfully = []

        for plot_instance in self.plots:
            try:
                plot_instance.global_mask = self.global_mask
                plot_instance.make_plot(
                    soap=self.soap,
                    directory=directory,
                    file_extension=file_extension,
                    no_plot=no_plots,
                )
                self.created_successfully.append(True)
            except (AttributeError, ValueError) as e:
                print(
                    f"Unable to create plot {plot_instance.filename} due to exception: {e}."
                )
                self.created_successfully.append(False)
                if debug:
                    import traceback

                    _, _, exc_traceback = sys.exc_info()
                    print("Traceback:", file=sys.stderr)
                    traceback.print_tb(exc_traceback, limit=10, file=sys.stderr)
            except UnitConversionError as e:
                print(
                    f"Unable to create plot {plot_instance.filename} due to an error when "
                    "trying to convert units. This likely means that you are trying "
                    "to set the output units for your plot to something not "
                    "dimensionally consistent with your catalogue. The error may "
                    "also be in your registration file, if you are using one and this "
                    "failure was on a figure using registered quantities."
                )
                self.created_successfully.append(False)
                if debug:
                    import traceback

                    _, _, exc_traceback = sys.exc_info()
                    print("Traceback:", file=sys.stderr)
                    traceback.print_tb(exc_traceback, limit=10, file=sys.stderr)
            except Exception as e:
                print(
                    f"Unable to create plot {plot_instance.filename} due to an unknown error: {e}!",
                    file=sys.stderr,
                )
                self.created_successfully.append(False)
                if debug:
                    import traceback

                    _, _, exc_traceback = sys.exc_info()
                    print("Traceback:", file=sys.stderr)
                    traceback.print_tb(exc_traceback, limit=10, file=sys.stderr)

        return
