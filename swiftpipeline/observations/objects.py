"""
Objects for observational data plotting.

Tools for adding in extra (e.g. observational) data to plots.

Includes an object container and helper functions for creating
and reading files.
"""

from unyt import unyt_quantity, unyt_array
from numpy import tanh, log10, logical_and
from matplotlib.pyplot import Axes
from matplotlib import rcParams

from astropy.units import Quantity
from astropy.cosmology import Cosmology
from astropy.cosmology import wCDM, FlatLambdaCDM

import h5py

from typing import Union, Optional, List

from swiftpipeline import __version__ as code_version

# Default z_orders for errorbar points and lines
line_zorder = -5
points_zorder = -6


class ObservationalDataError(Exception):
    def __init__(self, message):
        self.message = message


def save_cosmology(handle: h5py.File, cosmology: Cosmology):
    """
    Save the (astropy) cosmology to a HDF5 dataset.
    """
    group = handle.create_group("cosmology").attrs

    group.create("H0", cosmology.H0)
    group.create("Om0", cosmology.Om0)
    group.create("Ode0", cosmology.Ode0)
    group.create("Tcmb0", cosmology.Tcmb0)
    group.create("Neff", cosmology.Neff)
    group.create("m_nu", cosmology.m_nu if cosmology.m_nu is not None else 0.0)
    group.create(
        "m_nu_units", str(cosmology.m_nu.unit if cosmology.m_nu is not None else "")
    )
    group.create("Ob0", cosmology.Ob0 if cosmology.Ob0 is not None else 0.0)
    group.create("name", cosmology.name if cosmology.name is not None else "")

    try:
        group.create("w0", cosmology.w0)
    except:
        # No EoS!
        pass

    return


def load_cosmology(handle: h5py.File):
    """
    Load the (astropy) cosmology from a HDF5 dataset.
    """

    try:
        group = handle["cosmology"].attrs
    except:
        return None

    try:
        cosmology = wCDM(
            H0=group["H0"],
            Om0=group["Om0"],
            Ode0=group["Ode0"],
            w0=group["w0"],
            Tcmb0=group["Tcmb0"],
            Neff=group["Neff"],
            m_nu=Quantity(group["m_nu"], unit=group["m_nu_units"]),
            Ob0=group["Ob0"],
            name=group["name"],
        )
    except KeyError:
        # No EoS
        cosmology = FlatLambdaCDM(
            H0=group["H0"],
            Om0=group["Om0"],
            Tcmb0=group["Tcmb0"],
            Neff=group["Neff"],
            m_nu=Quantity(group["m_nu"], unit=group["m_nu_units"]),
            Ob0=group["Ob0"],
            name=group["name"],
        )

    return cosmology


class ObservationalData(object):
    """
    Observational data object. Contains routines for both writing and reading
    HDF5 files containing the observations, as well as plotting.
    """

    # Data stored in this object
    name: str
    x_units: unyt_quantity
    y_units: unyt_quantity
    x: unyt_array
    y: unyt_array
    x_scatter: Union[unyt_array, None]
    y_scatter: Union[unyt_array, None]
    lower_limits: Union[unyt_array, None]
    upper_limits: Union[unyt_array, None]
    x_comoving: bool
    y_comoving: bool
    x_description: str
    y_description: str
    filename: str
    comment: str
    citation: str
    bibcode: str
    redshift: float
    redshift_lower: float
    redshift_upper: float
    plot_as: Union[str, None] = None
    cosmology: Cosmology

    def __init__(self):
        return

    def load(self, filename: str, prefix: Optional[str] = None):
        """
        Loads the observations from file.
        """

        if prefix is not None:
            prefix = f"{prefix}_"
        else:
            prefix = ""

        self.filename = filename

        self.x = unyt_array.from_hdf5(
            filename, dataset_name=f"{prefix}values", group_name="x"
        )
        self.y = unyt_array.from_hdf5(
            filename, dataset_name=f"{prefix}values", group_name="y"
        )
        self.x_units = self.x.units
        self.y_units = self.y.units

        try:
            self.x_scatter = unyt_array.from_hdf5(
                filename, dataset_name=f"{prefix}scatter", group_name="x"
            )
        except KeyError:
            self.x_scatter = None

        try:
            self.y_scatter = unyt_array.from_hdf5(
                filename, dataset_name=f"{prefix}scatter", group_name="y"
            )
        except KeyError:
            self.y_scatter = None

        try:
            self.lower_limits = unyt_array.from_hdf5(
                filename, dataset_name=f"{prefix}lower_limits", group_name="y"
            )
        except KeyError:
            self.lower_limits = None

        try:
            self.upper_limits = unyt_array.from_hdf5(
                filename, dataset_name=f"{prefix}upper_limits", group_name="y"
            )
        except KeyError:
            self.upper_limits = None

        with h5py.File(filename, "r") as handle:
            metadata = handle[f"{prefix}metadata"].attrs

            self.comment = metadata["comment"]
            self.name = metadata["name"]
            self.citation = metadata["citation"]
            self.bibcode = metadata["bibcode"]
            self.redshift = metadata["redshift"]
            self.redshift_lower = metadata.get("redshift_lower", self.redshift)
            self.redshift_upper = metadata.get("redshift_upper", self.redshift)
            self.plot_as = metadata["plot_as"]

            self.x_comoving = bool(handle["x"].attrs[f"{prefix}comoving"])
            self.y_comoving = bool(handle["y"].attrs[f"{prefix}comoving"])
            self.y_description = str(handle["y"].attrs[f"{prefix}description"])
            self.x_description = str(handle["x"].attrs[f"{prefix}description"])

            self.cosmology = load_cosmology(handle)

        self.x.name = self.x_description
        self.y.name = self.y_description

        return

    def write(self, filename: str, prefix: Optional[str] = None):
        """
        Writes the observations to file.
        """

        if prefix is not None:
            prefix = f"{prefix}_"
        else:
            prefix = ""

        self.filename = filename

        self.x.write_hdf5(filename, dataset_name=f"{prefix}values", group_name="x")
        self.y.write_hdf5(filename, dataset_name=f"{prefix}values", group_name="y")

        if self.x_scatter is not None:
            self.x_scatter.write_hdf5(
                filename, dataset_name=f"{prefix}scatter", group_name="x"
            )

        if self.y_scatter is not None:
            self.y_scatter.write_hdf5(
                filename, dataset_name=f"{prefix}scatter", group_name="y"
            )

        if self.lower_limits is not None:
            self.lower_limits.write_hdf5(
                filename, dataset_name=f"{prefix}lower_limits", group_name="y"
            )

        if self.upper_limits is not None:
            self.upper_limits.write_hdf5(
                filename, dataset_name=f"{prefix}upper_limits", group_name="y"
            )

        with h5py.File(filename, "a") as handle:
            metadata = handle.create_group(f"{prefix}metadata").attrs

            metadata.create("comment", self.comment)
            metadata.create("name", self.name)
            metadata.create("citation", self.citation)
            metadata.create("bibcode", self.bibcode)
            metadata.create("redshift", self.redshift)
            metadata.create("redshift_lower", self.redshift_lower)
            metadata.create("redshift_upper", self.redshift_upper)
            metadata.create("plot_as", self.plot_as)

            handle["x"].attrs.create(f"{prefix}comoving", self.x_comoving)
            handle["y"].attrs.create(f"{prefix}comoving", self.y_comoving)
            handle["x"].attrs.create(f"{prefix}description", self.x_description)
            handle["y"].attrs.create(f"{prefix}description", self.y_description)

            if not prefix:
                save_cosmology(handle=handle, cosmology=self.cosmology)

        return

    def associate_x(
        self,
        array: unyt_array,
        scatter: Union[unyt_array, None],
        comoving: bool,
        description: str,
    ):
        self.x = array
        self.x_units = array.units
        self.x_comoving = comoving
        self.x_description = description

        if scatter is not None:
            self.x_scatter = scatter.to(self.x_units)
        else:
            self.x_scatter = None

        return

    def associate_y(
        self,
        array: unyt_array,
        scatter: Union[unyt_array, None],
        comoving: bool,
        description: str,
        lolims: Union[unyt_array, None] = None,
        uplims: Union[unyt_array, None] = None,
    ):
        self.y = array
        self.y_units = array.units
        self.y_comoving = comoving
        self.y_description = description

        if lolims is not None:
            self.lower_limits = lolims

            if uplims is not None:
                if sum(logical_and(lolims, uplims)):
                    raise RuntimeError(
                        "Entries of the unyt arrays representing lower and upper limits must be "
                        "of 'bool' type and cannot both be 'True' for the same data points."
                    )

        else:
            self.lower_limits = None

        if uplims is not None:
            self.upper_limits = uplims
        else:
            self.upper_limits = None

        if scatter is not None:
            self.y_scatter = scatter.to(self.y_units)
        elif lolims is not None or uplims is not None:
            self.y_scatter = self.y * 0.0
            if lolims is not None:
                self.y_scatter[self.lower_limits.value] = (
                    self.y[self.lower_limits.value] / 3.0
                )
            if uplims is not None:
                self.y_scatter[self.upper_limits.value] = (
                    self.y[self.upper_limits.value] / 3.0
                )
        else:
            self.y_scatter = None

        return

    def associate_citation(self, citation: str, bibcode: str):
        self.citation = citation
        self.bibcode = bibcode
        return

    def associate_name(self, name: str):
        self.name = name
        return

    def associate_comment(self, comment: str):
        self.comment = comment
        return

    def associate_redshift(
        self,
        redshift: float,
        redshift_lower: Optional[float] = None,
        redshift_upper: Optional[float] = None,
    ):
        self.redshift = redshift
        self.redshift_lower = redshift_lower if redshift_lower is not None else redshift
        self.redshift_upper = redshift_upper if redshift_upper is not None else redshift
        return

    def associate_plot_as(self, plot_as: str):
        if plot_as not in ["line", "points"]:
            raise Exception("Please supply plot_as as either points or line.")
        self.plot_as = plot_as
        return

    def associate_cosmology(self, cosmology: Cosmology):
        self.cosmology = cosmology
        return

    def plot_on_axes(self, axes: Axes, errorbar_kwargs: Union[dict, None] = None):
        """
        Plot this set of observational data as an errorbar().
        """

        if errorbar_kwargs is not None:
            kwargs = errorbar_kwargs
        else:
            kwargs = {}

        if self.x_scatter is not None:
            self.x_scatter.convert_to_units(self.x.units)

        if self.y_scatter is not None:
            self.y_scatter.convert_to_units(self.y.units)

        if self.plot_as == "points":
            kwargs["linestyle"] = "none"
            kwargs["marker"] = "."
            kwargs["zorder"] = points_zorder

            kwargs["markersize"] = (
                rcParams["lines.markersize"]
                * (1.5 - tanh(2.0 * log10(len(self.x)) - 4.0))
                / 2.5
            )

            kwargs["alpha"] = (3.0 - tanh(2.0 * log10(len(self.x)) - 4.0)) / 4.0

            if self.y_scatter is None:
                kwargs["markerfacecolor"] = "none"

            if len(self.x) > 1000:
                kwargs["rasterized"] = True
        elif self.plot_as == "line":
            kwargs["zorder"] = line_zorder

        data_label = f"{self.citation} ($z={self.redshift:.1f}$)"

        try:
            axes.errorbar(
                self.x,
                self.y,
                yerr=self.y_scatter,
                xerr=self.x_scatter,
                lolims=(
                    self.lower_limits.value if self.lower_limits is not None else None
                ),
                uplims=(
                    self.upper_limits.value if self.upper_limits is not None else None
                ),
                **kwargs,
                label=data_label,
            )
        except ValueError as e:
            raise ValueError(
                f"Problem while adding {data_label} data!"
                f" x: {self.x}, y: {self.y},"
                f" x_scatter: {self.x_scatter}, y_scatter: {self.y_scatter}"
            )
            raise e

        return


class MultiRedshiftObservationalData(object):
    """
    Multi-redshift version of :class:`ObservationalData` class.
    """

    datasets: List[ObservationalData]
    name: str
    x_description: str
    y_description: str
    filename: str
    comment: str
    citation: str
    bibcode: str
    cosmology: Cosmology
    code_version = code_version
    maximum_number_of_returns = 1024

    def __init__(self):
        self.datasets = []
        return

    def get_datasets_overlapping_with(
        self, redshifts: List[float] = [0.0, 1000.0]
    ) -> List[ObservationalData]:
        """
        Gets individual redshift datasets overlapping with the specified redshift range.
        """

        overlapping_datasets = []
        lower, upper = redshifts

        for dataset in self.datasets:
            if (
                (dataset.redshift_lower <= lower and lower <= dataset.redshift_upper)
                or (dataset.redshift_lower <= upper and upper <= dataset.redshift_upper)
                or (lower <= dataset.redshift_lower and dataset.redshift_upper <= upper)
            ):
                overlapping_datasets.append(dataset)

        a = lambda z: 1.0 / (1.0 + z)

        central_scale_factor = 0.5 * sum([a(z) for z in redshifts])

        overlapping_datasets = sorted(
            overlapping_datasets,
            key=lambda x: abs(central_scale_factor - a(x.redshift)),
        )[: self.maximum_number_of_returns]

        return overlapping_datasets

    def associate_dataset(self, dataset: ObservationalData):
        try:
            dataset.associate_citation(citation=self.citation, bibcode=self.bibcode)
            dataset.associate_comment(comment=self.comment)
            dataset.associate_name(name=self.name)
            dataset.associate_cosmology(cosmology=self.cosmology)
        except AttributeError:
            raise ObservationalDataError(
                "Ensure that you have associated the citation, including bibcode, "
                "comment, name, and cosmology with the multi-redshift container "
                "object before associating any individual datasets. This is required "
                "to preserve metadata integrity."
            )

        self.datasets.append(dataset)
        return

    def associate_citation(self, citation: str, bibcode: str):
        self.citation = citation
        self.bibcode = bibcode
        return

    def associate_name(self, name: str):
        self.name = name
        return

    def associate_comment(self, comment: str):
        self.comment = comment
        return

    def associate_cosmology(self, cosmology: Cosmology):
        self.cosmology = cosmology
        return

    def associate_maximum_number_of_returns(self, maximum_number_of_returns: int):
        self.maximum_number_of_returns = maximum_number_of_returns
        return

    def write(self, filename: str):
        """
        Writes all of the datasets currently present in the object to a HDF5 file.
        """

        prefixes = [f"z{dataset.redshift:07.3f}" for dataset in self.datasets]
        self.filename = filename

        for dataset, prefix in zip(self.datasets, prefixes):
            dataset.write(filename, prefix=prefix)

        with h5py.File(filename, "a") as handle:
            group = handle.create_group("multi_file_metadata")
            group.attrs.create("prefixes", prefixes)
            group.attrs.create("number_of_datasets", len(prefixes))
            group.attrs.create(
                "minimal_redshift",
                min([dataset.redshift_lower for dataset in self.datasets]),
            )
            group.attrs.create(
                "maximal_redshift",
                max([dataset.redshift_upper for dataset in self.datasets]),
            )
            group.attrs.create(
                "maximum_number_of_returns", self.maximum_number_of_returns
            )
            group.attrs.create("comment", self.comment)
            group.attrs.create("name", self.name)
            group.attrs.create("citation", self.citation)
            group.attrs.create("bibcode", self.bibcode)
            group.attrs.create("code_version", self.code_version)

            save_cosmology(handle, self.cosmology)

        return

    def load(self, filename: str):
        """
        Reads all of the datasets from an associated file to the object.
        """

        self.filename = filename

        with h5py.File(filename, "r") as handle:
            try:
                group = handle["multi_file_metadata"].attrs
            except KeyError:
                raise ObservationalDataError(
                    "This file is not a multi-redshift dataset. Try opening "
                    "it with ObservationalData instead, or use load_observations."
                )

            self.prefixes = group["prefixes"]
            self.maximum_number_of_returns = group["maximum_number_of_returns"]
            self.comment = group["comment"]
            self.name = group["name"]
            self.citation = group["citation"]
            self.bibcode = group["bibcode"]
            self.code_version = group["code_version"]

            self.cosmology = load_cosmology(handle)

        for prefix in self.prefixes:
            this_observation = ObservationalData()
            this_observation.load(filename, prefix=prefix)
            self.datasets.append(this_observation)
