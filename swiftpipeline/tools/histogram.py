"""
Tools for creating histograms. Uses the same API as mass_functions.
"""

import unyt
import numpy as np

from swiftpipeline.tools.labels import get_mass_function_label_no_units


def create_histogram_given_bins(
    masses: unyt.unyt_array,
    bins: unyt.unyt_array,
    box_volume: unyt.unyt_quantity,
    minimum_in_bin: int = 1,
    cumulative: bool = False,
    reverse: bool = False,
):
    bins.convert_to_units(masses.units)

    histogram = unyt.unyt_array(np.histogram(masses, bins)[0], units="dimensionless")
    valid_bins = histogram >= minimum_in_bin

    bin_centers = 0.5 * (bins[1:] + bins[:-1])

    histogram.name = "Number of Haloes"
    bin_centers.name = masses.name

    # Compute cumulative sum?
    if cumulative:
        if reverse:
            # Cumulative sum from high to low
            histogram = np.cumsum(histogram[::-1])[::-1]
        else:
            # Cumulative sum from low to high
            histogram = np.cumsum(histogram)

        # Change the Y-axis label
        histogram.name = "Cumulative Number of Haloes"

    return bin_centers[valid_bins], histogram[valid_bins], None


def create_histogram(
    masses: unyt.unyt_array,
    lowest_mass: unyt.unyt_quantity,
    highest_mass: unyt.unyt_quantity,
    box_volume: unyt.unyt_quantity,
    n_bins: int = 25,
    minimum_in_bin: int = 1,
    return_bin_edges: bool = False,
    cumulative: bool = False,
    reverse: bool = False,
):
    assert (
        masses.units == lowest_mass.units and lowest_mass.units == highest_mass.units
    ), "Please ensure that all mass quantities have the same units."

    bins = (
        np.logspace(np.log10(lowest_mass), np.log10(highest_mass), n_bins + 1)
        * masses.units
    )

    bin_centers, mass_function, _ = create_histogram_given_bins(
        masses=masses,
        bins=bins,
        box_volume=box_volume,
        minimum_in_bin=minimum_in_bin,
        cumulative=cumulative,
        reverse=reverse,
    )

    if return_bin_edges:
        return bin_centers, mass_function, None, bins
    else:
        return bin_centers, mass_function, None
