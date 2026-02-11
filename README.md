# PVSizer: A PV & BESS Sizing and Impact Analysis Tool

**PVSizer (Alpha Version)** is a design tool built on Python and OpenDSS. It offers a comprehensive framework to help engineers and researchers tackle two critical challenges in renewable energy integration:

1.  **Impact Analysis**: Perform detailed time-series simulations to evaluate the impact of specific PV and BESS configurations on the distribution network's performance, such as voltage profiles and equipment loading.
2.  **Optimal Sizing**: Determine the maximum capacity of Photovoltaic (PV) systems and the minimum required capacity of Battery Energy Storage Systems (BESS) without violating grid constraints.

For a complete guide on installation, configuration, and usage, please see the [➡️ Full User Guide](User_guide.md).

## 🚀 Download the Latest Version

The recommended way to get the PVSizer tool is to download the latest official release. This ensures you have a stable, tested version of the code. The source code on the main branch may be under active development and is not recommended for general use. 

**[➡️ Download the Stable Release (v1.0.1)](https://github.com/yayuyang/PVSizer_Tool_AlphaVersion/releases)** 

## Core Features

This tool offers three primary analysis modules

-  **single_run** Performs a detailed 24-hour simulation to evaluate the impact of IBRs on distribution networks for a single, user-defined PV and BESS configuration.
-  **traversal** Conducts a global traversal analysis to map the feasible operating regions for different PV and BESS capacities.
-  **optimization** Utilizes a hill-climbing algorithm to efficiently find the optimal PV and BESS sizes that meet all grid constraints.
-  **violation solution** Resolves voltage and loading violations by upgrading lines or adjusting components.

## How to Run

1.  Configure Open `main_gui.py` and set your desired `run_mode` and other parameters in the `UserSettings` and `Config` classes.
2.  Execute Run the main script from your terminal
    ```bash
    python main_gui.py
    ```
3.  Analyze All results, including plots and CSV files, will be saved in the output directory specified in the configuration.

## Funding

This work was supported by the U.S. Department of Energy (DOE) under the EARNEST project.

## Authors 
Yayu(Andy) Yang, Jian Zhang, Samuel Okhuegbe, Yilu Liu

<table border="0">
  <tr>
    <td align="center">
      <img src="./logo/UTK.jpg" alt="Image 1" width="150">
    </td>
    <td align="center">
      <img src="./logo/CURENT.png" alt="Image 2" width="150">
    </td>
    <td align="center">
      <img src="./logo/ORNL.png" alt="Image 3" width="150">
    </td>
    <td align="center">
      <img src="./logo/DOE.png" alt="Image 4" width="150">
    </td>
    <td align="center">
      <img src="./logo/EARNEST.png" alt="Image 5" width="150">
    </td>
  </tr>
</table>








