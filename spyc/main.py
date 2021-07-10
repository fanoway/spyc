"""SPYC (pronounced spicy).
  
  Usage:
      spyc plot <dir> [--verbose|--debug]
      spyc -h | --help
      spyc --version
  
  Options:
      -h --help              Show this screen.
      --version              Show version.
      -v --verbose           Verbose
      -d --debug             Debug Output
  
  Attributes:
      arguments (TYPE): Description
      console (TYPE): Description
      external_stylesheets (list): Description
      log (TYPE): Description
  
  """  # noqa

# Imports

import os
import glob
import logging
from typing import Optional, List, Dict, Any, Union
import json

from mainentry import entry
from rich.console import Console
from rich.markdown import Markdown
from rich_dataframe import prettify  # type: ignore
from docopt import docopt  # type: ignore
import pandas as pd  # type: ignore

import dash  # type: ignore
import dash_core_components as dcc  # type: ignore
import dash_html_components as html  # type: ignore
from dash.dependencies import Input, Output  # type: ignore

# these imports will not work if ran as a script
# use python -m main
from .__init__ import __version__  # type: ignore
from .helpers.partnumber import PartNumber
from .helpers.spcfigure import SPCFigure

# create logger
log = logging.getLogger(__name__)
console = Console()

# Argument handling and setup
arguments = docopt(__doc__, version=f"SPYC {__version__}")

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

# Get plot options from json source file
with open("spyc/plot_options.json") as f:
    plot_types: Dict[str, Any] = json.load(f)

# Manage verbose and debug output levels
if arguments["--verbose"]:
    logging.basicConfig(format="%(levelname)s: %(message)s", level=20)

elif arguments["--debug"]:
    # set to debug level
    logging.basicConfig(format="%(levelname)s: %(message)s", level=10)
else:
    # Set logging threshold at info
    logging.basicConfig(format="%(levelname)s: %(message)s", level=30)


def make_parts(filepath: str) -> Dict[str, PartNumber]:
    """Create list of parts in the target directory.

    Args:
        filepath (str): Directory to look within

    Returns:
        Dict[str, PartNumber]: Partslist, key is part number string

    Raises:
        ValueError: Description
    """

    if not os.path.isabs(filepath):

        filepath = os.path.abspath(filepath)
        log.debug(f"dir input is not absolute, new dir is: {filepath}")

    log.debug(f"Looking in dir: {filepath}")

    # Look up xlsx file in the specified directory
    data_files = glob.glob(f"{filepath}/*.xlsx")

    log.info(f"{len(data_files)} files found in {filepath}")

    # create Part_Number Object for each file
    parts = {}
    for file in data_files:
        log.debug(f"Reading from {file}")
        try:
            part = PartNumber(file)
            if part.header["Part Number"] in parts:
                raise ValueError(
                    "Duplicate PN in source directory,"
                    f" {part.header['Part Number']}"
                )
            parts[part.header["Part Number"]] = part
        except ValueError as e:
            log.warning(e)

    return parts


def dash_app(filepath: str, debug: bool = False):
    """Create a dash app.

    Args:
        filepath (str): Description
        debug (bool, optional): Description

    Raises:
        FileNotFoundError: Description
    """
    app = dash.Dash(
        __name__, external_stylesheets=external_stylesheets, title="SPYC"
    )
    app.config["suppress_callback_exceptions"] = True

    # Get PartNumber objects
    part_dict = make_parts(filepath)

    if not part_dict:
        raise FileNotFoundError(
            f"No Parts generated from dir = {arguments['<dir>']}"
        )

    # Build dict for part selection drop down
    part_dd_options = []
    for pn in list(part_dict.keys()):

        part_dd_options.append({"label": pn, "value": pn})

    # Elements to always display. The rest are generate by the code
    disp_elements = [
        html.H1(children="SPYC"),
        dcc.Dropdown(
            id="part_dd",
            options=part_dd_options,
            placeholder="Select a Part Number",
            clearable=True,
        ),
        html.Div(id="loc_title"),
        dcc.Checklist(id="loc_dd", labelStyle={"display": "inline-block"}),
        dcc.Dropdown(
            id="test_dd",
            placeholder="Select tests to plot, leave blank to plot all",
            multi=True,
            clearable=True,
        ),
        dcc.RadioItems(id="plot_dd", labelStyle={"display": "inline-block"}),
        html.Div(id="cap_title"),
        dcc.RadioItems(
            id="cap_dd", labelStyle={"display": "inline-block"}, value="None"
        ),
        html.Div(id="fig_container"),
    ]

    @app.callback(Output("loc_title", "children"), Input("part_dd", "value"))
    def show_loc_title(pn: str) -> str:
        """Show location title only if PN is selected.

        Args:
            pn (str): pn to plot

        Returns:
            str: location title
        """
        if pn:
            return "Plot data for:"

    @app.callback(
        Output("cap_title", "children"),
        [Input("part_dd", "value"), Input("plot_dd", "value")],
    )
    def show_cap_title(pn: str, ptype: str) -> str:
        """Show location title only if PN is selected. And plot allows capability

        Args:
            pn (str): pn to plot
            ptype (str): plot type

        Returns:
            str: Capability title
        """
        if pn and ptype:
            if plot_types[ptype]["capability"]:
                return "Measure capability from:"
        else:
            return ""

    @app.callback(Output("loc_dd", "options"), [Input("part_dd", "value")])
    def get_loc(value: str) -> List[Dict[str, str]]:
        """Display graphs selected by part number dropdown.

        Parameters
        ----------
        value : str
            part number

        Returns
        -------
        List[Dict[str:str]]
            checklist options for locations
        """

        loc_dd_options = []

        if value is not None:

            part = part_dict[value]

            # build dict for part slection drop down

            for loc in list(part.data.keys()):
                loc_dd_options.append({"label": loc, "value": loc})

            return loc_dd_options
        return []

    @app.callback(Output("test_dd", "options"), [Input("part_dd", "value")])
    def get_test_id(pn: str) -> List[Dict[str, str]]:
        """Display plot types avaialable.

        Parameters
        ----------
        pn: str
            Part Number to plot

        Returns
        -------
        List[Dict[str,str]]
            Dropdown options for tests types
        """
        if pn:
            test_dd_options = []
            # get part
            part = part_dict[pn]

            for test_id in part.tests.index.get_level_values(0).unique():
                test_dd_options.append(
                    {
                        "label": part.tests.loc[test_id]["Test_Name"],
                        "value": test_id,
                    }
                )

            return test_dd_options

        return []

    @app.callback(Output("plot_dd", "options"), [Input("loc_dd", "value")])
    def get_plot_type(locs: List[str]) -> List[Dict[str, str]]:
        """Display plot types avaialable.

        Parameters
        ----------
        locs: List[str]
            List of Locations selected

        Returns
        -------
        List[Dict[str,str]]
            Radio options for plot types
        """
        if locs:
            plot_dd_options = []
            for ptype in plot_types:
                # Filter Plot Options Based On Maximum # Locations to plot
                max_locs = plot_types[ptype]["max_locs"]

                if max_locs is None or max_locs >= len(locs):
                    plot_dd_options.append({"label": ptype, "value": ptype})

            return plot_dd_options

        return []

    @app.callback(
        Output("cap_dd", "options"),
        [Input("loc_dd", "value"), Input("plot_dd", "value")],
    )
    def get_capability_loc(
        locs: List[str], ptype: str
    ) -> List[Dict[str, str]]:
        """Display plot types avaialable.

        Parameters
        ----------
        locs: List[str]
            List of Locations selected
        ptype: str
            Selected plot type

        Returns
        -------
        List[Dict[str,str]]
            Radio options for capability location
        """
        if locs and ptype and plot_types[ptype]["capability"]:
            cap_dd_options = [{"label": "None", "value": "None"}]

            for loc in locs:
                cap_dd_options.append({"label": loc, "value": loc})

            return cap_dd_options

        return []

    @app.callback(
        Output("fig_container", "children"),
        [
            Input("part_dd", "value"),
            Input("loc_dd", "value"),
            Input("plot_dd", "value"),
            Input("test_dd", "value"),
            Input("cap_dd", "value"),
        ],
    )
    def plot_figure(
        pn: str,
        locs: List[str],
        ptype: str,
        test_id: List[str],
        capability_loc: str,
    ) -> List[Any]:
        """plot the figures.

        Args:
            pn (str): Part Number to plot
            locs (List[str]): Locations to plot
            ptype (str): Type of plot
            test_id (List[str]): Tests to plot
            capability_loc (str): Location to calculate cpability for

        Returns:
            List[Any]: Elements to display
        """
        # Get all inputs first (except test_id as that can be None)
        if locs and pn and ptype:

            # if test_id is empty then change to None
            if not test_id:
                test_id = None

            # get part
            part = part_dict[pn]

            # Convert "None" option to NoneType
            if capability_loc == "None":
                capability_loc = None

            elements = []

            for title, fig in plot_factory(
                part, ptype, locs, test_id, capability_loc
            ).items():
                elements.append(html.H2(children=title))
                elements.append(
                    dcc.Graph(
                        figure=fig, animate=True, config={"displaylogo": False}
                    )
                )
                elements.append(html.Hr())

            return elements

    app.layout = html.Div(children=disp_elements)

    app.run_server(debug=debug)


def plot_factory(
    part: PartNumber,
    plot_type: str,
    locations: Union[List[str], None],
    test_id: Union[List[str], str],
    capability_loc: str,
) -> Dict[str, SPCFigure]:
    """Create plot using parameters from the dash interface.

    Args:
        part (PartNumber): PartNubmer object to plot for object
        plot_type (str): Type of plot
        locations (Union[List[str], None]): List of locations to plot for
        test_id (Union[List[str], str]): Test_ids to plot for
        capability_loc (str): Lcoation to calcualte capability for
    """
    # Select plot type
    if plot_type == "xbar":
        log.info("xbar plot")

        # Plots for all sites all tests,
        # calculate capability for Portland
        return part.xbar(
            location=locations,
            test_id=test_id,
            capability_loc=capability_loc,
            meanline=True,
            violin=True,
        )

        # TODO capability loc and test_id

        #     else:
        #         log.error(
        #             "Invalid capability_loc passed for PN:"
        #             f" {part.header['Part Number']}\ncapability_loc"
        #             " passed as :"
        #             f" {arguments['--capability_loc']}\nLocations in"
        #             f" input: {locations}"
        #         )
        #         raise ValueError("Invalid capability_loc")

        # else:
        #     log.error(
        #         "Invalid Locations passed for PN:"
        #         f" {part.header['Part Number']}\nLocations passed as"
        #         f" argument: {locations}\nLocations in data files:"
        #         f" {part.data.keys()}"
        #     )
        #     raise ValueError("Invalid locations")


@entry
def main():
    """Read user input from cli and call plot functions as required."""
    # Run command passed
    if arguments["plot"]:
        log.debug("Plot command")

        # Launch dash app
        dash_app(filepath=arguments["<dir>"], debug=arguments["--debug"])


# Catch exceptions to use them as breakpoints
try:
    main()
except Exception as e:
    log.error(e)
