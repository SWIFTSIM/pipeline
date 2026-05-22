"""
Sub-module for adding observational data to plots.

Includes the ObservationalData object and helper functions
to convert data to this new format.
"""

from swiftpipeline.observations.objects import (
    ObservationalData,
    MultiRedshiftObservationalData,
    ObservationalDataError,
)

from typing import Union, List, Iterable
from warnings import warn


def load_observation(filename: str):
    """
    Load an observation from file filename. This should be in the
    standard observational data format.

    Deprecated in favour of :func:`load_observations`
    """

    warn(
        "load_observation is deprecated. Please use load_observations.",
        DeprecationWarning,
    )

    data = ObservationalData()
    data.load(filename)

    return data


def load_observations(
    filenames: Union[str, Iterable[str]], redshift_bracket: List[float] = [0.0, 1000.0]
):
    """
    Load observations from file(s), returning those overlapping with the
    specified redshift bracket.
    """

    returned_data = []

    if not isinstance(filenames, list):
        filenames = [filenames]

    for filename in filenames:
        try:
            multi_z = MultiRedshiftObservationalData()
            multi_z.load(filename)

            returned_data += multi_z.get_datasets_overlapping_with(
                redshifts=redshift_bracket
            )
        except ObservationalDataError:
            data = ObservationalData()
            data.load(filename)

            lower, upper = redshift_bracket

            if (
                (data.redshift_lower <= lower and lower <= data.redshift_upper)
                or (data.redshift_lower <= upper and upper <= data.redshift_upper)
                or (lower <= data.redshift_lower and data.redshift_upper <= upper)
            ):
                returned_data.append(data)

    return returned_data
