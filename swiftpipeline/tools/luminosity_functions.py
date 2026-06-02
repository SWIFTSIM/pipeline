"""
Tools for creating luminosity functions!
"""

import unyt
import numpy as np

from swiftpipeline.tools.labels import get_luminosity_function_label_no_units


def create_luminosity_function_given_bins(
    luminosities: unyt.unyt_array,
    bins: unyt.unyt_array,
    box_volume: unyt.unyt_quantity,
    minimum_in_bin: int = 3,
):
    bins.convert_to_units(luminosities.units)

    # This is required to ensure that the luminosity function converges with bin width
    bin_width = bins[1] - bins[0]
    normalization_factor = 1.0 / (bin_width * box_volume)

    luminosity_function, _ = np.histogram(luminosities, bins)
    valid_bins = luminosity_function >= minimum_in_bin

    # Poisson sampling
    error = np.sqrt(luminosity_function)

    luminosity_function *= normalization_factor
    error *= normalization_factor

    bin_centers = 0.5 * (bins[1:] + bins[:-1])

    luminosity_function.name = get_luminosity_function_label_no_units("{}")
    bin_centers.name = luminosities.name

    return bin_centers[valid_bins], luminosity_function[valid_bins], error[valid_bins]


def create_luminosity_function(
    luminosities: unyt.unyt_array,
    lowest_magnitude: unyt.unyt_quantity,
    highest_magnitude: unyt.unyt_quantity,
    box_volume: unyt.unyt_quantity,
    n_bins: int = 25,
    minimum_in_bin: int = 3,
    return_bin_edges: bool = False,
):
    assert (
        luminosities.units == lowest_magnitude.units
        and lowest_magnitude.units == highest_magnitude.units
    ), "Please ensure that all luminosity quantities have the same units."

    bins = (
        np.linspace(lowest_magnitude, highest_magnitude, n_bins + 1)
        * luminosities.units
    )

    bin_centers, luminosity_function, error = create_luminosity_function_given_bins(
        luminosities=luminosities,
        bins=bins,
        box_volume=box_volume,
        minimum_in_bin=minimum_in_bin,
    )

    if return_bin_edges:
        return bin_centers, luminosity_function, error, bins
    else:
        return bin_centers, luminosity_function, error
