"""
Makes a rho-T plot. Uses the swiftsimio library.
"""

import matplotlib.pyplot as plt
import numpy as np

from swiftsimio import load

from unyt import mh, cm, Gyr
from matplotlib.colors import LogNorm
from matplotlib.animation import FuncAnimation

# Set the limits of the figure.
density_bounds = [10 ** (-9.5), 1e6]  # in nh/cm^3
temperature_bounds = [10 ** (0), 10 ** (9.5)]  # in K
bins = 256


def get_data(filename):
    """
    Grabs the data (T in Kelvin and density in mh / cm^3).
    """

    data = load(filename)

    number_density = (data.gas.densities.to_physical() / mh).to(cm ** -3)
    temperature = data.gas.temperatures.to_physical().to("K")

    return number_density.value, temperature.value


def make_hist(filename, density_bounds, temperature_bounds, bins):
    """
    Makes the histogram for filename with bounds as lower, higher
    for the bins and "bins" the number of bins along each dimension.

    Also returns the edges for pcolormesh to use.
    """

    density_bins = np.logspace(
        np.log10(density_bounds[0]), np.log10(density_bounds[1]), bins
    )
    temperature_bins = np.logspace(
        np.log10(temperature_bounds[0]), np.log10(temperature_bounds[1]), bins
    )

    H, density_edges, temperature_edges = np.histogram2d(
        *get_data(filename), bins=[density_bins, temperature_bins]
    )

    return H.T, density_edges, temperature_edges


def setup_axes(number_of_simulations: int):
    """
    Creates the figure and axis object. Creates a grid of a x b subplots
    that add up to at least number_of_simulations.
    """

    sqrt_number_of_simulations = np.sqrt(number_of_simulations)
    horizontal_number = int(np.ceil(sqrt_number_of_simulations))
    # Ensure >= number_of_simulations plots in a grid
    vertical_number = int(np.ceil(number_of_simulations / horizontal_number))

    fig, ax = plt.subplots(
        vertical_number, horizontal_number, squeeze=True, sharex=True, sharey=True,
    )

    ax = np.array([ax]) if number_of_simulations == 1 else ax

    if horizontal_number * vertical_number > number_of_simulations:
        for axis in ax.flat[number_of_simulations:]:
            axis.axis("off")

    # Set all valid on bottom row to have the horizontal axis label.
    for axis in np.atleast_2d(ax)[:][-1]:
        axis.set_xlabel("Density [$n_H$ cm$^{-3}$]")

    for axis in np.atleast_2d(ax).T[:][0]:
        axis.set_ylabel("Temperature [K]")

    ax.flat[0].loglog()

    return fig, ax


def make_single_image(
    filenames,
    names,
    number_of_simulations,
    density_bounds,
    temperature_bounds,
    bins,
    output_path,
):
    """
    Makes a single plot of rho-T
    """

    fig, ax = setup_axes(number_of_simulations=number_of_simulations)

    hists = []

    for filename in filenames:
        hist, d, T = make_hist(filename, density_bounds, temperature_bounds, bins)
        hists.append(hist)

    vmax = np.max([np.max(hist) for hist in hists])

    for hist, name, axis in zip(hists, names, ax.flat):
        mappable = axis.pcolormesh(d, T, hist, norm=LogNorm(vmin=1, vmax=vmax))
        axis.text(0.025, 0.975, name, ha="left", va="top", transform=axis.transAxes)

    fig.colorbar(mappable, ax=ax.ravel().tolist(), label="Number of particles")

    fig.savefig(f"{output_path}/density_temperature.png")

    return


if __name__ == "__main__":
    from swiftpipeline.argumentparser import ScriptArgumentParser

    arguments = ScriptArgumentParser(description="Basic density-temperature figure.")

    snapshot_filenames = [
        f"{directory}/{snapshot}"
        for directory, snapshot in zip(
            arguments.directory_list, arguments.snapshot_list
        )
    ]

    plt.style.use(arguments.stylesheet_location)

    make_single_image(
        filenames=snapshot_filenames,
        names=arguments.name_list,
        number_of_simulations=arguments.number_of_inputs,
        density_bounds=density_bounds,
        temperature_bounds=temperature_bounds,
        bins=bins,
        output_path=arguments.output_directory,
    )

