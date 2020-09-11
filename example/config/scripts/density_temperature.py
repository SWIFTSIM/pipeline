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


def setup_axes():
    """
    Creates the figure and axis object.
    """
    fig, ax = plt.subplots(1)

    ax.set_xlabel("Density [$n_H$ cm$^{-3}$]")
    ax.set_ylabel("Temperature [K]")

    ax.loglog()

    return fig, ax


def make_single_image(filename, density_bounds, temperature_bounds, bins, output_path):
    """
    Makes a single plot of rho-T
    """

    fig, ax = setup_axes()
    hist, d, T = make_hist(filename, density_bounds, temperature_bounds, bins)

    mappable = ax.pcolormesh(d, T, hist, norm=LogNorm(vmin=1))
    fig.colorbar(mappable, label="Number of particles", pad=0)

    fig.tight_layout()

    fig.savefig(f"{output_path}/density_temperature.png")

    return


if __name__ == "__main__":
    import argparse as ap

    parser = ap.ArgumentParser(description="Basic density-temperature plot.")

    parser.add_argument(
        "-s", "--snapshots", type=str, required=True, nargs="*",
    )
    parser.add_argument(
        "-c", "--catalogues", type=str, required=True, nargs="*",
    )
    parser.add_argument(
        "-d", "--input-directories", type=str, required=True, nargs="*",
    )
    parser.add_argument("-n", "--run-names", type=str, required=False, nargs="*")
    parser.add_argument("-o", "--output-directory", type=str, required=True)
    parser.add_argument("-C", "--config", type=str, required=True)

    args = parser.parse_args()

    snapshot_names = args.snapshots
    catalogue_names = args.catalogue_names
    run_directories = args.input_directories
    run_names = (
        args.run_names if args.run_names is not None else [None] * len(run_directories)
    )
    output_paths = args.output_directory
    config = args.config
    run_directory = None
    snapshot_name = None
    output_path = None

    snapshot_filename = f"{run_directory}/{snapshot_name}"

    make_single_image(
        snapshot_filename, density_bounds, temperature_bounds, bins, output_path
    )

