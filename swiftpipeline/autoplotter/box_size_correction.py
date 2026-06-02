"""
Functionality to apply a mass dependent correction to quantities that have been
binned in mass bins (e.g. a mass function).
"""

import numpy as np
import yaml
import os
import scipy.interpolate as interpol
import unyt
from typing import Tuple


class BoxSizeCorrection:
    def __init__(self, filename: str, correction_directory: str):
        correction_file = f"{correction_directory}/{filename}"
        if not os.path.exists(correction_file):
            raise FileNotFoundError(f"Could not find {correction_file}!")
        with open(correction_file, "r") as handle:
            correction_data = yaml.safe_load(handle)
        self.is_log_x = correction_data["is_log_x"]
        self.x_min, self.x_max = correction_data["x_limits"]
        x = np.array(correction_data["x"])
        y = np.array(correction_data["y"])
        self.correction_spline = interpol.InterpolatedUnivariateSpline(x, y)

    def apply_mass_function_correction(
        self,
        mass_function_output: Tuple[unyt.unyt_array, unyt.unyt_array, unyt.unyt_array],
    ) -> Tuple[unyt.unyt_array, unyt.unyt_array, unyt.unyt_array]:

        bin_centers, mass_function, error = mass_function_output

        x_vals = bin_centers
        correction = np.ones(x_vals.shape)
        if self.is_log_x:
            x_vals = np.log10(x_vals)
        x_mask = (self.x_min <= x_vals) & (x_vals <= self.x_max)
        correction[x_mask] = self.correction_spline(x_vals[x_mask])

        corrected_mass_function = mass_function * correction
        corrected_mass_function.name = mass_function.name

        return bin_centers, corrected_mass_function, error
