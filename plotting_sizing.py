# -*- coding: utf-8 -*-
"""
Created on Thu August 6 15:03:16 2025
Functions:
- Mode 1 (SINGLE_RUN): Perform a detailed 24-hour simulation for a single specified configuration    
- Mode 2 (TRAVERSAL): Globally traverse combinations of PV, energy storage, and SOC to plot the feasible region map (original bianliSIN)
- Mode 3 (OPTIMIZATION): Use hill-climbing algorithm to find the maximum PV and minimum energy storage that satisfy constraints (original mountainclimbing)

@author: Yayu(Andy) Yang
"""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import os
from datetime import datetime
from plotting import _setup_plot_style


#%% ===== 'traversal' global traversal analysis (Map Drawer)================
def plot_feasibility_maps(results_df, pv_range, battery_range, initial_soc_range):
    print("\n--- Generating Sizing Feasibility Maps (Scatter Plot) ---")
    _setup_plot_style()

    for soc in initial_soc_range:
        fig, ax = plt.subplots(figsize=(12, 10))

        soc_results = results_df[results_df['initial_soc'] == soc].copy()

        successful_runs = soc_results[soc_results['status_code'] == 1]
        failed_runs = soc_results[soc_results['status_code'] == 0]

        ax.scatter(
            failed_runs['battery_kw'], 
            failed_runs['pv_kw'], 
            c='#FF4136',  
            marker='x', 
            s=50,         
            alpha=0.6,    
            label='Failure'
        )

        ax.scatter(
            successful_runs['battery_kw'], 
            successful_runs['pv_kw'], 
            c='#2ECC40',  
            marker='o',
            s=50,
            alpha=0.8,
            edgecolor='k', 
            linewidth=0.5,
            label='Success'
        )
        

        if not successful_runs.empty:
            boundary = successful_runs.groupby('pv_kw')['battery_kw'].min().sort_index()
            ax.plot(
                boundary.values, 
                boundary.index,
                color='gold', 
                linestyle='-', 
                linewidth=2.5,
                marker='o',
                markersize=5,
                label='Feasibility Frontier'
            )
            max_pv = successful_runs['pv_kw'].max()
            runs_with_max_pv = successful_runs[successful_runs['pv_kw'] == max_pv]
            min_battery_at_max_pv = runs_with_max_pv['battery_kw'].min()

            ax.scatter(
                [min_battery_at_max_pv], [max_pv], 
                c='yellow', 
                marker='*', 
                s=300, 
                edgecolor='black', 
                label='Final Optimized Point', 
                zorder=5 
            )

        ax.set_title(f'IBRNet/GridSize Feasibility Domain Map')
        ax.set_xlabel('Battery Rated Power (kW)')
        ax.set_ylabel('PV Rated Power (kW)')
        ax.legend(loc='best')
        ax.grid(True)
        
        ax.set_xlim(left=0, right=battery_range.max() * 1.05)
        ax.set_ylim(bottom=0, top=pv_range.max() * 1.05)

        plt.tight_layout()
        plt.show()

def export_sizing_results_to_csv(results_df, pv_range, battery_range, initial_soc_range, output_path):
    """
    All files are saved in the "Traverse all sizing results" subfolder.
    """
    print("\n--- Exporting Sizing Analysis Results to CSV ---")
    if results_df.empty:
        print("Warning: Results DataFrame is empty. Skipping CSV export.")
        return

    results_dir = os.path.join(output_path, "Traverse all sizing results")
    os.makedirs(results_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        filename_list = f"sizing_results_list_{date_str}.csv"
        full_filepath_list = os.path.join(results_dir, filename_list)
        results_df.to_csv(full_filepath_list, index=False, encoding='utf_8_sig')
    except Exception as e:
        print(f"An error occurred during list-style CSV export: {e}")

    try:
        filename_status = f"sizing_results_status_code_matrix_{date_str}.csv"
        full_filepath_status = os.path.join(results_dir, filename_status)
        
        with open(full_filepath_status, 'w', encoding='utf_8_sig') as f:
            for soc in initial_soc_range:
                f.write(f"\n--- Initial SOC: {soc}% ---\n\n")
                df_soc = results_df[results_df['initial_soc'] == soc]

                pivot_df = df_soc.pivot_table(
                    index='pv_kw', 
                    columns='battery_kw', 
                    values='status_code',
                    aggfunc='first'
                )
                pivot_df.to_csv(f)
                f.write("\n")

    except Exception as e:
        print(f"An error occurred during status code matrix CSV export: {e}")

    try:
        filename_reason = f"sizing_results_reason_matrix_{date_str}.csv"
        full_filepath_reason = os.path.join(results_dir, filename_reason)

        with open(full_filepath_reason, 'w', encoding='utf_8_sig') as f:
            for soc in initial_soc_range:
                f.write(f"\n--- Initial SOC: {soc}% ---\n\n")
                df_soc = results_df[results_df['initial_soc'] == soc]

                pivot_df = df_soc.pivot_table(
                    index='pv_kw', 
                    columns='battery_kw', 
                    values='failure_reason',
                    aggfunc='first'
                )
                pivot_df.to_csv(f)
                f.write("\n")

    except Exception as e:
        print(f"An error occurred during failure reason matrix export: {e}")
        
        
        
#%% 'traversal' global parameter sweep analysis (Map Drawer): plot illustrating combinations with detailed failure reasons

def _categorize_failure_reason_final(reason_str):
    """
    Precisely map the original failure reason strings
    """
    if "Success" in reason_str:
        return "Success"

    if "Invalid Data" in reason_str:
        return "Invalid Data"

    if "Runtime Error" in reason_str: 
        return "Runtime Error"

    has_C = "Convergence" in reason_str
    has_V = "Voltage" in reason_str
    has_L = "Loading" in reason_str

    if has_C and has_V and has_L:
        return "Convergence Failure & Voltage Violation & Loading Violation"
    elif has_C and has_V:
        return "Convergence Failure & Voltage Violation"
    elif has_C and has_L:
        return "Convergence Failure & Loading Violation"
    elif has_V and has_L:
        return "Voltage Violation & Loading Violation"
    elif has_C:
        return "Convergence Failure"
    elif has_V:
        return "Voltage Violation"
    elif has_L:
        return "Loading Violation"

    if "OK But Battery Oversize" in reason_str:
        return "OK But Battery Oversize"    
    
    return "Unknown" 

def plot_feasibility_maps_with_reasons(results_df, pv_range, battery_range, initial_soc_range):
    """
    Plot a high-contrast feasible region scatter plot with a fixed, customized legend
    """
    print("\n--- Generating Sizing Feasibility Maps---")
    _setup_plot_style()

    reason_style_map = {
        'Success':                                     {'color': 'green',   'marker': 'o', 's': 50},
        'Invalid Data':                                {'color': 'brown',    'marker': 's', 's': 70}, # 新增样式
        'OK But Battery Oversize':                     {'color': 'cyan',    'marker': 'd', 's': 70}, # d for diamond
        'Convergence Failure':                         {'color': 'lightcoral', 'marker': 's', 's': 50},
        'Voltage Violation':                           {'color': 'blue',    'marker': 'v', 's': 60},
        'Loading Violation':                           {'color': 'orange',  'marker': 'D', 's': 50},
        'Convergence Failure & Voltage Violation':     {'color': 'red',     'marker': 'P', 's': 70},
        'Convergence Failure & Loading Violation':     {'color': 'magenta', 'marker': 'X', 's': 70},
        'Voltage Violation & Loading Violation':       {'color': 'purple',   'marker': 'h', 's': 70},
        'Convergence Failure & Voltage Violation & Loading Violation':   {'color': 'black',   'marker': '*', 's': 90},
    }

    for soc in initial_soc_range:
        fig, ax = plt.subplots(figsize=(18, 11))
        
        soc_results = results_df[results_df['initial_soc'] == soc].copy()
        if soc_results.empty:
            print(f"No results for SOC = {soc}%. Skipping plot.")
            plt.close(fig) 
            continue

        soc_results['category'] = soc_results['failure_reason'].apply(_categorize_failure_reason_final)

        for reason, style in reason_style_map.items():
            category_runs = soc_results[soc_results['category'] == reason]           
            if not category_runs.empty:
                ax.scatter(
                    category_runs['battery_kw'], 
                    category_runs['pv_kw'], 
                    c=style['color'],
                    marker=style['marker'],
                    s=style['s'],
                    alpha=0.9,
                    label=reason, 
                    edgecolors='k', 
                    linewidths=0.5
                )

        successful_runs = soc_results[soc_results['category'] == 'Success']
        if not successful_runs.empty:
            max_pv = successful_runs['pv_kw'].max()
            runs_with_max_pv = successful_runs[successful_runs['pv_kw'] == max_pv]
            min_battery_at_max_pv = runs_with_max_pv['battery_kw'].min()
            ax.scatter(
                [min_battery_at_max_pv], [max_pv],
                c='yellow',
                marker='*',
                s=300,
                edgecolor='black',
                label='Final Optimized Point',
                zorder=5 
            )

        ax.set_title(f'IBRNet/GridSize Constraint Diagnostic Map')
        ax.set_xlabel('Battery Rated Power (kW)')
        ax.set_ylabel('PV Rated Power (kW)')
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)
        ax.grid(True)
        
        ax.set_xlim(left=0, right=battery_range.max() * 1.05)
        ax.set_ylim(bottom=0, top=pv_range.max() * 1.05)

        plt.tight_layout(rect=[0, 0, 0.99, 0.99])
        plt.show()
        
#%% Hill-Climbing Optimization (Climber)
def generate_allSOC_optimization_plot(all_paths_by_soc):
    if not all_paths_by_soc:
        print("Warning: Optimization path data is empty. Skipping plot.")
        return

    _setup_plot_style()
    fig, ax = plt.subplots(figsize=(14, 9))
    colors = plt.cm.get_cmap('viridis', len(all_paths_by_soc))
    for i, (soc, path) in enumerate(all_paths_by_soc.items()):
        success_points = [p for p in path if p['success']]
        if len(success_points) > 1:
            success_points.sort(key=lambda p: (p['battery_kw'], p['pv_kw']))
            frontier_x = [p['battery_kw'] for p in success_points]
            frontier_y = [p['pv_kw'] for p in success_points]
            ax.plot(frontier_x, frontier_y, 
                    color=colors(i), 
                    linewidth=2.5, 
                    marker='.', 
                    markersize=8, 
                    label=f'Initial SOC = {soc}%')
    ax.set_title('PV-Battery Feasibility Frontier vs. Initial SOC')
    ax.set_xlabel('Battery Rated Active Power (kW)')
    ax.set_ylabel('PV Rated Active Power (kW)')
    ax.legend(title="Operating Condition")
    ax.grid(True, which='both', linestyle=':', linewidth=0.6)
    
    plt.tight_layout()
    plt.show()


def generate_optimization_plot(config, optimization_path, final_pv_kw, final_battery_kw):
    """
    Plot optimization hill-climbing path and final feasible boundary
    """
    print("Plotting Optimization Path...")
    if not optimization_path:
        print("Warning: Optimization path data is empty. Skipping plot.")
        return
    _setup_plot_style()
    
    initial_soc = config.dss_elements.StorageInfo.pct_energy_availabless[0]

    success_points = [p for p in optimization_path if p['success']]
    failure_points = [p for p in optimization_path if not p['success']]

    fig, ax = plt.subplots(figsize=(14, 8))
    
    if failure_points:
        fail_x = [p['battery_kw'] for p in failure_points]
        fail_y = [p['pv_kw'] for p in failure_points]
        ax.scatter(fail_x, fail_y, c='lightcoral', marker='x', label='Failure', s=50, zorder=2)

    if success_points:
        succ_x = [p['battery_kw'] for p in success_points]
        succ_y = [p['pv_kw'] for p in success_points]
        ax.scatter(succ_x, succ_y, c='mediumseagreen', marker='o', label='Success', s=50, zorder=3)

    if len(success_points) > 1:
        success_points.sort(key=lambda p: (p['battery_kw'], p['pv_kw']))
        frontier_x = [p['battery_kw'] for p in success_points]
        frontier_y = [p['pv_kw'] for p in success_points]

        ax.plot(frontier_x, frontier_y, 
                    color='gold', 
                    linewidth=2.5, 
                    marker='.', 
                    markersize=8, 
                    label=f'Feasibility Frontier', 
                    zorder=4)

    if final_pv_kw > 0:
        ax.scatter([final_battery_kw], [final_pv_kw], c='yellow', marker='*', s=300, edgecolor='black', label='Final Optimized Point', zorder=5)

    ax.set_title('IBRNet/GridSize Hill-Climbing Optimization Process')
    ax.set_xlabel('Battery Rated Power (kW)')
    ax.set_ylabel('PV Rated Power (kW)')
    ax.legend()
    ax.grid(True, which='both', linestyle=':', linewidth=0.6)
    
    max_x = max(p['battery_kw'] for p in optimization_path) * 1.1
    max_y = max(p['pv_kw'] for p in optimization_path) * 1.1
    ax.set_xlim(left=0, right=max_x if max_x > 0 else 1000)
    ax.set_ylim(bottom=0, top=max_y if max_y > 0 else 1000) # <-- 此处是关键修改

    plt.tight_layout()
    plt.show()    