"""
Functions for registering derived quantities on a SOAP catalogue.
"""

import numpy as np
import unyt


def register_derived_quantities(soap, registration_file_paths):
    """
    Execute registration files to add derived quantities to the SOAP catalogue.

    Each registration file is executed with ``soap``, ``np``, and ``unyt``
    in scope. The file should assign new cosmo_array attributes to SOAP
    sub-objects (e.g. soap.exclusive_sphere_30kpc.is_active = ...).

    Parameters
    ----------
    soap:
        A swiftsimio SOAP dataset as returned by swiftsimio.load().

    registration_file_paths: list of str
        Paths to registration Python files to execute.
    """

    for file_path in registration_file_paths:
        with open(file_path, "r") as handle:
            exec(handle.read(), {"soap": soap, "np": np, "unyt": unyt})
