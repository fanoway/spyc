"""Plotting library."""

# Imports
import statistics
import logging
from typing import Optional, Dict, Any
import pandas as pd  # type: ignore
import plotly.graph_objects as go  # type: ignore
import plotly.io as pio  # type: ignore
import numpy as np

# Plot formattingpipen
pio.templates.default = "plotly_white"


class SPCFigure(go.FigureWidget):  # pylint: disable=too-many-ancestors
    """Extenstion of plotly's graphical object figurewidget library.

    Custom plots for SPC between mulitple sites,
    i.e can add meanlines and violin plots if requested.
    """

    colour_list = ["#fbaf00", "#007cbe", "#ffd639", "#ffa3af", "#00af54"]

    def __init__(
        self, *args: str, title: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Override __init__ method to add title at creation.

        Parameters
        ----------
        *args : str
            FigureWidget *args
        title : Optional[str], optional
            title to include on plot
        **kwargs : Any
            FigureWidget **kwargs
        """
        # self.log object
        self.log: logging.Logger = logging.getLogger(__name__)
        super().__init__(*args, **kwargs)
        self.update_layout(title=title, font_family="Arial")

    def xbar_plot(
        self,
        datasets: Dict[str, pd.DataFrame],
        test: pd.Series,
        meanline: bool = False,
        violin: bool = False,
    ):
        """Plot an xbar graph for a single test on to the figure.

        Pass a list of dataframes to plot for multiple sites

        Data sets must by pandas dataframes with index = Unit SN
        and column = 'Reading'
        Test is a series = Test_Name, Min_Tol, Max_Tol, Units
        Options to include violin and meanline in plot

        Parameters
        ----------
        datasets : dict[pd.DataFrame]
            Data to plot index = Unit SN and column = 'Reading'
            Dict key is location

        test : pd.Series
            series = Test_Name, Min_Tol, Max_Tol, Units
        meanline : bool, optional
            Plot meanline, default is False
        violin : bool, optional
            Plot violin, default is False
        """
        if not isinstance(datasets, dict):
            # if not a dict then raise an error
            self.log.error(
                f"{type(datasets)} passed to xbar_plot, expected a dict"
            )
            raise ValueError

        # plot limits, ignore if np.nan (i.e left blank on input data)
        lsl = test["Min_Tol"]
        if not np.isnan(lsl):
            self.add_hline(
                y=lsl,
                line_dash="dot",
                annotation_text="lsl",
                annotation_position="bottom right",
                line_color="#333F48",
                line_width=3,
                opacity=0.25,
            )
        usl = test["Max_Tol"]
        if not np.isnan(usl):
            self.add_hline(
                y=usl,
                line_dash="dot",
                annotation_text="usl",
                annotation_position="top right",
                line_color="#333F48",
                line_width=3,
                opacity=0.25,
            )

        # green box for tolerance band if both usl and lsl are specified
        if not np.isnan(lsl) and not np.isnan(usl):
            self.add_hrect(
                y0=lsl, y1=usl, line_width=0, fillcolor="#00af54", opacity=0.1
            )

        # loop through datasets and plot
        # Counter for colours so meanline and violinmatch in each legend group
        colour_count = 0
        for location, data in datasets.items():
            colour = self.colour_list[
                colour_count
            ]  # Get colour for this dataset

            # Marker style to flag OOT data
            data["Marker"] = [
                "x" if x < lsl or x > usl else "circle"
                for x in data["Reading"]
            ]

            # Plot data
            self.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data["Reading"],
                    mode="lines+markers",
                    name=location,
                    marker_symbol=data["Marker"],
                    marker=dict(
                        size=12, line=dict(width=2, color="DarkSlateGrey")
                    ),
                    legendgroup=location,
                    legendgrouptitle_text=location,
                    line=dict(color=colour, width=4),
                )
            )

            if meanline:
                self.add_hline(
                    y=statistics.mean(data["Reading"]),
                    line_dash="dash",
                    annotation_text=(
                        f"{location}-Mean ="
                        f" {statistics.mean(data['Reading']):.2f}"
                    ),
                    annotation_position="top right",
                    line_color=colour,
                    line_width=3,
                    opacity=0.75,
                )
            if violin:
                self.add_trace(
                    go.Violin(
                        y=data["Reading"],
                        meanline_visible=True,
                        line=dict(color=colour),
                        legendgroup=location,
                        name="Distribution",
                        showlegend=False,
                    )
                )
            colour_count += 1  # increment colour counter

        self.update_layout(
            uniformtext_minsize=8,
            uniformtext_mode="hide",
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            xaxis_title="Unit SN",
            yaxis_title=f"{test['Test_Name']}, {test['Units']}",
        )
