# -*- coding: utf-8 -*-
"""
Created on Fri Dec  9 20:39:55 2022

@author: veenstra
"""


import os
import matplotlib.pyplot as plt
plt.close('all')
import numpy as np
import contextily as ctx
import datetime as dt
import dfm_tools as dfmt

dir_testinput = r'c:\DATA\dfm_tools_testdata'
dir_output = '.'

file_nc_list = [#os.path.join(dir_testinput,'DFM_sigma_curved_bend\\DFM_OUTPUT_cb_3d\\cb_3d_map.nc'), #sigmalayer
                os.path.join(dir_testinput,'DFM_3D_z_Grevelingen','computations','run01','DFM_OUTPUT_Grevelingen-FM','Grevelingen-FM_0000_map.nc'), #zlayer
                #r'p:\1204257-dcsmzuno\2006-2012\3D-DCSM-FM\A18b_ntsu1\DFM_OUTPUT_DCSM-FM_0_5nm\DCSM-FM_0_5nm_0000_map.nc', #fullgrid
                #r'p:\11206813-006-kpp2021_rmm-2d\C_Work\31_RMM_FMmodel\computations\model_setup\run_207\results\RMM_dflowfm_0000_map.nc', #2D model
                #r'p:\archivedprojects\11203379-005-mwra-updated-bem\03_model\02_final\A72_ntsu0_kzlb2\DFM_OUTPUT_MB_02\MB_02_0000_map.nc',
                ]


from dfm_tools import reconstruct_zw_zcc_fromsigma, reconstruct_zw_zcc_fromz
import warnings
def get_mapdata_atdepth(data_xr_map, depth, reference='z0', varname=None, zlayer_z0_interp=False):
    """
    data_xr_map:
        has to be Dataset (not a DataArray), otherwise mesh2d_flowelem_zw etc are not available (interface z values)
        in case of zsigma/sigma layers (or fullgrid), it is advisable to .sel()/.isel() the time dimension first, because that is less computationally heavy
    reference:
        compute depth w.r.t. z0/waterlevel/bed
        default: reference='z0'
    zlayer_z0_interp:
        Use xr.interp() to interpolate zlayer model to z-value. Only possible for reference='z' (not 'waterlevel' or 'bedlevel'). Only used if "mesh2d_layer_z" is present (zlayer model)
        This is faster but results in values interpolated between zcc (z cell centers), so it is different than slicing.
    
    #TODO: zmodel gets depth in figure title, because of .set_index() in open_partitioned_dataset(). Sigmamodel gets percentage/fraction in title
    #TODO: check if attributes should be passed/altered
    #TODO: what happens with variables without a depth dimension? Not checked yet
    """
    
    data_wl = data_xr_map['mesh2d_s1']
    data_bl = data_xr_map['mesh2d_flowelem_bl']
    depth_name = f'depth_from_{reference}'
    if not 'nmesh2d_layer' in data_xr_map.dims: #TODO: maybe raise exception instead?
        print('WARNING: depth dimension not found, probably 2D model, returning input Dataset')
        return data_xr_map
    elif 'mesh2d_flowelem_zcc' in data_xr_map.coords: #fullgrid info available, so continuing
        print('zw/zcc (fullgrid) values already present in Dataset')
        pass
    elif 'mesh2d_layer_sigma' in data_xr_map.coords: #reconstruct_zw_zcc_fromsigma and treat as zsigma/fullgrid mapfile from here
        print('sigma-layer model, computing zw/zcc (fullgrid) values and treat as fullgrid model from here')
        data_xr_map = reconstruct_zw_zcc_fromsigma(data_xr_map)
    elif 'mesh2d_layer_z' in data_xr_map.coords:
        if zlayer_z0_interp and reference=='z0': # interpolates between z-center values  (instead of slicing), should be faster #TODO: check if this is faster than fullgrid
            if varname is not None:
                print('WARNING: varname!=None, but zlayer_interp_z=True so varname will be ignored')
            print('z-layer model, zlayer_interp_z=True and reference=="z0" so using xr.interp()]')
            depth_attrs = data_xr_map.mesh2d_layer_z.attrs
            data_xr_map = data_xr_map.set_index({'nmesh2d_layer':'mesh2d_layer_z'}).rename({'nmesh2d_layer':depth_name}) #set depth as index on layers, to be able to interp to depths instead of layernumbers
            data_xr_map[depth_name] = data_xr_map[depth_name].assign_attrs(depth_attrs) #set attrs from depth to layer
            data_xr_map_ondepth = data_xr_map.interp({depth_name:depth},kwargs=dict(bounds_error=False,fill_value='extrapolate')) #interpolate to fixed z-depth
            data_xr_map_ondepth = data_xr_map_ondepth.where((depth>=data_bl) & (depth<=data_wl)) #filter above wl and below bl values
            return data_xr_map_ondepth #early return
        
        print('z-layer model, computing zw/zcc (fullgrid) values and treat as fullgrid model from here')
        data_xr_map = reconstruct_zw_zcc_fromz(data_xr_map)
    else:
        raise Exception('layers present, but unknown layertype')
    
    #correct reference level
    if reference=='z0': #TODO: check if all references work properly
        zw_reference = data_xr_map.mesh2d_flowelem_zw
        zcc_reference = data_xr_map.mesh2d_flowelem_zcc
    elif reference=='waterlevel':
        zw_reference = data_xr_map.mesh2d_flowelem_zw - data_wl
        zcc_reference = data_xr_map.mesh2d_flowelem_zcc - data_wl
    elif reference=='bedlevel':
        zw_reference = data_xr_map.mesh2d_flowelem_zw + data_bl
        zcc_reference = data_xr_map.mesh2d_flowelem_zcc + data_bl
    else:
        raise Exception(f'unknown reference: {reference}')
    
    if varname is not None: #TODO: maybe remove this, although with varname=None DCSM gives "PerformanceWarning: Increasing number of chunks by factor of 20" (maybe apply where only on vars with facedim solves it?)
        data_xr_map_var = data_xr_map[varname]
    else:
        data_xr_map_var = data_xr_map
    
    print('>> subsetting data on fixed depth in fullgrid z-data: ',end='')
    dtstart = dt.datetime.now()
        
    if 'time' in data_xr_map.dims:
        warnings.warn(UserWarning('get_mapdata_onfixedepth() can be very slow when supplying dataset with time dimension for zsigma/sigma models'))
    bool_valid = zw_reference.min(dim='nmesh2d_interface') <= depth #TODO suppress warning: C:\Users\veenstra\Anaconda3\envs\dfm_tools_env\lib\site-packages\dask\array\reductions.py:640: RuntimeWarning: All-NaN slice encountered. return np.nanmax(x_chunk, axis=axis, keepdims=keepdims)
    bool_mindist = data_xr_map.nmesh2d_layer==abs(zcc_reference - depth).argmin(dim='nmesh2d_layer').load()
    print('performing .where() on fixed depth for zsigma/fullgrid model')
    data_xr_map_ondepth = data_xr_map_var.where(bool_valid&bool_mindist).max(dim='nmesh2d_layer',keep_attrs=True) #set all layers but one to nan, followed by an arbitrary reduce (max in this case)
    #add zvalue as coordinate
    data_xr_map_ondepth[depth_name] = depth
    data_xr_map_ondepth[depth_name] = data_xr_map_ondepth[depth_name].assign_attrs({'units':'m'})
    data_xr_map_ondepth = data_xr_map_ondepth.set_coords([depth_name])
    print(f'{(dt.datetime.now()-dtstart).total_seconds():.2f} sec')
    
    return data_xr_map_ondepth



for file_nc in file_nc_list:
    print('processing %s'%(os.path.basename(file_nc)))
    basename = os.path.basename(file_nc).replace('.','')
    data_frommap_merged = dfmt.open_partitioned_dataset(file_nc.replace('_0000_','_000*_')) #TODO: make starred default, but not yet supported by older code
    
    #get ugrid data, vars informatin and grid units (latter from bedlevel coordinates)
    vars_pd = dfmt.get_ncvarproperties(file_nc=file_nc)
    timestep = 3
    clim_sal = [28, 36]
    depth = -1#-4

    print('plot grid and values from mapdata (salinity on layer, 3dim, on cell centers) >> on fixed depth')
    data_frommap_timesel = data_frommap_merged.isel(time=timestep) #select data for all layers
    data_frommap_timesel_ondepth = get_mapdata_atdepth(data_xr_map=data_frommap_timesel, depth=depth, 
                                                       reference='z0', zlayer_z0_interp=True)
    fig, ax = plt.subplots()
    pc = data_frommap_timesel_ondepth['mesh2d_sa1'].ugrid.plot(edgecolor='face',cmap='jet')
    pc.set_clim(clim_sal)
    ax.set_aspect('equal')
    fig.tight_layout()
    