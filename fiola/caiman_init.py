#!/usr/bin/env python
"""
This file is used for performing offline initialization to provide spatial footprints
for FIOLA online analysis.
@author: @caichangjia
"""
import cv2
import glob
import logging
import matplotlib.pyplot as plt
import numpy as np
import os

try:
    cv2.setNumThreads(0)
except:
    pass

try:
    if __IPYTHON__:
        # this is used for debugging purposes only. allows to reload classes
        # when changed
        get_ipython().magic('load_ext autoreload')
        get_ipython().magic('autoreload 2')
except NameError:
    pass


import caiman as cm
from caiman.motion_correction import MotionCorrect
from caiman.source_extraction.cnmf import cnmf as cnmf
from caiman.source_extraction.cnmf import params as params
from caiman.utils.utils import download_demo
from caiman.summary_images import local_correlations_movie_offline

# %%
# Set up the logger (optional); change this if you like.
# You can log to a file using the filename parameter, or make the output more
# or less verbose by setting level to logging.DEBUG, logging.INFO,
# logging.WARNING, or logging.ERROR

#logging.basicConfig(format=
#                    "%(relativeCreated)12d [%(filename)s:%(funcName)20s():%(lineno)s]"\
#                    "[%(process)d] %(message)s",
#                    level=logging.WARNING)

#%%
def run_caiman_init(mov, fnames, mc_dict, opts_dict, quality_dict):

#%% Select file(s) to be processed (download if not present)
    m = cm.movie(mov)
    m.save(fnames)    

#%% First setup some parameters for data and motion correction
    print('start motion correction')
    opts = params.CNMFParams(params_dict=mc_dict)

# %% play the movie (optional)
    # playing the movie using opencv. It requires loading the movie in memory.
    # To close the video press q
    display_images = False

    if display_images:
        m_orig = cm.load_movie_chain(fnames)
        ds_ratio = 0.2
        moviehandle = m_orig.resize(1, 1, ds_ratio)
        moviehandle.play(q_max=99.5, fr=60, magnification=2)

# %% start a cluster for parallel processing
    c, dview, n_processes = cm.cluster.setup_cluster(
        backend='local', n_processes=None, single_thread=False)

# %%% MOTION CORRECTION
    # first we create a motion correction object with the specified parameters
    mc = MotionCorrect(fnames, dview=dview, **opts.get_group('motion'))
    # note that the file is not loaded in memory

# %% Run (piecewise-rigid motion) correction using NoRMCorre
    mc.motion_correct(save_movie=True)

# %% compare with original movie
    if display_images:
        m_orig = cm.load_movie_chain(fnames)
        m_els = cm.load(mc.mmap_file)
        ds_ratio = 0.2
        moviehandle = cm.concatenate([m_orig.resize(1, 1, ds_ratio) - mc.min_mov*mc.nonneg_movie,
                                      m_els.resize(1, 1, ds_ratio)], axis=2)
        moviehandle.play(fr=60, q_max=99.5, magnification=2)  # press q to exit

# %% MEMORY MAPPING
    print('start memory mapping')
    border_to_0 = 0 if mc.border_nan == 'copy' else mc.border_to_0
    # you can include the boundaries of the FOV if you used the 'copy' option
    # during motion correction, although be careful about the components near
    # the boundaries

    # memory map the file in order 'C'
    fname_new = cm.save_memmap(mc.mmap_file, base_name='memmap_', order='C',
                               border_to_0=border_to_0)  # exclude borders


    # now load the file
    Yr, dims, T = cm.load_memmap(fname_new)
    images = np.reshape(Yr.T, [T] + list(dims), order='F')
    # load frames in python format (T x X x Y)

# %% restart cluster to clean up memory
    cm.stop_server(dview=dview)
    c, dview, n_processes = cm.cluster.setup_cluster(
        backend='local', n_processes=None, single_thread=False)

# %%  parameters for source extraction and deconvolution
    print('start cnmf')
    opts.change_params(params_dict=opts_dict);
# %% RUN CNMF ON PATCHES
    # First extract spatial and temporal components on patches and combine them
    # for this step deconvolution is turned off (p=0). If you want to have
    # deconvolution within each patch change params.patch['p_patch'] to a
    # nonzero value

    #opts.change_params({'p': 0})
    cnm = cnmf.CNMF(n_processes, params=opts, dview=dview)
    cnm = cnm.fit(images)

# %% ALTERNATE WAY TO RUN THE PIPELINE AT ONCE
    #   you can also perform the motion correction plus cnmf fitting steps
    #   simultaneously after defining your parameters object using
    #  cnm1 = cnmf.CNMF(n_processes, params=opts, dview=dview)
    #  cnm1.fit_file(motion_correct=True)

# %% plot contours of found components
    Cns = local_correlations_movie_offline(mc.mmap_file[0],
                                           remove_baseline=True, window=1000, stride=1000,
                                           winSize_baseline=100, quantil_min_baseline=10,
                                           dview=dview)
    Cn = Cns.max(axis=0)
    Cn[np.isnan(Cn)] = 0
    cnm.estimates.plot_contours(img=Cn)
    plt.title('Contour plots of found components')
#%% save results
    cnm.estimates.Cn = Cn
    cnm.save(fname_new[:-5]+'_init.hdf5')

# %% RE-RUN seeded CNMF on accepted patches to refine and perform deconvolution
    print('start cnmf refit')
    cnm2 = cnm.refit(images, dview=dview)
    # %% COMPONENT EVALUATION
    cnm2.params.set('quality', quality_dict)
    cnm2.estimates.evaluate_components(images, cnm2.params, dview=dview)
    # %% PLOT COMPONENTS
    cnm2.estimates.plot_contours(img=Cn, idx=cnm2.estimates.idx_components)

    # %% VIEW TRACES (accepted and rejected)

    if display_images:
        cnm2.estimates.view_components(images, img=Cn,
                                      idx=cnm2.estimates.idx_components)
        cnm2.estimates.view_components(images, img=Cn,
                                      idx=cnm2.estimates.idx_components_bad)
    #%% update object with selected components
    cnm2.estimates.select_components(use_object=True)
    #%% Extract DF/F values
    cnm2.estimates.detrend_df_f(quantileMin=8, frames_window=250)

    #%% Show final traces
    cnm2.estimates.view_components(img=Cn)
    #%%
    cnm2.estimates.Cn = Cn
    cnm2.estimates.fname_new = fname_new
    cnm2.save(cnm2.mmap_file[:-4] + 'hdf5')
        
    #from caiman.source_extraction.cnmf import cnmf 
    #cnm2 = cnmf.load_CNMF('/home/nel/NEL-LAB Dropbox/NEL/Papers/VolPy_online/data/voltage_data/k53/memmap__d1_512_d2_512_d3_1_order_C_frames_3000_.hdf5')
    #cnm2.estimates.view_components()
    
    #%% reconstruct denoised movie (press q to exit)
    if display_images:
        cnm2.estimates.play_movie(images, q_max=99.9, gain_res=2,
                                  magnification=1,
                                  bpx=border_to_0,
                                  include_bck=False)  # background not shown

    #%% STOP CLUSTER and clean up log files
    cm.stop_server(dview=dview)
    log_files = glob.glob('*_LOG_*')
    for log_file in log_files:
        os.remove(log_file)

    return cnm2.estimates
