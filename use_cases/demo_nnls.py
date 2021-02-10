#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  9 17:35:16 2021

@author: cxd00
"""
#%% imports!
import numpy as np
import pylab as plt
import os
import tensorflow as tf
# tf.compat.v1.disable_eager_execution()
import tensorflow.keras as keras
import tensorflow_addons as tfa
from queue import Queue
from threading import Thread
from past.utils import old_div
from skimage import io
from skimage.transform import resize
import cv2
import timeit
import multiprocessing as mp
from tensorflow.python.keras import backend as K
from viola.caiman_functions import to_3D, to_2D
import scipy
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

#%% The following section is for generating NNLS traces, as per Fig <insert number>
#%% set folders
base_folder = "../../../NEL-LAB Dropbox/NEL/Papers/VolPy_online/CalciumData/DATA_PAPER_ELIFE"
dataset = ["/N.00.00", "/N.01.01", "/N.02.00", "/N.03.00.t", "/N.04.00.t", "/YST"][0]
slurm_data = base_folder + dataset + "/results_analysis_online_sensitive_SLURM_01.npz"
#%% get ground truth data
with np.load(slurm_data, allow_pickle=True) as ld:
    print(list(ld.keys()))
    locals().update(ld)
    Ab_gt = Ab[()].toarray()
    num_bckg = f.shape[0]
    b_gt, A_gt = Ab_gt[:,:num_bckg], Ab_gt[:,num_bckg:]
    num_comps = Ab_gt.shape[-1]
    f_gt, C_gt = Cf[:num_bckg], Cf[num_bckg:num_comps]
    noisyC = noisyC[num_bckg:num_comps]
#%% start comps : save the indices where each spatial footprint first appears
start_comps = []
for i in range(num_comps):
    start_comps.append(np.where(np.diff(Cf[i])>0)[0][0])
plt.plot(start_comps,np.arange(num_comps),'.')
#%% initialize with i frames, calculate GT
for i in [len(noisyC[0])//4]: #50%
    included_comps = np.where(np.array(start_comps)<i)[0]
    A_start = A_gt[:,included_comps]
    C_start = C_gt[included_comps]
    noisyC_start = noisyC[included_comps] # ground truth
    b_gt = b_gt
    f_gt = f_gt  
#%% pick up images as a movie file
dirname = base_folder + dataset + "/images_" + dataset[1:]
a2 = []
#for fname in os.listdir(dirname):r
for i in range(noisyC.shape[1]//2):
    fname = "image" + str(i).zfill(5) + ".tif"
    im = io.imread(os.path.join(dirname, fname))
    #a2.append(resize(im, (256, 256)))
    a2.append(im)
    #a2.append(im[0:125, 125:256])    
#%% image normalization for movie
img_norm = np.std(a2, axis=0)
img_norm += np.median(img_norm)
a2 = a2/img_norm[None, :, :]
#a2 = to_2D(np.asarray(Y_tot)).T
#%% one-time calculations and template
template = np.median(a2[:len(a2)//2], axis=0) # template created w/ first half
#f, Y =  f_full[:, 0][:, None], Y_tot[:, 0][:, None]
#YrA = YrA_full[:, 0][:, None]
# YrA = 
#C = C_full[:, 0][:, None]

#Ab = np.concatenate([A_sp_full.toarray()[:], b_full], axis=1).astype(np.float32) # A_gt
#b = Y_tot[:, 0]
Ab_gt_start = np.concatenate([A_start, b_gt], axis=1).astype(np.float32)
AtA = Ab_gt_start.T@Ab_gt_start
Atb = Ab_gt_start.T@b_gt
n_AtA = np.linalg.norm(AtA, ord='fro') #Frob. normalization
theta_1 = (np.eye(Ab_gt_start.shape[-1]) - AtA/n_AtA)
theta_2 = (Atb/n_AtA)[:, None].astype(np.float32)


#Cff = np.concatenate([C_full+YrA_full,f_full], axis=0)
Cf = np.concatenate([noisyC_start,f_gt], axis=0)
x0 = Cf[:,0].copy()[:,None]
#%% nnls
from scipy.optimize import nnls
fe = slice(0,None)
trace_nnls = np.array([nnls(Ab_gt,fr)[0] for fr in (a2)[fe]])
trace_nnls = trace_nnls.T 
#%% model creation
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
shapes = a2[0].shape
from viola.pipeline_gpu import Pipeline, get_model
model = get_model(template, shapes, Ab_gt_start.astype(np.float32), 30)
#model = get_model(template, shapes, newAb, 30)
model.compile(optimizer='rmsprop', loss='mse')
#%% extract traces
a2 = np.asarray(a2)
mc0 = np.expand_dims(a2[0:1, :, :], axis=3)
trace_extractor = Pipeline(model, x0[None, :], x0[None, :], mc0, theta_2, a2)
#%%
out = trace_extractor.get_traces(500)

test_traces = out
test_traces = np.array(test_traces).T.squeeze()