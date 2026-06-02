"""
Tools for creating adaptive bins based on an input array.
"""

import numpy as np
import unyt

adaptive_bin_cache = {}


def adaptive_bin_hash(
    values,
    lowest_value,
    highest_value,
    base_n_bins,
    minimum_in_bin,
    logarithmic,
    stretch_final_bin,
):
    """
    Hash for adaptive binning. Note that this can raise AttributeError
    in the case where the array is unhashable.
    """

    this_hash = (
        f"{values.size}{values.name}{lowest_value}{highest_value}"
        f"{base_n_bins}{minimum_in_bin}{logarithmic}{stretch_final_bin}"
    )

    return this_hash


def create_adaptive_bins(
    values: unyt.unyt_array,
    lowest_value: unyt.unyt_quantity,
    highest_value: unyt.unyt_quantity,
    base_n_bins: int = 25,
    minimum_in_bin: int = 3,
    logarithmic: bool = True,
    stretch_final_bin: bool = False,
):
    """
    Creates a set of adaptive bins based on the input values.

    Parameters
    ----------

    values: unyt.unyt_array
        The array that you want to create a mass function of (usually this is
        for example halo masses or stellar masses).

    lowest_value: unyt.unyt_quantity
        the lowest value edge of the bins

    highest_value: unyt.unyt_quantity
        the highest value edge of the bins

    base_n_bins: unyt.unyt_array, optional
        The number of equal width bins across the range to use in the case
        where no adaptive sampling is required. This returns the minimal allowed
        bin width. Default: 25.

    minimum_in_bin: int, optional
        The number of objects in a bin for it to be classed as valid. Bins
        with a number of objects smaller than this are not returned. Bins are
        stretched so that they have at least this many items in them.
        Default: 3.

    logarithmic: bool, optional
        Whether or not to use logarithmically spaced bins. Default: True.

    stretch_final_bin: bool, optional
        Stretch the final bin to include all values. If ``False``, some values
        may fall outside of all of the bins.

    Returns
    -------

    bin_centers: unyt.unyt_array
        The centers of the bins (taken to be the median of the items in the bin).

    bin_edges: unyt.unyt_array, optional
        Bin edges that were used in the binning process.

    Notes
    -----

    Caches the output as this procedure can be very expensive, and will be
    repeated several times.

    """

    # First we check in the cache to see if we have already performed
    # the binning procedure.
    try:
        this_hash = adaptive_bin_hash(
            values=values,
            lowest_value=lowest_value,
            highest_value=highest_value,
            base_n_bins=base_n_bins,
            minimum_in_bin=minimum_in_bin,
            logarithmic=logarithmic,
            stretch_final_bin=stretch_final_bin,
        )
    except AttributeError:
        this_hash = False

    if this_hash:
        try:
            return adaptive_bin_cache[this_hash]
        except:
            # Not created yet!
            pass

    assert (
        values.units == lowest_value.units and lowest_value.units == highest_value.units
    ), "Please ensure that all value quantities have the same units."

    # We must do this and not modify the data internally as it could be used for
    # plotting elsewhere.
    sorted_values = np.sort(values)

    mask = np.logical_and(sorted_values >= lowest_value, sorted_values <= highest_value)

    if logarithmic:
        sorted_values = np.log10(sorted_values[mask].value)

        minimal_bin_width = (
            np.log10(highest_value.value) - np.log10(lowest_value.value)
        ) / base_n_bins
    else:
        minimal_bin_width = ((highest_value - lowest_value) / base_n_bins).value
        sorted_values = sorted_values.value

    number_in_bin = []
    bin_edges_left = [
        np.log10(lowest_value.value) if logarithmic else lowest_value.value
    ]
    bin_edges_right = []
    bin_medians = []

    current_edge_left = bin_edges_left[0]
    current_lower_index = 0
    current_bin_count = 0

    for index, value in enumerate(sorted_values):
        current_bin_count += 1

        if value < current_edge_left + minimal_bin_width:
            # Nothing to do, we're just filling the bin
            continue
        elif current_bin_count > minimum_in_bin:
            # Let's just end this here
            bin_medians.append(
                np.median(sorted_values[current_lower_index : index + 1])
            )

            # The new bin edge lives half way in between our current value and the
            # next value, if it exists.
            try:
                new_edge = 0.5 * (sorted_values[index + 1] + value)
            except IndexError:
                # This case is where `value` is the last item in the array.
                new_edge = value

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

    if stretch_final_bin:
        # Clean up any left-overs.
        if current_bin_count > 1:
            # We can create a novel bin!
            bin_edges_right.append(value)
            bin_medians.append(
                np.median(sorted_values[current_lower_index : index + 1])
            )
            number_in_bin.append(current_bin_count)
        elif current_bin_count == 1:
            # Extend the previous bin (otherwise error is consistent with zero)
            try:
                bin_edges_right[-1] = value
                number_in_bin[-1] += 1
                bin_medians[-1] = np.median(sorted_values[-number_in_bin[-1] :])
                # We don't need the next bin now.
                bin_edges_left = bin_edges_left[:-1]

            # There is no previous bin because we have just one bin in total
            except IndexError:
                bin_edges_right.append(value)
                number_in_bin.append(1)
                bin_medians.append(sorted_values[-1])
        else:
            # This bin doesn't exist anyway, boo...
            bin_edges_left = bin_edges_left[:-1]
    else:
        bin_edges_left = bin_edges_left[:-1]

    try:
        if logarithmic:
            bin_centers = unyt.unyt_array(
                [10 ** x for x in bin_medians], units=values.units, name=values.name
            )

            bin_edges = unyt.unyt_array(
                10 ** np.array([*bin_edges_left, bin_edges_right[-1]]),
                units=values.units,
                name=values.name,
            )
        else:
            bin_centers = unyt.unyt_array(
                bin_medians, units=values.units, name=values.name
            )

            bin_edges = unyt.unyt_array(
                np.array([*bin_edges_left, bin_edges_right[-1]]),
                units=values.units,
                name=values.name,
            )
    except IndexError:
        # We weren't able to generate _any_ bins! In this case, it's probably
        # safest to just return a set of bins that are non-dynamic.
        if logarithmic:
            edges = np.logspace(
                np.log10(lowest_value.value), np.log10(highest_value.value), base_n_bins
            )
        else:
            edges = np.linspace(lowest_value.value, highest_value.value, base_n_bins)

        centers = 0.5 * (edges[:-1] + edges[1:])

        bin_centers = unyt.unyt_array(centers, units=values.units, name=values.name)
        bin_edges = unyt.unyt_array(edges, units=values.units, name=values.name)

    if this_hash:
        adaptive_bin_cache[this_hash] = (bin_centers, bin_edges)

    return bin_centers, bin_edges
