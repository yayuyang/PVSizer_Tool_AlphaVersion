# -*- coding: utf-8 -*-
"""
Created on Thu August 6 15:03:16 2025
Functions:
- Mode 1 (SINGLE_RUN): Perform a detailed 24-hour simulation for a single specified configuration    
- Mode 2 (TRAVERSAL): Globally traverse combinations of PV, energy storage, and SOC to plot the feasible region map (original bianliSIN)
- Mode 3 (OPTIMIZATION): Use hill-climbing algorithm to find the maximum PV and minimum energy storage that satisfy constraints (original mountainclimbing)

@author: Yayu(Andy) Yang
"""

# importing the modules needed
import matplotlib.pyplot as plt
import numpy as np
import re
import opendssdirect as dss
from types import SimpleNamespace
import os 
import pandas as pd
from datetime import datetime
from IBRNetGridSize_DssBasicFunctions import Get_All_Load_Data_For_Full_Feeder, get_base_bus_name, get_phase_letter
from IBRNetGridSize_DssPowerFlowFunctions import parse_stepsize_to_hours

#%% 1. Data Preparation and Processing Center
def _prepare_data_for_visualization(config, res_orig, res_der):
    print("Preparing data for plotting and export...")   
    data = SimpleNamespace()

    time_cfg = config.time_series
    step_in_hours = parse_stepsize_to_hours(time_cfg.stepsize)
    total_hours = time_cfg.number * step_in_hours # <--- 新增：计算总小时数
    data.time_axis = [i * step_in_hours for i in range(time_cfg.number)]
    data.time_label = "Time (Hours)"

    data.total_hours = total_hours 
    data.x_ticks = np.arange(0, total_hours + 1, 6) 

    data.limits_cfg = config.grid_limits
    dss.Text.Command(f'Compile "{config.files.dss_master_file}"') 
    _, _, _, _, _, _, _, _, data.base_load_name_list = Get_All_Load_Data_For_Full_Feeder()

    data.voltages_orig = res_orig.Bus_Vol_PU_LN
    data.voltages_der = res_der.Bus_Vol_PU_LN
    data.bus_names_sorted_orig = res_orig.Bus_Names_Sorted_By_Distance
    data.bus_names_sorted_der = res_der.Bus_Names_Sorted_By_Distance
    data.loadings_orig = {el: data for el, data in res_orig.Element_Loadings_Pct.items() if 'line' in el.lower() or 'transformer' in el.lower()}
    data.loadings_der = {el: data for el, data in res_der.Element_Loadings_Pct.items() if 'line' in el.lower() or 'transformer' in el.lower()}

    data.grid_active_power_orig = [-p[0] for p in res_orig.Total_Power]
    data.grid_active_power_der = [-p[0] for p in res_der.Total_Power]
    data.grid_reactive_power_orig = [-p[1] for p in res_orig.Total_Power]
    data.grid_reactive_power_der = [-p[1] for p in res_der.Total_Power]

    data.loss_active_power_orig = [-l[0] for l in res_orig.Total_Losses]
    data.loss_active_power_der = [-l[0] for l in res_der.Total_Losses]
    data.loss_reactive_power_orig = [-l[1] for l in res_orig.Total_Losses] # 新增
    data.loss_reactive_power_der = [-l[1] for l in res_der.Total_Losses] # 新增    

    data.measured_powers_orig = SimpleNamespace(load={}, pv={}, storage={}, capacitor={})
    data.measured_powers_der = SimpleNamespace(load={}, pv={}, storage={}, capacitor={})    
    data.soc_der = res_der.storage_soc
    
    for case, results_obj, data_obj in [('orig', res_orig, data.measured_powers_orig), ('der', res_der, data.measured_powers_der)]:
        for name, powers in results_obj.load_powers.items():
            data_obj.load[name] = {'active': [p[0] for p in powers], 'reactive': [p[1] for p in powers]}
        for name, powers in results_obj.pv_actual_powers.items():
            data_obj.pv[name] = {'active': [p[0] for p in powers], 'reactive': [p[1] for p in powers]}
        for name, powers in results_obj.storage_powers.items():
            data_obj.storage[name] = {'active': [p[0] for p in powers], 'reactive': [p[1] for p in powers]}
        for name, powers in results_obj.capacitor_powers.items():
            data_obj.capacitor[name] = {'active': [p[0] for p in powers], 'reactive': [p[1] for p in powers]}
            
    num_steps = len(data.time_axis)
    data.load_active_total_orig = np.sum([p['active'] for p in data.measured_powers_orig.load.values()], axis=0) if data.measured_powers_orig.load else np.zeros(num_steps)
    data.load_reactive_total_orig = np.sum([p['reactive'] for p in data.measured_powers_orig.load.values()], axis=0) if data.measured_powers_orig.load else np.zeros(num_steps)
    data.capacitor_reactive_total_orig = np.sum([p['reactive'] for p in data.measured_powers_orig.capacitor.values()], axis=0) if data.measured_powers_orig.capacitor else np.zeros(num_steps)

    data.load_active_total_der = np.sum([p['active'] for p in data.measured_powers_der.load.values()], axis=0) if data.measured_powers_der.load else np.zeros(num_steps)
    data.load_reactive_total_der = np.sum([p['reactive'] for p in data.measured_powers_der.load.values()], axis=0) if data.measured_powers_der.load else np.zeros(num_steps)
    data.pv_active_total_der = np.sum([p['active'] for p in data.measured_powers_der.pv.values()], axis=0) if data.measured_powers_der.pv else np.zeros(num_steps)
    data.pv_reactive_total_der = np.sum([p['reactive'] for p in data.measured_powers_der.pv.values()], axis=0) if data.measured_powers_der.pv else np.zeros(num_steps)
    data.storage_active_total_der = np.sum([p['active'] for p in data.measured_powers_der.storage.values()], axis=0) if data.measured_powers_der.storage else np.zeros(num_steps)
    data.storage_reactive_total_der = np.sum([p['reactive'] for p in data.measured_powers_der.storage.values()], axis=0) if data.measured_powers_der.storage else np.zeros(num_steps)
    data.capacitor_reactive_total_der = np.sum([p['reactive'] for p in data.measured_powers_der.capacitor.values()], axis=0) if data.measured_powers_der.capacitor else np.zeros(num_steps)

    data.balance_active_power_orig = (np.array(data.grid_active_power_orig) + 
                                      np.array(data.load_active_total_orig) + 
                                      np.array(data.loss_active_power_orig))
    data.balance_active_power_der = (np.array(data.grid_active_power_der) + 
                                     np.array(data.pv_active_total_der) + 
                                     np.array(data.storage_active_total_der) +
                                     np.array(data.load_active_total_der) + 
                                     np.array(data.loss_active_power_der))

    data.balance_reactive_power_orig = (np.array(data.grid_reactive_power_orig) + 
                                        np.array(data.capacitor_reactive_total_orig) +
                                        np.array(data.load_reactive_total_orig) + 
                                        np.array(data.loss_reactive_power_orig))
    data.balance_reactive_power_der = (np.array(data.grid_reactive_power_der) + 
                                       np.array(data.capacitor_reactive_total_der) +
                                       np.array(data.pv_reactive_total_der) +
                                       np.array(data.storage_reactive_total_der) +
                                       np.array(data.load_reactive_total_der) + 
                                       np.array(data.loss_reactive_power_der))
    
    print("Data preparation complete.")
    return data

#%% 2.Global Plot Style Settings
def _setup_plot_style():
    style_params = {
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Calibri', 'SimHei'],
    'font.size': 16,                    
    'axes.titlesize': 20,               
    'axes.labelsize': 18,              
    'xtick.labelsize': 16,             
    'ytick.labelsize': 16,            
    'legend.fontsize': 16,          
    'figure.titlesize': 22,          
    'grid.linestyle': ':',
    'grid.alpha': 0.7,
    'lines.linewidth': 2.5,         
    'axes.unicode_minus': False
}
    plt.rcParams.update(style_params)

#%% 3.Independent plotting function
def _plot_voltage_profiles(data):
    print("Plotting Figure 1: Bus Voltages (Comparison)...")
    
    all_buses = sorted(list(set(data.bus_names_sorted_orig) | set(data.bus_names_sorted_der)))
    colors = plt.cm.get_cmap('tab20', len(all_buses))
    color_map = {name: colors(i) for i, name in enumerate(all_buses)}
    
    fig, axs = plt.subplots(2, 1, figsize=(16, 12), sharex=True, sharey=True)
    fig.suptitle("Figure 1: Bus Node Voltage Time Series Comparison")

    axs[0].set_title("Original Case")
    for bus_name in data.bus_names_sorted_orig:
        bus_key = bus_name.lower()
        if bus_key in data.voltages_orig and len(data.voltages_orig[bus_key]) == len(data.time_axis):
            axs[0].plot(data.time_axis, data.voltages_orig[bus_key], label=bus_name, alpha=0.8, color=color_map.get(bus_name))
    axs[0].axhline(y=data.limits_cfg.high_limit, color='r', linestyle='--', label='Voltage Limits')
    axs[0].axhline(y=data.limits_cfg.low_limit, color='r', linestyle='--')
    axs[0].set_ylabel("Voltage (pu)")
    axs[0].grid(True)
    axs[0].legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., ncol=2)

    axs[1].set_title("With DER Case")
    for bus_name in data.bus_names_sorted_der:
        bus_key = bus_name.lower()
        if bus_key in data.voltages_der and len(data.voltages_der[bus_key]) == len(data.time_axis):
            axs[1].plot(data.time_axis, data.voltages_der[bus_key], label=bus_name, alpha=0.8, color=color_map.get(bus_name))
    axs[1].axhline(y=data.limits_cfg.high_limit, color='r', linestyle='--')
    axs[1].axhline(y=data.limits_cfg.low_limit, color='r', linestyle='--')
    axs[1].set_xlabel(data.time_label)
    axs[1].set_ylabel("Voltage (pu)")
    axs[1].grid(True)
    axs[1].legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., ncol=2)
    
    plt.xlim(0, data.total_hours); plt.xticks(data.x_ticks); plt.ylim(bottom=0.92, top=1.08)
    plt.tight_layout(rect=[0, 0.03, 0.99, 0.97]) 
    plt.show()

def _plot_element_loadings(data):
    print("Plotting Figure 2: Element Loadings (Comparison)...")
    all_elements = sorted(list(set(data.loadings_orig.keys()) | set(data.loadings_der.keys())))
    colors = plt.cm.get_cmap('tab20', len(all_elements))
    color_map = {name: colors(i) for i, name in enumerate(all_elements)}

    fig, axs = plt.subplots(2, 1, figsize=(16, 12), sharex=True, sharey=True)
    fig.suptitle("Figure 2: Element Loading Time Series Comparison")

    axs[0].set_title("Original Case")
    for el_name, loadings in data.loadings_orig.items():
        if len(loadings) == len(data.time_axis):
            axs[0].plot(data.time_axis, loadings, label=el_name, alpha=0.8, color=color_map.get(el_name))
    axs[0].axhline(y=data.limits_cfg.loading_limit, color='r', linestyle='--', label=f'Loading Limit')
    axs[0].set_ylabel("Element Loading (% Normal)")
    axs[0].grid(True)
    axs[0].legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., ncol=2)

    axs[1].set_title("With DER Case")
    for el_name, loadings in data.loadings_der.items():
        if len(loadings) == len(data.time_axis):
            axs[1].plot(data.time_axis, loadings, label=el_name, alpha=0.8, color=color_map.get(el_name))
    axs[1].axhline(y=data.limits_cfg.loading_limit, color='r', linestyle='--')
    axs[1].set_xlabel(data.time_label)
    axs[1].set_ylabel("Element Loading (% Normal)")
    axs[1].grid(True)
    axs[1].legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., ncol=2)

    plt.xlim(0, data.total_hours); plt.xticks(data.x_ticks); plt.ylim(bottom=0)
    plt.tight_layout(rect=[0, 0.03, 0.99, 0.97])
    plt.show()

def _plot_grid_power_summary(data):
    print("Plotting Figure 3: Grid Power and Losses...")
    fig, axs = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    fig.suptitle("Figure 3: Total Power from Grid and System Losses")
    
    axs[0].set_title("Total Active Power from Grid")
    axs[0].plot(data.time_axis, data.grid_active_power_orig, label='Original')
    axs[0].plot(data.time_axis, data.grid_active_power_der, label='With DER', linestyle='--')
    axs[0].set_ylabel("Power (kW)"); axs[0].legend(); axs[0].grid(True)
    
    axs[1].set_title("Total Reactive Power from Grid")
    axs[1].plot(data.time_axis, data.grid_reactive_power_orig, label='Original')
    axs[1].plot(data.time_axis, data.grid_reactive_power_der, label='With DER', linestyle='--')
    axs[1].set_ylabel("Power (kVAR)"); axs[1].legend(); axs[1].grid(True)
    
    axs[2].set_title("Total Active Power Loss")
    axs[2].plot(data.time_axis, data.loss_active_power_orig, label='Original')
    axs[2].plot(data.time_axis, data.loss_active_power_der, label='With DER', linestyle='--')
    axs[2].set_ylabel("Power Loss (kW)"); axs[2].legend(); axs[2].grid(True)
    
    axs[2].set_xlabel(data.time_label)
    plt.xlim(0, data.total_hours); plt.xticks(data.x_ticks)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

def _plot_component_power_and_soc(data):
    print("Plotting Figure 4: Component Power Analysis and Storage SOC")

    fig, axs = plt.subplots(3, 1, figsize=(12, 18), sharex=True) # 增加图像高度
    fig.suptitle("Figure 4: Component Power Analysis and Storage SOC")

    axs[0].set_title("Measured Load and PV Active Power")    
    axs[0].plot(data.time_axis, -data.load_active_total_orig, label='-Measured Total Load (Original)', color='darkgreen')
    axs[0].plot(data.time_axis, -data.load_active_total_der, label='-Measured Total Load (With DER)', linestyle=':', color='darkred')

    if data.measured_powers_der.pv:
        pv_name = list(data.measured_powers_der.pv.keys())[0]
        axs[0].plot(data.time_axis, data.measured_powers_der.pv[pv_name]['active'], label='PV Generation (Measured)', color='orange', linestyle='--')
    axs[0].set_ylabel("Active Power (kW)"); axs[0].legend(); axs[0].grid(True)
    
    axs[1].set_title("Measured Load and PV Reactive Power")
    axs[1].plot(data.time_axis, -data.load_reactive_total_orig, label='-Measured Total Load (Original)', color='darkgreen')    
    axs[1].plot(data.time_axis, -data.load_reactive_total_der, label='-Measured Total Load (With DER)', linestyle=':', color='darkred')
    if data.measured_powers_der.pv:
        pv_name = list(data.measured_powers_der.pv.keys())[0]
        axs[1].plot(data.time_axis, data.measured_powers_der.pv[pv_name]['reactive'], label='PV Generation (Measured)', color='orange', linestyle='--')
    axs[1].set_ylabel("Reactive Power (kVAR)"); axs[1].legend(); axs[1].grid(True)

    axs[2].set_title("Storage SOC")
    if data.soc_der:
        for name, soc_series in data.soc_der.items():
            if len(soc_series) == len(data.time_axis):
                axs[2].plot(data.time_axis, soc_series, label=f'{name} SOC')
    axs[2].set_ylabel("SOC (%)"); axs[2].set_ylim(0, 100); axs[2].legend(); axs[2].grid(True)
    
    axs[2].set_xlabel(data.time_label)
    plt.xlim(0, data.total_hours); plt.xticks(data.x_ticks)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()
  
def _plot_load_active_loads(data):
    print("Plotting Figure 5: Load Active Power Comparison (Measured)...")
    
    colors = plt.cm.get_cmap('tab20', len(data.base_load_name_list))
    color_map = {name: colors(i) for i, name in enumerate(data.base_load_name_list)}

    fig, axs = plt.subplots(2, 1, figsize=(16, 18), sharex=True, sharey=True)
    fig.suptitle("Figure 5: Load Active Power Comparison (Measured)")

    axs[0].set_title("Original Case (Measured)")
    for name, powers in data.measured_powers_orig.load.items():
        axs[0].plot(data.time_axis, powers['active'], label=name, color=color_map.get(name))

    axs[1].set_title("With DER Case (Measured)")
    for name, powers in data.measured_powers_der.load.items():
        axs[1].plot(data.time_axis, powers['active'], label=name, color=color_map.get(name))

    for ax in axs:
        ax.set_ylabel("Active Power (kW)")
        ax.grid(True)
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., ncol=2)
    
    axs[1].set_xlabel(data.time_label)
    plt.xlim(0, data.total_hours)
    plt.xticks(data.x_ticks)
    plt.tight_layout(rect=[0, 0.03, 0.99, 0.97])
    plt.show()

def _plot_load_reactive_loads(data):
    print("Plotting Figure 6: Load Reactive Power Comparison (Measured)...")

    colors = plt.cm.get_cmap('tab20', len(data.base_load_name_list))
    color_map = {name: colors(i) for i, name in enumerate(data.base_load_name_list)}

    fig, axs = plt.subplots(2, 1, figsize=(16, 18), sharex=True, sharey=True)
    fig.suptitle("Figure 6: Load Reactive Power Comparison (Measured)")

    axs[0].set_title("Original Case (Measured)")
    for name, powers in data.measured_powers_orig.load.items():
        axs[0].plot(data.time_axis, powers['reactive'], label=name, color=color_map.get(name))

    axs[1].set_title("With DER Case (Measured)")
    for name, powers in data.measured_powers_der.load.items():
        axs[1].plot(data.time_axis, powers['reactive'], label=name, color=color_map.get(name))

    for ax in axs:
        ax.set_ylabel("Reactive Power (kVAR)")
        ax.grid(True)
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., ncol=2)
    
    axs[1].set_xlabel(data.time_label)
    plt.xlim(0, data.total_hours)
    plt.xticks(data.x_ticks)
    plt.tight_layout(rect=[0, 0.03, 0.99, 0.97])
    plt.show()    
    
def _plot_all_components_active_power(data):
    print("Plotting Figure 7: All Components Active Power (Measured)...")
    fig, axs = plt.subplots(2, 1, figsize=(16, 12), sharex=True, sharey=True)
    fig.suptitle("Figure 7: Measured Active Power of All Components")

    axs[0].set_title("Original Case")
    for name, powers in data.measured_powers_orig.load.items():
        axs[0].plot(data.time_axis, powers['active'], label=name, color='b', alpha=0.7)

    axs[1].set_title("With DER Case")
    for name, powers in data.measured_powers_der.load.items():
        axs[1].plot(data.time_axis, powers['active'], label=name, color='b', alpha=0.7)
    for name, powers in data.measured_powers_der.pv.items():
        axs[1].plot(data.time_axis, powers['active'], label=name, color='orange', linestyle='--')
    for name, powers in data.measured_powers_der.storage.items():
        axs[1].plot(data.time_axis, powers['active'], label=name, color='g', linestyle=':')

    for ax in axs:
        ax.set_ylabel("Active Power (kW)")
        ax.grid(True)
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., ncol=2)
    axs[1].set_xlabel(data.time_label)
    plt.xlim(0, data.total_hours); plt.xticks(data.x_ticks)
    plt.tight_layout(rect=[0, 0.03, 0.99, 0.97])
    plt.show()

def _plot_all_components_reactive_power(data):
    print("Plotting Figure 8: All Components Reactive Power (Measured)...")
    fig, axs = plt.subplots(2, 1, figsize=(16, 12), sharex=True, sharey=True)
    fig.suptitle("Figure 8: Measured Reactive Power of All Components")

    axs[0].set_title("Original Case")
    for name, powers in data.measured_powers_orig.load.items():
        axs[0].plot(data.time_axis, powers['reactive'], label=name, color='b', alpha=0.7)
    for name, powers in data.measured_powers_orig.capacitor.items():
        axs[0].plot(data.time_axis, powers['reactive'], label=name, color='purple', linestyle='-.')

    axs[1].set_title("With DER Case")
    for name, powers in data.measured_powers_der.load.items():
        axs[1].plot(data.time_axis, powers['reactive'], label=name, color='b', alpha=0.7)
    for name, powers in data.measured_powers_der.pv.items():
        axs[1].plot(data.time_axis, powers['reactive'], label=name, color='orange', linestyle='--')
    for name, powers in data.measured_powers_der.storage.items():
        axs[1].plot(data.time_axis, powers['reactive'], label=name, color='g', linestyle=':')
    for name, powers in data.measured_powers_der.capacitor.items():
        axs[1].plot(data.time_axis, powers['reactive'], label=name, color='purple', linestyle='-.')

    for ax in axs:
        ax.set_ylabel("Reactive Power (kVAR)")
        ax.grid(True)
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0., ncol=2)
    axs[1].set_xlabel(data.time_label)
    plt.xlim(0, data.total_hours); plt.xticks(data.x_ticks)
    plt.tight_layout(rect=[0, 0.03, 0.99, 0.97])
    plt.show()

def _plot_active_power_balance(data):
    print("Plotting Figure 9: Active Power Balance Verification...")
    fig, axs = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
    fig.suptitle("Figure 9: Active Power Balance Verification")

    axs[0].set_title("Original Case")
    axs[0].plot(data.time_axis, data.grid_active_power_orig, label='Grid Supply', color='black', linestyle='-')
    axs[0].plot(data.time_axis, data.load_active_total_orig, label='Load Demand', color='blue')
    axs[0].plot(data.time_axis, data.loss_active_power_orig, label='System Losses', color='grey', linestyle=':')
    axs[0].plot(data.time_axis, data.balance_active_power_orig, label='Net Balance (Should be Zero)', color='cyan', linestyle='--', linewidth=2.5)

    axs[1].set_title("With DER Case")

    axs[1].plot(data.time_axis, data.grid_active_power_der, label='Grid Supply', color='black', linestyle='-')
    axs[1].plot(data.time_axis, data.pv_active_total_der, label='PV Generation', color='orange')
    axs[1].plot(data.time_axis, data.storage_active_total_der, label='Storage (+ Discharge / - Charge)', color='green')

    axs[1].plot(data.time_axis, data.load_active_total_der, label='Load Demand', color='blue')
    axs[1].plot(data.time_axis, data.loss_active_power_der, label='System Losses', color='grey', linestyle=':')

    axs[1].plot(data.time_axis, data.balance_active_power_der, label='Net Balance (Should be Zero)', color='cyan', linestyle='--', linewidth=2.5)

    for ax in axs:
        ax.set_ylabel("Active Power (kW)")
        ax.grid(True)
        ax.axhline(0, color='k', linestyle='-', linewidth=0.7)
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)
    axs[1].set_xlabel(data.time_label)
    plt.xlim(0, data.total_hours); plt.xticks(data.x_ticks)
    plt.tight_layout(rect=[0, 0.03, 0.99, 0.97])
    plt.show()

def _plot_reactive_power_balance(data):
    print("Plotting Figure 10: Reactive Power Balance Verification...")
    fig, axs = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
    fig.suptitle("Figure 10: Reactive Power Balance Verification")

    axs[0].set_title("Original Case")

    axs[0].plot(data.time_axis, data.grid_reactive_power_orig, label='Grid Supply', color='black', linestyle='-')
    axs[0].plot(data.time_axis, data.capacitor_reactive_total_orig, label='Capacitor Supply', color='purple')

    axs[0].plot(data.time_axis, data.load_reactive_total_orig, label='Load Demand', color='blue')

    axs[0].plot(data.time_axis, data.loss_reactive_power_orig, label='System Losses', color='grey', linestyle=':')
    
    axs[0].plot(data.time_axis, data.balance_reactive_power_orig, label='Net Balance (Should be Zero)', color='cyan', linestyle='--', linewidth=2.5)

    axs[1].set_title("With DER Case")

    axs[1].plot(data.time_axis, data.grid_reactive_power_der, label='Grid Supply', color='black', linestyle='-')
    axs[1].plot(data.time_axis, data.capacitor_reactive_total_der, label='Capacitor Supply', color='purple')

    axs[1].plot(data.time_axis, data.pv_reactive_total_der, label='PV Reactive Power', color='orange')
    axs[1].plot(data.time_axis, data.storage_reactive_total_der, label='Storage Reactive Power ', color='green')

    axs[1].plot(data.time_axis, data.load_reactive_total_der, label='Load Demand', color='blue')
    axs[1].plot(data.time_axis, data.loss_reactive_power_der, label='System Losses', color='grey', linestyle=':')

    axs[1].plot(data.time_axis, data.balance_reactive_power_der, label='Net Balance (Should be Zero)', color='cyan', linestyle='--', linewidth=2.5)

    for ax in axs:
        ax.set_ylabel("Reactive Power (kVAR)")
        ax.grid(True)
        ax.axhline(0, color='k', linestyle='-', linewidth=0.7)
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)
    axs[1].set_xlabel(data.time_label)
    plt.xlim(0, data.total_hours); plt.xticks(data.x_ticks)
    plt.tight_layout(rect=[0, 0.03, 0.99, 0.97])
    plt.show()

#%% 4.Public Interface
def generate_all_plots(config, results_origin, results_der):
    if not results_origin.converged or not results_der.converged or not all(results_der.converged):
        print("Plotting skipped due to empty results or simulation failure.")
        return

    _setup_plot_style()

    prepared_data = _prepare_data_for_visualization(config, results_origin, results_der)

    _plot_voltage_profiles(prepared_data)
    _plot_element_loadings(prepared_data)
    _plot_grid_power_summary(prepared_data)
    _plot_component_power_and_soc(prepared_data)

    _plot_load_active_loads(prepared_data)
    _plot_load_reactive_loads(prepared_data)

    _plot_all_components_active_power(prepared_data)
    _plot_all_components_reactive_power(prepared_data)

    _plot_active_power_balance(prepared_data)
    _plot_reactive_power_balance(prepared_data)
    
def export_results_to_csv(config, results_origin, results_der):
    """
    Export all time-series data from figures to a timestamped CSV file.
    """
    print("\nExporting all plot data to CSV file...")
    
    try:
        data = _prepare_data_for_visualization(config, results_origin, results_der)
        data_to_export = {
            'Time (Hours)': data.time_axis
        }

        for bus, volts in data.voltages_orig.items():
            data_to_export[f'F1_S1_Voltage_Orig_{bus}'] = volts
        for bus, volts in data.voltages_der.items():
            data_to_export[f'F1_S2_Voltage_DER_{bus}'] = volts
        
        for el, loadings in data.loadings_orig.items():
            data_to_export[f'F2_S1_Loading_Orig_{el}'] = loadings
        for el, loadings in data.loadings_der.items():
            data_to_export[f'F2_S2_Loading_DER_{el}'] = loadings

        data_to_export['F3_S1_GridActivePower_Orig'] = data.grid_active_power_orig
        data_to_export['F3_S1_GridActivePower_DER'] = data.grid_active_power_der
        data_to_export['F3_S2_GridReactivePower_Orig'] = data.grid_reactive_power_orig
        data_to_export['F3_S2_GridReactivePower_DER'] = data.grid_reactive_power_der
        data_to_export['F3_S3_SystemLoss_kW_Orig'] = data.loss_active_power_orig
        data_to_export['F3_S3_SystemLoss_kW_DER'] = data.loss_active_power_der

        data_to_export['F4_S1_LoadActive_Total_Orig'] = data.load_active_total_orig
        data_to_export['F4_S1_LoadActive_Total_DER'] = data.load_active_total_der
        data_to_export['F4_S2_LoadReactive_Total_Orig'] = data.load_reactive_total_orig
        data_to_export['F4_S2_LoadReactive_Total_DER'] = data.load_reactive_total_der
        
        if data.measured_powers_der.pv:
            pv_name = list(data.measured_powers_der.pv.keys())[0]
            data_to_export['F4_S1_PVActive_Measured'] = data.measured_powers_der.pv[pv_name]['active']
            data_to_export['F4_S2_PVReactive_Measured'] = data.measured_powers_der.pv[pv_name]['reactive']
        for name, soc in data.soc_der.items():
            data_to_export[f'F4_S3_SOC_{name}'] = soc        

        for name, powers in data.measured_powers_orig.load.items():
            data_to_export[f'F5_S1_LoadActive_Measured_Orig_{name}'] = powers['active']
        for name, powers in data.measured_powers_der.load.items():
            data_to_export[f'F5_S2_LoadActive_Measured_DER_{name}'] = powers['active']

        for name, powers in data.measured_powers_orig.load.items():
            data_to_export[f'F6_S1_LoadReactive_Measured_Orig_{name}'] = powers['reactive']
        for name, powers in data.measured_powers_der.load.items():
            data_to_export[f'F6_S2_LoadReactive_Measured_DER_{name}'] = powers['reactive']

        for case_name, powers_obj in [('Orig', data.measured_powers_orig), ('DER', data.measured_powers_der)]:
            for name, powers in powers_obj.load.items():
                data_to_export[f'F7_LoadActive_{case_name}_{name}'] = powers['active']
                data_to_export[f'F8_LoadReactive_{case_name}_{name}'] = powers['reactive']
            for name, powers in powers_obj.pv.items():
                data_to_export[f'F7_PVActive_{case_name}_{name}'] = powers['active']
                data_to_export[f'F8_PVReactive_{case_name}_{name}'] = powers['reactive']
            for name, powers in powers_obj.storage.items():
                data_to_export[f'F7_StorageActive_{case_name}_{name}'] = powers['active']
                data_to_export[f'F8_StorageReactive_{case_name}_{name}'] = powers['reactive']
            for name, powers in powers_obj.capacitor.items():
                data_to_export[f'F8_CapacitorReactive_{case_name}_{name}'] = powers['reactive']

        data_to_export['F9_S1_GridActive_Orig'] = data.grid_active_power_orig
        data_to_export['F9_S1_LoadActiveTotal_Orig'] = data.load_active_total_orig
        data_to_export['F9_S1_LossActive_Orig'] = data.loss_active_power_orig
        data_to_export['F9_S1_NetBalanceActive_Orig'] = data.balance_active_power_orig

        data_to_export['F9_S2_GridActive_DER'] = data.grid_active_power_der
        data_to_export['F9_S2_PVActiveTotal_DER'] = data.pv_active_total_der
        data_to_export['F9_S2_StorageActiveTotal_DER'] = data.storage_active_total_der
        data_to_export['F9_S2_LoadActiveTotal_DER'] = data.load_active_total_der
        data_to_export['F9_S2_LossActive_DER'] = data.loss_active_power_der
        data_to_export['F9_S2_NetBalanceActive_DER'] = data.balance_active_power_der

        data_to_export['F10_S1_GridReactive_Orig'] = data.grid_reactive_power_orig
        data_to_export['F10_S1_CapacitorReactiveTotal_Orig'] = data.capacitor_reactive_total_orig
        data_to_export['F10_S1_LoadReactiveTotal_Orig'] = data.load_reactive_total_orig
        data_to_export['F10_S1_LossReactive_Orig'] = data.loss_reactive_power_orig
        data_to_export['F10_S1_NetBalanceReactive_Orig'] = data.balance_reactive_power_orig

        data_to_export['F10_S2_GridReactive_DER'] = data.grid_reactive_power_der
        data_to_export['F10_S2_CapacitorReactiveTotal_DER'] = data.capacitor_reactive_total_der
        data_to_export['F10_S2_PVReactiveTotal_DER'] = data.pv_reactive_total_der
        data_to_export['F10_S2_StorageReactiveTotal_DER'] = data.storage_reactive_total_der
        data_to_export['F10_S2_LoadReactiveTotal_DER'] = data.load_reactive_total_der
        data_to_export['F10_S2_LossReactive_DER'] = data.loss_reactive_power_der
        data_to_export['F10_S2_NetBalanceReactive_DER'] = data.balance_reactive_power_der        

        max_len = len(data.time_axis)
        for col_name, col_data in data_to_export.items():
            if len(col_data) < max_len:
                padding = [np.nan] * (max_len - len(col_data))
                data_to_export[col_name] = list(col_data) + padding
        
        df = pd.DataFrame(data_to_export)

        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{date_str}.csv"

        output_path = config.files.output_path
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            
        full_filepath = os.path.join(output_path, filename)

        df.to_csv(full_filepath, index=False, encoding='utf_8_sig')
        print(f"Successfully exported data to {full_filepath}")

    except Exception as e:
        print(f"An error occurred during data export: {e}")