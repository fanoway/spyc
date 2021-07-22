"""Object for individual part numbers.

Some basic structure to call on the SPCFigure library etc.
"""

# Imports

import statistics
import logging
from typing import Union, Tuple, Optional, List, Dict, Any
import pandas as pd  # type: ignore
import numpy as np
from .spcfigure import SPCFigure


class PartNumber:
    """Object to represent a single part number.

    Includes associated test data and methods
    See "Dummy Data.xlsx" for an example input data file

    Deleted Attributes
    ------------------
    log : logging:Logger
        logging object
    data : dict[str, pd.Dataframe]
        Dictionary of data frames
        containing raw test data
    header : dict[str,str]
        Dict of outline infomation
    tests : pd.Dataframe
        Dataframe with test descriptions
    """

    def __init__(self, filepath: str) -> None:
        """Set up logging and read in data from filepath.

        Parameters
        ----------
        filepath : str
            path to data file

        Raises
        ------
        ValueError
            Description
        """
        # self.log object
        self.log: logging.Logger = logging.getLogger(__name__)

        # Read from excel
        try:

            col_dtype = {
                "Part Number": "string",
                "Notes": "string",
                "Test_ID": "string",
                "Test_Name": "string",
                "Min_Tol": np.float64,
                "Max_Tol": np.float64,
                "Units": "string",
                "Reading": np.float64,
                "Unit SN": "string",
            }

            # Single call to Excel
            xls = pd.ExcelFile(filepath, engine = "openpyxl")

            # Generic header infomation
            self.header: Dict[str, str] = (
                pd.read_excel(
                    xls, sheet_name="Header", header=0, dtype=col_dtype
                )
                .iloc[0]
                .to_dict()
            )
            self.log.debug("Header Read")
            self.log.debug(self.header)

            # Test list
            self.tests: pd.DataFrame = pd.read_excel(
                xls, sheet_name="Test_List", header=0, dtype=col_dtype
            ).set_index("Test_ID")
            self.log.debug("Test_List Read")
            self.log.debug(self.tests.head(5))

            # Data from each site. Store in dict with key as sheetname
            self.data: Dict[str, pd.DataFrame] = {}  # empty dict
            for sheet_name in xls.sheet_names:

                if sheet_name not in [
                    "Header",
                    "Test_List",
                ]:  # reserved sheet names
                    try:
                        self.data[sheet_name] = pd.read_excel(
                            xls,
                            sheet_name=sheet_name,
                            header=0,
                            dtype=col_dtype,
                        ).set_index(["Test_ID", "Unit SN"])
                        self.log.debug(f"{sheet_name} loaded")
                        self.log.debug(self.data[sheet_name].head(5))
                    except Exception as e:
                        self.log.info(f"{sheet_name} failed to load\n{e}")

            # Return an error if no data sheets are loaded
            if not self.data:
                raise ValueError(f"No data sheets were read from {filepath}")

            self.log.info(f"{filepath} loaded with {len(self.data)} locations")
            self.log.debug(f"locations= {list(self.data.keys())}")

        except ValueError as e:
            self.log.warning(f"{filepath} failed to load\n{e}")
            raise ValueError from e

    def __repr__(self) -> str:
        """Override the __repr__ function with a friendly output.

        Returns
        -------
        str
            String representation of the partnumber object
        """
        return (
            f"PN: {self.header['Part Number']}, locations ="
            f" {list(self.data.keys())}"
        )

    def xbar(
        self,
        location: Optional[Union[str, List[str]]] = None,
        test_id: Optional[Union[str, List[str]]] = None,
        capability_loc: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, SPCFigure]:
        """Plot an xbar chart (value against SN) using SPCFigure module.

        Args:
            location (Optional[Union[str, list[str]]], optional): Sheetname(s)
            test_id ((Optional[Union[str, list[str]]], optional):
                id of the test(s) in test list to plot,
                default to plot all tests seperately
            capability_loc (Optional[str], optional): Sheetname for cp & cpk
                default is to not calculate for multiple locations
            meanline (bool, optional): Plot a meanline for each location
                off bv default
            violin (bool, optional): Plot a violin for each location
                off bv default
            to plot data for, default is to plot all locations
        """
        # Dict to hold all plots, title is the key
        figs = {}

        # Check for single plot
        if not isinstance(test_id, str):
            self.log.debug("Plotting multiple tests")

            # Check to plot all
            if test_id is None:
                test_id = self.tests.index.get_level_values(0).unique()

            # Plot selected tests
            for t_id in test_id:
                self.log.debug(f"Plotting test = {t_id}")

                title, fig = self.xbar_plot(
                    str(t_id),
                    location=location,
                    capability_loc=capability_loc,
                    **kwargs,
                )
                figs[title] = fig

        else:
            # Plot one test
            self.log.debug(f"Single Plot, test = {test_id}")

            title, fig = self.xbar_plot(
                str(test_id),
                location=location,
                capability_loc=capability_loc,
                **kwargs,
            )

            figs[title] = fig

        return figs

    def xbar_plot(
        self,
        test_id: str,
        location: Optional[Union[str, List[str]]] = None,
        capability_loc: Optional[str] = None,
        **kwargs: Any,
    ) -> Tuple[str, SPCFigure]:
        """Plot an xbar chart (value against SN) for 1 test.

        Uses SPCFigure module.

        Args:
            test_id (str): id of the test in test list to plot
            location (Optional[Union[str, list[str]]], optional): Sheetname(s)
            capability_loc (Optional[str], optional): sheetname for cp & cpk
            meanline (bool, optional): Plot a meanline for each location
                off bv default
            violin (bool, optional): Plot a violin for each location
                off bv default
            to plot data for, default is to plot all locations
        """
        # Enforce string type
        test_id = str(test_id)

        # Get Limits
        lsl, usl = self.get_limits(test_id)

        # Check if capability is set
        if capability_loc is not None:

            self.log.debug(
                f"Calculating capability for {capability_loc}, test {test_id}"
            )

            # Calcualte cp and cpk for specified location
            try:
                cp, cpk = PartNumber.calculate_capability(
                    PartNumber.extract_test(
                        self.data[capability_loc], test_id
                    ),
                    lsl,
                    usl,
                )

                title = (
                    f"{self.header['Part Number']}  "
                    f"{self.tests.loc[test_id,'Test_Name']}"
                    f"  Cp/Cpk={cp:.2f}/{cpk:.2f} @ {capability_loc}"
                )

            except KeyError as e:
                self.log.error(f"Invalid capability_loc -\n{e}")

        else:
            self.log.debug(
                "Not calculating capability, capability_loc not set"
            )

            title = (
                f"{self.header['Part Number']}  "
                f"{self.tests.loc[test_id,'Test_Name']}"
            )

        fig = SPCFigure(title=title)

        # if location is none then it is all
        if location is None:
            location = list(self.data.keys())

        # extract test to plot
        datasets = {}
        if isinstance(location, list):
            # multiple locations so extract single test for each
            for loc in location:
                datasets[loc] = PartNumber.extract_test(
                    self.data[loc], test_id
                )
        else:
            datasets[location] = PartNumber.extract_test(
                self.data[location], test_id
            )

        self.log.debug(f"Plotting {len(datasets)} locations")

        fig.xbar_plot(
            datasets,
            self.tests.loc[test_id],
            meanline=kwargs.get("meanline", False),
            violin=kwargs.get("violin", False),
        )

        return title, fig

    def get_limits(self, test_id: str) -> Tuple[float, float]:
        """Get upper and lower spec limits.

        Args:
            test_id (str): Test id in test list

        Returns:
            Tuple[float, float]: USL, LSL
        """
        lsl = self.tests.loc[test_id]["Min_Tol"]
        usl = self.tests.loc[test_id]["Max_Tol"]
        # if not specified set to None
        if np.isnan(usl):
            usl = None
        if np.isnan(lsl):
            lsl = None

        return lsl, usl

    @staticmethod
    def calculate_capability(
        test_dataset: pd.DataFrame,
        lsl: Union[int, float, None],
        usl: Union[int, float, None],
    ) -> Tuple[float, float]:
        """Calculate capability for a dataset.

        Must be filtered to a single test and location

        Args:
            test_dataset (pd.DataFrame): Dataset reduced to a single test
           usl (Union[int, float, None]): Upper Spec Limit
            lsl (Union[int, float, None]): Lower Spec Limit

        """
        log = logging.getLogger(__name__)

        mean = statistics.mean(test_dataset["Reading"])
        SD = statistics.stdev(test_dataset["Reading"])

        # Error check
        if lsl is None and usl is None:
            log.error("Neither Min_Tol or Max_Tol is set")
            raise ValueError("Neither Min_Tol or Max_Tol is set")

        if usl is None:
            cpk = (mean - lsl) / (3 * SD)
            cp = np.nan
        elif lsl is None:
            cpk = (usl - mean) / (3 * SD)
            cp = np.nan
        else:
            cp = (usl - lsl) / (6 * SD)
            cpk = min((mean - lsl) / (3 * SD), (usl - mean) / (3 * SD))

        return cp, cpk

    @staticmethod
    def extract_test(dataset: pd.DataFrame, test_id: str) -> pd.DataFrame:
        """Return a dataset in the format needed by SPCFigure.

           * 1 location
           * 1 test
           * all SNs

        Args:
            dataset (pd.DataFrame): Single location to extract from
            test_id (str): test id in test list

        Returns:
            pd.DataFrame: Dataset reduced to a single test
        """
        return dataset.loc[test_id]
