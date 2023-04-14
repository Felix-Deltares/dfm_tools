# -*- coding: utf-8 -*-
"""
Created on Fri Oct  7 09:36:01 2022

@author: veenstra
"""

import os
import matplotlib.pyplot as plt
plt.close('all')
import dfm_tools as dfmt
import hydrolib.core.dflowfm as hcdfm

dir_output = '.'

file_xyz = r'p:\archivedprojects\11205258-006-kpp2020_rmm-g6\C_Work\08_RMM_FMmodel\geometry_j19_NL_6-v2\rmm_vzm_v1p1_initial_water_level.xyz'
#file_xyz = r'p:\archivedprojects\11206813-006-kpp2021_rmm-2d\C_Work\31_RMM_FMmodel\general\diffusivity_rivzee_v6.xyz'
#TODO: some of the timfiles contain duplicate times, but these are not validated anymore since the TimRecord implementation: file_struct = r'p:\archivedprojects\11205258-006-kpp2020_rmm-g6\C_Work\08_RMM_FMmodel\structures_toRTC\RMM_structures_ts_cl10_coeff10.ini' #TODO: incorrect timfiles (e.g. with duplicate times) are now read as ForcingModel instead: https://github.com/Deltares/HYDROLIB-core/issues/519

data_xyz = hcdfm.XYZModel(file_xyz)
xyz_pd = dfmt.pointlike_to_DataFrame(data_xyz)

fig,ax = plt.subplots()
xyz_pd.plot.scatter(x='x',y='y',c='z',s=0.5,ax=ax)#,vmin=-1,vmax=1)
fig.tight_layout()
fig.savefig(os.path.join(dir_output,os.path.basename(file_xyz).replace('.','')))

file_xyn = r'p:\archivedprojects\11206813-006-kpp2021_rmm-2d\C_Work\31_RMM_FMmodel\geometry_j19_6-v2\output_locations\rmm_vzm-j19_6-v2b_3_measurement_obs.xyn'
data_xyn1 = hcdfm.ObservationPointModel(file_xyn) #TODO: this should raise an error, but it returns an empy list: https://github.com/Deltares/HYDROLIB-core/issues/502
data_xyn2 = hcdfm.XYNModel(file_xyn) #TODO: this raises an error for rmm obspoints "ValueError: Error parsing XYN file [..], line 22. Name `"lichteiland goeree 1 / lichteiland goeree"` contains whitespace, so should be enclosed in single quotes." >> https://github.com/Deltares/HYDROLIB-core/issues/537
data_xyn2_pd = dfmt.pointlike_to_DataFrame(data_xyn2) #works as expected #TODO: add DataFrame_to_XYNModel() conversion?
data_xyn2.save(file_xyn.replace('_obs.xyn','_out_obs.xyn'))

file_crs = r'p:\archivedprojects\11206813-006-kpp2021_rmm-2d\C_Work\31_RMM_FMmodel\geometry_j19_6-v2\cross_sections\rmm_vzm-j19_6-v2b_3_measurement_crs.pli'
data_crs1 = hcdfm.CrossLocModel(file_crs) #TODO: this should raise an error, but it returns an empty list: https://github.com/Deltares/HYDROLIB-core/issues/502
data_crs2 = hcdfm.CrossDefModel(file_crs) #TODO: same
data_crs3 = hcdfm.PolyFile(file_crs) #works with polyfile
polyobject_pd = [dfmt.pointlike_to_DataFrame(x) for x in data_crs3.objects] #TODO: how to get a useful+plottable object?
