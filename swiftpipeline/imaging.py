"""
Creates images based upon the configuration provided in
``imageconfig.py``.
"""

from swiftpipeline.imageconfig import ImageConfig, Image

import matplotlib.pyplot as plt
import numpy as np

from tqdm import tqdm
from p_tqdm import p_map

from matplotlib.colors import LogNorm, Normalize
from matplotlib.patches import Circle
from mpl_toolkits.axes_grid1 import make_axes_locatable

from unyt import unyt_quantity, unyt_array

from swiftsimio.visualisation.projection import project_pixel_grid
from swiftsimio.visualisation.slice import kernel_gamma
from swiftsimio.visualisation.smoothing_length_generation import (
    generate_smoothing_lengths,
)
from swiftsimio.visualisation.rotation import rotation_matrix_from_vector

from swiftsimio import load, mask, SWIFTDataset
from velociraptor import load as load_catalogue
from swiftpipeline.html import ImageWebpageCreator

from pathlib import Path
from enum import Enum, auto

from typing import Optional, List


def latex_float(f):
    units = f"${f.units.latex_repr}$"

    if f < 1e3 and f > 1e-1:
        return f"${f.value:.3g}$ {units}"

    float_str = "${0:.2g}".format(f.value)
    if "e" in float_str:
        base, exponent = float_str.split("e")
        return r"{0} \times 10^{{{1}}}$ {2}".format(base, int(exponent), units)
    else:
        return float_str + f"$ {units}"


class Projection(Enum):
    DEFAULT = auto()
    FACE_ON = auto()
    EDGE_ON = auto()


class Halo(object):
    """
    Stores some helpful properties of an individual halo.
    """

    mass_200_crit: unyt_quantity
    radius_200_crit: unyt_quantity
    mass_100_kpc_star: unyt_quantity
    radius_100_kpc_star: unyt_quantity
    unique_id: int
    position: unyt_array
    L: unyt_array

    def __init__(
        self,
        mass_200_crit: unyt_quantity,
        radius_200_crit: unyt_quantity,
        mass_100_kpc_star: unyt_quantity,
        radius_100_kpc_star: unyt_quantity,
        unique_id: int,
        position: unyt_array,
        L: unyt_array,
    ):

        self.mass_200_crit = mass_200_crit
        self.radius_200_crit = radius_200_crit
        self.mass_100_kpc_star = mass_100_kpc_star
        self.radius_100_kpc_star = radius_100_kpc_star
        self.unique_id = unique_id
        self.position = unyt_array(position, position[0].units)
        self.L = unyt_array(L, L[0].units)

        return


def haloes_to_visualise(config: ImageConfig, catalogue_path: Path) -> List[Halo]:
    """
    Returns the haloes to visualise from the catalogue.

    Parameters
    ----------

    config: ImageConfig
        Complete image configuration object, containing importantly
        the ``raw_images`` list.

    catalogue_path: Path, str
        Path to the catalogue (``/path/to/halo_0000.properties``).

    Returns
    -------

    haloes: List[Halo]
        Haloes to visualise, with their properties filled out.
    """

    catalogue = load_catalogue(catalogue_path)

    mass_200crit = catalogue.masses.mass_200crit
    a = catalogue.a

    mask = mass_200crit > config.minimum_halo_mass

    if config.centrals_only:
        mask = np.logical_and(mask, catalogue.structure_type.structuretype == 10)

    # Generate some randomness
    rng = np.random.default_rng()

    if config.use_binned_image_selection:
        # Generate a further mask
        max_halo_mass = np.max(mass_200crit).to(config.minimum_halo_mass.units)

        bins = np.arange(
            np.log10(config.minimum_halo_mass),
            np.log10(max_halo_mass) + config.bin_width_in_dex,
            config.bin_width_in_dex,
        )

        digitized = np.digitize(
            x=np.log10(mass_200crit[mask].to(config.minimum_halo_mass.units)), bins=bins
        )

        # Now we ensure that there are at most haloes_to_visualise_per_bin
        # in each of the digitized bins. Haloes are valid in bin 1 and above,
        # we cannot use bin 0 as this is haloes below our minimum mass (which
        # should not be present, see the mask above).

        mass_mask = np.zeros(len(digitized), dtype=bool)

        # This loop can definitely be optimised.
        for bin_id in range(1, len(bins) + 1):
            matches = digitized == bin_id
            number_of_matches = matches.sum()

            # If there's too many, we must sub-sample randomly.
            if number_of_matches > config.haloes_to_visualise_per_bin:
                choices = rng.choice(
                    number_of_matches,
                    size=config.haloes_to_visualise_per_bin,
                    replace=False,
                )

                mass_mask[np.where(matches)[0][choices]] = True

            else:
                mass_mask[matches] = True

        # Modify our original mask with our new changes
        mask[mask] = mass_mask

    # Now build the list of halo objects from valid objects, starting
    # with the most massive.

    haloes = []
    halo_id_order = np.argsort(mass_200crit[mask])[::-1]
    halo_ids_valid = np.arange(len(mass_200crit))[mask][halo_id_order]

    for unique_id in halo_ids_valid:
        haloes.append(
            Halo(
                mass_200_crit=catalogue.masses.mass_200crit[unique_id],
                radius_200_crit=catalogue.radii.r_200crit[unique_id] / a,
                mass_100_kpc_star=catalogue.apertures.mass_star_100_kpc[unique_id],
                radius_100_kpc_star=catalogue.apertures.rhalfmass_star_100_kpc[
                    unique_id
                ]
                / a,
                unique_id=unique_id,
                position=[
                    getattr(catalogue.positions, f"{c}cmbp")[unique_id] / a
                    for c in "xyz"
                ],
                L=[
                    getattr(catalogue.angular_momentum, f"l{c}_star")[unique_id]
                    for c in "xyz"
                ],
            )
        )

    return haloes


def create_scatter(
    snapshot: SWIFTDataset,
    halo: Halo,
    image: Image,
    projection: Projection,
    resolution: int,
) -> unyt_array:
    """
    Creates a projected image for a given image class, and snapshot.

    Parameters
    ----------

    snapshot: SWIFTDataset,
        The opened dataset.

    halo: Halo
        Halo with properties to visualise

    image: Image
        Image class to visualise this time around

    projection: Projection
        Which projection to make

    resolution: int
        Image size along each axis.

    Returns
    -------

    grid: unyt.unyt_array
        Output grid, in the requested units.
    """

    region_given_r = lambda r: [
        halo.position[0] - r,
        halo.position[0] + r,
        halo.position[1] - r,
        halo.position[1] + r,
        halo.position[2] - r,
        halo.position[2] + r,
    ]

    radius = image.get_radius(
        stellar_half_mass=halo.radius_100_kpc_star, r_200_crit=halo.radius_200_crit
    )

    particle_data = getattr(snapshot, image.particle_type, "gas")

    region = region_given_r(radius)

    rotation_center = None
    rotation_matrix = None

    # If the L vector is poorly constrained this will complain,
    # but we don't really care.
    with np.testing.suppress_warnings() as sup:
        sup.filter(RuntimeWarning)
        if projection == Projection.EDGE_ON:
            rotation_center = halo.position.to(particle_data.coordinates.units)
            rotation_matrix = rotation_matrix_from_vector(halo.L.v, "y")
        elif projection == Projection.FACE_ON:
            rotation_center = halo.position.to(particle_data.coordinates.units)
            rotation_matrix = rotation_matrix_from_vector(halo.L.v, "z")

    if hasattr(particle_data, "smoothing_lengths"):
        backend = "fast"
    else:
        backend = "histogram"

    common_attributes = dict(
        data=particle_data,
        boxsize=snapshot.metadata.boxsize,
        resolution=resolution,
        region=region,
        mask=None,
        rotation_matrix=rotation_matrix,
        rotation_center=rotation_center,
        parallel=False,
        backend=backend,
    )

    mass_image = project_pixel_grid(project="masses", **common_attributes)

    if image.visualise == "projected_densities":
        # We're done!
        x_range = region[1] - region[0]
        y_range = region[3] - region[2]
        units = 1.0 / (x_range * y_range)
        units.convert_to_units(1.0 / (x_range.units * y_range.units))
        units *= particle_data.masses.units

        grid = unyt_array(mass_image, units=units)
    else:
        # Need to make the complementary image.
        cache_name = f"_CACHE_MASSWEIGHTED_{image.visualise}"
        cache = getattr(particle_data, cache_name, None)
        particle_array = getattr(particle_data, image.visualise)

        if cache is None:
            cache = particle_array * particle_data.masses

            setattr(
                particle_data,
                cache_name,
                cache,
            )

        weighted_image = project_pixel_grid(project=cache_name, **common_attributes)

        # Deal with zeroes:
        mass_image[mass_image == 0.0] = 1.0

        # K * 1e10 Msun -> K * Msun for the 'units' internally. So we need
        # to reconstruct the true ratio, although this should be ideally the
        # same as particle_array.units.
        units = cache.units / particle_data.masses.units

        grid = unyt_array(weighted_image / mass_image, units=units)

    # Fill if required
    output_units = None
    unit_steal = [image.output_units, image.vmin, image.vmax, grid]

    while output_units is None:
        potential_unit = unit_steal.pop(0)
        if potential_unit is not None:
            output_units = potential_unit.units

    grid.convert_to_units(output_units)

    if image.fill_below is not None:
        mask = grid < image.fill_below.to(output_units)
        grid[mask] = image.fill_below.to(output_units)

    return grid


def save_figure_from_scatter(
    scatter: unyt_array,
    config: ImageConfig,
    halo: Halo,
    image: Image,
    projection: Projection,
    output_path: Path,
):
    """

    Produces the figure associated with a given scatter.

    Parameters
    ----------

    scatter: unyt_array,
        Array of the scattered image.

    config: ImageConfig
        The global image configuration.

    halo: Halo
        Halo with properties to visualise

    image: Image
        Image class to visualise this time around

    projection: Projection
        Which projection to make

    output_path: Path
        Path to save the figure at
    """

    output_filename = (
        output_path
        / f"{image.base_name}_{projection.name.lower()}.{config.image_format}"
    )

    fig, ax = plt.subplots(
        figsize=[config.figure_size] * 2,
        dpi=config.resolution // config.figure_size,
        constrained_layout=False,
        tight_layout=False,
    )

    fig.subplots_adjust(0, 0, 1, 1, 0, 0)
    ax.axis("off")

    vmin = image.vmin.to(scatter.units) if image.vmin is not None else None
    vmax = image.vmax.to(scatter.units) if image.vmax is not None else None

    if image.log_norm:
        norm = LogNorm(vmin=vmin, vmax=vmax, clip=True)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax, clip=True)

    radius = image.get_radius(
        stellar_half_mass=halo.radius_100_kpc_star, r_200_crit=halo.radius_200_crit
    )

    extent_given_r = lambda r: [
        halo.position[0] - r,
        halo.position[0] + r,
        halo.position[1] - r,
        halo.position[1] + r,
    ]

    extent = extent_given_r(radius)

    imshow = ax.imshow(
        scatter.v.T,
        origin="lower",
        norm=norm,
        cmap=image.cmap,
        extent=extent,
    )

    color_bar_ax = fig.add_axes([0.05, 0.95, 0.9, 0.03])

    color_bar = fig.colorbar(
        mappable=imshow,
        ax=ax,
        cax=color_bar_ax,
        orientation="horizontal",
    )

    color_bar_label = image.visualise.title().replace("_", " ")
    color_bar_label = f"{color_bar_label} $\\left[{scatter.units.latex_repr}\\right]$"

    color_bar.set_label(color_bar_label, color=image.text_color)
    color_bar.ax.xaxis.set_tick_params(color=image.text_color)
    color_bar.outline.set_edgecolor(image.text_color)
    plt.setp(plt.getp(color_bar.ax.axes, "xticklabels"), color=image.text_color)

    if image.log_norm:
        color_bar.minorticks_off()

    # Decorate the plot with some additional information

    two_thirds_circle = Circle(
        halo.position[:2],
        radius=(radius * (2.0 / 3.0)).to(halo.position.units).v,
        color=image.text_color,
        linestyle="dashed",
        fill=False,
    )

    ax.add_artist(two_thirds_circle)

    x = halo.position[0]
    y = halo.position[1] - (2.05 / 3.0) * radius
    two_thirds_label = f"{(radius * (2.0 / 3.0)).to('kpc'):3.1f}"

    ax.text(x, y, two_thirds_label, ha="center", va="top", color=image.text_color)

    ax.text(
        0.025,
        0.025,
        (f"Halo {halo.unique_id}\n{projection.name.title().replace('_', ' ')}"),
        ha="left",
        va="bottom",
        transform=ax.transAxes,
        color=image.text_color,
    )

    ax.text(
        0.975,
        0.025,
        (
            f"$M_{{\\rm 200, crit}}$={latex_float(halo.mass_200_crit.to('Solar_Mass'))}\n"
            f"$M_{{*, 100}}$={latex_float(halo.mass_100_kpc_star.to('Solar_Mass'))}"
        ),
        color=image.text_color,
        ha="right",
        va="bottom",
        transform=ax.transAxes,
    )

    fig.savefig(output_filename)

    plt.close(fig)

    return


def save_thumbnail_from_scatter(
    scatter: unyt_array,
    config: ImageConfig,
    halo: Halo,
    image: Image,
    projection: Projection,
    output_path: Path,
):
    """

    Produces the thumbnail image associated with a given scatter.
    Will save at thumbnail.{image type}.

    Parameters
    ----------

    scatter: unyt_array,
        Array of the scattered image.

    config: ImageConfig
        The global image configuration.

    halo: Halo
        Halo with properties to visualise

    image: Image
        Image class to visualise this time around

    projection: Projection
        Which projection to make

    output_path: Path
        Path to save the figure at
    """

    output_filename = output_path / f"thumbnail.{config.image_format}"

    fig, ax = plt.subplots(
        figsize=[1] * 2, dpi=128, constrained_layout=False, tight_layout=False
    )

    fig.subplots_adjust(0, 0, 1, 1, 0, 0)
    ax.axis("off")

    vmin = image.vmin.to(scatter.units) if image.vmin is not None else None
    vmax = image.vmax.to(scatter.units) if image.vmax is not None else None

    if image.log_norm:
        norm = LogNorm(vmin=vmin, vmax=vmax, clip=True)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax, clip=True)

    radius = image.get_radius(
        stellar_half_mass=halo.radius_100_kpc_star, r_200_crit=halo.radius_200_crit
    )

    extent_given_r = lambda r: [
        halo.position[0] - r,
        halo.position[0] + r,
        halo.position[1] - r,
        halo.position[1] + r,
    ]

    extent = extent_given_r(radius)

    ax.imshow(
        scatter.v.T,
        origin="lower",
        norm=norm,
        cmap=image.cmap,
        extent=extent,
    )

    fig.savefig(output_filename)

    plt.close(fig)

    return


def visualise_halo(
    output_path: Path,
    snapshot_path: Path,
    config: ImageConfig,
    halo: Halo,
):
    """
    Creates all of the visualisations in the config for the
    specified halo, and saves them to disk.

    Parameters
    ----------

    output_path: Path, str
        Output path to save images to. Inside this path, there will be
        a number of directories created (one per halo). This path must
        already exist.

    snapshot_path: Path,
        Path to the snapshot. For a sufficiently large volume, and
        a sufficiently small number of haloes, there will be little-to
        -no overlap in the read regions.

    config: ImageConfig
        Opened configuration file.

    halo: Halo
        The halo to read the data for and visualise.
    """

    # First need to find the maximum radius, amongst any
    # of the images.
    radii = [
        image.get_radius(
            stellar_half_mass=halo.radius_100_kpc_star, r_200_crit=halo.radius_200_crit
        )
        for image in config.images
    ]

    max_radius = max(radii)

    extent_given_r = lambda r: [
        [halo.position[x] - r, halo.position[x] + r] for x in range(3)
    ]

    halo_mask = mask(filename=snapshot_path, spatial_only=True)
    halo_mask.constrain_spatial(restrict=extent_given_r(max_radius))

    data = load(filename=snapshot_path, mask=halo_mask)

    # Generate the smoothing lengths if required.
    if config.calculate_dark_matter_smoothing_lengths:
        data.dark_matter.smoothing_lengths = generate_smoothing_lengths(
            coordinates=data.dark_matter.coordinates,
            boxsize=data.metadata.boxsize,
            kernel_gamma=kernel_gamma,
        )

    if config.recalculate_stellar_smoothing_lengths and hasattr(data, "stars"):
        if len(data.stars.coordinates) > 0:
            data.stars.smoothing_lengths = generate_smoothing_lengths(
                coordinates=data.stars.coordinates,
                boxsize=data.metadata.boxsize,
                kernel_gamma=kernel_gamma,
            )

    halo_directory = output_path / f"halo_{halo.unique_id}"
    halo_directory.mkdir(exist_ok=True)

    for image in config.images:
        # Which projections should we make?
        projections = [Projection.DEFAULT]

        if image.face_on:
            projections.append(Projection.FACE_ON)

        if image.edge_on:
            projections.append(Projection.EDGE_ON)

        for projection in projections:
            scatter = create_scatter(
                snapshot=data,
                halo=halo,
                image=image,
                projection=projection,
                resolution=config.resolution,
            )

            save_figure_from_scatter(
                scatter=scatter,
                config=config,
                halo=halo,
                image=image,
                projection=projection,
                output_path=halo_directory,
            )

            if (
                projection == Projection.DEFAULT
                and image.base_name == config.thumbnail_image
            ):
                save_thumbnail_from_scatter(
                    scatter=scatter,
                    config=config,
                    halo=halo,
                    image=image,
                    projection=projection,
                    output_path=halo_directory,
                )


def build_webpage(config: ImageConfig, haloes: List[Halo], output_path: Path):
    """
    Builds and aves the webpages.
    """
    creator = ImageWebpageCreator(
        haloes=haloes,
        config=config,
    )

    creator.save_html(output_path=output_path)

    return


def create_all_images(
    config: ImageConfig,
    output_path: Path,
    snapshot_path: Path,
    catalogue_path: Path,
    parallel: bool = False,
    debug: bool = False,
):
    """
    Create all images, given a config and a set of snapshots
    and catalogues.

    Parameters
    ----------

    config: ImageConfig
        Complete image configuration object, containing importantly
        the ``raw_images`` list.

    output_path: Path, str
        Output path to save images to. Inside this path, there will be
        a number of directories created (one per halo). This path must
        already exist.

    snapshot_path: Path, str
        Path to the snapshot (``/path/to/output_0000.hdf5``).

    catalogue_path: Path, str
        Path to the catalogue (``/path/to/halo_0000.properties``).

    parallel: bool, optional
        Whether or not to create all images in parallel with each other
        (uses p_tqdm).

    debug: bool, optional
        Whether or not to print out the progress of the image creation
    """

    haloes = haloes_to_visualise(config=config, catalogue_path=catalogue_path)

    def packed_vis(halo):
        visualise_halo(
            output_path=output_path,
            snapshot_path=snapshot_path,
            config=config,
            halo=halo,
        )

    if parallel:
        p_map(packed_vis, haloes, disable=not debug)
    else:
        list(map(packed_vis, tqdm(haloes, disable=not debug)))

    build_webpage(config=config, haloes=haloes, output_path=output_path)

    pass