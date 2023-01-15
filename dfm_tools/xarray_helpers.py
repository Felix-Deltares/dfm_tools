# -*- coding: utf-8 -*-
"""
Created on Fri Oct 14 19:58:36 2022

@author: veenstra
"""

from netCDF4 import Dataset
import xarray as xr
import numpy as np
import xugrid as xu
import matplotlib.pyplot as plt
plt.close('all')
import datetime as dt
import glob
import pandas as pd
import warnings


def preprocess_hisnc(ds):
    """
    Look for dim/coord combination and use this for Dataset.set_index(), to enable station/gs/crs/laterals label based indexing. If duplicate labels are found (like duplicate stations), these are dropped to avoid indexing issues.
    
    Parameters
    ----------
    ds : xarray.Dataset
        DESCRIPTION.
    drop_duplicate_stations : TYPE, optional
        DESCRIPTION. The default is True.

    Returns
    -------
    ds : TYPE
        DESCRIPTION.

    """
    
    #generate dim_coord_dict to set indexes, this will be something like {'stations':'station_name','cross_section':'cross_section_name'} after loop
    dim_coord_dict = {}
    for ds_coord in ds.coords.keys():
        ds_coord_dtype = ds[ds_coord].dtype
        ds_coord_dim = ds[ds_coord].dims[0] #these vars always have only one dim
        if ds_coord_dtype.str.startswith('|S'): #these are station/crs/laterals/gs names/ids
            dim_coord_dict[ds_coord_dim] = ds_coord
    
    #loop over dimensions and set corresponding coordinates/variables from dim_coord_dict as their index
    for dim in dim_coord_dict.keys():
        coord = dim_coord_dict[dim]
        coord_str = f'{coord}'#_str' #avoid losing the original variable by creating a new name
        ds[coord_str] = ds[coord].load().str.decode('utf-8',errors='ignore').str.strip() #.load() is essential to convert not only first letter of string.
        #ds = ds.set_index({dim:[coord_str,'station_x_coordinate','station_y_coordinate']}) #nearest station: "ValueError: multi-index does not support ``method`` and ``tolerance``"  #slice x/y: "TypeError: float() argument must be a string or a number, not 'slice'"
        ds = ds.set_index({dim:coord_str})
        
        #drop duplicate indices (stations/crs/gs), this avoids "InvalidIndexError: Reindexing only valid with uniquely valued Index objects"
        duplicated_keepfirst = ds[dim].to_series().duplicated(keep='first')
        if duplicated_keepfirst.sum()>0:
            print(f'dropping {duplicated_keepfirst.sum()} duplicate "{coord}" labels to avoid InvalidIndexError')
            ds = ds[{dim:~duplicated_keepfirst}]

    
    if 'source' in ds.attrs.keys():
        source_attr = ds.attrs["source"]
    else:
        source_attr = None
    try:
        source_attr_version = source_attr.split(', ')[1]
        source_attr_date = source_attr.split(', ')[2]
        if pd.Timestamp(source_attr_date) < dt.datetime(2020,11,28):
            warnings.warn(UserWarning(f'Your model was run with a D-FlowFM version from before 28-10-2020 ({source_attr_version} from {source_attr_date}), the layers in the hisfile are incorrect. Check UNST-2920 and UNST-3024 for more information, it was fixed from OSS 67858.'))
    except:
        #print('No source attribute present in hisfile, cannot check version')
        pass

    return ds


def preprocess_hirlam(ds):
    """
    add xy variables as longitude/latitude to avoid duplicate var/dim names
    add xy as variables again with help of NetCDF4 
    #TODO: this part is hopefully temporary, necessary since variables cannot have the same name as dimensions in xarray
    # background and future solution: https://github.com/pydata/xarray/issues/6293
    """
    
    print('adding x/y variables again as lon/lat')
    file_nc_one = ds.encoding['source']
    with Dataset(file_nc_one) as data_nc:
        data_nc_x = data_nc['x']
        data_nc_y = data_nc['y']
        ds['longitude'] = xr.DataArray(data_nc_x,dims=data_nc_x.dimensions,attrs=data_nc_x.__dict__)
        ds['latitude'] = xr.DataArray(data_nc_y,dims=data_nc_y.dimensions,attrs=data_nc_y.__dict__)
    ds = ds.set_coords(['latitude','longitude'])
    for varkey in ds.data_vars:
        del ds[varkey].encoding['coordinates'] #remove {'coordinates':'y x'} from encoding (otherwise set twice)
    return ds


def preprocess_ERA5(ds):
    """
    Reduces the expver dimension in some of the ERA5 data (mtpr and other variables), which occurs in files with very recent data. The dimension contains the unvalidated data from the latest month in the second index in the expver dimension. The reduction is done with mean, but this is arbitrary, since there is only one valid value per timestep and the other one is nan.
    """
    if 'expver' in ds.dims:
        ds = ds.mean(dim='expver')
    return ds


def Dataset_varswithdim(ds,dimname):
    if dimname not in ds.dims:
        raise Exception(f'dimension {dimname} not in dataset, available are: {list(ds.dims)}')
    
    varlist_keep = []
    for varname in ds.variables.keys():
        if dimname in ds[varname].dims:
            varlist_keep.append(varname)
    ds = ds[varlist_keep]
    
    return ds


def get_vertical_dimensions(uds): #TODO: maybe add layer_dimension and interface_dimension properties to xugrid?
    """
    get vertical_dimensions from grid_info of ugrid mapfile (this will fail for hisfiles). The info is stored in the layer_dimension and interface_dimension attribute of the mesh2d variable of the dataset (stored in uds.grid after reading with xugrid)
    
    processing cb_3d_map.nc
        >> found layer/interface dimensions in file: mesh2d_nLayers mesh2d_nInterfaces
    processing Grevelingen-FM_0*_map.nc
        >> found layer/interface dimensions in file: nmesh2d_layer nmesh2d_interface (these are updated in open_partitioned_dataset)
    processing DCSM-FM_0_5nm_0*_map.nc
        >> found layer/interface dimensions in file: mesh2d_nLayers mesh2d_nInterfaces
    processing MB_02_0*_map.nc
        >> found layer/interface dimensions in file: mesh2d_nLayers mesh2d_nInterfaces
    """
    gridname = uds.grid.name
    grid_info = uds.grid.to_dataset()[gridname]
    if hasattr(grid_info,'layer_dimension'):
        print('>> found layer/interface dimensions in file: ',end='')
        print(grid_info.layer_dimension, grid_info.interface_dimension) #combined in attr vertical_dimensions
        return grid_info.layer_dimension, grid_info.interface_dimension
    else:
        return None, None


def open_partitioned_dataset(file_nc, chunks={'time':1}, merge_xugrid=True): 
    """
    Opmerkingen HB:
        - Voor data op de edges zou het ook werken, maar dan is nog een andere isel noodzakelijk, specifiek voor de edge data.
        - Dit werkt nu ook alleen als je enkel grid in je dataset hebt. Bij meerdere grids zouden we een keyword moeten toevoegen dat je aangeeft welke je gemerged wilt zien.    

    Parameters
    ----------
    file_nc : TYPE
        DESCRIPTION.
    chunks : TYPE, optional
        chunks={'time':1} increases performance significantly upon reading, but causes memory overloads when performing sum/mean/etc actions over time dimension (in that case 100/200 is better). The default is {'time':1}.

    Raises
    ------
    Exception
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.
    
    file_nc = 'p:\\1204257-dcsmzuno\\2006-2012\\3D-DCSM-FM\\A18b_ntsu1\\DFM_OUTPUT_DCSM-FM_0_5nm\\DCSM-FM_0_5nm_0000_map.nc' #3D DCSM
    file_nc = 'p:\\11206813-006-kpp2021_rmm-2d\\C_Work\\31_RMM_FMmodel\\computations\\model_setup\\run_207\\results\\RMM_dflowfm_0000_map.nc' #RMM 2D
    file_nc = 'p:\\1230882-emodnet_hrsm\\GTSMv5.0\\runs\\reference_GTSMv4.1_wiCA_2.20.06_mapformat4\\output\\gtsm_model_0*_map.nc' #GTSM 2D
    file_nc = 'p:\\11208053-005-kpp2022-rmm3d\\C_Work\\01_saltiMarlein\\RMM_2019_computations_02\\computations\\theo_03\\DFM_OUTPUT_RMM_dflowfm_2019\\RMM_dflowfm_2019_0*_map.nc' #RMM 3D
    file_nc = 'p:\\archivedprojects\\11203379-005-mwra-updated-bem\\03_model\\02_final\\A72_ntsu0_kzlb2\\DFM_OUTPUT_MB_02\\MB_02_0000_map.nc'
    Timings (open_dataset/merge_partitions): (update timings after new xugrid code)
        - DCSM 3D 20 partitions  367 timesteps: 219.0/4.68 sec
        - RMM  2D  8 partitions  421 timesteps:  60.6/1.4+0.1 sec
        - GTSM 2D  8 partitions  746 timesteps:  73.8/6.4+0.1 sec
        - RMM  3D 40 partitions  146 timesteps: 166.0/3.6+0.5 sec
        - MWRA 3D 20 partitions 2551 timesteps: 826.2/3.4+1.2 sec
    """
    
    dtstart_all = dt.datetime.now()
    if isinstance(file_nc,list):
        file_nc_list = file_nc
    else:
        file_nc_list = glob.glob(file_nc)
    if len(file_nc_list)==0:
        raise Exception('file(s) not found, empty file_nc_list')
    
    print(f'>> xu.open_dataset() with {len(file_nc_list)} partition(s): ',end='')
    dtstart = dt.datetime.now()
    partitions = []
    for iF, file_nc_one in enumerate(file_nc_list):
        print(iF+1,end=' ')
        ds = xr.open_dataset(file_nc_one, chunks=chunks)
        #rename layers (also in mesh2d attributes)
        if 'nmesh2d_layer' in ds.dims: #renaming old layerdim for Grevelingen model, easier to do before mesh2d var is parsed by xugrid. This is hardcoded, so model with old layerdim names and non-mesh2d gridname is not renamed
            #TODO: add layer_dimension/interface_dimension as attributes to xugrid dataset? (like face_dimension property)
            print('[renaming old layerdim] ',end='')
            ds = ds.rename({'nmesh2d_layer':'mesh2d_nLayers','nmesh2d_interface':'mesh2d_nInterfaces'})
            ds.mesh2d.attrs.update(layer_dimension='mesh2d_nLayers', interface_dimension='mesh2d_nInterfaces')
        #convert zcc/zw from coords to data_vars
        for var_coord in ['mesh2d_flowelem_zcc','mesh2d_flowelem_zw']: #TODO: xugrid.ugrid.partitioning.group_vars_by_ugrid_dim() loops over ds.data_vars, but these two are coords instead of data_vars so are skipped and therefore dropped (necessary for crosssect plots and depth-slices) >> related: mesh2d_layer_z/mesh2d_interface_z is dropped with merging since it has no face/node/edge dim
            if var_coord in ds.coords:
                ds = ds.reset_coords([var_coord])
        #convert to xugrid dataset
        from xugrid.core.wrap import UgridDataset
        uds = UgridDataset(ds)
        partitions.append(uds) #TODO: speed up, for instance by doing decode after merging? (or is second-read than not faster anymore?)
    print(': ',end='')
    print(f'{(dt.datetime.now()-dtstart).total_seconds():.2f} sec')
    
    if merge_xugrid:
        if len(partitions) == 1:
            return partitions[0]
        print(f'>> xu.merge_partitions() with {len(file_nc_list)} partition(s): ',end='')
        dtstart = dt.datetime.now()
        ds_merged_xu = xu.merge_partitions(partitions)
        print(f'{(dt.datetime.now()-dtstart).total_seconds():.2f} sec')
        
        #add non face/node/edge variables back to merged dataset
        #TODO: add this to xugrid? contains data_vars ['projected_coordinate_system', 'timestep', 'mesh2d_layer_z', 'mesh2d_interface_z']
        #TODO: xugrid has .crs property, projected_coordinate_system/wgs should be updated to be crs so it will be automatically handled? >> make dflowfm issue
        facedim = ds_merged_xu.grid.face_dimension
        nodedim = ds_merged_xu.grid.node_dimension
        edgedim = ds_merged_xu.grid.edge_dimension
        ds_rest = partitions[0].drop_dims([facedim,nodedim,edgedim])
        for data_var in ds_rest.data_vars:
            ds_merged_xu[data_var] = ds_rest[data_var]
        
        #print variables that are dropped in merging procedure
        varlist_onepart = list(partitions[0].variables.keys())
        varlist_merged = list(ds_merged_xu.variables.keys())
        varlist_dropped_bool = ~pd.Series(varlist_onepart).isin(varlist_merged)
        varlist_dropped = pd.Series(varlist_onepart).loc[varlist_dropped_bool]
        if varlist_dropped_bool.any():
            print(f'WARNING: some variables dropped with merging of partitions:\n{varlist_dropped}')
    else: #TODO: remove this part after ghostcell decision (would also be solved if edges are really not plotted)
        #rename old dimension names and some variable names #TODO: move to separate definition
        gridname = 'mesh2d' #partitions[0].ugrid.grid.name #'mesh2d' #TODO: works if xugrid accepts arbitrary grid names
        rename_dict = {}
        varn_maxfnodes = f'max_n{gridname}_face_nodes' #TODO: replace mesh2d with grid.name
        maxfnodes_opts = [f'{gridname}_nMax_face_nodes','nNetElemMaxNode'] #options for old domain variable name
        for opt in maxfnodes_opts:
            if opt in partitions[0].dims:
                rename_dict.update({opt:varn_maxfnodes})
        # layer_nlayers_opts = ['mesh2d_nLayers','laydim'] # options for old layer dimension name #TODO: others from get_varname_fromnc: ['nmesh2d_layer_dlwq','LAYER','KMAXOUT_RESTR','depth'
        # for opt in layer_nlayers_opts:
        #     if opt in partitions[0].dims:
        #         #print(f'hardcoded replacing {opt} with nmesh2d_layer. Auto would replace "{partitions[0].ugrid.grid.to_dataset().mesh2d.vertical_dimensions}"')
        #         rename_dict.update({opt:f'n{gridname}_layer'})
        # layer_ninterfaces_opts = ['mesh2d_nInterfaces']
        # for opt in layer_ninterfaces_opts:
        #     if opt in partitions[0].dims:
        #         rename_dict.update({opt:f'n{gridname}_interface'})
        varn_domain = f'{gridname}_flowelem_domain' #TODO: replace mesh2d with grid.name
        domain_opts = ['idomain','FlowElemDomain'] #options for old domain variable name
        for opt in domain_opts:
            if opt in partitions[0].data_vars:
                rename_dict.update({opt:varn_domain})
        varn_globalnr = f'{gridname}_flowelem_globalnr'
        globalnr_opts = ['iglobal_s'] #options for old globalnr variable name
        for opt in globalnr_opts:
            if opt in partitions[0].data_vars:
                rename_dict.update({opt:varn_globalnr})
        partitions = [part.rename(rename_dict) for part in partitions]
        
        varlist_onepart = list(partitions[0].variables.keys())
        
        all_indices = []
        all_faces = []
        all_nodes_x = []
        all_nodes_y = []
        accumulator = 0
        domainno_all = []
        
        #dtstart = dt.datetime.now()
        #print('>> process partitions facenumbers/ghostcells: ',end='')
        for i, part in enumerate(partitions):
            # For ghost nodes, keep the values of the domain number that occurs most.
            grid = part.ugrid.grid
            if varn_domain not in varlist_onepart:
                if len(partitions)!=1:#escape for non-partitioned files (domainno not found and one file provided). skip rest of function
                    raise Exception('no domain variable found, while there are multiple partition files supplied, this is not expected')
                xu_return = partitions[0]
                return xu_return
            
            #get domain number from partition
            da_domainno = part[varn_domain]
            part_domainno = np.bincount(da_domainno).argmax() 
            if part_domainno in domainno_all:
                raise Exception(f'something went wrong, domainno {part_domainno} already occured: {domainno_all}') #this can happen if more ghostcells than actual cells (very small partitions). Alternative is: part_domainno = int(part.encoding['source'][-11:-7]) >> does not work on restartfiles, since it is _0000_20200101_120000_rst.nc
            domainno_all.append(part_domainno)
            
            idx = np.flatnonzero(da_domainno == part_domainno) #something like >=i is applicable to edges/nodes
            faces = grid.face_node_connectivity[idx] #is actually face_node_connectivity for non-ghostcells
            #edges_allnos = np.unique(grid.face_edge_connectivity) #match with face_idx?
            faces[faces != grid.fill_value] += accumulator
            accumulator += grid.n_node
            all_indices.append(idx)
            all_faces.append(faces)
            all_nodes_x.append(grid.node_x)
            all_nodes_y.append(grid.node_y)
        #print(f'{(dt.datetime.now()-dtstart).total_seconds():.2f} sec')
        node_x = np.concatenate(all_nodes_x)
        node_y = np.concatenate(all_nodes_y)
        node_xy = np.column_stack([node_x, node_y])
        merged_nodes, inverse = np.unique(node_xy, return_inverse=True, axis=0)
        n_face_total = sum(len(faces) for faces in all_faces)
        n_max_node = max(faces.shape[1] for faces in all_faces)
        merged_faces = np.full((n_face_total, n_max_node), -1, dtype=np.intp)
        start = 0
        for faces in all_faces:
            n_face, n_max_node = faces.shape
            end = start + n_face
            merged_faces[start:end, :n_max_node] = faces
            start = end
        isnode = merged_faces != -1
        faces_flat = merged_faces[isnode]
        renumbered = inverse[faces_flat]
        merged_faces[isnode] = renumbered
        merged_grid = xu.Ugrid2d(
            node_x=merged_nodes[:, 0],
            node_y=merged_nodes[:, 1],
            fill_value=-1,
            face_node_connectivity=merged_faces,
        )
        facedim = partitions[0].ugrid.grid.face_dimension
        nodedim = partitions[0].ugrid.grid.node_dimension
        edgedim = partitions[0].ugrid.grid.edge_dimension
        #print(facedim,nodedim,edgedim)
        
        #define list of variables per dimension
        ds_face_list = []
        #ds_node_list = []
        #ds_edge_list = []
        #ds_rest_list = []
        print('>> ds.isel()/xr.append(): ',end='')
        dtstart = dt.datetime.now()
        for idx, uds in zip(all_indices, partitions):
            face_variables = []
            node_variables = []
            edge_variables = []
            for varname in uds.variables.keys():
                if varn_maxfnodes in uds[varname].dims: # not possible to concatenate this dim (size varies per partition) #therefore, vars mesh2d_face_x_bnd and mesh2d_face_y_bnd cannot be included currently. Maybe drop topology_dimension?: partitions[0].ugrid.grid.to_dataset().mesh2d.topology_dimension
                    continue
                if facedim in uds[varname].dims:
                    face_variables.append(varname)
                if nodedim in uds[varname].dims:
                    node_variables.append(varname)
                if edgedim in uds[varname].dims:
                    edge_variables.append(varname)
            ds_face = uds.ugrid.obj[face_variables]
            #ds_node = uds.ugrid.obj[node_variables]
            #ds_edge = uds.ugrid.obj[edge_variables]
            ds_rest = uds.ugrid.obj.drop_dims([facedim,nodedim,edgedim])
            ds_face_list.append(ds_face.isel({facedim: idx}))
            #ds_node_list.append(ds_node)#.isel({nodedim: idx})) #TODO: add ghostcell removal for nodes and edges? take renumbering into account
            #ds_edge_list.append(ds_edge)#.isel({edgedim: idx}))
            #ds_rest_list.append(ds_rest)
        print(f'{(dt.datetime.now()-dtstart).total_seconds():.2f} sec')
        
        print('>> xr.concat(): ',end='')
        dtstart = dt.datetime.now()
        ds_face_concat = xr.concat(ds_face_list, dim=facedim)
        #ds_node_concat = xr.concat(ds_node_list, dim=nodedim) #TODO: evt compat="override" proberen
        #ds_edge_concat = xr.concat(ds_edge_list, dim=edgedim)
        #ds_rest_concat = xr.concat(ds_rest_list, dim=None)
        print(f'{(dt.datetime.now()-dtstart).total_seconds():.2f} sec')
        
        ds_merged = xr.merge([ds_face_concat,ds_rest])#,ds_node_concat,ds_edge_concat,ds_rest])
            
        varlist_merged = list(ds_merged.variables.keys())
        varlist_dropped_bool = ~pd.Series(varlist_onepart).isin(varlist_merged)
        varlist_dropped = pd.Series(varlist_onepart).loc[varlist_dropped_bool]
        if varlist_dropped_bool.any():
            print(f'WARNING: some variables dropped with merging of partitions:\n{varlist_dropped}')
        
        ds_merged = ds_merged.rename({facedim: merged_grid.face_dimension,
                                      #nodedim: merged_grid.node_dimension,
                                      #edgedim: merged_grid.edge_dimension
                                      }) #TODO: xugrid does not support other dimnames, xugrid issue is created: https://github.com/Deltares/xugrid/issues/25
        ds_merged_xu = xu.UgridDataset(ds_merged, grids=[merged_grid])
        
    
    print(f'>> dfmt.open_partitioned_dataset() total: {(dt.datetime.now()-dtstart_all).total_seconds():.2f} sec')
    return ds_merged_xu

