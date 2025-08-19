# -*- coding: utf-8 -*-
"""
Created on Thu August 6 15:03:16 2025
Functions:
- Mode 1 (SINGLE_RUN): Perform a detailed 24-hour simulation for a single specified configuration    
- Mode 2 (TRAVERSAL): Globally traverse combinations of PV, energy storage, and SOC to plot the feasible region map (original bianliSIN)
- Mode 3 (OPTIMIZATION): Use hill-climbing algorithm to find the maximum PV and minimum energy storage that satisfy constraints (original mountainclimbing)

@author: Yayu(Andy) Yang
"""

import numpy as np
# ---Global variables for caching loaded data---
_pv_profile_cache = None
_load_profile_cache = None 
_total_base_load_kw_cache = None 

#%%
def strategy_self_consumption(dss, config, step, results):
    """
    Strategy 1: PV self-consumption; excess power fed to the grid; storage compensates for deficits.
    """
    storage_info = config.dss_elements.StorageInfo
    if not storage_info.storage_namess: return

    if step == 0:
        return
    current_load_kw = 0
    if results.load_powers:
        current_load_kw = sum(power_tuple[0]
                              for powers in results.load_powers.values()
                              if len(powers) > step - 1 and not np.isnan((power_tuple := powers[step - 1])[0]))
    current_pv_kw = 0
    if results.pv_actual_powers:
        current_pv_kw = sum(power_tuple[0]
                            for powers in results.pv_actual_powers.values()
                            if len(powers) > step - 1 and not np.isnan((power_tuple := powers[step - 1])[0]))

    sto_name = storage_info.storage_namess[0]
    dss.Storages.Name(sto_name)
    current_soc_pct = float(dss.Properties.Value('%stored'))
    
    battery_kw_rated = storage_info.storage_kwratedss[0]
    soc_min = storage_info.pct_min_reserve_reqss[0]
    soc_max = 100 

    power_setpoint, state = 0, 'IDLING'

    net_power = current_pv_kw + current_load_kw

    if net_power > 0:
        if current_soc_pct < soc_max:
            charge_power = min(net_power, battery_kw_rated)
            power_setpoint = -charge_power
            state = 'CHARGING'
    else:
        if current_soc_pct > soc_min:
            deficit = abs(net_power)
            discharge_power = min(deficit, battery_kw_rated)
            power_setpoint = discharge_power
            state = 'DISCHARGING'
            
    dss.Properties.Value('kW', str(power_setpoint))
    dss.Properties.Value('State', state)

#%%
def strategy_self_consumption_present_pv_load(dss, config, step, results):
    """
    Strategy 2: Determine the system total load and PV output at the current time based on PV and load profile data.
    """
    global _pv_profile_cache, _load_profile_cache, _total_base_load_kw_cache

    if _pv_profile_cache is None:
        try:
            _pv_profile_cache = np.loadtxt(config.files.pv_shape_profile)
        except Exception as e:
            print(f"FATAL ERROR in control strategy: Could not load PV profile file. {e}")
            _pv_profile_cache = "error"
            return
            
    if isinstance(_pv_profile_cache, str) and _pv_profile_cache == "error":
        return

    if _load_profile_cache is None:
        try:
            _load_profile_cache = np.loadtxt(config.files.load_shape_profile)
        except Exception as e:
            print(f"FATAL ERROR in control strategy: Could not load Load profile file. {e}")
            _load_profile_cache = "error"
            return
    if isinstance(_load_profile_cache, str) and _load_profile_cache == "error":
        return

    if _total_base_load_kw_cache is None:
        all_loads = dss.Loads.AllNames()
        if not all_loads:
            _total_base_load_kw_cache = 0
        else:
            total_kw = 0
            for load_name in all_loads:
                dss.Loads.Name(load_name)
                total_kw += dss.Loads.kW()
            _total_base_load_kw_cache = total_kw


    storage_info = config.dss_elements.StorageInfo
    if not storage_info.storage_namess: return

    pv_rated_kw = sum(config.dss_elements.PVInfo.pv_pmpp_kwss)
    predicted_pv_kw = pv_rated_kw * _pv_profile_cache[step]

    predicted_load_kw = -1 * (_total_base_load_kw_cache * _load_profile_cache[step])

    net_power = predicted_pv_kw + predicted_load_kw

    sto_name = storage_info.storage_namess[0]
    dss.Storages.Name(sto_name)
    current_soc_pct = float(dss.Properties.Value('%stored'))
    battery_kw_rated = storage_info.storage_kwratedss[0]
    soc_min = storage_info.pct_min_reserve_reqss[0]
    soc_max = 100

    ideal_power_setpoint = 0
    if net_power > 0:
        if current_soc_pct < soc_max:
            ideal_power_setpoint = -min(net_power, battery_kw_rated) # 充电为负
    else:
        if current_soc_pct > soc_min:
            ideal_power_setpoint = min(abs(net_power), battery_kw_rated) # 放电为正

    # Apply power ramp rate limits to improve smoothness. This feature is disabled in the current version and will be enabled in the next release.
    final_power_setpoint = ideal_power_setpoint
    if hasattr(storage_info, 'max_ramp_kw_per_step') and step > 0:
        last_power_setpoint = results.storage_powers[sto_name][step - 1][0]
        max_ramp = storage_info.max_ramp_kw_per_step[0]
        delta = final_power_setpoint - last_power_setpoint
        if abs(delta) > max_ramp:
            final_power_setpoint = last_power_setpoint + np.sign(delta) * max_ramp

    if final_power_setpoint > 0.1: state = 'DISCHARGING'
    elif final_power_setpoint < -0.1: state = 'CHARGING'
    else: state = 'IDLING'

    dss.Properties.Value('kW', str(final_power_setpoint))
    dss.Properties.Value('State', state)


#%% This feature is disabled in the current version and will be enabled in the next release.
def create_strategy_from_file(dispatch_profile):
    def strategy_file_dispatch(dss, config, step, results):
        storage_info = config.dss_elements.StorageInfo
        if not storage_info.storage_namess: return

        if step < len(dispatch_profile):
            power_setpoint = dispatch_profile[step]
            state = 'IDLING'
            if power_setpoint > 0: state = 'DISCHARGING'
            elif power_setpoint < 0: state = 'CHARGING'
            
            dss.Storages.Name(storage_info.storage_namess[0])
            dss.Properties.Value('kW', str(power_setpoint))
            dss.Properties.Value('State', state)

    return strategy_file_dispatch