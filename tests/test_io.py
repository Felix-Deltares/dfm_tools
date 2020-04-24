# -*- coding: utf-8 -*-
"""
Created on Wed Mar 18 16:33:52 2020

@author: veenstra
"""

import pytest
import inspect
import os

dir_testinput = os.path.join(r'c:/DATA','dfm_tools_testdata')
from dfm_tools.testutils import getmakeoutputdir




@pytest.mark.acceptance
def test_mdu():
    """
    tests whether mdu file can be imported and exported
    """

    dir_output = getmakeoutputdir(__file__,inspect.currentframe().f_code.co_name)
    #dir_output = './test_output'
    if not os.path.exists(dir_output):
        os.mkdir(dir_output)

    from dfm_tools.io import mdu
        
    try:
        filename_mdu = os.path.join(dir_testinput, r'DFM_3D_z_Grevelingen\computations\run01\Grevelingen-FM.mdu')
        data_mdu = mdu.read_deltares_ini(filename_mdu)
        print(data_mdu)
        import_success = True
    except:
        import_success = False

    try:
        filename_mdu_out = os.path.join(dir_output, 'Grevelingen-FM_out.mdu')
        mdu.write_deltares_ini(data_mdu, filename_mdu_out)
        export_success = True
    except:
        export_success = False
    
    assert import_success == True
    assert export_success == True






@pytest.mark.parametrize("file_pol", [pytest.param(os.path.join(dir_testinput,'DFM_3D_z_Grevelingen\\geometry\\structures\\Grevelingen-FM_BL_fxw.pliz'), id='Grevelingen pliz'),
                                      pytest.param(os.path.join(dir_testinput,'DFM_3D_z_Grevelingen\\geometry\\structures\\Grevelingen-FM_BL_fxw.pli'), id='Grevelingen pli'),
                                      pytest.param(os.path.join(dir_testinput,'world.ldb'), id='world'),
                                      pytest.param(os.path.join(dir_testinput,'Maeslant.tek'), id='Maeslant'),
                                      pytest.param(os.path.join(dir_testinput,'ballenplot\\0200a.tek'), id='Kivu tek map sal'),
                                      pytest.param(os.path.join(dir_testinput,'ballenplot\\SDS-zd003b5dec2-sal.tek'), id='Kivu tek map more'),
                                      pytest.param(os.path.join(dir_testinput,'test_new.tek'), id='ts_Theo')])
@pytest.mark.unittest
def test_readpolygon(file_pol):
    dir_output = getmakeoutputdir(__file__,inspect.currentframe().f_code.co_name)
    """
    this test tests if a netcdf varname can be retrieved from the 'dictionary' and if the variable can be retrieved from de netcdf
    file_pol = os.path.join(dir_testinput,'DFM_3D_z_Grevelingen\\geometry\\structures\\Grevelingen-FM_BL_fxw.pliz')
    file_pol = os.path.join(dir_testinput,'DFM_3D_z_Grevelingen\\geometry\\structures\\Grevelingen-FM_BL_fxw.pli')
    file_pol = os.path.join(dir_testinput,'world.ldb')
    file_pol = 'p:\\11205258-006-kpp2020_rmm-g6\\C_Work\\08_RMM_FMmodel\\geometry_j13_6-w3\\rmm_v1p3_fixed_weirs.pliz'
    file_pol = 'p:\\11205258-006-kpp2020_rmm-g6\\C_Work\\08_RMM_FMmodel\\geometry_j13_6-w3\\structures\\rmm_v1p3_structures.pli'
    file_pol = 'p:\\11205258-006-kpp2020_rmm-g6\\C_Work\\04_randvoorwaarden\\keringen\\Maeslantkering\\Maeslant.tek'
    file_pol = os.path.join(dir_testinput,'Maeslant.tek')
    file_pol = os.path.join(dir_testinput,'test_new.tek')
    file_pol = os.path.join(dir_testinput,'ballenplot\\0200a.tek')
    file_pol = os.path.join(dir_testinput,'ballenplot\\SDS-zd003b5dec2-sal.tek')

    dir_output = './test_output'
    """
    
    
    import matplotlib.pyplot as plt
    plt.close('all')
    
    from dfm_tools.io.polygon import Polygon
        
    pol_data_list, pol_name_list, pol_comment_list = Polygon.fromfile(file_pol, pd_output=False)
    pol_data_pd_list = Polygon.fromfile(file_pol, pd_output=True)
    pol_object_list = Polygon.fromfile(file_pol, obj_output=True)

    fig, ax = plt.subplots()
    for iP, pol_data in enumerate(pol_data_list):
        pd_collist = pol_data_pd_list[iP].columns.tolist()
        if 'datetime' in pd_collist:
            for iV in range(3,len(pd_collist)):
                ax.plot(pol_data_pd_list[iP].loc[:,'datetime'],pol_data_pd_list[iP].iloc[:,iV],'-',label=pd_collist[iV], linewidth=0.5)
        elif '*column 1 : X' in pd_collist or '*column 1 = x coordinate' in pd_collist:
            for iV in range(len(pd_collist)):
                ax.plot(pol_data_pd_list[iP].iloc[:,iV],'-',label=pd_collist[iV], linewidth=0.5)
        else: #eg ldb
            ax.plot(pol_data[:,0],pol_data[:,1],'-',linewidth=0.5)
    ax.legend()
    plt.savefig(os.path.join(dir_output,os.path.basename(file_pol).replace('.','')))






@pytest.mark.unittest
def test_readnoosfile():
    dir_output = getmakeoutputdir(__file__,inspect.currentframe().f_code.co_name)
    """
    this test tests if a netcdf varname can be retrieved from the 'dictionary' and if the variable can be retrieved from de netcdf

    dir_output = './test_output'
    """
    
    file_noos = os.path.join(dir_testinput,'KORNWDZBTN_waterlevel_20061201_20190101_diffnanvals.noos')
    #import matplotlib.pyplot as plt
    
    from dfm_tools.io.noos import read_noosfile, write_noosfile
    
    
    noosdata_pd, noosheader_dict = read_noosfile(file_noos=file_noos,get_header=True,na_values=['N/A',-999])
    """
    fig, ax = plt.subplots()
    ax.plot(noosdata_pd['datetime'], noosdata_pd['values'])
    """
    #write noosfile
    header_dict = {'Source': 'from noosfile', 'Analysis time': 200201012300, 'Time zone': 'GMT', 'Coordinate system': 'WGS84',
                   'x-coordinate': 200, 'y-coordinate': 300, 'Variable': 'waterlevel', 'Unit': 'm', 'teststring': ''}
    
    write_noosfile(os.path.join(dir_output,'noos_out.noos'), noosdata_pd, metadata=noosheader_dict, na_values=-999.999)
    write_noosfile(os.path.join(dir_output,'noos_out2.noos'), noosdata_pd, metadata=header_dict, na_values=-999.999)







@pytest.mark.acceptance
def test_mergenetCDFtime():
    dir_output = getmakeoutputdir(__file__,inspect.currentframe().f_code.co_name)
    """
    this test tests merging a (eg meteo) netcdf over time

    dir_output = './test_output'
    """

    import datetime as dt
    
    from dfm_tools.io.netCDF_utils import merge_netCDF_time
    """
    if mode == 'meteo':
        dir_data = 'P:\\1204257-dcsmzuno\\2014\\data\\meteo'
        subfolders = ['HIRLAM72_2011','HIRLAM72_2012','HIRLAM72_2013','HIRLAM72_2014','HIRLAM72_2015','HIRLAM72_2016','HIRLAM72_2017','HIRLAM72_2018','HIRLAM72_2019']
        ignorelist = ['P:\\1204257-dcsmzuno\\2014\\data\\meteo\\HIRLAM72_2016\\h72_2016_merged.nc']
        vars_orig = ['air_pressure_fixed_height','northward_wind','eastward_wind'] #voor meteo folder
        vars_dest = vars_orig
        convert_vars = [0,0,0]
    elif mode == 'meteo_heatflux':
        dir_data = 'P:\\1204257-dcsmzuno\\2014\\data\\meteo-heatflux'
        subfolders = ['HIRLAM72_2011','HIRLAM72_2012','HIRLAM72_2013','HIRLAM72_2014','HIRLAM72_2015','HIRLAM72_2016','HIRLAM72_2017','HIRLAM72_2018','HIRLAM72_2019']
        ignorelist = []
        vars_orig = ['dew_point_temperature','air_temperature','cloud_area_fraction'] #voor meteo-heatflux folder
        vars_dest = vars_orig
        convert_vars = [1,1,2] #0 is no conversion, 1 is K to C (incl unit), 2 is cloud cover fraction (0-1) to cloud cover percentage (0-100) (unit is al %)
    else:
        raise Exception('ERROR: wrong mode %s'%(mode))
    """
    
    #SETTINGS
    tstart = dt.datetime(2016,4,28)
    tstop = dt.datetime(2016,5,3)
    tstep_sec = 3600*24
    dir_data = r'n:\Deltabox\Postbox\Veenstra, Jelmer\vanReimer\GLBu0.08_expt_91.2'
    nc_prefix = 'HYCOM_ST_GoO_'
    fn_match_pattern = '%s(.*).nc'%(nc_prefix)
    fn_dateformat = '%Y%m%d'
    #subfolders = ''
    dir_out = r'n:\Deltabox\Postbox\Veenstra, Jelmer\vanReimer\merged_new'
    renamevars = {'salinity':'so', 'water_temp':'thetao'}
    ###############
    file_to = merge_netCDF_time(tstart=tstart, tstop=tstop, tstep_sec=tstep_sec, dir_data=dir_data, nc_prefix=nc_prefix, 
                                fn_match_pattern=fn_match_pattern, fn_dateformat=fn_dateformat, dir_out=dir_out, renamevars=renamevars)
    
    file_nc = file_to

    from dfm_tools.get_nc import get_ncmodeldata#, get_netdata, get_ncmodeldata, plot_netmapdata
    from dfm_tools.get_nc_helpers import get_ncvardimlist#, get_ncfilelist
    
    vars_pd, dims_pd = get_ncvardimlist(file_nc=file_nc)
    
    data_fromnc = get_ncmodeldata(file_nc=file_nc, varname=renamevars['salinity'], timestep='all', layer='all')
    data_to = data_fromnc.var_ncobject
    
    varlist = data_to.variables.keys()
    print(varlist)
    #data_to.variables['salinity'].setncattr('standard_name','sea_water_salinity')
    #data_to.variables['water_temp'].setncattr('standard_name','sea_water_potential_temperature')