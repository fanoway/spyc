"""SPYC (pronounced spicy).
  
  Usage:
      spyc plot <dir> [--verbose|--debug] [--url=<url>] [--port=<port>] [--header = <text>]
      spyc -h | --help
      spyc --version
  
  Options:
      --url=<url>            Specify the URL
      --port=<port>          Specify the Port
      --header               Header to dispal on website
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
from typing import List, Dict, Union
import json
import webbrowser
import importlib.resources

from mainentry import entry
from docopt import docopt  # type: ignore

# import pandas as pd  # type: ignore

import dash  # type: ignore
import dash_core_components as dcc  # type: ignore
import dash_html_components as html  # type: ignore
from dash.dependencies import Input, Output  # type: ignore
from cheroot.wsgi import Server as WSGIServer  # type: ignore
from cheroot.wsgi import PathInfoDispatcher  # type: ignore

# these imports will not work if ran as a script
# use python -m main
from .__init__ import __version__  # type: ignore
from .helpers.partnumber import PartNumber
from .helpers.spcfigure import SPCFigure

# create logger
log = logging.getLogger(__name__)

# Argument handling and setup
arguments = docopt(__doc__, version=f"SPYC {__version__}")

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

# Get plot options from json source file
with importlib.resources.path("spyc_spc", "plot_options.json") as plot_options:
    with open(plot_options) as f:
        plot_types = json.load(f)

# Manage verbose and debug output levels
if arguments["--verbose"]:
    logging.basicConfig(format="%(levelname)s: %(message)s", level=20)

elif arguments["--debug"]:
    # set to debug level
    logging.basicConfig(format="%(levelname)s: %(message)s", level=10)
else:
    # Set logging threshold at info
    logging.basicConfig(format="%(levelname)s: %(message)s", level=30)

# Dash App
app = dash.Dash(
    __name__, external_stylesheets=external_stylesheets, title="SPYC"
)
app.config["suppress_callback_exceptions"] = True

server = app.server


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


def plot_factory(
    part: PartNumber,
    plot_type: str,
    locations: Union[List[str], None],
    test_id: Union[List[str], str, None],
    capability_loc: Union[str, None],
    options: List[str],
) -> Union[Dict[str, SPCFigure], Dict[None, None]]:
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

        # Plots for all sites all tests,
        # calculate capability for Portland
        return part.xbar(
            location=locations,
            test_id=test_id,
            capability_loc=capability_loc,
            meanline="meanline" in options,
            violin="violin" in options,
        )
    else:
        return {None: None}


# Get PartNumber objects
part_dict = make_parts(arguments["<dir>"])

if not part_dict:
    raise FileNotFoundError(
        f"No Parts generated from dir = {arguments['<dir>']}"
    )

# Build dict for part selection drop down
part_dd_options = []
for pn in list(part_dict.keys()):
    part_dd_options.append({"label": pn, "value": pn})
    
header = "SPYC"
if arguments['--header']:
  header = arguments['--header']

# Elements to always display. The rest are generate by the code
disp_elements = [
    html.H1(children="header"),
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
    html.Div(id="option_title"),
    dcc.Checklist(id="option_dd", labelStyle={"display": "inline-block"}),
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
    return ""


@app.callback(
    Output("cap_title", "children"),
    [Input("part_dd", "value"), Input("plot_dd", "value")],
)
def show_cap_title(pn: str, ptype: str) -> str:
    """Show capability title only if PN is selected and plot allows capability.

    Args:
        pn (str): pn to plot
        ptype (str): plot type

    Returns:
        str: Capability title
    """
    if pn and ptype:
        if plot_types[ptype]["capability"]:
            return "Measure capability from:"
    return ""


@app.callback(Output("option_title", "children"), Input("plot_dd", "value"))
def show_option_title(ptype: str) -> str:
    """Show option title only if PN is selected.

    Args:
        ptype (str): plot type

    Returns:
        str: plot options title
    """
    # only disaply if the plot type has options
    if ptype and len(plot_types[ptype]["options"]) > 0:
        return "Plot Options:"
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
def get_capability_loc(locs: List[str], ptype: str) -> List[Dict[str, str]]:
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


@app.callback(Output("option_dd", "options"), Input("plot_dd", "value"))
def get_options(ptype: str) -> List[Dict[str, str]]:
    """Display plot types avaialable.

    Parameters
    ptype: str
        Selected plot type

    Returns
    -------
    List[Dict[str,str]]
        Checklist options for plot options
    """
    if ptype and len(plot_types[ptype]["options"]) > 0:
        option_dd_options = []

        for option in plot_types[ptype]["options"]:
            option_dd_options.append({"label": option, "value": option})

        return option_dd_options

    return []


@app.callback(
    Output("fig_container", "children"),
    [
        Input("part_dd", "value"),
        Input("loc_dd", "value"),
        Input("plot_dd", "value"),
        Input("test_dd", "value"),
        Input("cap_dd", "value"),
        Input("option_dd", "value"),
    ],
)
def plot_figure(
    pn: str,
    locs: List[str],
    ptype: str,
    test_id: Union[List[str], None],
    capability_loc: Union[str, None],
    options: Union[List[str], None],
):
    """Plot the figures.

    Args:
        pn (str): Part Number to plot
        locs (List[str]): Locations to plot
        ptype (str): Type of plot
        test_id (Union[List[str], None]): Tests to plot
        capability_loc (str): Location to calculate cpability for
        options (List(str)): options selected by the user

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

        # handle no options slected case
        if options is None:
            options = []

        elements = []

        for title, fig in plot_factory(
            part, ptype, locs, test_id, capability_loc, options
        ).items():
            if fig is not None:
                elements.append(
                    dcc.Graph(
                        id=title, figure=fig, config={"displaylogo": False}
                    )
                )
                elements.append(html.Hr())

        return elements


app.layout = html.Div(children=disp_elements)


@entry
def main():
    """Read user input from cli and call plot functions as required."""
    # Run command passed
    if arguments["plot"]:
        log.debug("Plot command, launching dash app")

        # set port and url
        if arguments["--port"] is None:
            port = 80
        else:
            port = arguments["--port"]

        if arguments["--url"] is None:
            url = "127.0.0.1"
        else:
            url = arguments["--url"]

        if arguments["--debug"]:
            app.run_server(debug=True)
        else:
            print(f"Launching Server at http://{url}:{port}/")
            wsgiserver = WSGIServer(
                (url, int(port)), PathInfoDispatcher({"/": server})
            )

            try:
                print("Server started")
                webbrowser.open(f"http://{url}:{port}/")
                wsgiserver.start()
            except KeyboardInterrupt:
                wsgiserver.stop()
                print("Server stopped")


# Catch exceptions to use them as breakpoints
try:
    main()
except Exception as e:
    log.error(e)
