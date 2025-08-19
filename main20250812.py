# -*- coding: utf-8 -*-
"""
Created on Thu August 6 15:03:16 2025
Functions:
- Mode 1 (SINGLE_RUN): Perform a detailed 24-hour simulation for a single specified configuration    
- Mode 2 (TRAVERSAL): Globally traverse combinations of PV, energy storage, and SOC to plot the feasible region map (original bianliSIN)
- Mode 3 (OPTIMIZATION): Use hill-climbing algorithm to find the maximum PV and minimum energy storage that satisfy constraints (original mountainclimbing)

@author: Yayu(Andy) Yang(yyang117@utk.edu；www.linkedin.com/in/yayu-andy-yang-279991117); Samuel Okhuegbe;
"""

import numpy as np
import pandas as pd  # 
import matplotlib.pyplot as plt
import re
import opendssdirect as dss   
import math
import os
import cmath
import time  
import multiprocessing 

from itertools import product 
from types import SimpleNamespace
from IBRNetGridSize_DssPowerFlowFunctions import run_grid_connected_impact_analysis_SIMPLE, parse_stepsize_to_hours
from IBRNetGridSize_DssBasicFunctions import * 
from control import *
from plotting import *
from plotting_sizing import *

#%% ======================== 1. User Main Control Panel=======================
class UserSettings:
    """
    Configure the operating mode and all related parameters here.
    """
    # 1.1 --- Operating Mode Selection ---
    # Options: 'traversal', 'optimization', 'single_run'
    # 'single_run':   single case detailed simulation with fixed PV and battery sizes
    # 'traversal':    Global traversal analysis (Map Drawer)
    # 'optimization': Hill-climbing optimization (Climber)
    # run_mode = 'single_run'  # <--- Switch to desired mode here    
    # run_mode = 'traversal'   # <--- Switch to desired mode here
    run_mode = 'optimization'  # <--- Switch to desired mode here
    
    # 1.2 --- Global Component Parameters ---
    storage_duration = 4                             # Ratio of battery capacity (kWh) to rated power (kW).
    chosen_battery_strategy = strategy_self_consumption_present_pv_load    # Multiple battery control strategies are available. See control.py for details.  
    inverter_sizing_factor = 1.7                     # Ratio of storage inverter's apparent power (kVA) to battery's rated active power (kW).

    # 1.3 --- Single-run Mode Parameters (effective only when run_mode = 'single_run') ---
    single_run_pv_kw = 3000.0                      # Specified PV rated active power for a single simulation run.
    single_run_batt_kw = 2000.0                    # Specified battery rated active power for a single simulation run.

    # 1.4 --- Traversal Mode Parameters (effective only when run_mode = 'traversal') ---
    # np.arange(start, stop, step) defines the range. 'stop' is not included in the range.
    traversal_pv_kw_range = np.arange(0, 10001, 200)      # Range of PV rated active power to traverse (kW).
    traversal_battery_kw_range = np.arange(100, 10001, 100) # Range of battery rated active power to traverse (kW).
    # Note: The minimum value of the battery's rated active power range should not be too small or equal to 0, minium should above 100kW. As a very low rated active power may cause numerical instability or convergence failures in the power flow solver.

    # 1.5 --- Optimization Mode Parameters (effective only when run_mode = 'optimization') ---
    optimization_initial_pv_kw = 200.0             # Starting PV rated active power for the optimization search.
    # Note: initial_pv_kw should >or= initial_batt_kw
    optimization_initial_batt_kw = 100.0           # Starting battery rated active power for the optimization search.
    optimization_pv_step = 200.0                   # Step size for increasing PV rated active power.
    optimization_batt_step = 100.0                 # Step size for increasing battery rated active power.
    optimization_max_pv_kw = 10000.0               # Maximum allowed PV rated active power.
    optimization_max_batt_kw = 10000.0             # Maximum allowed battery rated active power.

#%% ======================== 2.User Configuration =================
Config = SimpleNamespace(
    
    # 2.1 ---  File and Path Settings  ---
    files = SimpleNamespace(
        # Path to the master OpenDSS file that defines the power grid topology and components.
        dss_master_file = r'...\code\Loadfiles\IEEE13test.dss',        
        # Path to the load shape file, which defines the load variation over a 24-hour period for time-series analysis.
        load_shape_profile = r"...\code\Loadfiles\load_curve.txt",        
        # Path to the PV generation profile, defining solar power output over a 24-hour period.
        # Note: If PV output is too small (e.g., 0.1 p.u.), the system may fail to start. 
        # Therefore, non-zero values in the PV txt file should exceed the minimum per-unit power required.
        pv_shape_profile = r"...\code\Loadfiles\PV_curve.txt",        
        # Path for a predefined storage dispatch profile.
        # Note: This feature is not active in the current version; refrain from making any changes.
        storage_shape_profile = "",        
        # Directory path where all simulation results (CSV files, etc.) will be saved.
        output_path = r'...\code\result',
    ),

    # 2.2 --- Time Series Simulation Settings ---
    time_series = SimpleNamespace(
        mode = 'Daily',  # Sets the simulation mode. 'Daily' runs a 24-hour time-series analysis.
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
            pv_pmpp_kwss  = [1666*1],         # List of rated active power KW dispatch of Solar PV (peak rated active power from PV);In this version, it is determined by the real-time pv rated active power in `class UserSettings`.     
            # --- PV control begin---
            pv_pf_ss = [0.97], # If set to None or 0, fixed kvar mode is used.
            # The value of pv_pf_ss has higher priority. As long as it is not None or 0,
            # the program uses it to set the power factor and ignores pv_kvarss.
            # Otherwise, pv_kvarss will be used.
            pv_kvar_goals_ss = [765*1],       # Desired reactive power target; This parameter is only used when pv_pf_ss is None.
            # --- PV control end---
            pv_irad_valss    = [1],           # List of PV irradiance (0-1)
            pv_model_codess  = [1],           # List of PV model code,see opendss help
            pv_conn_valss   = ['wye'],        # Enter 'wye' or 'delta' (default should be 'wye')
            pv_daily_shape_valss  = ['snap'], # If snap, the code disregards daily or yearly loadshape. Unless you edit the shape name
            pv_yearly_shape_valss = ['snap'], # If snap, the code disregards daily or yearly loadshape. Unless you edit the shape name;This function is not enabled.
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
        #ScaleLoadInfo is not enabled in this version (feature will be enabled in future versions) 
        #Option to uniofromly scale all loads in the OpenDSS Case
        ScaleLoadInfo = SimpleNamespace(
            scale_load_uniform = 0 ,#0 means no scaling is done, this means scaling is ignored WHILE 1 means scaling is performed. 
            Load_scaling_percent_kw = 0,#Percentage active power increase or decrease. Leave as empty if you do not want to scale with %
            Load_scaling_percent_kvar = [],#Percentage reactive power increase or decrease. Leave as empty if you do not want to scale with %
            new_total_load_kw = 0,#Value of total new load active power
            new_total_load_kvar = 0,#Value of total new load reactive power
            maintain_p_q_ratio_flag = 1,# 1 means maintain the same active to reactive power load ratio as inoriginal case WHILE 0 means ignore
            use_actual_total_loads_to_scale = 1,# 1 means the new_total_loads to scale, WHILE 0 means scale using perecent (Load_scaling_percent)
        ),      
        # GeneratorInfo is not enabled in this version (feature will be enabled in future versions)       
        GeneratorInfo = SimpleNamespace(
            gen_names = [] ,#list of genertor names as a strings, #if name is empty then device would not be connected and all other parameters are ignored
            gen_bus1_nums = [] ,#list of bus numbers
            gen_nodess    = [[],[]] ,#list of list of the nodes for each bus e.g for three buses [[1,2,3],[1,3], [2]]
            gen_phasess   = [] ,#list containing the phases of each generator
            gen_bus_kvs   = [] ,#list containing the KVs of the generator
            gen_kvas  = [] ,#list of KVA of generator
            gen_kws   = [] ,#list of Gen KW
            gen_kvars = [] ,#list of Gen KVARS
            gen_model_codes = [] ,#List Generator model (Use 1 for constant powe, 2 for contant admittance, 3 for constant KW, constant KV like PV bus in normal transmission powerflow)
            gen_connss = ['wye','wye'] ,#enter 'wye' or 'delta' (default should be 'wye')
            daily_shape_gen_valss  = ['snap','snap'] ,#if snap, the code disregards daily or yearly loadshape. Unless you edit the load shape name
            yearly_shape_gen_valss = ['snap','snap'] ,#if snap, the code disregards daily or yearly loadshape. Unless you edit the load shape name
        ),
        # InverterControlInfo is not enabled in this version (feature will be enabled in future versions)
        InverterControlInfo = SimpleNamespace(
            inv_ctrl_namess = [] ,#Name of Inverter Control if any
            DER_typess = [[],[]] ,#List of list #use 'PVsystem' for solar and 'Storage' for storage/battery
            DER_namess = [[],[]] ,#List of list
            inv_modes = [] ,#Control Mode 'GFM', Must be one of: {VOLTVAR* | VOLTWATT | DYNAMICREACCURR | WATTPF | WATTVAR | GFM}
        ),
        # TransformerInfo is not enabled in this version (feature will be enabled in future versions)
        TransformerInfo = SimpleNamespace(
            tnx_namess          = [] ,# List of Transformer Names if name is empty then device would not be connected.
            tnx_phasess         = [3,1] ,#list of Number of Phases
            tnx_windingss       = [2,2]  ,# List Number of windings
            tnx_nodess          = [[1,2,3],[2]] ,#List of nodes to connect to
            tnx_kva1ss          = [1000,1000] ,#List of Transformer KVA
            tnx_bus1_numss      = ['StoBus1','StoBus2'] ,#List of primary bus
            tnx_kv1ss           = [0.48,0.48] ,# List of Primary KV
            tnx_conn1ss         = ['delta','delta'] ,#List of Primary connectoion
            tnx_kva2ss          = [1000,1000] ,#list of secondary kva
            tnx_bus2_numss      = [675,646] ,#list of secondary buses
            tnx_kv2ss           = [4.16,2.4] ,#list of secondary voltages
            tnx_conn2ss         = ['wye','wye'] ,#list of secondary connection types
            tnx_taps1ss         = [1,1] ,#list of number of taps in primary
            tnx_taps2ss         = [1,1] ,#list of number of taps in secondary
            tnx_XHLss           = [0.5,0.5] ,#Winding reactance
        ),
        # NewLineInfo is not enabled in this version (feature will be enabled in future versions)             
        NewLineInfo = SimpleNamespace(
            line_code_namess = [] ,#name of linecode
            line_unitss = [] ,#km or ft
            line_phasess = [] ,#List of phases
            line_rmatrixss = [(),()] ,#takes a tuple separated by |
            line_xmatrixss = [(),()] ,#takes a tuple separated by |
            line_normampss = [] ,#list of normal current rating of line
            line_emergampss = []  ,#list of emergency current rating of line
            connect_line_namess = [] ,#List of Line names
            connect_line_unitss = [] ,#List of line units 'km' or 'ft'
            connect_line_lengthss = [] ,#List of Line length
            connect_line_nodess = [] ,#List of nodes
            connect_line_bus1_numss = [] ,#List of first bus to connect line to
            connect_line_bus2_numss = [] ,#List of second bus to connect line to
            connect_line_phasess = [] ,#List of line phases
            connect_line_codess = [] ,#list of #name of line code
        )
    ),
    
    # 2.4 ---Grid Constraints and Other Settings---
    grid_limits = SimpleNamespace(
        loading_limit = 100, #Thermal limit for both transformers and lines
        low_limit = 0.95, #voltage low limit in pu
        high_limit = 1.05, #voltage high limit in pu
    )

)

# 2.5 --- Dynamically add attributes dependent on other Config values ---
Config.dss_elements.PVInfo.pv_daily_shape_valss = [Config.time_series.pv_loadshape_name if Config.time_series.mode == 'Daily' else 'snap']
Config.dss_elements.StorageInfo.daily_shape_sto_valss = ['snap'] # Fixed in this version (feature will be enabled in future versions)


#%% ======================== 3. Define single simulation task function ==================
def _find_invalids_in_iterable(iterable_of_data):
    for item in iterable_of_data:
        if isinstance(item, (tuple, list)):
            if np.any(np.isnan(item)) or np.any(np.isinf(item)):
                return True  
        elif np.isnan(item) or np.isinf(item):
            return True
    return False 


def evaluate_simulation_results_unified(results_der, initial_soc, pv_kw, batt_kw):
    """
    A unified evaluation function to determine success or failure.
    """
    failure_reasons = []
    has_invalids = False
    
    power_dicts_to_check = ['pv_actual_powers', 'storage_powers', 'load_powers']
    for attr in power_dicts_to_check:
        if hasattr(results_der, attr):
            power_dict = getattr(results_der, attr)
            for power_list_of_tuples in power_dict.values():
                if _find_invalids_in_iterable(power_list_of_tuples):
                    has_invalids = True
                    break
        if has_invalids:
            break
            
    if not has_invalids and hasattr(results_der, 'Total_Power'):
        if _find_invalids_in_iterable(results_der.Total_Power):
            has_invalids = True
    
    if not has_invalids and hasattr(results_der, 'storage_soc'):
        for soc_list in results_der.storage_soc.values():
            if _find_invalids_in_iterable(soc_list):
                has_invalids = True
                break
        
    if has_invalids:
        failure_reasons.append("Invalid Data")
        
    if not all(results_der.converged):
        failure_reasons.append("Convergence Failure")
    if any(v for v in results_der.Violations.voltage.values()):
        failure_reasons.append("Voltage Violation")
    if any(v for v in results_der.Violations.loading.values()):
        failure_reasons.append("Loading Violation")

    # Battery Sizing Checks
    if hasattr(results_der, 'storage_soc') and results_der.storage_soc:
        storage_name = list(results_der.storage_soc.keys())[0]
        soc_series = results_der.storage_soc[storage_name]
        valid_socs = [s for s in reversed(soc_series) if not np.isnan(s)]
        if valid_socs:
            final_soc = valid_socs[0]
            if final_soc > 60:
                failure_reasons.append("OK But Battery Oversize")
        
        # SOC at 6:45 AM should be greater than minimum SOC; The time point is 6.75 hours (6h + 45min); it can be changed
        check_time_in_hours = 6.75
        total_steps = Config.time_series.number
        morning_check_step_index = int(check_time_in_hours/24 * total_steps)
        if len(soc_series) > morning_check_step_index and not np.isnan(soc_series[morning_check_step_index]):
            soc_at_morning = soc_series[morning_check_step_index]
            min_reserve_soc = Config.dss_elements.StorageInfo.pct_min_reserve_reqss[0]
            if soc_at_morning > min_reserve_soc: #minimum SOC=20
                failure_reasons.append("OK But Battery Oversize")
    if batt_kw > pv_kw:
        failure_reasons.append("OK But Battery Oversize")

    if not failure_reasons:
        status, status_code, reason_str = "Success", 1, "Success"
    else:
        status, status_code, reason_str = "Failure", 0, " & ".join(sorted(list(set(failure_reasons))))
        
    return status, status_code, reason_str       

def run_and_evaluate_one_case(pv_kw, batt_kw, soc):
    """
    (Main execution function – competition and adjudication)This function is called by all modes.
    """
    local_config = Config
    
    # A. Update current iteration Config
    local_config.dss_elements.PVInfo.pv_pmpp_kwss = [pv_kw]
    local_config.dss_elements.StorageInfo.storage_kwratedss = [batt_kw]
    local_config.dss_elements.StorageInfo.storage_kwhratedss = [UserSettings.storage_duration * batt_kw]
    local_config.dss_elements.StorageInfo.inverter_kvass = [UserSettings.inverter_sizing_factor * batt_kw]
    local_config.dss_elements.StorageInfo.pct_energy_availabless = [soc]
    
    # B.  Call simulation engine.     
    results_origin, results_der = run_grid_connected_impact_analysis_SIMPLE(
        local_config,
        battery_strategy_func=UserSettings.chosen_battery_strategy
    )
    
    # C. Call the unified evaluation function to obtain results
    status, status_code, reason_str = evaluate_simulation_results_unified(results_der, soc, pv_kw, batt_kw)
    
    # D. Return a tuple containing all necessary information
    return (results_origin, results_der, status, status_code, reason_str)

def worker_function_for_traversal(params):
    """
    This is the task function designed for the "traversal" mode
    """
    # soc, pv_kw, batt_kw = params
    pv_kw, batt_kw = params
    soc = Config.dss_elements.StorageInfo.pct_energy_availabless[0]
    try:
        _, _, status, status_code, reason_str = run_and_evaluate_one_case(pv_kw, batt_kw, soc)
        
        return {
            "pv_kw": pv_kw, "battery_kw": batt_kw, "initial_soc": soc,
            "status": status, "status_code": status_code, "failure_reason": reason_str
        }
    except Exception as e:
        return {
            "pv_kw": pv_kw, "battery_kw": batt_kw, "initial_soc": soc,
            "status": "Failure", "status_code": 0, "failure_reason": f"Runtime Error: {e}"
        }

#%% ======================== 4. Main Execution Workflow===========================
if __name__ == "__main__":
    # ---  Mode 1: Global Traversal Analysis (Map Drawer) ---
    if UserSettings.run_mode == 'traversal':
        print("--- Mode: Traversal ---")
  
        multiprocessing.freeze_support()
    
        start_time = time.time()
        
        soc = Config.dss_elements.StorageInfo.pct_energy_availabless[0]
        param_combinations = list(product(UserSettings.traversal_pv_kw_range, 
                                          UserSettings.traversal_battery_kw_range))
        
        total_iterations = len(param_combinations)
        print(f"--- Starting Parallel Sizing Analysis ---")
        print(f"Total simulations to run: {total_iterations}")
    
        num_processes = os.cpu_count() - 1 if os.cpu_count() > 1 else 1
        print(f"Using {num_processes} processes for parallel execution...")
        
        with multiprocessing.Pool(processes=num_processes) as pool:
            results_log = pool.map(worker_function_for_traversal, param_combinations)
    
        results_df = pd.DataFrame(results_log)
        
        successful_runs = results_df[results_df['status_code'] == 1]
        if not successful_runs.empty:
            max_pv_kw = successful_runs['pv_kw'].max()
            best_config = successful_runs[
                (successful_runs['pv_kw'] == max_pv_kw)
            ].sort_values(by='battery_kw').iloc[0]
            
            final_pv_kw = best_config['pv_kw']
            final_battery_kw = best_config['battery_kw']
            final_battery_kwh = UserSettings.storage_duration * final_battery_kw
            
            print("\nAnalysis Result from Traversal:")
            print(f"  - Maximum PV capacity: {final_pv_kw:.2f} kW")
            print(f"  - Minimum battery capacity: {final_battery_kw:.2f} kW / {final_battery_kwh:.2f} kWh (Duration = {UserSettings.storage_duration} hours)")
        else:
            print("\nError: No successful simulation found in the traversal search space.")
        
        plot_feasibility_maps(results_df, UserSettings.traversal_pv_kw_range, UserSettings.traversal_battery_kw_range, [soc])
        plot_feasibility_maps_with_reasons(results_df, UserSettings.traversal_pv_kw_range, UserSettings.traversal_battery_kw_range, [soc])
        export_sizing_results_to_csv(results_df, UserSettings.traversal_pv_kw_range, UserSettings.traversal_battery_kw_range, [soc], Config.files.output_path)    

    # --- Mode 2: Hill-Climbing Optimization (Climber) --- 
    #
    elif UserSettings.run_mode == 'optimization':
        print("--- Mode: Optimization (Hill Climbing) ---")    
                
        current_battery_kw = UserSettings.optimization_initial_batt_kw
        current_pv_kw = UserSettings.optimization_initial_pv_kw      
                
        last_successful_pv_kw = 0
        last_successful_battery_kw = 0
        last_successful_battery_kwh = 0
        
        optimization_path = []
        iteration_count = 0
        soc = Config.dss_elements.StorageInfo.pct_energy_availabless[0]
       
        while current_battery_kw <= UserSettings.optimization_max_batt_kw and current_pv_kw <= UserSettings.optimization_max_pv_kw:
            iteration_count += 1

            _, _, status, _, failure_reason = run_and_evaluate_one_case(current_pv_kw, current_battery_kw, soc)
            
            simulation_ok = (status == "Success")
            optimization_path.append({'battery_kw': current_battery_kw, 'pv_kw': current_pv_kw, 'success': simulation_ok})
                       
            if simulation_ok:               
                last_successful_pv_kw = current_pv_kw
                last_successful_battery_kw = current_battery_kw
                last_successful_battery_kwh = UserSettings.storage_duration * last_successful_battery_kw

                current_pv_kw += UserSettings.optimization_pv_step
                
            else:
                current_battery_kw += UserSettings.optimization_batt_step
        
        print("\n--- Optimization Complete ---")

        if optimization_path:
             generate_optimization_plot(Config, optimization_path, last_successful_pv_kw, last_successful_battery_kw)


        if last_successful_pv_kw > 0:
            print("Optimization Result:")
            print(f"  - Maximum PV capacity: {last_successful_pv_kw:.2f} kW")
            print(f"  - Minimum battery capacity: {last_successful_battery_kw:.2f} kW / {last_successful_battery_kwh:.2f} kWh (Duration = {UserSettings.storage_duration} hours)")
            
            Config.dss_elements.PVInfo.pv_pmpp_kwss = [last_successful_pv_kw]
            Config.dss_elements.StorageInfo.storage_kwratedss = [last_successful_battery_kw]
            Config.dss_elements.StorageInfo.storage_kwhratedss = [last_successful_battery_kwh]
            
            final_results_origin, final_results_der, status, _, reason = run_and_evaluate_one_case(
                last_successful_pv_kw,
                last_successful_battery_kw,
                soc
            )
            
            generate_all_plots(Config, final_results_origin, final_results_der)
            export_results_to_csv(Config, final_results_origin, final_results_der)
            

        else:
            print("Error: No successful simulation found in the optimization search space.")   

    # --- Mode 3: Single Detailed Simulation ---
    elif UserSettings.run_mode == 'single_run':
        print("--- Mode: Single Detailed Simulation ---")
        soc = Config.dss_elements.StorageInfo.pct_energy_availabless[0]
        
        results_origin, results_der, status, _, reason = run_and_evaluate_one_case(
            UserSettings.single_run_pv_kw, 
            UserSettings.single_run_batt_kw, 
            soc
        )

        print(f"Overall Status: {status}")
        if status == "Failure":
            print(f"Failure Reasons: {reason}")
        print("--------------------------------")

        print("\n--- Simulation Finished: Convergence Report ---")
        if all(results_origin.converged):
            print("Original Case: All simulation steps converged successfully.")
        else:
            failed_steps = [i + 1 for i, c in enumerate(results_origin.converged) if not c]
            print(f"Original Case: CONVERGENCE FAILED at steps: {failed_steps}")
        
        if all(results_der.converged):
            print("DER Case: All simulation steps converged successfully.")
        else:
            failed_steps = [i + 1 for i, c in enumerate(results_der.converged) if not c]
            print(f"DER Case: CONVERGENCE FAILED at steps: {failed_steps}")
            
        generate_all_plots(Config, results_origin, results_der)
        export_results_to_csv(Config, results_origin, results_der)

        print(f"Results have been saved to: {Config.files.output_path}")
        print("\n--- Process Complete ---")