# -*- coding: utf-8 -*-
"""
Created on Thu August 6 15:03:16 2025
Functions:
- Mode 1 (SINGLE_RUN): Perform a detailed 24-hour simulation for a single specified configuration    
- Mode 2 (TRAVERSAL): Globally traverse combinations of PV, energy storage, and SOC to plot the feasible region map (original bianliSIN)
- Mode 3 (OPTIMIZATION): Use hill-climbing algorithm to find the maximum PV and minimum energy storage that satisfy constraints (original mountainclimbing)

@author: Yayu(Andy) Yang; Samuel Okhuegbe;
"""

import numpy as np
import re
import opendssdirect as dss
from types import SimpleNamespace
import os
from IBRNetGridSize_DssBasicFunctions import *

#%% 
def _preprocess_pv_settings(config):
    """
    Preprocessing and automatic calculation for PV configuration
    """
    pv_info = config.dss_elements.PVInfo
    if not hasattr(pv_info, 'pv_namess') or not pv_info.pv_namess:
        print("--- Pre-processing PV: No PV systems defined in 'pv_namess'. Skipping PV setup. ---")
        return config    
    if not hasattr(pv_info, 'pv_pmpp_kwss') or not pv_info.pv_pmpp_kwss:
        return config
    pv_info.pv_kvass = []
    pv_info.pv_kvarss = []

    for i, p_rated in enumerate(pv_info.pv_pmpp_kwss):
        # S_rated = 1.1 * P_rated 
        s_rated = 1.1 * p_rated#
        pv_info.pv_kvass.append(s_rated)
        
        # Q_max = sqrt(S_rated^2 - P_rated^2) ≈ 0.458 * P_rated。                
        q_max = math.sqrt(s_rated**2 - p_rated**2)
        
        q_goal = pv_info.pv_kvar_goals_ss[i] if hasattr(pv_info, 'pv_kvar_goals_ss') and i < len(pv_info.pv_kvar_goals_ss) else 0
        
        q_final = np.clip(q_goal, -q_max, q_max)
        pv_info.pv_kvarss.append(q_final)
       
    return config

def parse_stepsize_to_hours(stepsize_str):
    step_value_match = re.findall(r'\d+\.?\d*', stepsize_str)
    step_value = float(step_value_match[0]) if step_value_match else 0
    step_unit_match = re.findall(r'[a-zA-Z]+', stepsize_str)
    step_unit = step_unit_match[0].lower() if step_unit_match else ""

    if step_unit == 'h': return step_value
    elif step_unit == 'm': return step_value / 60.0
    elif step_unit == 's': return step_value / 3600.0
    else: return 1
    

def annouce_violations_timeseries(Violations_obj, mode, low_limit, high_limit, loading_limit, stepsize_str='1h'):
    """Voltage and component overload violations, with timestamps of occurrences."""
    step_in_hours = parse_stepsize_to_hours(stepsize_str)
    print("--- Voltage Violation Summary ---")
    any_voltage_violation = False
    for bus_name, violations_list in Violations_obj.voltage.items():
        if violations_list:
            any_voltage_violation = True
            print(f"Bus {bus_name}:")
            summary = {}
            for step, voltage in violations_list:
                status = "High" if voltage > high_limit else "Low"
                if status not in summary:
                    summary[status] = {'count': 0, 'worst_val': voltage, 'worst_step': step}
                summary[status]['count'] += 1
                if (status == "High" and voltage > summary[status]['worst_val']) or \
                   (status == "Low" and voltage < summary[status]['worst_val']):
                    summary[status]['worst_val'] = voltage
                    summary[status]['worst_step'] = step
            for status, data in summary.items():
                worst_time_val = data['worst_step'] * step_in_hours
                print(f"  {status} Voltage: {data['count']} occurrences. Worst at step {data['worst_step']+1} (Time: {worst_time_val:.2f}h): {data['worst_val']:.3f} pu")
    if not any_voltage_violation:
        print("No voltage violations.")

    print("\n--- Element Overload Summary ---")
    any_loading_violation = False
    for element_name, violations_list in Violations_obj.loading.items():
        if violations_list:
            any_loading_violation = True
            print(f"Element {element_name}:")
            worst_step, worst_loading = max(violations_list, key=lambda item: item[1])
            worst_time_hours = worst_step * step_in_hours
            print(f"  Overloaded in {len(violations_list)} steps. Max loading at step {worst_step+1} (Time: {worst_time_hours:.2f}h): {worst_loading:.2f}% (Limit: {loading_limit}%)")
    if not any_loading_violation:
        print(f"No element overloads (Loading > {loading_limit}%).")

#%% --- Internal helper functions ---

def _initialize_results(mode, bus_names, element_names, load_names, pv_names, storage_names, capacitor_names):
    """# Initialize all required result storage structures"""
    results = SimpleNamespace(
        mode=mode, converged=[], Total_Power=[], Total_Losses=[],
        Bus_Names_Sorted_By_Distance=list(bus_names),
        Bus_Vol_PU_LN={}, Element_Loadings_Pct={},
        Violations=SimpleNamespace(voltage={}, loading={}),
        load_powers={}, pv_actual_powers={}, storage_powers={}, capacitor_powers={},
        storage_soc={}
    )

    for bus in bus_names:
        results.Bus_Vol_PU_LN[bus.lower()] = []
        results.Violations.voltage[bus.lower()] = []

    for el in element_names:
        results.Element_Loadings_Pct[el] = []
        results.Violations.loading[el] = []

    for item in load_names: results.load_powers[item] = []
    for item in pv_names: results.pv_actual_powers[item] = []
    for item in storage_names: 
        results.storage_powers[item] = []
        results.storage_soc[item] = [] 
    for item in capacitor_names: results.capacitor_powers[item] = []
    
    return results

def _collect_step_data(results, config, step, dss):
    """
    collect step data
    """
    limits_cfg = config.grid_limits

    for name in results.pv_actual_powers.keys():
        dss.PVsystems.Name(name)
        powers = dss.CktElement.Powers()
        p_kw = -sum(powers[0::2])
        q_kvar = -sum(powers[1::2])
        results.pv_actual_powers[name].append((p_kw, q_kvar))

    results.Total_Power.append(dss.Circuit.TotalPower())
    results.Total_Losses.append(np.array(dss.Circuit.Losses()) * 1e-3)

    all_bus_names_map = {name.lower(): mag for name, mag in zip(dss.Circuit.AllBusNames(), dss.Circuit.AllBusMagPu())}

    for bus_name in results.Bus_Names_Sorted_By_Distance:
        bus_key = bus_name.lower()

        voltage_pu = all_bus_names_map.get(bus_key, np.nan)
        
        results.Bus_Vol_PU_LN[bus_key].append(voltage_pu)
        if not np.isnan(voltage_pu) and (voltage_pu < limits_cfg.low_limit or voltage_pu > limits_cfg.high_limit):
            results.Violations.voltage[bus_key].append((step, voltage_pu))

    el_load_map = {name.lower(): load for name, load in zip(dss.PDElements.AllNames(), dss.PDElements.AllPctNorm(AllNodes=False))}
    for el_name in results.Element_Loadings_Pct.keys():
        loading = el_load_map.get(el_name.lower(), np.nan)
        results.Element_Loadings_Pct[el_name].append(loading)
        if not np.isnan(loading) and loading > limits_cfg.loading_limit:
            results.Violations.loading[el_name].append((step, loading))

    for name in results.load_powers.keys():
        dss.Loads.Name(name)
        powers = dss.CktElement.Powers()
        p_kw = -sum(powers[0::2]) 
        q_kvar = -sum(powers[1::2]) 
        results.load_powers[name].append((p_kw, q_kvar))

    for name in results.storage_powers.keys():
        dss.Storages.Name(name)
        powers = dss.CktElement.Powers()
        p_kw = -sum(powers[0::2])
        q_kvar = -sum(powers[1::2])
        results.storage_powers[name].append((p_kw, q_kvar))

    for name in results.capacitor_powers.keys():
        dss.Capacitors.Name(name)
        powers = dss.CktElement.Powers()
        p_kw = -sum(powers[0::2])
        q_kvar = -sum(powers[1::2])
        results.capacitor_powers[name].append((p_kw, q_kvar))

    for name in results.storage_soc.keys():
        dss.Storages.Name(name)
        soc_percent = float(dss.Properties.Value('%stored'))
        results.storage_soc[name].append(soc_percent)

#%%Private function
def _handle_non_converged_step(results):
    """
    handle non-convergence by filling NaN placeholders in all time-series data lists
    """
    results.Total_Power.append((np.nan, np.nan))
    results.Total_Losses.append((np.nan, np.nan))

    for bus_name in results.Bus_Names_Sorted_By_Distance:
        results.Bus_Vol_PU_LN[bus_name.lower()].append(np.nan)

    for el_name in results.Element_Loadings_Pct.keys():
        results.Element_Loadings_Pct[el_name].append(np.nan)

    for sto_name in results.storage_soc.keys():
        results.storage_soc[sto_name].append(np.nan)

    for name in results.load_powers.keys(): 
        results.load_powers[name].append((np.nan, np.nan))
    for name in results.pv_actual_powers.keys(): 
        results.pv_actual_powers[name].append((np.nan, np.nan))
    for name in results.storage_powers.keys(): 
        results.storage_powers[name].append((np.nan, np.nan))
    for name in results.capacitor_powers.keys(): 
        results.capacitor_powers[name].append((np.nan, np.nan))


def _run_timeseries_case(config, battery_strategy_func=None):
    """Run a complete 24-hour time-series simulation"""
    time_cfg = config.time_series
    
    bus_names, _ = get_sorted_bus_names_to_meter()
    element_names = dss.PDElements.AllNames()

    load_names = dss.Loads.AllNames()
    pv_names = dss.PVsystems.AllNames()
    storage_names = dss.Storages.AllNames()
    capacitor_names = dss.Capacitors.AllNames()      
    
    results = _initialize_results(time_cfg.mode, bus_names, element_names, load_names, pv_names, storage_names, capacitor_names)

    dss.Text.Command(f'Set mode={time_cfg.mode} stepsize={time_cfg.stepsize} number=1')

    for step in range(time_cfg.number):
        if battery_strategy_func:
            battery_strategy_func(dss, config, step, results)

        dss.Text.Command('Solve')  
            
        converged = dss.Solution.Converged()
        results.converged.append(converged)

        if converged:
            _collect_step_data(results, config, step, dss)
        else:
            _handle_non_converged_step(results)
            print(f"Warning: Convergence failed at step {step + 1}")    
    
    return results

    
def _add_der_to_circuit(config):
    """Adding DER devices defined in Config to the grid"""
    pv_info = config.dss_elements.PVInfo
    storage_info = config.dss_elements.StorageInfo
    
    if not hasattr(pv_info, 'pv_daily_shape_valss'):
        pv_info.pv_daily_shape_valss = [config.time_series.pv_loadshape_name] 

    if pv_info.pv_namess:
        Connect_Multiple_PVsystems(**pv_info.__dict__)
    if storage_info.storage_namess:
        Connect_Multiple_Storage(**storage_info.__dict__)

#%% -Public Interface ---

def run_grid_connected_impact_analysis_SIMPLE(config, battery_strategy_func):

    config = _preprocess_pv_settings(config)
    
    print("--- 1. Analyzing Original Case ---")
    dss.Text.Command("clear")
    dss.Text.Command(f'Compile "{config.files.dss_master_file}"')


    dss.Text.Command('Set MaxIter=100')

    add_an_energy_meter(**config.dss_elements.ElementInfo.__dict__)
    
    create_loadshape(
        config.time_series.load_loadshape_name,
        config.time_series.number,
        config.files.load_shape_profile,  # Pmult_val (as file path)
        None,                             # Qmult_val
        None,                             # Mult_val
        'interval',                       # time_interval_code
        parse_stepsize_to_hours(config.time_series.stepsize), # interval_val
        1                                 # use_file_flag
    )
    scale_all_loads_uniformly_timeseres(dss.Loads.AllNames(), config.time_series.load_loadshape_name)
    results_origin = _run_timeseries_case(config, battery_strategy_func=None)
    
    print("\nOriginal Case Violation Summary:")
    annouce_violations_timeseries(results_origin.Violations, config.time_series.mode, config.grid_limits.low_limit, config.grid_limits.high_limit, config.grid_limits.loading_limit, config.time_series.stepsize)


    print("\n--- 2. Analyzing Case with DER ---")
    dss.Text.Command("clear")
    dss.Text.Command(f'Compile "{config.files.dss_master_file}"')
    
    dss.Text.Command('Set MaxIter=100')
    
    add_an_energy_meter(**config.dss_elements.ElementInfo.__dict__)
    
    create_loadshape(config.time_series.load_loadshape_name, config.time_series.number, config.files.load_shape_profile, None, None, 'interval', parse_stepsize_to_hours(config.time_series.stepsize), 1)
    scale_all_loads_uniformly_timeseres(dss.Loads.AllNames(), config.time_series.load_loadshape_name)
    create_loadshape(config.time_series.pv_loadshape_name, config.time_series.number, config.files.pv_shape_profile, None, None, 'interval', parse_stepsize_to_hours(config.time_series.stepsize), 1)
    
    _add_der_to_circuit(config)
    results_der = _run_timeseries_case(config, battery_strategy_func)

    print("\nDER Case Violation Summary:")
    annouce_violations_timeseries(results_der.Violations, config.time_series.mode, config.grid_limits.low_limit, config.grid_limits.high_limit, config.grid_limits.loading_limit, config.time_series.stepsize)
    
    return results_origin, results_der
