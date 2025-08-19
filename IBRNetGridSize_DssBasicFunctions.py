# -*- coding: utf-8 -*-
"""
Created on Thu August 6 15:03:16 2025
Functions:
- Mode 1 (SINGLE_RUN): Perform a detailed 24-hour simulation for a single specified configuration    
- Mode 2 (TRAVERSAL): Globally traverse combinations of PV, energy storage, and SOC to plot the feasible region map (original bianliSIN)
- Mode 3 (OPTIMIZATION): Use hill-climbing algorithm to find the maximum PV and minimum energy storage that satisfy constraints (original mountainclimbing)

@author: Samuel Okhuegbe；Zhang Jian；Yayu(Andy) Yang
Most of the functions are not used, they are designed for other functions in our subsequent new versions.
"""

import numpy as np
import matplotlib.pyplot as plt

import re
import opendssdirect as dss
import math
import os
import cmath

#%% ------------HELPER FUNCTIONS----------------------------------------------------
def Radian2Degree(x):
    return (x*180)/np.pi

#%% Get Voltage At All Nodes and Buses
def Get_All_LN_Voltage_For_Full_Feeder(solve_converged):
    #Allnodename = dss.Circuit.AllNodeNames()
    if solve_converged:
        # get voltage magnitude in pu (each node)
        #Allnodename = dss.Circuit.AllNodeNames()
        AllVolMag = dss.Circuit.AllBusMagPu() # Get all bus voltage magnitude in pu
        AllVolMag = np.array(AllVolMag) #Shows LN Voltage
        Total_losses = np.array(dss.Circuit.Losses())*1e-3
        real_loss = Total_losses[0] # active power losses 
        All_Nodes_Bus_vol_LN = AllVolMag
    else:
        print("Case DIVERGED")
        All_Nodes_Bus_vol_LN = 0
        real_loss =0
        Total_losses=0
    return  All_Nodes_Bus_vol_LN,real_loss,Total_losses
#%%
def Get_All_PU_LN_Voltage_Feeder():
    # get voltage magnitude in pu (each node)
    AllVolMag = dss.Circuit.AllBusMagPu() # Get all bus voltage magnitude in pu
    #AllVolMag = np.array(AllVolMag) #Shows LN Voltage
    
    Total_losses = np.array(dss.Circuit.Losses())*1e-3
    real_loss = Total_losses[0] # active power losses 
    All_Nodes_Bus_vol_PU_LN = AllVolMag
   
    return  All_Nodes_Bus_vol_PU_LN, real_loss, Total_losses


#%% GET ACTUAL PHASE VOLTAGE MAGNITUDE AND ANGLES
def Get_Actual_Node_Voltage_and_Angle_LN():
    All_actual= dss.Circuit.AllBusVolts()
    half_length = int(len(All_actual)/2)
    Vol_mag = []
    Vol_angle = []
    for k in range(half_length):
        q= k*2
        val_one_real = All_actual[q]
        val_two_imag = All_actual[q+1]
        inp_num = complex(val_one_real, val_two_imag)
        Mag, Angl = cmath.polar(inp_num)
        Ang = Radian2Degree(Angl)
        Vol_mag.append(Mag)
        Vol_angle.append(Ang)
    return Vol_mag , Vol_angle


def Get_Actual_Node_Voltage_and_Angle_LL():
    all_bus_names =dss.Circuit.AllBusNames()
    Vol_mag_LL = []
    Vol_angle_LL = []
    for i in range(len(all_bus_names)):
        dss.Circuit.SetActiveBus(all_bus_names[i]) #set active bus
        vll_actual_list = dss.Bus.VLL()
        for k in range(int(len(vll_actual_list)/2)):
            q= k*2
            val_one_real = vll_actual_list[q]
            val_two_imag = vll_actual_list[q+1]
            inp_num = complex(val_one_real, val_two_imag)
            Mag, Angl = cmath.polar(inp_num)
            Ang = Radian2Degree(Angl)
            Vol_mag_LL.append(Mag)
            Vol_angle_LL.append(Ang)
    return Vol_mag_LL , Vol_angle_LL
#%%For load current
def Get_All_Load_Current(Allloads_Names):
    load_current_max = []
    for load_names in Allloads_Names:
        full_name = 'Load.' + load_names
        dss.Circuit.SetActiveElement(full_name)
        load_curr = dss.CktElement.Currents()
        tot_load_curr = len(load_curr)
        #Get the load current for each phase
        half_len = int(tot_load_curr/2)
        curr_mag = []
        curr_angle = []
        for i in range(half_len):
            p = i*2
            value_one_real = load_curr[p]
            value_two_imag = load_curr[p+1]
            input_num = complex(value_one_real, value_two_imag)
            r, phi = cmath.polar(input_num)
            curr_mag.append(r)
            curr_angle.append(phi)
        max_curr_mag = max(curr_mag)
        load_current_max.append(max_curr_mag)
    return load_current_max


#%%
#Get all loadbuses

def Get_All_Load_Data_For_Full_Feeder():
    Allloads_Names = dss.Loads.AllNames()
    idxx = dss.Loads.Idx() #Get Index of all loads. Index starts from 1
    #load_names = []
    load_kw = []
    load_kvar = []
    load_kVA = []
    load_model = []
    load_kv = []
    load_num_phase = []
    load_bus_connected_to =[]
    load_phase_connected_to = []
    for i in range(idxx):
        id_value = i+1
        #set the load with idvalue as active element
        dss.Loads.Idx(id_value)
        #get the power values for this activated load
        kw_load = dss.Loads.kW()
        #load_name = dss.Loads.Name()
        kvar_loads = dss.Loads.kvar()
        kvabase_loads = dss.Loads.kVABase()
        load_phases = dss.Loads.Phases()
        load_busname = dss.CktElement.BusNames() 
        
        dot_index = load_busname[0].find('.')
        load_bus_number = load_busname[0][:dot_index]
        load_bus_number = str(load_bus_number)
        if load_phases ==1:
            load_node_phase = load_busname[0][dot_index+1 : dot_index+2 ]
            load_node_phase = int(load_node_phase)
            load_phase_connected_to.append(load_node_phase)
        else:
            load_phase_connected_to.append(123) #Load is thee-phase
            
        #append values for each load
        #load_names.append(load_name)
        load_kw.append(kw_load)
        load_kvar.append(kvar_loads )
        load_kVA.append(kvabase_loads)
        load_model.append(dss.Loads.Model())
        load_kv.append(dss.Loads.kV())
        load_num_phase.append(load_phases)
        load_bus_connected_to.append(load_bus_number)
    return load_kVA,load_kw,load_kvar,load_model,load_kv,load_num_phase,load_bus_connected_to,load_phase_connected_to,Allloads_Names 
#Set back the full circuit as active

#%%

def Get_All_PVSystem_Data_For_Full_Feeder():
    All_PV_Names = dss.PVsystems.AllNames()
    idxx = dss.PVsystems.Idx() #Get Index of all loads. Index starts from 1
    #load_names = []
    pv_kw = []
    pv_kvar = []
    pv_kva = []
    pv_bus_connected_to =[]
    for i in range(idxx):
        id_value = i+1
        #set the load with idvalue as active element
        dss.PVsystems.Idx(id_value)
        #get the power values for this activated load
        kw_pv = dss.PVsystems.kW()
        #load_name = dss.Loads.Name()
        kvar_pv = dss.PVsystems.kvar()
        kva_pv = dss.PVsystems.kVARated()
        pv_busname = dss.CktElement.BusNames() 
        
        dot_index = pv_busname[0].find('.')
        pv_bus_number = pv_busname[0][:dot_index]
        pv_bus_number = str(pv_bus_number)
            
        #append values for each load
        #load_names.append(load_name)
        pv_kw.append(kw_pv)
        pv_kvar.append(kvar_pv )
        pv_kva.append(kva_pv)
        pv_bus_connected_to.append(pv_bus_number)
    return pv_kva, pv_kw,pv_kvar,pv_bus_connected_to,All_PV_Names 



#%%
def Get_All_Generator_Data_For_Full_Feeder():
    All_GEN_Names = dss.Generators.AllNames()
    idxx = dss.Generators.Idx() #Get Index of all loads. Index starts from 1
    #load_names = []
    gen_kw = []
    gen_kvar = []
    gen_kva = []
    gen_bus_connected_to =[]
    for i in range(idxx):
        id_value = i+1
        #set the load with idvalue as active element
        dss.Generators.Idx(id_value)
        #get the power values for this activated load
        kw_gen = dss.Generators.kW()
        kvar_gen = dss.Generators.kvar()
        kva_gen = dss.Generators.kVARated()
        gen_busname = dss.CktElement.BusNames() 
        
        dot_index = gen_busname[0].find('.')
        gen_bus_number = gen_busname[0][:dot_index]
        gen_bus_number = str(gen_bus_number)
            
        #append values for each load
        #load_names.append(load_name)
        gen_kw.append(kw_gen)
        gen_kvar.append(kvar_gen )
        gen_kva.append(kva_gen)
        gen_bus_connected_to.append(gen_bus_number)
    return gen_kva, gen_kw,gen_kvar,gen_bus_connected_to,All_GEN_Names 


#%%CALCULATE THE LOAD CURRENT PER PHASE

def Get_Load_Each_Phase_For_All_Feeder(load_bus_connected_to,load_kVA,load_kw,load_num_phase,load_kv,load_phase_connected_to):
    
    phase_one_ldcurrent = []
    phase_two_ldcurrent = []
    phase_three_ld_current = []

    #for i in range(len(load_bus_connected_to)):
    for i in range(len(load_bus_connected_to,load_kVA)):
        curr = load_kVA[i]/(np.sqrt(load_num_phase[i]) * load_kv[i])
        if  load_num_phase[i] ==3:
            phase_one_ldcurrent.append(curr)
            phase_two_ldcurrent.append(curr)
            phase_three_ld_current.append(curr)
        elif load_num_phase[i] ==1 and load_phase_connected_to[i] ==1:
            phase_one_ldcurrent.append(curr)
        elif load_num_phase[i] ==1 and load_phase_connected_to[i] ==2:
            phase_two_ldcurrent.append(curr)
        elif load_num_phase[i] ==1 and load_phase_connected_to[i] ==3:
            phase_three_ld_current.append(curr)
        else:
            pass
            
    total_phase_one_ldcurr = sum(phase_one_ldcurrent) 
    total_phase_two_ldcurr = sum(phase_two_ldcurrent)
    total_phase_three_ldcurr = sum(phase_three_ld_current)
    
    return total_phase_one_ldcurr,total_phase_two_ldcurr,total_phase_three_ldcurr 


    
#%%  Gettin Current for PD Elements Lines, Transformers, Capacitors etc
#LOOK AT ONLY THE CURRENT GOING INTO THE ELEMENT
def Get_All_Element_Current(All_Element_Names):
    element_current_max = []
    for element_names in All_Element_Names:
        dss.Circuit.SetActiveElement(element_names)
        element_curr = dss.CktElement.Currents()
        tot_element_curr = len(element_curr)
        #Get the load current for each phase
        half_len = int(tot_element_curr/2)
        element_curr = element_curr[:half_len]
        half_half_len = int(len(element_curr)/2)
        curr_mag = []
        curr_angle = []
        for i in range(half_half_len):
            p = i*2
            value_one_real = element_curr[p]
            value_two_imag = element_curr[p+1]
            input_num = complex(value_one_real, value_two_imag)
            r, phi = cmath.polar(input_num)
            curr_mag.append(r)
            curr_angle.append(phi)
        max_curr_mag = max(curr_mag)
        element_current_max.append(max_curr_mag)  
    return element_current_max 


#%%

def create_loadshape(load_shape_name,npts_val:int,Pmult_val,Qmult_val,Mult_val,time_interval_code:str,interval_val,use_file_flag):
    cmd_parts = [f"New LoadShape.{load_shape_name}", f"npts={npts_val}", f"{time_interval_code}={interval_val}"]

    if use_file_flag == 1:
        if isinstance(Pmult_val, str) and Pmult_val: # Pmult_val is a file path
            cmd_parts.append(f"Pmult=(file={Pmult_val})")
        if isinstance(Qmult_val, str) and Qmult_val: # Qmult_val is a file path
            cmd_parts.append(f"Qmult=(file={Qmult_val})")
        if isinstance(Mult_val, str) and Mult_val and not (Pmult_val or Qmult_val) : # Mult_val is a file path, and Pmult/Qmult are not file paths
            cmd_parts.append(f"Mult=(file={Mult_val})")
        elif isinstance(Mult_val, str) and Mult_val and (Pmult_val or Qmult_val): # If Pmult/Qmult are also specified, Mult from file might be ignored or cause error depending on OpenDSS version. Usually, Pmult/Qmult take precedence if also loading from file.
             print(f"Warning: Mult file specified for Loadshape {load_shape_name} but Pmult or Qmult file also specified. Mult may be ignored.")
    else: # Data is provided directly as a list/tuple of values
        def format_direct_values(val_list):
            if isinstance(val_list, (list, tuple)) and val_list:
                return f"({', '.join(map(str, val_list))})" # OpenDSS expects (v1, v2, v3) or [v1, v2, v3] or "v1 v2 v3"
            return ""

        pmult_str = format_direct_values(Pmult_val)
        qmult_str = format_direct_values(Qmult_val)
        mult_str = format_direct_values(Mult_val)

        if pmult_str: cmd_parts.append(f"Pmult={pmult_str}")
        if qmult_str: cmd_parts.append(f"Qmult={qmult_str}")
        if mult_str and not (pmult_str or qmult_str): cmd_parts.append(f"Mult={mult_str}")
        elif mult_str and (pmult_str or qmult_str):
            print(f"Warning: Mult values specified for Loadshape {load_shape_name} but Pmult or Qmult also specified. Mult may be ignored.")

    string_name = " ".join(cmd_parts)
    return dss.Text.Command(string_name)

#%%
def create_multiple_loadshape(load_shape_namess,npts_valss,Pmult_valss,Qmult_valss,Mult_valss,time_interval_codess,interval_valss,use_file_flagss): 
    for g in range(len(load_shape_namess)):
        jj = create_loadshape(load_shape_namess[g],npts_valss[g],Pmult_valss[g],Qmult_valss[g],Mult_valss[g],time_interval_codess[g],interval_valss[g],use_file_flagss[g])
        
    return jj


#%%
def connect_one_inveter_control(inv_ctrl_name,DER_types:list,DER_names:list,inv_mode):
    #DER_types list of strings, DER_names list of names
    #DER Types are 'Storage' or 'PVSystem'
    #inv_mode are 'GFM'
    space = " "
    for i in range(len(DER_names)):
        space = space + str(DER_types[i])+"."+str(DER_names[i])+" "
         
    inv_connect = "New InvControl."+str(inv_ctrl_name)+" "+"DERList=["+str(space)+"]"+" "+"mode="+str(inv_mode)
    #print(inv_connect)
     
    return dss.Text.Command(inv_connect)
         
#%%
def connect_multiple_inveter_controls(inv_ctrl_namess,DER_typess:list,DER_namess:list,inv_modes):
    for g in range(len(inv_ctrl_namess)):
        inv_connect_ctrl = connect_one_inveter_control(inv_ctrl_namess[g],DER_typess[g],DER_namess[g],inv_modes[g])
    return inv_connect_ctrl
        
     

#%%

def Connect_A_New_Two_WindingTransformer(tnx_name,tnx_phases,tnx_windings,nodes:list, tnx_kva1,tnx_bus1_num,tnx_kv1,tnx_conn1, tnx_kva2,tnx_bus2_num,tnx_kv2, tnx_conn2, taps1,taps2, tnx_XHL):
    for t in range(len(nodes)):
        tnx_bus1_num = str(tnx_bus1_num) + "."+str(nodes[t])
        tnx_bus2_num = str(tnx_bus2_num) + "."+str(nodes[t])
        
    Trans_connect= "New Transformer."+str(tnx_name)+" "+"phases="+str(tnx_phases)+" "+"windings="+str(tnx_windings)+" "+"buses=("+str(tnx_bus1_num)+" "+str(tnx_bus2_num)+")"+" "+"conns=("+str(tnx_conn1)+" "+str(tnx_conn2)+")"+" "+"kvs=("+str(tnx_kv1)+" "+str(tnx_kv2)+")"+" "+"kvas=("+str(tnx_kva1)+" "+str(tnx_kva2)+")"+" "+"taps=("+str(taps1)+" "+str(taps2)+")"+" "+"XHL="+str(tnx_XHL) 
    #print(Trans_connect)
    
    return dss.Text.Command(Trans_connect)
#%%
def Connect_Multiple_Two_WindingTransformer(tnx_namess,tnx_phasess,tnx_windingss,nodess, tnx_kva1ss,tnx_bus1_numss,tnx_kv1ss,tnx_conn1ss, tnx_kva2ss,tnx_bus2_numss,tnx_kv2ss, tnx_conn2ss, taps1ss,taps2ss, tnx_XHLss):
    for g in range(len(tnx_namess)):
        tnx_connect = Connect_A_New_Two_WindingTransformer(tnx_namess[g],tnx_phasess[g],tnx_windingss[g],nodess[g], tnx_kva1ss[g],tnx_bus1_numss[g],tnx_kv1ss[g],tnx_conn1ss[g], tnx_kva2ss[g],tnx_bus2_numss[g],tnx_kv2ss[g], tnx_conn2ss[g], taps1ss[g],taps2ss[g], tnx_XHLss[g])

    return tnx_connect


#%%
def Connect_A_New_Storage(storage_name:str,bus1_num,nodes:list, phases:int,bus_kv, inverter_kva,storage_kwrated, storage_kvar,storage_kwhrated,pct_energy_available, pct_min_reserve_req,storage_state,sto_IdlingkW=1,model_code=1,sto_conn='wye',daily_shape_sto_val='snap',yearly_shape_sto_val='snap'):
    for t in range(len(nodes)):
        bus1_num = str(bus1_num) + "."+str(nodes[t])
        
    max_storage_kvar = np.sqrt(np.square(inverter_kva) - np.square(storage_kwrated) )
    if storage_kvar>max_storage_kvar:
        #the default in open dss calculate the available power in a different way
        #so we added this code to calculate the actual available kvar left based on specified kva
        storage_kvar=max_storage_kvar
    else:
        storage_kvar = storage_kvar 
            
        
        
    if daily_shape_sto_val=='snap' and yearly_shape_sto_val=='snap' :
        storage_string = "New Storage."+str(storage_name)+" "+"bus1="+bus1_num+" "+"phases="+str(phases)+" "+"kV="+str(bus_kv)+" "+"kva="+str(inverter_kva)+" "+"kWrated="+str(storage_kwrated)+" "+"kvar="+str(storage_kvar)+" "+"kWhrated="+str(storage_kwhrated)+" "+"%stored="+str(pct_energy_available)+" "+"%reserve="+str(pct_min_reserve_req)+" " \
            +"%IdlingkW="+str(sto_IdlingkW)+" "+"State="+str(storage_state)+" "+"model="+str(model_code)+" "+"conn="+str(sto_conn)
    elif daily_shape_sto_val == 'snap' and yearly_shape_sto_val != 'snap':
        storage_string = "New Storage."+str(storage_name)+" "+"bus1="+bus1_num+" "+"phases="+str(phases)+" "+"kV="+str(bus_kv)+" "+"kva="+str(inverter_kva)+" "+"kWrated="+str(storage_kwrated)+" "+"kvar="+str(storage_kvar)+" "+"kWhrated="+str(storage_kwhrated)+" "+"%stored="+str(pct_energy_available)+" "+"%reserve="+str(pct_min_reserve_req)+" " \
            +"%IdlingkW="+str(sto_IdlingkW)+" "+"State="+str(storage_state)+" "+"model="+str(model_code)+" "+"conn="+str(sto_conn)+" "+"yearly="+str(yearly_shape_sto_val)
    elif daily_shape_sto_val != 'snap' and yearly_shape_sto_val == 'snap':
        storage_string = "New Storage."+str(storage_name)+" "+"bus1="+bus1_num+" "+"phases="+str(phases)+" "+"kV="+str(bus_kv)+" "+"kva="+str(inverter_kva)+" "+"kWrated="+str(storage_kwrated)+" "+"kvar="+str(storage_kvar)+" "+"kWhrated="+str(storage_kwhrated)+" "+"%stored="+str(pct_energy_available)+" "+"%reserve="+str(pct_min_reserve_req)+" " \
            +"%IdlingkW="+str(sto_IdlingkW)+" "+"State="+str(storage_state)+" "+"model="+str(model_code)+" "+"conn="+str(sto_conn)+" "+"daily="+str(daily_shape_sto_val)
    else:
        
        print("Check Data: Assuming Snaphot")
        storage_string = "New Storage."+str(storage_name)+" "+"bus1="+bus1_num+" "+"phases="+str(phases)+" "+"kV="+str(bus_kv)+" "+"kva="+str(inverter_kva)+" "+"kWrated="+str(storage_kwrated)+" "+"kvar="+str(storage_kvar)+" "+"kWhrated="+str(storage_kwhrated)+" "+"%stored="+str(pct_energy_available)+" "+"%reserve="+str(pct_min_reserve_req)+" " \
            +"%IdlingkW="+str(sto_IdlingkW)+" "+"State="+str(storage_state)+" "+"model="+str(model_code)+" "+"conn="+str(sto_conn)
            
    #print(storage_string)
    return dss.Text.Command(storage_string)


#%%

def Connect_Multiple_Storage(storage_namess, store_bus1_numss, store_nodess, store_phasess, store_bus_kvss, inverter_kvass, storage_kwratedss, storage_kvarss, storage_kwhratedss, pct_energy_availabless, pct_min_reserve_reqss, storage_statess, sto_IdlingkWss, sto_model_codess, sto_connss, daily_shape_sto_valss, yearly_shape_sto_valss):
    for g in range(len(storage_namess)):
        Connect_A_New_Storage(storage_namess[g], store_bus1_numss[g], store_nodess[g], store_phasess[g], store_bus_kvss[g], inverter_kvass[g], storage_kwratedss[g], storage_kvarss[g], storage_kwhratedss[g], pct_energy_availabless[g], pct_min_reserve_reqss[g], storage_statess[g], sto_IdlingkWss[g], sto_model_codess[g], sto_connss[g], daily_shape_sto_valss[g], yearly_shape_sto_valss[g])
    return True          
   
#%%
def Connect_A_New_Generator(gen_name:str,bus1_num,nodes:list, phases:int,bus_kv, gen_kva,gen_kw, gen_kvar, model_code:int,gen_conn='wye',daily_shape_gen_val='snap',yearly_shape_gen_val='snap'):
    for t in range(len(nodes)):
        bus1_num = str(bus1_num) + "."+str(nodes[t])
        
    max_gen_kvar = np.sqrt(np.square(gen_kva) - np.square(gen_kw) )
    if gen_kvar>max_gen_kvar:
        #the default in open dss calculate dthe available power in a different way
        #so we added this code to calculate the actual available kvar left based on specified kva
        gen_kvar=max_gen_kvar
    else:
        gen_kvar = gen_kvar 
        
        
        
    if daily_shape_gen_val=='snap' and yearly_shape_gen_val=='snap' :
        new_gen_connect = "New Generator."+str(gen_name)+" "+"bus1="+bus1_num+" "+"phases="+str(phases)+" "+"kV="+str(bus_kv)+" "+"kVA="+str(gen_kva)+" "+"kW="+str(gen_kw)+" "+"kVAR="+str(gen_kvar)+" "+"model="+str(model_code)+" "+"conn="+str(gen_conn)   
    elif daily_shape_gen_val == 'snap' and yearly_shape_gen_val != 'snap':
        new_gen_connect = "New Generator."+str(gen_name)+" "+"bus1="+bus1_num+" "+"phases="+str(phases)+" "+"kV="+str(bus_kv)+" "+"kVA="+str(gen_kva)+" "+"kW="+str(gen_kw)+" "+"kVAR="+str(gen_kvar)+" "+"model="+str(model_code)+" "+"yearly="+str(yearly_shape_gen_val)+" "+"conn="+str(gen_conn) 
    elif daily_shape_gen_val != 'snap' and yearly_shape_gen_val == 'snap':
        new_gen_connect = "New Generator."+str(gen_name)+" "+"bus1="+bus1_num+" "+"phases="+str(phases)+" "+"kV="+str(bus_kv)+" "+"kVA="+str(gen_kva)+" "+"kW="+str(gen_kw)+" "+"kVAR="+str(gen_kvar)+" "+"model="+str(model_code)+" "+"daily="+str(daily_shape_gen_val)+" "+"conn="+str(gen_conn)
    else:
        print("Check Data: Assuming Snaphot")
        new_gen_connect = "New Generator."+str(gen_name)+" "+"bus1="+bus1_num+" "+"phases="+str(phases)+" "+"kV="+str(bus_kv)+" "+"kVA="+str(gen_kva)+" "+"kW="+str(gen_kw)+" "+"kVAR="+str(gen_kvar)+" "+"model="+str(model_code)+" "+"conn="+str(gen_conn)
    
    #print(new_gen_connect)
    return dss.Text.Command(new_gen_connect)


#%%

def Connect_Multiple_Generators(gen_names, gen_bus1_nums, gen_nodess, gen_phasess, gen_bus_kvs, gen_kvas, gen_kws, gen_kvars, gen_model_codes, gen_connss, daily_shape_gen_valss, yearly_shape_gen_valss):
    for g in range(len(gen_names)):
        Connect_A_New_Generator(gen_names[g], gen_bus1_nums[g], gen_nodess[g], gen_phasess[g], gen_bus_kvs[g], gen_kvas[g], gen_kws[g], gen_kvars[g], gen_model_codes[g], gen_connss[g], daily_shape_gen_valss[g], yearly_shape_gen_valss[g])
    return True   



#%%
def Connect_A_New_PVsystem(pv_name:str,bus1_num,nodes:list,phases:int,pv_bus_kv, pv_kva,pv_pmpp_kw, pv_kvar,irrad_val=1,model_code=1,daily_shape_val='snap',conn_val='wye',yearly_shape_val='snap', pv_pf_val=None):
    bus1_full_name = str(bus1_num)
    if nodes and nodes[0] is not None:
         bus1_full_name += "." + ".".join(map(str, nodes))
    
    base_cmd = f"New PVSystem.{pv_name} bus1={bus1_full_name} phases={phases} kV={pv_bus_kv} kva={pv_kva} pmpp={pv_pmpp_kw} model={model_code} conn={conn_val} irradiance={irrad_val}"
    
    if pv_pf_val is not None and pv_pf_val != 0:
        q_control_cmd = f"pf={pv_pf_val}"
    else:
        max_pv_kvar = np.sqrt(np.square(pv_kva) - np.square(pv_pmpp_kw)) if pv_kva > pv_pmpp_kw else 0
        if abs(pv_kvar) > max_pv_kvar:
            pv_kvar = max_pv_kvar * np.sign(pv_kvar)
        q_control_cmd = f"kvar={pv_kvar}"

    final_cmd = f"{base_cmd} {q_control_cmd}"
    
    if daily_shape_val and daily_shape_val.lower() != 'snap':
        final_cmd += f" daily={daily_shape_val}"
    if yearly_shape_val and yearly_shape_val.lower() != 'snap':
        final_cmd += f" yearly={yearly_shape_val}"
        
    return dss.Text.Command(final_cmd)

def Connect_Multiple_PVsystems(pv_namess, pv_bus1_nums, pv_nodess, pv_phasess, pv_bus_kvss,
                               pv_kvass, pv_pmpp_kwss, pv_kvarss, pv_irad_valss,
                               pv_model_codess, pv_daily_shape_valss, pv_conn_valss,
                               pv_yearly_shape_valss, pv_pf_ss, **kwargs):
    for g in range(len(pv_namess)):
        pf_val_for_this_pv = pv_pf_ss[g] if g < len(pv_pf_ss) else None
        Connect_A_New_PVsystem(
            pv_namess[g], pv_bus1_nums[g], pv_nodess[g], pv_phasess[g],
            pv_bus_kvss[g], pv_kvass[g], pv_pmpp_kwss[g], pv_kvarss[g],
            pv_pf_val=pf_val_for_this_pv,
            irrad_val=pv_irad_valss[g],
            model_code=pv_model_codess[g],
            daily_shape_val=pv_daily_shape_valss[g],
            conn_val=pv_conn_valss[g],
            yearly_shape_val=pv_yearly_shape_valss[g]
        )
    return True




#%%
def isource_PandQ_Values_using_solved_data(device_name:str,device_nodes:list,phases:int,mach_type_dssname):
    #gen_string = 'Generator.'+generator_name, 'PVsystem', 'Storage'
    gen_string = str(mach_type_dssname)+'.'+str(device_name)
    dss.Circuit.SetActiveElement(gen_string)
    #print('Active Element is:',dss.CktElement.Name())
    injected_power_gen = dss.CktElement.Powers()
    Pg_list = []
    Qg_list = []
    for i in range(len(device_nodes)):
        p = i*2
        Pi = injected_power_gen[p]
        Qi = injected_power_gen[p+1]
        Pg_list.append(Pi)
        Qg_list.append(Qi)
    return Pg_list,Qg_list
#%%
def isource_GenPandQ_Values_using_gen_data(generator_name:str,gen_nodes:list,phases:int):
    gen_string = 'Generator.'+generator_name
    dss.Circuit.SetActiveElement(gen_string)
    #print('Active Element is:',dss.CktElement.Name())
    injected_power_gen = dss.CktElement.Powers()
    Pg_list = []
    Qg_list = []
    for i in range(phases):
        p = i*2
        Pi = injected_power_gen[p]
        Qi = injected_power_gen[p+1]
        Pg_list.append(Pi)
        Qg_list.append(Qi)
    return Pg_list,Qg_list
#%%

def isource_vrms_theta_using_bus_data(generator_bus_num,gen_nodes:list,phases:int,All_Nodename,actual_vmag:list,actual_vangle:list):
    vrms_list = []
    vangle_list = []
    for i in range(phases):
        gen_naming = str(generator_bus_num) + "."+str(gen_nodes[i])
        gen_naming_lower = gen_naming.lower()
        #print(gen_naming)
        idx= All_Nodename.index(gen_naming_lower)
        vrms =actual_vmag[idx]
        vangle = actual_vangle[idx]
        vrms_list.append(vrms)
        vangle_list.append(vangle)
    return vrms_list,vangle_list

def isource_per_phase_vrms_theta_using_solved_bus_data(device_bus_num,device_nodes:list,phases:int,All_Nodename,actual_vmag:list,actual_vangle:list):
    vrms_list = []
    vangle_list = []
    for i in range(len(device_nodes)):
        gen_naming = str(device_bus_num) + "."+str(device_nodes[i])
        gen_naming_lower = gen_naming.lower()
        #print(gen_naming)
        idx= All_Nodename.index(gen_naming_lower)
        vrms =actual_vmag[idx]
        vangle = actual_vangle[idx]
        vrms_list.append(vrms)
        vangle_list.append(vangle)
    return vrms_list,vangle_list
#%%
def Calculate_isource_Amps_and_Angle(Pg_list,Qg_list,vangle_list,vrms_list,phases):
    iamp_list = []
    iangle_list = []
    for i in range(phases):
        Pg_i =abs(Pg_list[i])
        Qg_i = abs(Qg_list[i])
        iamp = np.sqrt(sum(np.square([Pg_i,Qg_i]))) / (vrms_list[i]/1000)
        iangle = vangle_list[i] - Radian2Degree(np.arctan(Qg_i/Pg_i))
        iamp_list.append(iamp)
        iangle_list.append(iangle)
    return iamp_list, iangle_list

def Calculate_isource_Amps_and_Angle_2(Pg_list,Qg_list,vangle_list,vrms_list,phases):
    iamp_list = []
    iangle_list = []
    if phases == 3:
        Pg_i =abs(Pg_list)
        Qg_i = abs(Qg_list)
        iamp = np.sqrt(sum(np.square([Pg_i,Qg_i]))) / (vrms_list/1000)
        iangle = vangle_list - Radian2Degree(np.arctan(Qg_i/Pg_i))
        iamp_list.append(iamp)
        iangle_list.append(iangle)
        
    else:  
        for i in range(phases):
            Pg_i =abs(Pg_list[i])
            Qg_i = abs(Qg_list[i])
            iamp = np.sqrt(sum(np.square([Pg_i,Qg_i]))) / (vrms_list[i]/1000)
            iangle = vangle_list[i] - Radian2Degree(np.arctan(Qg_i/Pg_i))
            iamp_list.append(iamp)
            iangle_list.append(iangle)
    return iamp_list, iangle_list

#%%
def connect_isources_for_main_gen(iamp_list:list,iangle_list:list,isource_name:str,gen_name:str,gen_bus_num:int,gen_connected_nodes:list,phases:int):
    #First Disconnect that Generator
    #Gen_Naming = 'Generator.'+str(gen_name)
    #gen_disconnect_string = 'Edit'+' '+'Generator.'+str(gen_name)+' '+'enabled=No'
    #dss.Text.Command(gen_disconnect_string)
    
    for t in range(phases):
        bus1 = str(gen_bus_num) +'.'+ str(gen_connected_nodes[t])
        iamp = iamp_list[t]
        iangle = iangle_list[t]
        isource_naming = isource_name + gen_name + str(t)
        isource_string = 'New Isource.'+isource_naming+'_'+str(gen_connected_nodes[t])+' '+'bus1='+bus1+' '+'phases='+str(1)+' '+'angle='+str(iangle)+' '+'amps='+str(iamp)
        #print(isource_string)
        dss.Text.Command(isource_string)
    return None


def connect_isources_for_main_2(iamp_list:list,iangle_list:list,isource_name:str,gen_name:str,gen_bus_num:int,gen_connected_nodes:list,phases:int):
    #First Disconnect that Generator
    #Gen_Naming = 'Generator.'+str(gen_name)
    #gen_disconnect_string = 'Edit'+' '+'Generator.'+str(gen_name)+' '+'enabled=No'
    #dss.Text.Command(gen_disconnect_string)
    if phases ==3:
        for t in range(phases):
            bus1 = str(gen_bus_num) +'.'+ str(gen_connected_nodes[t])
        iamp = iamp_list[0]
        iangle = iangle_list[0]
        isource_naming = isource_name + gen_name
        isource_string = 'New Isource.'+isource_naming+'_'+str(gen_connected_nodes[t])+' '+'bus1='+bus1+' '+'phases='+str(3)+' '+'angle='+str(iangle)+' '+'amps='+str(iamp)
        #print(isource_string)
        dss.Text.Command(isource_string)
    else:      
        for t in range(phases):
            bus1 = str(gen_bus_num) +'.'+ str(gen_connected_nodes[t])
            iamp = iamp_list[t]
            iangle = iangle_list[t]
            isource_naming = isource_name + gen_name + str(t)
            isource_string = 'New Isource.'+isource_naming+'_'+str(gen_connected_nodes[t])+' '+'bus1='+bus1+' '+'phases='+str(1)+' '+'angle='+str(iangle)+' '+'amps='+str(iamp)
            #print(isource_string)
            dss.Text.Command(isource_string)
    return None
#%%

def Calculate_isource_Amps_and_Angle_using_input(Pg_value,Qg_value,vangle_num,vrms_num,phases):
    iamp = np.sqrt(sum(np.square([Pg_value,Qg_value]))) / (vrms_num/1000)
    iangle = vangle_num - Radian2Degree(np.arctan(Qg_value/Pg_value))
    
    return iamp, iangle


def connect_isources_using_input(iamp,iangle,isource_name,isource_nodes:list,bus1_num,isource_phases:int):
    for t in range(len(isource_nodes)):
        bus1_num = str(bus1_num) + "."+str(isource_nodes[t])
        isource_name = str(isource_name)
        isource_string = 'New Isource.'+isource_name+' '+'bus1='+bus1_num+' '+'phases='+str(isource_phases)+' '+'angle='+str(iangle)+' '+'amps='+str(iamp)
        #print(isource_string)
        dss.Text.Command(isource_string)
    return None
#%%
def get_gen_injected_powers():
    all_generator_names = dss.Generators.AllNames()
    gen_powers_list_of_list = []
    gen_total_real_power_list = []
    gen_total_reactive_power_list = []
    for i in range(len(all_generator_names)):
        gens_name = 'Generator.'+ all_generator_names[i]
        dss.Circuit.SetActiveElement(gens_name)
        dss.CktElement.Name()
        gen_injected_power = dss.CktElement.Powers()
        gen_powers_list_of_list.append(gen_injected_power)
        gen_real_power_list = []
        gen_reactive_power_list = [] 
        for j in range(len(gen_injected_power)):
            if j%2 ==0:
                gen_real_power_list.append(gen_injected_power[j])
            else:
                gen_reactive_power_list.append(gen_injected_power[j])
        gen_total_real_power_list.append(sum(gen_real_power_list))
        gen_total_reactive_power_list.append(sum(gen_reactive_power_list))
        
    return all_generator_names,gen_powers_list_of_list,gen_total_real_power_list,gen_total_reactive_power_list
        
def get_isource_injected_powers():
    isource_names_all = dss.Isource.AllNames()
    isource_powers_list_of_list = []
    isource_total_real_power = []
    isource_total_reactive_power = []
    for i in range(len(isource_names_all)):
        isource_name = 'Isource.'+ isource_names_all[i]
        dss.Circuit.SetActiveElement(isource_name)
        dss.CktElement.Name()
        isource_injected_power = dss.CktElement.Powers()
        isource_powers_list_of_list.append(isource_injected_power)
        isource_real_power_list = []
        isource_reactive_power_list = []       
        for j in range(len(isource_injected_power)):
            if j%2 ==0:
                isource_real_power_list.append(isource_injected_power[j])
            else:
                isource_reactive_power_list.append(isource_injected_power[j])
        isource_total_real_power.append(sum(isource_real_power_list))
        isource_total_reactive_power.append(sum(isource_reactive_power_list))        
        
    return isource_names_all,isource_powers_list_of_list ,isource_total_real_power, isource_total_reactive_power    
        

def get_pv_injected_powers():
    pvsystem_names_all = dss.PVsystems.AllNames()
    pvsystem_powers_list_of_list = []
    pv_system_total_real_power = []
    pv_system_total_reactive_power = []
    for i in range(len(pvsystem_names_all)):
        pvsystem_name = 'PVsystem.'+ pvsystem_names_all[i]
        dss.Circuit.SetActiveElement(pvsystem_name)
        dss.CktElement.Name()
        pvsystem_injected_power = dss.CktElement.Powers()
        pvsystem_powers_list_of_list.append(pvsystem_injected_power)
        pv_real_power_list = []
        pv_reactive_power_list = []
        for j in range(len(pvsystem_injected_power)):
            if j%2 ==0:
                pv_real_power_list.append(pvsystem_injected_power[j])
            else:
                pv_reactive_power_list.append(pvsystem_injected_power[j])
        pv_system_total_real_power.append(sum(pv_real_power_list))
        pv_system_total_reactive_power.append(sum(pv_reactive_power_list))
            
    return pvsystem_names_all,pvsystem_powers_list_of_list,pv_system_total_real_power,pv_system_total_reactive_power


def get_storage_injected_powers():
    sto_system_names_all = dss.Storages.AllNames()
    sto_system_powers_list_of_list = []
    sto_total_real_power_list = []
    sto_total_reactive_power_list = []
    for i in range(len(sto_system_names_all)):
        sto_system_name = 'Storage.'+ sto_system_names_all[i]
        dss.Circuit.SetActiveElement(sto_system_name)
        dss.CktElement.Name()
        sto_system_injected_power = dss.CktElement.Powers()
        sto_system_powers_list_of_list.append(sto_system_injected_power)
        sto_real_power_list = []
        sto_reactive_power_list = []
        for j in range(len(sto_system_injected_power)):
            if j%2 ==0:
                sto_real_power_list.append(sto_system_injected_power[j])
            else:
                sto_reactive_power_list.append(sto_system_injected_power[j])
        sto_total_real_power_list.append(sum(sto_real_power_list))
        sto_total_reactive_power_list.append(sum(sto_reactive_power_list))       
        
        
    return sto_system_names_all,sto_system_powers_list_of_list,sto_total_real_power_list,sto_total_reactive_power_list


def editing_load_daily_yearly(load_name,type_name='daily',loadshape_name= 'default'):
    #type_name = 'daily' or yearly
    load_chang_string = "Edit Load."+str(load_name)+" "+str(type_name)+"="+str(loadshape_name)
    #print(load_chang_string)
    return dss.Text.Command(load_chang_string)
    
def editing_multiple_load_loadshapes(load_names_lists,type_namess,loadshape_namess):
    for g in range(len(load_names_lists)):
        editing_string = editing_load_daily_yearly(load_names_lists[g],type_namess[g],loadshape_namess[g])
    return editing_string


def editing_deviceloadshape_daily_yearly(device_type,device_name,type_name='daily',loadshape_name= 'default'):
    #type_name = 'daily' or yearly
    #device_type is "PVSystem", "Load","Generator","Storage"
    device_chang_string = "Edit "+str(device_type)+"." +str(device_name)+" "+str(type_name)+"="+str(loadshape_name)
    #print(device_chang_string)
    return dss.Text.Command(device_chang_string)
    
def editing_multiple_device_loadshapes(device_typess,device_namess,type_namess,loadshape_namess):
    for g in range(len(device_namess)):
        editing_device_string = editing_deviceloadshape_daily_yearly(device_typess[g],device_namess[g],type_namess[g],loadshape_namess[g])
    return editing_device_string
            
#%% loadshape


def edit_assign_load_loadshape(change_all_loads,change_loads_type_names,change_loads_loadshape_names,Load_names_to_Edit,Load_type_names_to_Edit,Load_loadshape_names_to_Edit):
    Allloads_Names = dss.Loads.AllNames()
    
    if len(Load_names_to_Edit)!=0:
        #print("Editting Load")
        edit_load_shapes = editing_multiple_load_loadshapes(Load_names_to_Edit,Load_type_names_to_Edit,Load_loadshape_names_to_Edit)
    elif len(Load_names_to_Edit) ==0 and change_all_loads == 1 :
        #Change Every Thing
        type_namess = []
        for i in range(len(Allloads_Names)):
            type_namess.append(str(change_loads_type_names))
        loadshape_namess = []
        for i in range(len(Allloads_Names)):
            loadshape_namess.append(str(change_loads_loadshape_names))
        edit_load_shapes = editing_multiple_load_loadshapes(Allloads_Names,type_namess,loadshape_namess)
        
    #print(edit_load_shapes)
    return edit_load_shapes




def edit_assign_pvsystem_loadshapes(change_all_pvs,change_pvs_type_names,change_pv_loadshape_names,pv_names_to_Edit,pv_type_names_to_Edit,pv_loadshape_names_to_Edit):
    pvsystem_names_all = dss.PVsystems.AllNames()

    if len(pv_names_to_Edit)!=0:
        #print("Editting PVSystem Loadshape")
        #This part changes devices specified in the list of pv
        
        device_typess = []
        for j in range(len(pv_names_to_Edit)):
            device_typess.append("PVSystem")
    
        edit_pv_shapes = editing_multiple_device_loadshapes(device_typess,pv_names_to_Edit,pv_type_names_to_Edit ,pv_loadshape_names_to_Edit)
        
    elif change_all_pvs == 1 :
        #This part changes all the devices of type PVSystem

        #Change Every Thing
        pv_type_names_to_Edit = []
        for i in range(len(pvsystem_names_all)):
            pv_type_names_to_Edit.append(str(change_pvs_type_names))
            
        pv_loadshape_names_to_Edit = []
        for i in range(len(pvsystem_names_all)):
            pv_loadshape_names_to_Edit.append(str(change_pv_loadshape_names))
            
        device_typess = []
        for j in range(len(pvsystem_names_all)):
            device_typess.append("PVSystem")
            
            
        edit_pv_shapes = editing_multiple_device_loadshapes(device_typess,pvsystem_names_all,pv_type_names_to_Edit ,pv_loadshape_names_to_Edit)
    else:
        pass
 
    return edit_pv_shapes




def edit_assign_generator_loadshapes(change_all_gens,change_gens_type_names,change_gen_loadshape_names,gen_names_to_Edit,gen_type_names_to_Edit,gen_loadshape_names_to_Edit):
    all_generator_names = dss.Generators.AllNames()

    if len(gen_names_to_Edit)!=0:
        #print("Editting Generator Loadshape")
        #This part changes devices specified in the list of pv
        
        device_typess = []
        for j in range(len(gen_names_to_Edit)):
            device_typess.append("Generator")
    
        edit_gen_shapes = editing_multiple_device_loadshapes(device_typess,gen_names_to_Edit,gen_type_names_to_Edit ,gen_loadshape_names_to_Edit)
        
    elif change_all_gens == 1 :
        #This part changes all the devices of type PVSystem

        

        #Change Every Thing
        gen_type_names_to_Edit = []
        for i in range(len(all_generator_names)):
            gen_type_names_to_Edit.append(str(change_gens_type_names))
            
        gen_loadshape_names_to_Edit = []
        for i in range(len(all_generator_names)):
            gen_loadshape_names_to_Edit.append(str(change_gen_loadshape_names))
            
        device_typess = []
        for j in range(len(all_generator_names)):
            device_typess.append("Generator")
        
            
        edit_gen_shapes = editing_multiple_device_loadshapes(device_typess,all_generator_names,gen_type_names_to_Edit ,gen_loadshape_names_to_Edit)
    else:
        pass
        
    return edit_gen_shapes




def edit_assign_storage_loadshapes(change_all_sto,change_sto_type_names,change_sto_loadshape_names,sto_names_to_Edit,sto_type_names_to_Edit,sto_loadshape_names_to_Edit):
    sto_system_names_all = dss.Storages.AllNames()

    if len(sto_names_to_Edit)!=0:
        #print("Editting Storage Loadshape")
        #This part changes devices specified in the list of pv
        
        device_typess = []
        for j in range(len(sto_names_to_Edit)):
            device_typess.append("Storage")
    
        edit_sto_shapes = editing_multiple_device_loadshapes(device_typess,sto_names_to_Edit,sto_type_names_to_Edit ,sto_loadshape_names_to_Edit)
        
    elif change_all_sto == 1 :
        #This part changes all the devices of type PVSystem

        #Change Every Thing
        sto_type_names_to_Edit = []
        for i in range(len(sto_system_names_all)):
            sto_type_names_to_Edit.append(str(change_sto_type_names))
            
        sto_loadshape_names_to_Edit = []
        for i in range(len(sto_system_names_all)):
            sto_loadshape_names_to_Edit.append(str(change_sto_loadshape_names))
            
        device_typess = []
        for j in range(len(sto_system_names_all)):
            device_typess.append("Storage")
            
            
        edit_sto_shapes = editing_multiple_device_loadshapes(device_typess,sto_system_names_all,sto_type_names_to_Edit ,sto_loadshape_names_to_Edit)
    else:
        pass
        
    return edit_sto_shapes



#%%
def scale_all_loads_uniformly(n,load_kw,load_kvar, use_actual_total_loads_to_scale,maintain_p_q_ratio_flag,original_total_load_kw,original_total_load_kvar,Allloads_Names,new_total_load_kvar_list,new_total_load_kw_list,Load_scaling_percent_kvar_list,Load_scaling_percent_kw_list):
    
    if use_actual_total_loads_to_scale == 1:
        pct_load_change_kw = ((new_total_load_kw_list[n] - original_total_load_kw)/original_total_load_kw)
        pct_load_change_kw = pct_load_change_kw +1
        if maintain_p_q_ratio_flag == 1:
            pct_load_change_kvar = pct_load_change_kw
        else:
            pct_load_change_kvar = ((new_total_load_kvar_list[n] - original_total_load_kvar)/original_total_load_kvar)
            pct_load_change_kvar = pct_load_change_kvar +1
    else:
        pct_load_change_kw = Load_scaling_percent_kw_list[n]
        if maintain_p_q_ratio_flag == 1:
            pct_load_change_kvar = pct_load_change_kw
        else:
            pct_load_change_kvar =Load_scaling_percent_kvar_list[n]         
    
    for i in range(len(Allloads_Names)):
        load_name_i = Allloads_Names[i]
        #print("Changing for load: ", str(load_name_i))
        load_Pkw_new = load_kw[i] * pct_load_change_kw
        load_Qkvar_new = load_kvar[i] * pct_load_change_kvar
        load_edit_string = "Edit Load."+str(load_name_i)+" "+"kW="+str(load_Pkw_new)+" "+"kvar="+str(load_Qkvar_new)
        #print(load_edit_string)
        #print("The percent used is: ",pct_load_change_kw)
        ld = dss.Text.Command(load_edit_string)
    return ld
#%%
def scale_all_loads_uniformly_snap(load_kw,load_kvar, use_actual_total_loads_to_scale,maintain_p_q_ratio_flag,original_total_load_kw,original_total_load_kvar,Allloads_Names,new_total_load_kvar,new_total_load_kw,Load_scaling_percent_kvar,Load_scaling_percent_kw):
    #print("Activating Load Scaling")
    if use_actual_total_loads_to_scale == 1:
        pct_load_change_kw = ((new_total_load_kw - original_total_load_kw)/original_total_load_kw)
        pct_load_change_kw = pct_load_change_kw +1
        if maintain_p_q_ratio_flag == 1:
            pct_load_change_kvar = pct_load_change_kw
        else:
            pct_load_change_kvar = ((new_total_load_kvar - original_total_load_kvar)/original_total_load_kvar)
            pct_load_change_kvar = pct_load_change_kvar +1
    else:
        pct_load_change_kw = Load_scaling_percent_kw
        if maintain_p_q_ratio_flag == 1:
            pct_load_change_kvar = pct_load_change_kw
        else:
            pct_load_change_kvar =Load_scaling_percent_kvar         
    
    for i in range(len(Allloads_Names)):
        load_name_i = Allloads_Names[i]
        #print("Changing for load: ", str(load_name_i))
        load_Pkw_new = load_kw[i] * pct_load_change_kw
        load_Qkvar_new = load_kvar[i] * pct_load_change_kvar
        load_edit_string = "Edit Load."+str(load_name_i)+" "+"kW="+str(load_Pkw_new)+" "+"kvar="+str(load_Qkvar_new)
        #print(load_edit_string)
        #print("The percent used is: ",pct_load_change_kw)
        ld = dss.Text.Command(load_edit_string)
    return ld

#%%
def scale_all_loads_uniformly_timeseres(Allloads_Names,loadshape):
    
    for i in range(len(Allloads_Names)):
        load_name_i = Allloads_Names[i]
        load_edit_string = "Edit Load."+str(load_name_i)+" daily="+str(loadshape)

        ld = dss.Text.Command(load_edit_string)
    return ld

#%%

def scale_using_specific_loads(n,load_kw,load_kvar, Load_names_to_scale,use_actual_specific_loads_to_scale, maintain_p_q_ratio_flag ,Allloads_Names,Load_values_Pkw_list,Load_values_Qkw_list,Load_values_Pkw_pct_list,Load_values_Qkw_pct_list):
    
    for i in range(len(Load_names_to_scale)):
        load_name_i = str(Load_names_to_scale[i])
        load_name_i = load_name_i.lower()
        idxx = Allloads_Names.index(str(load_name_i))
        og_load_kw = load_kw[idxx]
        og_load_kvar = load_kvar[idxx]
        
        if use_actual_specific_loads_to_scale == 1:
            # load_name_i = str(Load_names_to_scale[i])
            # load_name_i = load_name_i.lower()
            # idxx = Allloads_Names.index(str(load_name_i))
            # og_load_kw = load_kw[idxx]
            # og_load_kvar = load_kvar[idxx]
            
            new_load_kw = Load_values_Pkw_list[i][n]
            pct_load_change_kw = ((new_load_kw - og_load_kw)/og_load_kw)
            pct_load_change_kw = pct_load_change_kw +1
            
            if maintain_p_q_ratio_flag == 1:
                pct_load_change_kvar = pct_load_change_kw
            else:
                new_load_kvar = Load_values_Qkw_list[n][i]
                pct_load_change_kvar =((new_load_kvar - og_load_kvar)/og_load_kvar)
                pct_load_change_kvar = 1 + pct_load_change_kvar
                
        else:
            pct_load_change_kw = Load_values_Pkw_pct_list[i][n]
            if maintain_p_q_ratio_flag == 1:
                pct_load_change_kvar = pct_load_change_kw
            else:
                pct_load_change_kvar =Load_values_Qkw_pct_list[i][n]  
        
        load_Pkw_new = og_load_kw * pct_load_change_kw
        load_Qkvar_new = og_load_kvar * pct_load_change_kvar
        load_edit_string = "Edit Load."+str(load_name_i)+" "+"kW="+str(load_Pkw_new)+" "+"kvar="+str(load_Qkvar_new)
        print(load_edit_string)
        hh = dss.Text.Command(load_edit_string)
    return hh
    
def scale_using_specific_loads_2(n,load_kw,load_kvar, Load_names_to_scale,use_actual_specific_loads_to_scale, maintain_p_q_ratio_flag ,Allloads_Names,Load_values_Pkw_list,Load_values_Qkw_list,Load_values_Pkw_pct_list,Load_values_Qkw_pct_list):
    
    for i in range(len(Load_names_to_scale)):
        load_name_i = str(Load_names_to_scale[i])
        load_name_i = load_name_i.lower()
        idxx = Allloads_Names.index(str(load_name_i))
        og_load_kw = load_kw[idxx]
        og_load_kvar = load_kvar[idxx]
        
        if use_actual_specific_loads_to_scale == 1:
            # load_name_i = str(Load_names_to_scale[i])
            # load_name_i = load_name_i.lower()
            # idxx = Allloads_Names.index(str(load_name_i))
            # og_load_kw = load_kw[idxx]
            # og_load_kvar = load_kvar[idxx]
            
            new_load_kw = Load_values_Pkw_list[i][n]
            pct_load_change_kw = ((new_load_kw - og_load_kw)/og_load_kw)
            pct_load_change_kw = pct_load_change_kw +1
            
            if maintain_p_q_ratio_flag == 1:
                pct_load_change_kvar = pct_load_change_kw
            else:
                new_load_kvar = Load_values_Qkw_list[i][n]
                pct_load_change_kvar =((new_load_kvar - og_load_kvar)/og_load_kvar)
                pct_load_change_kvar = 1 + pct_load_change_kvar
                
        else:
            pct_load_change_kw = Load_values_Pkw_pct_list[i][n]
            if maintain_p_q_ratio_flag == 1:
                pct_load_change_kvar = pct_load_change_kw
            else:
                pct_load_change_kvar =Load_values_Qkw_pct_list[i][n]  
        
        load_Pkw_new = og_load_kw * pct_load_change_kw
        load_Qkvar_new = og_load_kvar * pct_load_change_kvar
        load_edit_string = "Edit Load."+str(load_name_i)+" "+"kW="+str(load_Pkw_new)+" "+"kvar="+str(load_Qkvar_new)
        #print(load_edit_string)
        hh = dss.Text.Command(load_edit_string)
    return hh
    


def scale_specific_pv_using_actuals_dispatch(n,pv_actual_kws_list, pv_actual_kvar_dispatch_list ,pv_names_to_scale, use_actual_specific_pv_to_scale, maintain_p_q_pv_ratio_flag):
    pv_kva,pv_kw,pv_kvar,pv_bus_connected_to,All_PV_Names = Get_All_PVSystem_Data_For_Full_Feeder()
    for i in range(len(pv_names_to_scale)):
        pv_name_i = str(pv_names_to_scale[i])
        pv_name_i = pv_name_i.lower()
        idxx = All_PV_Names.index(str(pv_name_i))
        og_pv_kw = pv_kw[idxx]
        og_pv_kvar = pv_kvar[idxx]
        rated_pv_inv_kva = pv_kva[idxx]
                 
        new_pv_kw = pv_actual_kws_list[i][n]
        pv_Pkw_new = new_pv_kw
        pct_pv_change_kw = ((new_pv_kw - og_pv_kw)/og_pv_kw)
        pct_pv_change_kw = pct_pv_change_kw +1
        
        if maintain_p_q_pv_ratio_flag == 1:
            pct_pv_change_kvar = pct_pv_change_kw
            pv_Qkvar_new = og_pv_kvar * pct_pv_change_kvar
        else:
            new_pv_kvar = pv_actual_kvar_dispatch_list[i][n]
            pv_Qkvar_new  = new_pv_kvar
        if rated_pv_inv_kva < pv_Pkw_new:
            print("KVA Cannot be smaller than kw")
        max_pv_kvar = np.sqrt(np.square(rated_pv_inv_kva) - np.square(pv_Pkw_new) )
        if pv_Qkvar_new > max_pv_kvar:
            #the default in open dss calculate the available power in a different way
            #so we added this code to calculate the actual available kvar left based on specified kva
            pv_Qkvar_new = max_pv_kvar
        else:
            pv_Qkvar_new = pv_Qkvar_new 
                    
            
        pv_edit_string = "Edit PVSystem."+str(pv_name_i)+" "+"pmpp="+str(pv_Pkw_new)+" "+"kvar="+str(pv_Qkvar_new)
        print(pv_edit_string)
        #hh = print(pv_edit_string)
        hh = dss.Text.Command(pv_edit_string)
    return hh
    
def scale_specific_pv_iraddiance(n,pv_names_to_scale,pv_irad_timeseries,pv_actual_kvar_dispatch_list,also_scale_pv_kvar_flag=0 ):
    
    pv_kva,pv_kw,pv_kvar,pv_bus_connected_to,All_PV_Names = Get_All_PVSystem_Data_For_Full_Feeder()
    
    for i in range(len(pv_names_to_scale)):
    
        pv_name_i = str(pv_names_to_scale[i])
        pv_name_i = pv_name_i.lower()
        pv_irad = pv_irad_timeseries[i][n]
        
        idxx = All_PV_Names.index(str(pv_name_i))
        og_pv_kw = pv_kw[idxx]
        rated_pv_inv_kva = pv_kva[idxx]
    
        if also_scale_pv_kvar_flag == 0:
            pv_edit_string = "Edit PVSystem."+str(pv_name_i)+" "+"irradiance="+str(pv_irad)
            
        else:
            new_pv_kvar = pv_actual_kvar_dispatch_list[i][n]
            pv_Qkvar_new  = new_pv_kvar
            if rated_pv_inv_kva < (pv_irad * og_pv_kw):
                print("KVA Cannot be smaller than kw")
            max_pv_kvar = np.sqrt(np.square(rated_pv_inv_kva) - np.square(pv_irad * og_pv_kw) )
            if pv_Qkvar_new > max_pv_kvar:
                #the default in open dss calculate the available power in a different way
                #so we added this code to calculate the actual available kvar left based on specified kva
                pv_Qkvar_new = max_pv_kvar
            else:
                pv_Qkvar_new = pv_Qkvar_new 
            pv_edit_string = "Edit PVSystem."+str(pv_name_i)+" "+"irradiance="+str(pv_irad)+" "+"kvar="+str(pv_Qkvar_new)
            
        #print(pv_edit_string)
        hh = dss.Text.Command(pv_edit_string)
    return hh


def scale_using_specific_generator(n,gen_names_to_scale,gen_actual_kws_list,gen_actual_kvar_dispatch_list, gen_pct_kws_list, gen_pct_kvar_dispatch_list,  use_actual_specific_gen_to_scale, maintain_p_q_gen_ratio_flag):
    gen_kva, gen_kw,gen_kvar,gen_bus_connected_to,All_GEN_Names = Get_All_Generator_Data_For_Full_Feeder()
    
    for i in range(len(gen_names_to_scale)):
        gen_name_i = str(gen_names_to_scale[i])
        gen_name_i = gen_name_i.lower()
        idxx = All_GEN_Names.index(str(gen_name_i))
        og_gen_kw = gen_kw[idxx]
        og_gen_kvar = gen_kvar[idxx]
        rated_gen_kva = gen_kva[idxx]
        
        if use_actual_specific_gen_to_scale == 1:

            
            new_gen_kw = gen_actual_kws_list[i][n]        
            pct_gen_change_kw = ((new_gen_kw - og_gen_kw)/og_gen_kw)
            pct_gen_change_kw = pct_gen_change_kw +1
            gen_Pkw_new = new_gen_kw
            
            if maintain_p_q_gen_ratio_flag == 1:
                pct_gen_change_kvar = pct_gen_change_kw
                gen_Qkvar_new = og_gen_kvar * pct_gen_change_kvar
            else:
                new_gen_kvar = gen_actual_kvar_dispatch_list[i][n]
                pct_gen_change_kvar =((new_gen_kvar - og_gen_kvar)/og_gen_kvar)
                pct_gen_change_kvar = 1 + pct_gen_change_kvar
                gen_Qkvar_new  = new_gen_kvar
                
        else:
            pct_gen_change_kw = gen_pct_kws_list[i][n]
            gen_Pkw_new = og_gen_kw * pct_gen_change_kw
            
            
            if maintain_p_q_gen_ratio_flag == 1:
                pct_gen_change_kvar = pct_gen_change_kw
                gen_Qkvar_new = og_gen_kvar * pct_gen_change_kvar
                
            else:
                pct_gen_change_kvar =gen_pct_kvar_dispatch_list[i][n]  
                gen_Qkvar_new = og_gen_kvar * pct_gen_change_kvar
                
                
        max_gen_kvar = np.sqrt(np.square(rated_gen_kva) - np.square(gen_Pkw_new) )
        if rated_gen_kva < gen_Qkvar_new:
            print("KVA Cannot be smaller than kw")
        if gen_Qkvar_new > max_gen_kvar:
            #the default in open dss calculate the available power in a different way
            #so we added this code to calculate the actual available kvar left based on specified kva
            gen_Qkvar_new = max_gen_kvar
        else:
            gen_Qkvar_new = gen_Qkvar_new
        gen_edit_string = "Edit Generator."+str(gen_name_i)+" "+"kW="+str(gen_Pkw_new)+" "+"kvar="+str(gen_Qkvar_new)
        #print(gen_edit_string)
        hh = dss.Text.Command(gen_edit_string)
    return hh


def open_disable_devices(Lines_names_to_open_disable,Transformer_names_to_disable):
    
    if len(Lines_names_to_open_disable) !=0:
        for i in range(len(Lines_names_to_open_disable)):
            line_name = str(Lines_names_to_open_disable[i])
            line_open_string = "Edit Line."+str(line_name)+" "+"enabled=no"
            print(line_open_string)
            dss.Text.Command(line_open_string)
            
    if len(Transformer_names_to_disable) !=0:
        for j in range(len(Transformer_names_to_disable)):
            Trans_name = str(Transformer_names_to_disable[j])
            Trans_open_string = "Edit Transformer."+str(Trans_name)+" "+"enabled=no"
            #print(Trans_open_string)
            dss.Text.Command(Trans_open_string)
            
    return None


def close_enable_devices(Lines_names_to_close_enable,Transformer_names_to_enable):
    
    if len(Lines_names_to_close_enable) !=0:
        for i in range(len(Lines_names_to_close_enable)):
            line_name = str(Lines_names_to_close_enable[i])
            line_open_string = "Edit Line."+str(line_name)+" "+"enabled=yes"
            #print(line_open_string)
            dss.Text.Command(line_open_string)
            
    if len(Transformer_names_to_enable) !=0:
        for j in range(len(Transformer_names_to_enable)):
            Trans_name = str(Transformer_names_to_enable[j])
            Trans_open_string = "Edit Transformer."+str(Trans_name)+" "+"enabled=yes"
            #print(Trans_open_string)
            dss.Text.Command(Trans_open_string)
            
    return None




def activate_pv_storage_GFM(pvsystem_as_GFM, storage_as_GFM):
    if len(pvsystem_as_GFM)!=0:
        for i in range(len(pvsystem_as_GFM)):
            pv_name = str(pvsystem_as_GFM[i])
            gfm_string = "Edit PVSystem."+str(pv_name)+" ControlMode = GFM"
            print(gfm_string)
            dss.Text.Command(gfm_string)
            
    if len(storage_as_GFM)!=0:
        for j in range(len(storage_as_GFM)):
            sto_name = str(storage_as_GFM[j])
            gfm_string = "Edit Storage."+str(sto_name)+" ControlMode = GFM"
            print(gfm_string)
            dss.Text.Command(gfm_string)
    return None



def create_matrix_string(matrix_list):
    matrix_string = "(" 
    for i in range(len(matrix_list)):
        row_i = matrix_list[i]
        for j in range(len(row_i)):
            matrix_string = matrix_string + str(row_i[j]) + " "
        if i != (len(matrix_list) -1):
            matrix_string = matrix_string + "|" + " "
    matrix_string = matrix_string + ")"
    return matrix_string
    

def create_a_line_code(line_code_name,line_unit,line_phase,line_rmatrix, line_xmatrix, line_normamp, line_emergamp):
    #create rmatrix string
    rmatrix = create_matrix_string(line_rmatrix)
    xmatrix = create_matrix_string(line_xmatrix)
    
    line_code_string = 'New Linecode.'+str(line_code_name)+' '+'units='+str(line_unit)+' '+'nphases='+str(line_phase)+' '+'Rmatrix='+str(rmatrix)+' '+'Xmatrix='+str(xmatrix)+' '+'normamps='+str(line_normamp)+' '+'emergamps='+str(line_emergamp)
    #print(line_code_string)
    dss.Text.Command(line_code_string)
    return None

def create_multiple_line_codes(line_code_namess,line_unitss,line_phasess,line_rmatrixss, line_xmatrixss, line_normampss, line_emergampss):
    for n in range(len(line_code_namess)):
        create_a_line_code(line_code_namess[n],line_unitss[n],line_phasess[n],line_rmatrixss[n], line_xmatrixss[n], line_normampss[n], line_emergampss[n])
    return None


def connect_a_new_line(line_name, line_unit, line_length, line_nodes, line_bus1_num, line_bus2_num, line_phases, line_code):
    
    for t in range(len(line_nodes)):
        line_bus1_num = str(line_bus1_num) + "."+str(line_nodes[t])
        line_bus2_num = str(line_bus2_num) + "."+str(line_nodes[t])
    line_string = 'New Line.'+str(line_name)+' '+'Units='+str(line_unit)+' '+'Length='+str(line_length)+' '+'bus1='+str(line_bus1_num)+' '+'bus2='+str(line_bus2_num)+' '+'phases='+str(line_phases)+' '+'Linecode='+str(line_code)
    #print(line_string)
    dss.Text.Command(line_string)
    return None


def connect_a_multiple_new_line(line_namess, line_unitss, line_lengthss, line_nodess, line_bus1_numss, line_bus2_numss, line_phasess, line_codess):
    for i in range(len(line_namess)):
        connect_a_new_line(line_namess[i], line_unitss[i], line_lengthss[i], line_nodess[i], line_bus1_numss[i], line_bus2_numss[i], line_phasess[i], line_codess[i])
    return None


def check_voltage_violation_flag_limit(voltage_value,low_limit,high_limit):
    if voltage_value > high_limit:
        flag_high =1 
        volt_violate = 1 
    elif voltage_value < low_limit:
        flag_high =0 
        volt_violate = 1 
    else:
        volt_violate = 0
        flag_high = -1 
    return volt_violate, flag_high
        
def check_all_voltage_violations(bus_name, bus_voltage_phase,low_limit, high_limit):
    violate_bus_name = []
    violate_bus_voltage = []
    for i in range(len(bus_voltage_phase)):
        voltage_value = bus_voltage_phase[i]
        volt_violate, flag_high = check_voltage_violation_flag_limit(voltage_value,low_limit,high_limit)
        if volt_violate ==1:
            violate_bus_name.append(bus_name[i])
            violate_bus_voltage.append(voltage_value)
    return violate_bus_name, violate_bus_voltage
            




def voltage_result_by_phase(all_node_names,bus_vol_pu_ln_base):
    
    bus_name_phase_1 = []
    bus_name_phase_2 = []
    bus_name_phase_3 = []
    bus_voltage_phase_1 = []
    bus_voltage_phase_2 = []
    bus_voltage_phase_3 = []
    
    for n in range(len(all_node_names)):
        bus_name_all = all_node_names[n]
        bus_split = bus_name_all.split('.')
        bus_name = bus_split[0]
        bus_phase = bus_split[-1]
        if bus_phase == '1':
            bus_name_phase_1.append(bus_name)
            bus_voltage_phase_1.append(bus_vol_pu_ln_base[n])
        elif bus_phase == '2':
            bus_name_phase_2.append(bus_name)
            bus_voltage_phase_2.append(bus_vol_pu_ln_base[n])
        elif bus_phase == '3':
            bus_name_phase_3.append(bus_name)
            bus_voltage_phase_3.append(bus_vol_pu_ln_base[n])
        else:
            pass
    return bus_name_phase_1, bus_name_phase_2, bus_name_phase_3, bus_voltage_phase_1,bus_voltage_phase_2,bus_voltage_phase_3


def add_an_energy_meter(meter_name,element_type, element_name, terminal_point):
    #element type is 'line' or 'transformer
    meter_string = 'New energymeter.'+str(meter_name)+' '+'element='+str(element_type)+'.'+str(element_name)+' '+'terminal='+str(terminal_point)
    #print(meter_string)
    dss.Text.Command(meter_string)
    return None




def get_sorted_bus_names_to_meter():
    
    dist = dss.Circuit.AllBusDistances()
    bname = dss.Circuit.AllBusNames()
    combo = zip(dist, bname)
    combo_sort = sorted(combo)
    
    sorted_bus_distance = []
    sorted_bus_name = []
    for sort_dist, sort_bname in combo_sort:
        sorted_bus_distance.append(sort_dist)
        sorted_bus_name.append(sort_bname)
    return sorted_bus_name, sorted_bus_distance
        

def sort_orginal_voltages_per_phase(sorted_bus_name,org_bus_name_phase, org_bus_voltage_phase):
    sort_bus_phase_name = []
    sorted_volt = []
    for i in range(len(sorted_bus_name)):
        b_name = sorted_bus_name[i]
        if b_name in org_bus_name_phase:
            sort_bus_phase_name.append(b_name)
            index_value = org_bus_name_phase.index(b_name)
            volt = org_bus_voltage_phase[index_value]
            sorted_volt.append(volt)
    return sort_bus_phase_name, sorted_volt


def check_element_overloads(all_PDelement_Names_base, all_PDelement_loading_percent_base, loading_limit = 100):
    violate_loading = []
    violate_element_name = []
    for i in range(len(all_PDelement_loading_percent_base)):
        ld_pct = all_PDelement_loading_percent_base[i]
        if ld_pct > loading_limit:
            violate_element_name.append(all_PDelement_Names_base[i])
            violate_loading.append(ld_pct)
    return violate_loading, violate_element_name 


def microgrid_details_from_full_feeder_per_phase(microgrid_buses_name,sort_bus_name, sorted_bus_voltage ):
    microgrid_busname = []
    microgrid_voltage = []
    for i in range(len(sort_bus_name)):
        sort_bus_i = sort_bus_name[i]
        sort_bus_i = sort_bus_i.lower()
        if sort_bus_i in microgrid_buses_name:
            microgrid_busname.append(sort_bus_i)
            microgrid_voltage.append(sorted_bus_voltage[i])
    return microgrid_busname,microgrid_voltage 

# --- Helper function to map node number to phase letter ---
def get_phase_letter(full_bus_name_with_node):
    parts = full_bus_name_with_node.split('.')
    if len(parts) > 1:
        node_num = parts[-1]
        if node_num == '1':
            return 'A'
        elif node_num == '2':
            return 'B'
        elif node_num == '3':
            return 'C'
        else: # For other node numbers
            return f"Node {node_num}"
    return " " # If no node part is found after splitting by '.'

def get_base_bus_name(full_bus_name):
    return full_bus_name.split('.')[0]

                