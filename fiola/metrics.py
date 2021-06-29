#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May 23 08:29:29 2020

@author: agiovann
"""

#%% import library
#import os
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import linear_sum_assignment
from viola.nmf_support import normalize, normalize_piecewise
#from scipy.signal import find_peaks
#import peakutils
#from scipy import signal
#from scipy.signal import savgol_filter
#from time import time
#from caiman.components_evaluation import mode_robust_fast
#from scipy import stats
#%% relevant functions
def distance_spikes(s1, s2, max_dist):
    """ Define distance matrix between two spike train.
    Distance greater than maximum distance is assigned one.
    """    
    D = np.ones((len(s1), len(s2)))
    for i in range(len(s1)):
        for j in range(len(s2)):
            if np.abs(s1[i] - s2[j]) > max_dist:
                D[i, j] = 1
            else:
                D[i, j] = (np.abs(s1[i] - s2[j]))/5/max_dist
    return D

def find_matches(D):
    """ Find matches between two spike train by solving linear assigment problem.
    Delete matches where their distance is greater than maximum distance
    """
    index_gt, index_method = linear_sum_assignment(D)
    del_list = []
    for i in range(len(index_gt)):
        if D[index_gt[i], index_method[i]] == 1:
            del_list.append(i)
    index_gt = np.delete(index_gt, del_list)
    index_method = np.delete(index_method, del_list)
    return index_gt, index_method

def spike_comparison(i, e_sg, e_sp, e_t, v_sg, v_sp, v_t, scope, max_dist, save=False):
    e_sg = e_sg[np.where(np.multiply(e_t>=scope[0], e_t<=scope[1]))[0]]
    e_sg = (e_sg - np.mean(e_sg))/(np.max(e_sg)-np.min(e_sg))*np.max(v_sg)
    e_sp = e_sp[np.where(np.multiply(e_sp>=scope[0], e_sp<=scope[1]))[0]]
    e_t = e_t[np.where(np.multiply(e_t>=scope[0], e_t<=scope[1]))[0]]
    #plt.plot(e_t, e_sg, label='ephys', color='blue')
    #plt.plot(e_sp, np.max(e_sg)*1.1*np.ones(e_sp.shape),color='b', marker='.', ms=2, fillstyle='full', linestyle='none')
    
    v_sg = v_sg[np.where(np.multiply(v_t>=scope[0], v_t<=scope[1]))[0]]
    v_sp = v_sp[np.where(np.multiply(v_sp>=scope[0], v_sp<=scope[1]))[0]]
    v_t = v_t[np.where(np.multiply(v_t>=scope[0], v_t<=scope[1]))[0]]
    #plt.plot(v_t, v_sg, label='ephys', color='blue')
    #plt.plot(v_sp, np.max(v_sg)*1.1*np.ones(v_sp.shape),color='b', marker='.', ms=2, fillstyle='full', linestyle='none')
    
    # Distance matrix and find matches
    D = distance_spikes(s1=e_sp, s2=v_sp, max_dist=max_dist)
    index_gt, index_method = find_matches(D)
    spike = [e_sp, v_sp]
    match = [e_sp[index_gt], v_sp[index_method]]
    height = np.max(np.array(e_sg.max(), v_sg.max()))
    
    # Calculate measures
    TP = len(index_gt)
    FP = len(v_sp) - TP
    FN = len(e_sp) - TP
    
    if len(e_sp) == 0:
        F1 = np.nan
        precision = np.nan
        recall = np.nan
    else:
        try:    
            precision = TP / (TP + FP)
        except ZeroDivisionError:
            precision = 0
    
        recall = TP / (TP + FN)
    
        try:
            F1 = 2 * (precision * recall) / (precision + recall) 
        except ZeroDivisionError:
            F1 = 0
 
    print('precision:',precision)
    print('recall:',recall)
    print('F1:',F1)      
    if save:
        plt.figure()
        plt.plot(e_t, e_sg, color='b', label='ephys')
        plt.plot(e_sp, 1.2*height*np.ones(e_sp.shape),color='b', marker='.', ms=2, fillstyle='full', linestyle='none')
        plt.plot(v_t, v_sg, color='orange', label='VolPy')
        plt.plot(v_sp, 1.4*height*np.ones(len(v_sp)),color='orange', marker='.', ms=2, fillstyle='full', linestyle='none')
        for j in range(len(index_gt)):
            plt.plot((e_sp[index_gt[j]], v_sp[index_method[j]]),(1.25*height, 1.35*height), color='gray',alpha=0.5, linewidth=1)
        ax = plt.gca()
        ax.locator_params(nbins=7)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        plt.legend(prop={'size': 6})
        plt.tight_layout()
        plt.savefig(f'{volpy_path}/spike_sweep{i}_{vpy.params.volspike["threshold_method"]}.pdf')
    return precision, recall, F1, match, spike

def spnr_computation(i, e_sg, e_sp, e_t, v_sg, v_sp, v_t, scope, max_dist, save=False):
    spnr = []
    e_sg = e_sg[np.where(np.multiply(e_t>=scope[0], e_t<=scope[1]))[0]]
    e_sg = (e_sg - np.mean(e_sg))/(np.max(e_sg)-np.min(e_sg))*np.max(v_sg)
    e_sp = e_sp[np.where(np.multiply(e_sp>=scope[0], e_sp<=scope[1]))[0]]
    e_t = e_t[np.where(np.multiply(e_t>=scope[0], e_t<=scope[1]))[0]]
    
    v_sg = normalize_piecewise(v_sg, step=5000)    
    v_sg = v_sg[np.where(np.multiply(v_t>=scope[0], v_t<=scope[1]))[0]]
    v_sp = v_sp[np.where(np.multiply(v_sp>=scope[0], v_sp<=scope[1]))[0]]
    v_t = v_t[np.where(np.multiply(v_t>=scope[0], v_t<=scope[1]))[0]]
    
    for e in e_sp:
        tp = np.where(np.abs(v_t - e) == np.min(np.abs(v_t - e)))[0][0]
        spnr.append(np.max(v_sg[tp-1:tp+2]))
    return spnr

# Compute subthreshold correlation coefficents
def sub_correlation(i, v_t, e_sub, v_sub, scope, save=False):
    e_sub = e_sub[np.where(np.multiply(v_t>=scope[0], v_t<=scope[1]))[0]]
    v_sub = v_sub[np.where(np.multiply(v_t>=scope[0], v_t<=scope[1]))[0]]
    v_t = v_t[np.where(np.multiply(v_t>=scope[0], v_t<=scope[1]))[0]]
    corr = np.corrcoef(e_sub, v_sub)[0,1]
    if save:
        plt.figure()
        plt.plot(v_t, e_sub)
        plt.plot(v_t, v_sub)   
        plt.savefig(f'{volpy_path}/spike_sweep{i}_subthreshold.pdf')
    return corr

def metric(name, sweep_time, e_sg, e_sp, e_t, e_sub, v_sg, v_sp, v_t, v_sub, init_frames=20000, save=False):
    precision = []
    recall = []
    F1 = []
    sub_corr = []
    mean_time = []
    e_match = []
    v_match = []
    e_spike_aligned = []
    v_spike_aligned = []    
    spnr = []
    
    if 'Cell' in name: # belong Marton
        for i in range(len(sweep_time)):
            print(f'sweep{i}')
            if i == 0:
                scope = [max([e_t.min(), v_t.min()]), sweep_time[i][-1]]
            elif i == len(sweep_time) - 1:
                scope = [sweep_time[i][0], min([e_t.max(), v_t.max()])]
            else:
                scope = [sweep_time[i][0], sweep_time[i][-1]]
            mean_time.append(1 / 2 * (scope[0] + scope[-1]))
            
            # frames for initialization are not counted for F1 score            
            if v_t[init_frames] < scope[1]:
                if v_t[init_frames] < scope[0]:
                    pass
                else:
                    scope[0] = v_t[init_frames]               
                mean_time.append(1 / 2 * (scope[0] + scope[-1]))
                pr, re, F, match, spike = spike_comparison(i, e_sg, e_sp, e_t, v_sg, v_sp, v_t, scope, max_dist=0.01, save=save)
                sp = spnr_computation(i, e_sg, e_sp, e_t, v_sg, v_sp, v_t, scope, max_dist=0.01, save=save)
                corr = sub_correlation(i, v_t, e_sub, v_sub, scope, save=save)
                precision.append(pr)
                recall.append(re)
                F1.append(F)
                spnr.append(sp)
                sub_corr.append(corr)
                e_match.append(match[0])
                v_match.append(match[1])
                e_spike_aligned.append(spike[0])
                v_spike_aligned.append(spike[1])
            else:
                print(f'sweep{i} is used for initialization and not counted for F1 score')                
            
        e_match = np.concatenate(e_match)
        v_match = np.concatenate(v_match)
        e_spike_aligned = np.concatenate(e_spike_aligned)
        v_spike_aligned = np.concatenate(v_spike_aligned)
        spnr = np.mean(np.concatenate(spnr))
    else: 
        #import pdb
        #pdb.set_trace()
        scope = [e_t.min(), e_t.max()]
        scope[0] = v_t[init_frames]
        print(scope)
        
        if 'Mouse' in name:
            max_dist = 200  # 20000 Hz* 0.01s
        elif 'Fish' in name: 
            max_dist = 60 # 6000Hz * 0.01s

        pr, re, F, match, spike = spike_comparison(None, e_sg, e_sp, e_t, v_sg, v_sp, v_t, scope, max_dist=max_dist, save=False)
        sp = spnr_computation(None, e_sg, e_sp, e_t, v_sg, v_sp, v_t, scope, max_dist=0.01, save=save)
        precision.append(pr)
        recall.append(re)
        F1.append(F)
        spnr = np.mean(sp)
        e_match = match[0]
        v_match = match[1]
        e_spike_aligned = spike[0]
        v_spike_aligned = spike[1]


    return precision, recall, F1, sub_corr, e_match, v_match, mean_time, e_spike_aligned, v_spike_aligned, spnr

def compute_spnr(t1, t2, s1, s2, t_range, min_counts=10):
    t1 = normalize(t1)
    t2 = normalize(t2)
    both_found = np.intersect1d(s1, s2)
    both_found = both_found[np.logical_and(both_found>t_range[0], both_found<t_range[1])]
    print(len(both_found))
    spnr = [np.mean(t1[both_found]), np.mean(t2[both_found])]
    if len(both_found) < min_counts:
        spnr = [np.nan, np.nan]
    return spnr

