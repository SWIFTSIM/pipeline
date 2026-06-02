"""
Contains a class for collecting and writing metadata about autoplotter plots.
"""

from swiftpipeline.autoplotter.objects import (
    AutoPlot,
    AutoPlotter,
    valid_line_types,
    valid_plot_types,
)

from swiftpipeline.autoplotter.lines import AutoPlotterLine

from typing import List, Dict

import yaml


class LineMetadata(object):
    """
    Individual metadata for a given autoplotter line.
    """

    def __init__(self, line: AutoPlotterLine):
        self.line = line
        self._parse_line()
        return

    def _parse_line(self):
        (
            self.centers,
            self.values,
            self.scatter,
            self.additional_x,
            self.additional_y,
        ) = self.line.output
        self.line_type = self.line.line_type
        return

    def to_dict(self):
        output = dict(
            centers=self.centers.value.tolist(),
            centers_units=str(self.centers.units),
            values=self.values.value.tolist(),
            values_units=str(self.values.units),
            line_type=self.line_type,
            additional_points_x=self.additional_x.value.tolist(),
            additional_points_x_units=str(self.additional_x.units),
            additional_points_y=self.additional_y.value.tolist(),
            additional_points_y_units=str(self.additional_y.units),
            bins_x=(
                self.line.bins.value.tolist() if self.line.bins is not None else None
            ),
            bins_x_units=str(
                self.line.bins.units if self.line.bins is not None else None
            ),
        )

        try:
            output["scatter"] = self.scatter.value.tolist()
            output["scatter_units"] = str(self.scatter.units)
        except (TypeError, AttributeError):
            output["scatter"] = [0.0] * len(self.centers)
            output["scatter_units"] = "dimensionless"

        return output


class PlotMetadata(object):
    """
    Individual metadata for a given autoplotter plot.
    """

    plot: AutoPlot
    metadata: Dict[str, str]
    write_lines: bool
    lines: List[LineMetadata]
    title: str
    section: str
    caption: str
    show_on_webpage: bool

    def __init__(self, plot: AutoPlot):
        self.plot = plot
        self._parse_metadata()
        return

    def _parse_metadata_section_from_file(self):
        self.title = self.metadata.get("title", "")
        self.caption = self.metadata.get("caption", "")
        self.section = self.metadata.get("section", "")
        self.show_on_webpage = self.metadata.get("show_on_webpage", True)
        self.filename = self.plot.filename
        return

    def _parse_line_write(self):
        self.write_lines = bool(self.metadata.get("write_lines", True))
        return

    def _parse_metadata(self):
        self.metadata = self.plot.data.get("metadata", {})

        self._parse_metadata_section_from_file()
        self._parse_line_write()
        self._parse_lines()
        self._parse_labels()
        return

    def _parse_lines(self):
        self.lines = []

        for line_type in valid_line_types:
            try:
                line = getattr(self.plot, f"{line_type}_line")
            except AttributeError:
                continue

            if line:
                self.lines.append(LineMetadata(line=line))
        return

    def _parse_labels(self):
        self.x_quantity = self.plot.x
        self.y_quantity = self.plot.y

        self.x_label = self.plot.x_label
        self.y_label = self.plot.y_label
        return

    def to_dict(self):
        output = dict(
            title=self.title,
            section=self.section,
            caption=self.caption,
            show_on_webpage=self.show_on_webpage,
            filename=self.filename,
            x_quantity=self.x_quantity,
            y_quantity=self.y_quantity,
            x_label=self.x_label,
            y_label=self.y_label,
        )

        if self.write_lines:
            output["lines"] = {line.line_type: line.to_dict() for line in self.lines}

        return output


class AutoPlotterMetadata(object):
    """
    Contains metadata about the autoplotter, and in particular
    about the plots - for instance the values actually retrieved
    from the lines.
    """

    plots: List[AutoPlot]
    metadata: List[PlotMetadata]

    def __init__(self, auto_plotter: AutoPlotter):
        self.auto_plotter = auto_plotter
        self.plots = auto_plotter.plots
        self.file_extension = auto_plotter.file_extension

        self._generate_plotter_metadata()
        return

    def _generate_plotter_metadata(self):
        self.metadata = [PlotMetadata(plot=plot) for plot in self.plots]
        return

    def write_metadata(self, filename: str):
        """
        Writes the metadata out to a (yaml) file.
        """

        metadata = {plot.filename: plot.to_dict() for plot in self.metadata}

        try:
            metadata["metadata"] = dict(
                redshift=float(self.auto_plotter.soap.metadata.redshift),
                scale_factor=float(self.auto_plotter.soap.metadata.scale_factor),
            )
        except:
            pass

        with open(filename, "w") as handle:
            yaml.dump(metadata, stream=handle)

        return
