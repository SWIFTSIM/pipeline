"""
Tools for creating mass functions!
"""

import unyt
import numpy as np

from swiftpipeline.tools.labels import get_mass_function_label_no_units


def create_mass_function_given_bins(
    masses: unyt.unyt_array,
    bins: unyt.unyt_array,
    box_volume: unyt.unyt_quantity,
    minimum_in_bin: int = 3,
):
    bins.convert_to_units(masses.units)

    # This is required to ensure that the mass function converges with bin width
    bin_width_in_logspace = np.log10(bins[1]) - np.log10(bins[0])
    normalization_factor = 1.0 / (bin_width_in_logspace * box_volume)

    mass_function, _ = np.histogram(masses, bins)
    valid_bins = mass_function >= minimum_in_bin

    # Poisson sampling
    error = np.sqrt(mass_function)

    mass_function *= normalization_factor
    error *= normalization_factor

    bin_centers = 0.5 * (bins[1:] + bins[:-1])

    mass_function.name = get_mass_function_label_no_units("{}")
    bin_centers.name = masses.name

    return bin_centers[valid_bins], mass_function[valid_bins], error[valid_bins]


def create_mass_function(
    masses: unyt.unyt_array,
    lowest_mass: unyt.unyt_quantity,
    highest_mass: unyt.unyt_quantity,
    box_volume: unyt.unyt_quantity,
    n_bins: int = 25,
    minimum_in_bin: int = 3,
    return_bin_edges: bool = False,
):
    assert (
        masses.units == lowest_mass.units and lowest_mass.units == highest_mass.units
    ), "Please ensure that all mass quantities have the same units."

    bins = (
        np.logspace(np.log10(lowest_mass), np.log10(highest_mass), n_bins + 1)
        * masses.units
    )

    bin_centers, mass_function, error = create_mass_function_given_bins(
        masses=masses, bins=bins, box_volume=box_volume, minimum_in_bin=minimum_in_bin
    )

    if return_bin_edges:
        return bin_centers, mass_function, error, bins
    else:
        return bin_centers, mass_function, error


def create_adaptive_mass_function(
    masses: unyt.unyt_array,
    lowest_mass: unyt.unyt_quantity,
    highest_mass: unyt.unyt_quantity,
    box_volume: unyt.unyt_quantity,
    base_n_bins: int = 25,
    minimum_in_bin: int = 3,
    return_bin_edges: bool = False,
):
    assert (
        masses.units == lowest_mass.units and lowest_mass.units == highest_mass.units
    ), "Please ensure that all mass quantities have the same units."

    # We must do this and not modify the data internally as it could be used for
    # plotting elsewhere.
    sorted_masses = np.sort(masses)

    mask = np.logical_and(sorted_masses >= lowest_mass, sorted_masses <= highest_mass)

    # Also, we bin in logspace.
    sorted_masses = np.log10(sorted_masses[mask])

    minimal_log_bin_width = (
        np.log10(highest_mass) - np.log10(lowest_mass)
    ) / base_n_bins

    number_in_bin = []
    bin_edges_left = [np.log10(lowest_mass)]
    bin_edges_right = []
    bin_medians = []

    current_edge_left = bin_edges_left[0]
    current_lower_index = 0
    current_bin_count = 0

    for index, mass in enumerate(sorted_masses):
        current_bin_count += 1

        if mass < current_edge_left + minimal_log_bin_width:
            # Nothing to do, we're just filling the bin
            continue
        elif current_bin_count > minimum_in_bin:
            # Let's just end this here
            bin_medians.append(
                np.median(sorted_masses[current_lower_index : index + 1])
            )

            # The new bin edge lives half way in between our current value and the
            # next value, if it exists.
            try:
                new_edge = 0.5 * (sorted_masses[index + 1] + mass)
            except IndexError:
                # This case is where `value` is the last item in the array.
                new_edge = mass

            bin_edges_right.append(new_edge)
            bin_edges_left.append(new_edge)
            number_in_bin.append(current_bin_count)

            # Reset for the lads
            current_edge_left = new_edge
            current_lower_index = index
            current_bin_count = 0
        else:
            # Nothing we can do! Let's just keep going and
            # hope we find more matches.
            pass

    # Clean up the last bin? We're gonna miss the largest N galaxies..
    if current_bin_count > 1:
        # We can create a novel bin!
        bin_edges_right.append(mass)
        bin_medians.append(np.median(sorted_masses[current_lower_index : index + 1]))
        number_in_bin.append(current_bin_count)
    elif current_bin_count == 1:
        # Extend the previous bin (otherwise error is consistent with zero)
        try:
            bin_edges_right[-1] = mass
            number_in_bin[-1] += 1
            bin_medians[-1] = np.median(sorted_masses[-number_in_bin[-1] :])
            # We don't need the next bin now.
            bin_edges_left = bin_edges_left[:-1]

        # There is no previous bin because we have just one bin in total
        except IndexError:
            bin_edges_right.append(mass)
            number_in_bin.append(1)
            bin_medians.append(sorted_masses[-1])
    else:
        # This bin doesn't exist anyway, boo...
        bin_edges_left = bin_edges_left[:-1]

    bin_widths = [right - left for right, left in zip(bin_edges_right, bin_edges_left)]

    mass_function = [
        n / (width * box_volume) for n, width in zip(number_in_bin, bin_widths)
    ]
    error = [
        np.sqrt(n) / (width * box_volume) for n, width in zip(number_in_bin, bin_widths)
    ]

    try:
        mass_function_units = mass_function[0].units
    except IndexError:
        mass_function_units = (1 / box_volume).units

    try:
        error_units = error[0].units
    except IndexError:
        error_units = mass_function_units

    mass_function = unyt.unyt_array(mass_function, units=mass_function_units)
    # For some reason when using a name= argument here this ends up as None?
    mass_function.name = get_mass_function_label_no_units("{}")

    error = unyt.unyt_array(error, units=error_units)

    bin_centers = unyt.unyt_array(
        [10 ** x for x in bin_medians], units=masses.units, name=masses.name
    )

    if return_bin_edges:
        return (
            bin_centers,
            mass_function,
            error,
            unyt.unyt_array(
                10 ** np.array([bin_edges_left, bin_edges_right]), units=masses.units
            ),
        )
    else:
        return bin_centers, mass_function, error
