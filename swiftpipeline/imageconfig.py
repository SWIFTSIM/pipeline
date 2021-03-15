"""
Configuration for imaging creator.
"""

import yaml
from unyt import unyt_quantity
from typing import List, Optional

# Items to read directly from the yaml file with their defaults
direct_read = {
    "resolution": 512,
    "figure_size": 8,
    "image_format": "jpg",
    "recalculate_stellar_smoothing_lengths": True,
    "calculate_dark_matter_smoothing_lengths": True,
    "centrals_only": True,
    "minimum_halo_mass": unyt_quantity(1e9, "Solar_Mass"),
    "use_binned_image_selection": False,
    "bin_width_in_dex": 0.5,
    "haloes_to_visualise_per_bin": 10,
    "thumbnail_image": "",
}


class Image(object):
    """
    Object describing the properties of a given image, implementing
    defaults.
    """

    # Name (key in the dictionary); will form part of the filename
    base_name: str
    # Name of the group of figures
    name: str
    # Radius out to which to visualise
    radius_raw: List[str]
    radius: unyt_quantity
    # Particle type to visualise
    particle_type: str
    # Quantity to visualise; projected_densities is a special one because
    # it does not lead to dividing out by density.
    visualise: str
    # Vmin, vmax for the color map
    vmin: Optional[unyt_quantity]
    vmax: Optional[unyt_quantity]
    # Values in the output grid below this value will be filled with it
    fill_below: Optional[unyt_quantity]
    # Output units to use on the color bar. If not present, they use the
    # ones in `vmin`, which if not present uses the ones in `vmax`. If no
    # units are present anywhere, we use the internal units.
    output_units: Optional[unyt_quantity]
    # Color of the text overlaid on the image
    text_color: str
    # Background color for the figure
    plot_background_color: str
    # Color map to use
    cmap: str
    # Produce a 'face on' version of this image?
    face_on: bool
    # Produce an 'edge on' version of this image?
    edge_on: bool
    # Produce the default projection? Always on.
    default: bool = True
    # Logarithmically normalise the image?
    log_norm: bool

    def __init__(self, base_name: str, image_dict: dict):
        """
        Extracts the dictionary to internal variables
        """

        self.base_name = base_name
        self.name = image_dict.get("name", "")
        self.radius_raw = image_dict.get("radius", None)
        self.particle_type = image_dict.get("particle_type", "gas")
        self.visualise = image_dict.get("visualise", "projected_densities")
        self.vmin, self.vmax = self._unpack_vminmax(image_dict)
        self.fill_below = self._unpack_fill_below(image_dict)
        self.output_units = self._unpack_output_units(image_dict)
        self.cmap = image_dict.get("cmap", "viridis")
        self.text_color = image_dict.get("text_color", "white")
        self.plot_background_color = image_dict.get("plot_background_color", "white")
        self.face_on = bool(image_dict.get("face_on", True))
        self.edge_on = bool(image_dict.get("edge_on", True))
        self.log_norm = bool(image_dict.get("log_norm", True))

    def _unyt_from_dict_item(self, name, image_dict):
        """
        Extracts an unyt_quantity from items.
        """

        raw_possible = image_dict.get(name, None)

        if raw_possible is not None:
            try:
                size, unit = raw_possible
            except ValueError:
                size = 1.0
                unit = raw_possible

            raw_possible = unyt_quantity(float(size), unit)

        return raw_possible

    def _unpack_vminmax(self, image_dict):
        vmin = self._unyt_from_dict_item(name="vmin", image_dict=image_dict)
        vmax = self._unyt_from_dict_item(name="vmax", image_dict=image_dict)
        return vmin, vmax

    def _unpack_fill_below(self, image_dict):
        return self._unyt_from_dict_item(name="fill_below", image_dict=image_dict)

    def _unpack_output_units(self, image_dict):
        return self._unyt_from_dict_item(name="output_units", image_dict=image_dict)

    def get_radius(
        self, stellar_half_mass: unyt_quantity, r_200_crit: unyt_quantity
    ) -> unyt_quantity:
        """
        Gets the radius from the 'raw' radius. This requires using the half
        mass and r_200_crit values from the given halo, as we use an
        adaptive scale.

        Parameters
        ----------

        stellar_half_mass: unyt_quantity
            Half-mass radius (stars) for the object.

        r_200_crit: unyt_quantity
            Radius at which the density drops to 200 times the critical
            density for this halo.

        Returns
        -------

        vis_radius: unyt_quantity
            Radius to be used for visualisation, as specified in
            the parameter file.
        """

        if self.radius_raw is None:
            raise AttributeError(f"You must specify a radius for image {name}.")

        value, units = self.radius_raw

        if units == "stellar_half_mass":
            units = stellar_half_mass

            if units == 0.0:
                # Big mistake - fall back on r_200_crit
                units = r_200_crit

        if units == "r_200_crit":
            units = r_200_crit

        return unyt_quantity(float(value), units)


class ImageConfig(object):
    """
    Configuration object containing the image config parameters.
    """

    # Raw config read directly from the file, before processing.
    raw_config: dict
    images: List[Image]

    # Set up the object.
    __slots__ = list(direct_read.keys()) + [
        "images",
        "thumbnail_image",
        "raw_config",
        "config_directory",
    ]

    def __init__(self, config_directory: str):
        """
        Set up and load the config to this object.

        Parameters
        ----------

        config_directory: str
            Directory containing the configuration ``config.yml``.
        """

        self.config_directory = config_directory

        self.__read_config()
        self.__extract_to_variables()
        self.__extract_images()

        return

    def __str__(self):
        return f"Image configuration file object describing {self.config_directory}"

    def __repr__(self):
        return self.__str__()

    def __read_config(self):
        """
        Read the ``config.yml`` and store the basic contents in
        ``self.raw_config``.
        """

        with open(f"{self.config_directory}/images.yml", "r") as handle:
            self.raw_config = yaml.safe_load(handle)

        return

    def __extract_to_variables(self):
        """
        Extracts items from the configuration dictionary to local variables.
        """

        for variable, default in direct_read.items():
            try:
                setattr(
                    self,
                    variable,
                    type(default)(self.raw_config.get(variable, default)),
                )
            except RuntimeError:
                value, unit = self.raw_config.get(variable, default)
                setattr(
                    self,
                    variable,
                    unyt_quantity(float(value), unit),
                )

        return

    def __extract_images(self):
        """
        Extracts all of the individual images and their configuration.
        """

        raw_images = self.raw_config.get("images", {})
        self.images = [
            Image(base_name=name, image_dict=image_dict)
            for name, image_dict in raw_images.items()
        ]

        return
