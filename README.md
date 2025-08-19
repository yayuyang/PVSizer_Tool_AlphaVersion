# IBRNet/GridSize: A PV & BESS Sizing and Impact Analysis Tool

**IBRNet/GridSize (Alpha Version)**  is an advanced simulation tool built on Python and OpenDSS. It offers a comprehensive framework to help engineers and researchers tackle two critical challenges in renewable energy integration:

1.  **Impact Analysis**: Perform detailed time-series simulations to evaluate the impact of specific PV and BESS configurations on the distribution network's performance, such as voltage profiles and equipment loading.
2.  **Optimal Sizing**: Determine the maximum capacity of Photovoltaic (PV) systems and the minimum required capacity of Battery Energy Storage Systems (BESS) without violating grid constraints.

For a complete guide on installation, configuration, and usage, please see the [➡️ Full User Guide](User_guide.md).

## 🚀 Download the Latest Version

The recommended way to get the IBRNet/GridSize tool is to download the latest official release. This ensures you have a stable, tested version of the code. The source code on the main branch may be under active development and is not recommended for general use.

**[➡️ Download the Latest Release (v1.0.0-alpha)](https://github.com/yayuyang/IBRNet_GridSize_AlphaVersion_Tool/releases)**

## Core Features

This tool offers three primary analysis modes

-  **single_run** Performs a detailed 24-hour simulation to evaluate the impact of IBRs on distribution networks for a single, user-defined PV and BESS configuration.
-  **traversal** Conducts a global traversal analysis to map the feasible operating regions for different PV and BESS capacities.
-  **optimization** Utilizes a hill-climbing algorithm to efficiently find the optimal PV and BESS sizes that meet all grid constraints.

## How to Run

1.  Configure Open `main20250812.py` and set your desired `run_mode` and other parameters in the `UserSettings` and `Config` classes.
2.  Execute Run the main script from your terminal
    ```bash
    python main20250812.py
    ```
3.  Analyze All results, including plots and CSV files, will be saved in the output directory specified in the configuration.

## Funding


This work was supported by the U.S. Department of Energy (DOE) under the EARNEST project.




