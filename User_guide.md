# PVSizer (Alpha Version) Tool User Manual

**Authors:**  
Yilu Liu, Yayu(Andy) Yang, Samuel Okhuegbe, Jian Zhang  

**Affiliations:**  
- University of Tennessee, Knoxville, USA  
- Oak Ridge National Laboratory, USA

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

## Table of Contents
- [PVSizer (Alpha Version) Tool User Manual](#pvsizer-alpha-version-tool-user-manual)
  - [Table of Contents](#table-of-contents)
  - [1. Introduction](#1-introduction)
    - [1.1 Module 1: single\_run](#11-module-1-single_run)
    - [1.2 Module 2: traversal](#12-module-2-traversal)
    - [1.3 Module 3: optimization](#13-module-3-optimization)
  - [2. Installation and Dependencies](#2-installation-and-dependencies)
    - [2.1 System Requirements](#21-system-requirements)
    - [2.2 Library Installation](#22-library-installation)
  - [3. Tool Configuration (main20250812.py)](#3-tool-configuration-main20250812py)
    - [3.1 UserSettings: Module Selection and General Parameters](#31-usersettings-module-selection-and-general-parameters)
    - [3.2 Config: File Paths and Detailed Settings](#32-config-file-paths-and-detailed-settings)
  - [4. How to Run](#4-how-to-run)
  - [5. Result Analysis](#5-result-analysis)
    - [5.1 single\_run Module Results](#51-single_run-module-results)
    - [5.2 traversal Module Results](#52-traversal-module-results)
    - [5.3 optimization Module Results](#53-optimization-module-results)
  - [6. Code Architecture and Future Outlook](#6-code-architecture-and-future-outlook)
  - [7. Project Funding](#7-project-funding)
  - [8. Author information](#8-author-information)

---

## 1. Introduction
**PVSizer (Alpha Version)** is a design tool built on Python and OpenDSS, designed to help power system engineers and researchers analyze the impact of inverter-based resources (IBR), such as Photovoltaic systems(PV) and Battery Energy Storage System(BESS), on distribution networks. 
In this tool, OpenDSS serves as the powerful simulation engine responsible for modeling the grid and solving complex power flow calculations ⚙️. Python acts as the high-level automation and analysis layer 🧠, which controls the simulation workflows, processes the vast amount of output data, and generates insightful visualizations. 
The tool offers three core analysis modules:

### 1.1 Module 1: single_run
**Purpose:**  
Performs a detailed 24-hour simulation to evaluate the impact of IBRs on distribution networks for a single, user-defined PV and BESS configuration.

**Outputs:**  
- Comprehensive charts and data for analysis.  
- Automatic export of all simulation data to a CSV file.

### 1.2 Module 2: traversal
**Purpose:**  
A global traversal analysis that systematically tests combinations of PV and BESS capacities to generate a "feasibility region map", visually identifying configurations that satisfy grid constraints.

**Outputs:**  
- Visualization of feasible capacity configurations.  
- Detailed infeasible reasons for configurations that do **not** meet constraints, including:  
  - Convergence Failure  
  - Voltage Violation  
  - Loading Violation  
  - Battery Oversize  
- Automatic export of all simulation data to a CSV file.  
- Identification of the maximum PV size and the minimum corresponding BESS size from successful configurations.

**Optimization Objective:**  
Map the entire feasible region of operation. From successful configurations, identify the point that **maximizes PV rated active power** and, for that maximum PV level, determine the **minimum required BESS rated active power**.

**Constraints:**  
For a given combination of PV and BESS capacity to be considered successful, the 24-hour simulation must satisfy the following grid constraints:
  - **Power Flow Convergence:** The simulation must successfully converge at all time steps.  
  - **Voltage Limits:** All bus node voltages must remain within the predefined limits (e.g., 0.95 p.u. to 1.05 p.u.) for the entire duration.  
  - **Thermal Limits:** The loading on all power delivery elements (lines and transformers) must not exceed their thermal rating (e.g., 100%).
  - **Battery Capacity Constraints:**  1) Rated active power of the battery cannot exceed the rated active power of the PV；2) If the battery remains above its minimum SOC after discharging overnight, its capacity is considered unrealistic.


### 1.3 Module 3: optimization
**Purpose:**  
Uses a **hill-climbing algorithm** to efficiently search for the optimal configuration that **maximizes PV size** while **minimizing BESS size**, subject to the same grid constraints.

**Outputs:**  
- Detailed 24-hour time-series simulation for the identified optimal PV-BESS combination.

**Optimization Objective:**  
Same as Module 2: traversal.

**Constraints:**  
Same as Module 2: traversal.

---

## 2. Installation and Dependencies

### 2.1 System Requirements
- Python 3.x
- `opendssdirect.py`: Python library for interacting with the OpenDSS engine.
- `numpy`: Library for numerical operations.
- `pandas`: Library for data manipulation and result export.
- `matplotlib`: Library for plotting and data visualization.
- `multiprocessing`: Library for parallel processing, used in the traversal module.

### 2.2 Library Installation
You can also install `opendssdirect` using pip: https://pypi.org/project/opendssdirect.py/

The API documentation is here: https://dss-extensions.org/OpenDSSDirect.py/opendssdirect.html

---

## 3. Tool Configuration (main20250812.py)

All configurable parameters are located in the main20250812.py file, within the UserSettings and Config classes.

### 3.1 UserSettings: Module Selection and General Parameters

This class controls the operational module and high-level parameters for the analysis.

```python
class UserSettings:
    # 1.1 --- Operating Module Selection ---
    # Options: 'traversal', 'optimization', 'single_run'
    # 'single_run':   single case detailed simulation with fixed PV and battery sizes
    # 'traversal':    Global traversal analysis (Map Drawer)
    # 'optimization': Hill-climbing optimization (Climber)    
    run_mode = 'single_run'

    # 1.2 --- Global Component Parameters ---
    storage_duration = 4                             # Ratio of battery capacity (kWh) to rated power (kW).
    chosen_battery_strategy = strategy_self_consumption_present_pv_load    # Multiple battery control strategies are available. See control.py for details.  
    inverter_sizing_factor = 1.7                     # Ratio of storage inverter's apparent power (kVA) to battery's rated active power (kW).

    # 1.3 --- Single-run Module Parameters (effective only when run_mode = 'single_run') ---
    single_run_pv_kw = 3000.0                      # Specified PV rated active power for a single simulation run.
    single_run_batt_kw = 2000.0                    # Specified battery rated active power for a single simulation run.

    # 1.4 --- Traversal Module Parameters (effective only when run_mode = 'traversal') ---
    # np.arange(start, stop, step) defines the range. 'stop' is not included in the range.
    traversal_pv_kw_range = np.arange(0, 10001, 2000)      # Range of PV rated active power to traverse (kW).
    traversal_battery_kw_range = np.arange(100, 10001, 1000) # Range of battery rated active power to traverse (kW).
    # Note: The minimum value of the battery's rated active power range should not be too small or equal to 0, minium should above 100kW. As a very low rated active power may cause numerical instability or convergence failures in the power flow solver.

    # 1.5 --- Optimization Module Parameters (effective only when run_mode = 'optimization') ---
    optimization_initial_pv_kw = 200.0             # Starting PV rated active power for the optimization search.
    # Note: initial_pv_kw should >or= initial_batt_kw
    optimization_initial_batt_kw = 100.0           # Starting battery rated active power for the optimization search.
    optimization_pv_step = 200.0                   # Step size for increasing PV rated active power.
    optimization_batt_step = 100.0                 # Step size for increasing battery rated active power.
    optimization_max_pv_kw = 10000.0               # Maximum allowed PV rated active power.
    optimization_max_batt_kw = 10000.0             # Maximum allowed battery rated active power.
```
**Note:** For the 'traversal' and 'optimization' modules, you can use the open-source tool [PVWatts Calculator](https://pvwatts.nrel.gov) to estimate the energy production of grid-connected photovoltaic (PV) energy systems worldwide.  
> Using this tool, it is straightforward to estimate the average active power for each month.  
> From the PV power curve, you can determine the upper limit of the PV rated active power.  
> The recommended upper limit for the BESS rated active power is 50%–100% of the PV rated active power upper limit. For simplicity, directly take 100% 

### 3.2 Config: File Paths and Detailed Settings

This configuration defines the operational module, file paths, and high-level parameters required for the analysis of the power system. It centralizes all key settings, including input data locations, time-series simulation parameters, PV and storage system definitions, and grid constraints. By organizing these parameters in a single Config object, the code becomes more modular, readable, and easier to maintain or modify for different simulation scenarios.

```python
Config = SimpleNamespace(
    # 2.1 --- File and Path Settings ---
    files = SimpleNamespace(
        # Path to the master OpenDSS file that defines the power grid topology and components.
        dss_master_file = r'...\code\Loadfiles\IEEE13test.dss',        
        # Path to the load shape file, which defines the load variation over a 24-hour period for time-series analysis.
        load_shape_profile = r"...\code\Loadfiles\load_curve.txt",        
        # # --- pv_shape_profile's meaning and related settings ---
        # # 1. Identity: While the shape of this curve is determined by a solar irradiance profile, the values in this file are treated
        # #    directly as the PV system's output power as a percentage of its rated active power. This is its accurate identity within this code.
        # #    For example, a value of 0.5 means the PV output is 50% of its rated power.
        # # 2. PV Inverter Thresholds: To ensure the simulation accurately follows this profile, especially at very low output values,
        # #    the PV inverter's cut-in (%cutin) and cut-out (%cutout) power thresholds are explicitly set to 0.1% elsewhere in the code.
        # #    This overrides any OpenDSS defaults and allows the inverter to start up and remain active even at very low power outputs
        pv_shape_profile = r"...\code\Loadfiles\PV_curve.txt",        
        # Path for a predefined storage dispatch profile.
        # Note: This feature is not active in the current version; refrain from making any changes.
        storage_shape_profile = "",        
        # Directory path where all simulation results (CSV files, etc.) will be saved.
        output_path = r'...\code\result',
    ),

    # 2.2 --- Time Series Simulation Settings ---
    time_series = SimpleNamespace(
        mode = 'Daily',  # Sets the simulation module. 'Daily' runs a 24-hour time-series analysis.
        number = 96,     # 24 hours * (60min / 15min_interval) = 96 steps.
        stepsize = '15m',# Defines the time interval for each simulation step (e.g., '15m' for 15 minutes).
        load_loadshape_name = 'FileBasedLoadProfile',       # The internal name used within OpenDSS to identify the load shape profile.
        pv_loadshape_name = 'FileBasedPVProfile',           # The internal name used within OpenDSS to identify the PV generation profile.
        storage_loadshape_name = 'FileBasedStorageProfile', # The internal name used within OpenDSS to identify the storage dispatch profile.      
    ),

    # 2.3 --- OpenDSS Component Definitions ---
    dss_elements = SimpleNamespace(
        # Specifies the terminal of the element for measurements
        ElementInfo = SimpleNamespace(      
            meter_name = 'parent_meter',    # Name of the upstream EnergyMeter used as a reference for system-wide measurements.
            element_type = 'line',          # Type of the target element. This accepts 'line' or 'transformer'
            element_name = '650632',        # This is the name of the line or transformer
            terminal_point = 1 ,            # Specifies the terminal of the element for measurements
        ),
        # Enter the detailed information of pv to be connected, if not leave it blank
        PVInfo = SimpleNamespace(
            pv_namess     = ['PvOne'],        # list of Solar PV name  #if name is empty then device would not be connected and all other parameters are ignored
            pv_bus1_nums     = [671],         # List of Buses to connect PV to
            pv_nodess        = [[1,2,3]],     # List of node lists for each PV system；The default connection for this version is 3-phase
            pv_phasess       = [3],           # List of phase counts for each PV system (3 for 3-phase).
            pv_bus_kvss   = [4.16],           # List of bus voltages in kV for PV system.                      
            pv_pmpp_kwss  = [1666],         # List of rated active power KW dispatch of Solar PV (peak rated active power from PV);In this version, it is determined by the real-time pv rated active power in `class UserSettings`.
            # --- PV control begin---
            pv_pf_ss = [0.97], # If set to None or 0, fixed kvar mode is used.
            # The value of pv_pf_ss has higher priority. As long as it is not None or 0,
            # the program uses it to set the power factor and ignores pv_kvarss.
            # Otherwise, pv_kvarss will be used.
            pv_kvar_goals_ss = [765],       # Desired reactive power target; This parameter is only used when pv_pf_ss is None.
            # --- PV control end---
            pv_irad_valss    = [1],           # List of PV irradiance (0-1)
            pv_model_codess  = [1],           # List of PV model code,see opendss help
            pv_conn_valss   = ['wye'],        # Enter 'wye' or 'delta' (default should be 'wye')
            pv_daily_shape_valss  = ['snap'], # If snap, the code disregards daily or yearly loadshape. Unless you edit the load shape name
            pv_yearly_shape_valss = ['snap'], # If snap, the code disregards daily or yearly loadshape. Unless you edit the load shape name;This function is not enabled.
        ), 
        #Get Details for Storage to Add        
        StorageInfo = SimpleNamespace(
            # storage_namess = [],
            storage_namess = ['Sto1'],        # list of Storage name  #if name is empty then device would not be connected and all other parameters are ignored
            store_bus1_numss = [671],         # List of Buses to connect
            store_nodess = [[1,2,3]],         # List of node lists for each Storage system
            store_phasess = [3],              # List of phase counts for each PV system (3 for 3-phase).             
            store_bus_kvss = [4.16],          # List of bus voltages in kV for Storage system. 
            inverter_kvass = [1700],          # Storage inverter's apparent power (kVA)
            storage_kwratedss = [1000],       # List of rated active power KW dispatch;In this version, it is determined by the real-time BESS rated active power in `class UserSettings`.
            storage_kvarss = [0],             # List of reactive power dispatch KVAR;
            storage_kwhratedss =[4000],       # List of KWh Energy of Storage; In this version, it is determined by `storage_duration` and the BESS's rated active power in `class UserSettings`.
            pct_energy_availabless = [60],    # Fixed initial SOC = 60% in this version (feature will be enabled in future versions)
            pct_min_reserve_reqss = [20],     # % of minimum battery reserve in percentage
            storage_statess = ['IDLING'],     # Choose 'CHARGING' or DISCHARGING'
            sto_IdlingkWss = [0.1],           # Percentage of rated kW consumed by idling losses. Default = 1.
            sto_model_codess = [1],           # Model code, 1 for constant power
            sto_connss = ['wye'],             # Enter 'wye' or 'delta' 
            daily_shape_sto_valss=['snap'],   #if snap, the code disregards daily or yearly loadshape. Unless you edit the shape name
            yearly_shape_sto_valss = ['snap'],#if snap, the code disregards daily or yearly loadshape. Unless you edit the shape name;This function is not enabled.
        ),  
        # Other elements like ScaleLoadInfo, GeneratorInfo, TransformerInfo, and NewLineInfo are currently disabled in this version.        
    ),
    
    # 2.4 --- Grid Constraints and Other Settings ---
    grid_limits = SimpleNamespace(
        loading_limit = 100, # Thermal limit for transformers and lines (%).
        low_limit = 0.95,    # Voltage lower limit (p.u.).
        high_limit = 1.05,   # Voltage upper limit (p.u.).
    )
)
```

---

## 4. How to Run

Download `main20250812.py`, `PVSizer_DssBasicFunctions.py`, `PVSizer_DssPowerFlowFunctions.py`, `control.py`, `plotting.py`, and `plotting_sizing.py`.

To run the tool, simply execute the main20250812.py file from your command line or IDE:

```bash
python main20250812.py
```
The program will automatically perform the analysis based on the run_mode set in UserSettings.

---

## 5. Result Analysis

All results, including plots and CSV data, are saved to the directory specified in `Config.files.output_path`.

### 5.1 single_run Module Results

**Detailed Time-Series Plots (PNG):** Ten figures provide a comprehensive comparison between the "Original Case" (without DER) and the "With DER Case" (where PV and BESS are connected at the tie-in points):

1. **Bus Node Voltage Time Series Comparison**  
   Displays the voltage variation (typically in per-unit, p.u.) for all bus nodes over a 24-hour period. Both the original case and the DER case are plotted together for direct comparison.

2. **Element Loading Time Series Comparison**  
   Shows the loading percentage (actual power flow as a percentage of rated capacity) for key equipment such as transformers and lines over a 24-hour period.

3. **Total Power from Grid and System Losses**  
   Contains two key curves: one represents the total active/reactive power drawn from the main grid (substation), and the other represents the total system network losses.

4. **Component Power Analysis and Storage SOC**  
   A composite plot displaying the power output of the PV system, the load power, and the State of Charge (SOC) of the storage system.

5. **Load Active Power Comparison**  
   Compares the total system load's active power curves between the Original Case and the With DER Case.

6. **Load Reactive Power Comparison**  
   Compares the total system load's reactive power curves between the Original Case and the With DER Case.

7. **Measured Active Power of All Components**  
   Displays the active power flows of PV, BESS and Load on a single graph. Power sourced from the grid and generators is typically positive, while consumed power is negative.

8. **Measured Reactive Power of All Components**  
   Displays the reactive power flows of Capacitor, PV, BESS and Load on a single graph. Power sourced from the grid and generators is typically positive, while consumed power is negative.

9. **Active Power Balance Verification**  
   Calculates and shows the difference between total power generation from all sources and total power consumption (Load + Losses) at each time step.

10. **Reactive Power Balance Verification**  
    Calculates and shows the difference between total reactive power generation and total reactive power consumption (Load + Losses) at each time step.


**CSV File:**

- `results_*.csv`: Contains all the raw data used to generate the plots, enabling further custom analysis.

### 5.2 traversal Module Results

**Feasibility Maps (PNG):**

- **PVSizer Feasibility Domain Map:** A scatter plot showing successful (green circles) and failed (red crosses) PV/battery capacity combinations. It plots the feasibility frontier and highlights the final optimized point.
- **PVSizer Constraint Diagnostic Map:** A more detailed scatter plot that uses different colors and markers to categorize specific infeasible reasons (e.g., "Voltage Violation," "Loading Violation," "Convergence Failure").

**CSV Files:**

- `sizing_results_list_*.csv`: A list of all simulation combinations, including PV/battery capacities, status, and infeasible reasons.
- `sizing_results_status_code_matrix_*.csv`: A matrix where pv_kw and battery_kw are indices, and the cell value is the status code (1 for feasible, 0 for infeasible).
- `sizing_results_reason_matrix_*.csv`: A similar matrix, with cell values containing the specific infeasible reason string.

### 5.3 optimization Module Results

**Optimization Path Plot (PNG):**

- **PVSizer Hill-Climbing Optimization Process:** Visualizes the algorithm's search path, marking feasible and infeasible iterations and the final optimal point.

**Detailed Time-Series Results:** After finding the optimal point, the program automatically runs a detailed simulation and generates the full set of `single_run` results for that optimal configuration.

---

## 6. Code Architecture and Future Outlook

**Module Design:** The tool is separated into multiple modules, with each file serving a specific purpose:

- `PVSizer_DssBasicFunctions.py`: Handles fundamental OpenDSS interactions and element creation.
- `PVSizer_DssPowerFlowFunctions.py`: Contains advanced simulation logic, such as running time-series power flow and checking for violations.
- `control.py`: Defines the battery control strategies, making it easy to add or switch new control modes.
- `plotting.py` and `plotting_sizing.py`: Dedicated to result visualization for single runs and sizing analyses, respectively.

**Extensibility:** The current architecture provides a solid foundation for future features, as originally intended. New functionalities, like advanced reactive power control, siting optimization, and different control modes, can be integrated by adding logic to the relevant modules without needing to restructure the entire codebase.

---

## 7. Project Funding

This work was supported by the **U.S. Department of Energy (DOE)** under the project:**An Equitable, Affordable & Resilient Nationwide Energy System Transition (EARNEST)**  

**Collaborating Institutions and Organizations**: **Stanford University**, Argonne National Lab (ANL), Pacific Northwest National Laboratory (PNNL), Lawrence Livermore National Laboratory (LLNL), Electric Power Research Institute, NRECA, Iowa State University, Massachusetts Institute of Technology, North Carolina Agriculture and Technical State University, Northwest Indian College, Princeton University, Tec de Monterrey (Mexico), University of Alaska Fairbanks, University of Calgary (Canada), University of California San Diego, University of Hawaii at Manoa, University of Michigan, University of Tennessee, University of Texas, University of Waterloo (Canada), and Washington State University. 

<p align="center">
  <img src="./logo/Participants.jpg" alt="Participants Logo" width="650">
</p>


---

## 8. Author information

**Yilu Liu**<br>
IEEE Life Fellow, Governor’s Chair<br>
University of Tennessee, Knoxville<br>
Oak Ridge National Laboratory, USA  

**Yayu (Andy) Yang**<br>
Postdoctoral Researcher/Research Specialist<br>
Department of Electrical Engineering and Computer Science<br>
Center for Ultra-Wide-Area Resilient Energy Transmission Network(CURENT)<br>
University of Tennessee, Knoxville<br>
📎 LinkedIn: [Yayu(Andy) Yang](https://www.linkedin.com/in/yayu-andy-yang-279991117/)📚 Google Scholar: [Profile](https://scholar.google.com/citations?user=ZJegz88AAAAJ)✉️ Email: yyang117@utk.edu

**Samuel Okhuegbe**<br>
PhD Student, Energy Science and Engineering<br>
Bredesen Center for Interdisciplinary Research and Graduate Education<br>
Center for Ultra-Wide-Area Resilient Energy Transmission Network (CURENT)<br>
University of Tennessee, Knoxville

**Jian Zhang**<br> 
Research Associate<br>
Department of Electrical Engineering and Computer Science  <br>
University of Tennessee, Knoxville

[Power Information Technology Laboratory](https://powerit.utk.edu/index.html)

