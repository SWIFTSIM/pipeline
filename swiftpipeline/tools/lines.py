"""
Tools to generate various lines from datasets.
"""

import unyt
import numpy as np
import sys
from typing import List


def binned_mean_line(
    x: unyt.unyt_array,
    y: unyt.unyt_array,
    x_bins: unyt.unyt_array,
    minimum_in_bin: int = 3,
    return_additional: bool = False,
    minimum_additional_points: int = 0,
):
    """
    Gets a mean (y) line, binned in the x direction.

    Parameters
    ----------

    x: unyt.unyt_array
        Horizontal values, to be binned.

    y: unyt.unyt_array
        Vertical values, to have the mean calculated in the x-bins

    x_bins: unyt.unyt_array
        Horizontal bin edges. Must have the same units as x.

    minimum_in_bin: int, optional
        Minimum number of items in a bin to return that bin. If a bin has
        fewer values than this, it is excluded from the return values.
        Default: 3.

    return_additional: bool, optional
        Boolean. If true, makes the function return x and y data points that
        lie in the bins where the number of data points is smaller than
        minimum_in_bin, and any points that are higher than the highest bin
        edge. Default: false.

    minimum_additional_points: int, optional
        Minimum number of additional data points with the highest values of x to return.
        Has to be used with return_additional=True. If set to N, then at least N
        additional data points will always be present in the plot, regardless of how the
        adaptive binning is done. The adaptive binning is stopped at the lowest value of
        x among the additional data points so that these points and the mean line do
        not overlap.


    Returns
    -------

    bin_centers: unyt.unyt_array
        The centers of the bins (taken to be the linear mean of the bin edges).

    means: unyt.unyt_array
        Vertical mean values within the bins.

    standard_deviation: unyt.unyt_array
        Standard deviation within the bins, to be shown as scatter.

    additional_x: unyt.unyt_array, optional
        x data points from the bins where the number of data points is smaller
        than minimum_in_bin

    additional_y: unyt.unyt_array, optional
        y data points from the bins where the number of data points is smaller
        than minimum_in_bin


    Notes
    -----

    The return types are such that you can pass this directly to `plt.errorbar`,
    as follows:

    .. code-block:: python

        plt.errorbar(
            *binned_mean_line(x, y, x_bins, 10)
        )

    """

    assert (
        x.units == x_bins.units
    ), "Please ensure that the x values and bins have the same units."

    means = []
    standard_deviations = []
    centers = []
    additional_x = []
    additional_y = []

    # Do we want to have at least 'minimum_additional_points' additional data points in
    # the plot?
    if return_additional and minimum_additional_points > 0:

        # Sort the data along the X axis
        idx_sort = np.argsort(x)
        x, y = x[idx_sort], y[idx_sort]

        # Ensure we don't run out of data points to plot
        num_points_to_plot = min(minimum_additional_points, len(x))

        # Collect 'num_points_to_plot' additional data points
        additional_x += list(x[-num_points_to_plot:].value)
        additional_y += list(y[-num_points_to_plot:].value)

        # Don't use the collected additional data points for the bins
        x = x[:-num_points_to_plot]
        y = y[:-num_points_to_plot]

    hist = np.digitize(x, x_bins)

    for bin in range(1, len(x_bins)):
        indices_in_this_bin = hist == bin
        number_of_items_in_bin = indices_in_this_bin.sum()

        if number_of_items_in_bin >= minimum_in_bin:
            y_values_in_this_bin = y[indices_in_this_bin].value

            means.append(np.mean(y_values_in_this_bin))
            standard_deviations.append(np.std(y_values_in_this_bin))

            # Bin center is computed as the median of the X values of the data points
            # in the bin
            centers.append(np.median(x[indices_in_this_bin].value))

        # If the number of data points in the bin is less than minimum_in_bin,
        # collect these data points if needed
        elif number_of_items_in_bin > 0 and return_additional:
            additional_x += list(x[indices_in_this_bin].value)
            additional_y += list(y[indices_in_this_bin].value)

    # Add any points that are larger:
    above_highest = hist == len(x_bins)
    additional_x += list(x[above_highest].value)
    additional_y += list(y[above_highest].value)

    # If there is nothing to plot as the mean line, add a test point to avoid having
    # empty axes labels or/and wrong axes limits
    if len(means) == 0:
        float_min = sys.float_info.min
        means, centers, standard_deviations = [float_min], [float_min], [float_min]

    means = unyt.unyt_array(means, units=y.units, name=y.name)
    standard_deviations = unyt.unyt_array(
        standard_deviations, units=y.units, name=f"{y.name} ($sigma$)"
    )
    centers = unyt.unyt_array(centers, units=x.units, name=x.name)
    additional_x = unyt.unyt_array(additional_x, units=x.units, name=x.name)
    additional_y = unyt.unyt_array(additional_y, units=y.units, name=y.name)

    if not return_additional:
        return centers, means, standard_deviations
    else:
        return centers, means, standard_deviations, additional_x, additional_y


def binned_median_line(
    x: unyt.unyt_array,
    y: unyt.unyt_array,
    x_bins: unyt.unyt_array,
    percentiles: List[int] = [16, 84],
    minimum_in_bin: int = 3,
    return_additional: bool = False,
    minimum_additional_points: int = 0,
):
    """
    Gets a median (y) line, binned in the x direction.

    Parameters
    ----------

    x: unyt.unyt_array
        Horizontal values, to be binned.

    y: unyt.unyt_array
        Vertical values, to have the median calculated in the x-bins

    x_bins: unyt.unyt_array
        Horizontal bin edges. Must have the same units as x.

    percentiles: List[int], optional
        Percentiles to return as the positive and negative errors. By
        default these are 16 and 84th percentiles.

    minimum_in_bin: int, optional
        Minimum number of items in a bin to return that bin. If a bin has
        fewer values than this, it is excluded from the return values.
        Default: 3.

    return_additional: bool, optional
        Boolean. If true, makes the function return x and y data points that
        lie in the bins where the number of data points is smaller than
        minimum_in_bin, and any points that are higher than the highest bin
        edge. Default: false.

    minimum_additional_points: int, optional
        Minimum number of additional data points with the highest values of x to return.
        Has to be used with return_additional=True. If set to N, then at least N
        additional data points will always be present in the plot, regardless of how the
        adaptive binning is done. The adaptive binning is stopped at the lowest value of
        x among the additional data points so that these points and the median line do
        not overlap.


    Returns
    -------

    bin_centers: unyt.unyt_array
        The centers of the bins (taken to be the linear mean of the bin edges).

    medians: unyt.unyt_array
        Vertical median values within the bins.

    deviations: unyt.unyt_array
        Deviation from median vertically using the ``percentiles`` defined above.
        This has shape 2xN.

    additional_x: unyt.unyt_array, optional
        x data points from the bins where the number of data points is smaller
        than minimum_in_bin

    additional_y: unyt.unyt_array, optional
        y data points from the bins where the number of data points is smaller
        than minimum_in_bin


    Notes
    -----

    The return types are such that you can pass this directly to `plt.errorbar`,
    as follows:

    .. code-block:: python

        plt.errorbar(
            *binned_median_line(x, y, x_bins, 10)
        )

    """

    assert (
        x.units == x_bins.units
    ), "Please ensure that the x values and bins have the same units."

    medians = []
    deviations = []
    centers = []
    additional_x = []
    additional_y = []

    # Do we want to have at least 'minimum_additional_points' additional data points in
    # the plot?
    if return_additional and minimum_additional_points > 0:

        # Sort the data along the X axis
        idx_sort = np.argsort(x)
        x, y = x[idx_sort], y[idx_sort]

        # Ensure we don't run out of data points to plot
        num_points_to_plot = min(minimum_additional_points, len(x))

        # Collect 'num_points_to_plot' additional data points
        additional_x += list(x[-num_points_to_plot:].value)
        additional_y += list(y[-num_points_to_plot:].value)

        # Don't use the collected additional data points for the bins
        x = x[:-num_points_to_plot]
        y = y[:-num_points_to_plot]

    hist = np.digitize(x, x_bins)

    for bin in range(1, len(x_bins)):
        indices_in_this_bin = hist == bin
        number_of_items_in_bin = indices_in_this_bin.sum()

        if number_of_items_in_bin >= minimum_in_bin:
            y_values_in_this_bin = y[indices_in_this_bin].value

            medians.append(np.median(y_values_in_this_bin))
            deviations.append(np.percentile(y_values_in_this_bin, percentiles))

            # Bin center is computed as the median of the X values of the data points
            # in the bin
            centers.append(np.median(x[indices_in_this_bin].value))

        # If the number of data points in the bin is less than minimum_in_bin,
        # collect these data points if needed
        elif number_of_items_in_bin > 0 and return_additional:
            additional_x += list(x[indices_in_this_bin].value)
            additional_y += list(y[indices_in_this_bin].value)

    # Add any points that are larger:
    above_highest = hist == len(x_bins)
    additional_x += list(x[above_highest].value)
    additional_y += list(y[above_highest].value)

    # If there is nothing to plot as the median line, add a test point to avoid having
    # empty axes labels or/and wrong axes limits
    if len(medians) == 0:
        float_min = sys.float_info.min
        medians, centers, deviations = (
            [float_min],
            [float_min],
            [[float_min, float_min]],
        )

    medians = unyt.unyt_array(medians, units=y.units, name=y.name)
    # Percentiles actually gives us the values - we want to be able to use
    # matplotlib's errorbar function
    deviations = unyt.unyt_array(
        abs(np.array(deviations).T - medians.value),
        units=y.units,
        name=f"{y.name} {percentiles} percentiles",
    )
    centers = unyt.unyt_array(centers, units=x.units, name=x.name)
    additional_x = unyt.unyt_array(additional_x, units=x.units, name=x.name)
    additional_y = unyt.unyt_array(additional_y, units=y.units, name=y.name)

    if not return_additional:
        return centers, medians, deviations
    else:
        return centers, medians, deviations, additional_x, additional_y
