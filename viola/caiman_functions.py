#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May 30 09:32:42 2020

@author: andrea
"""

import numpy as np
from scipy import signal
from scipy import stats  
from past.utils import old_div
import matplotlib.pyplot as plt
import logging
import cv2

def play(mov, fr=400, backend='opencv', magnification=1, interpolation=cv2.INTER_LINEAR, offset=0, gain=1, q_max=100, q_min=1):
    if q_max < 100:
        maxmov = np.nanpercentile(mov[0:10], q_max)
    else:
        maxmov = np.nanmax(mov)
    if q_min > 0:
        minmov = np.nanpercentile(mov[0:10], q_min)
    else:
        minmov = np.nanmin(mov)
        
    for iddxx, frame in enumerate(mov):
        if backend == 'opencv':
            if magnification != 1:
                frame = cv2.resize(frame, None, fx=magnification, fy=magnification, interpolation=interpolation)
            frame = (offset + frame - minmov) * gain / (maxmov - minmov)
            cv2.imshow('frame', frame)
            if cv2.waitKey(int(1. / fr * 1000)) & 0xFF == ord('q'):
                break
            
    cv2.waitKey(100)
    cv2.destroyAllWindows()
    for i in range(10):
        cv2.waitKey(100)

def normalize(a):
    return (a-np.median(a))/(np.max(a)-np.min(a))

"""
def play(mov, fr=30, gain=1.0, magnification=1):    
    for frame in mov:
        if cv2.waitKey(int(1. / fr * 1000)) & 0xFF == ord('q'):
            break
        frame = cv2.resize(normalize(frame), None, fx=magnification, fy=magnification, interpolation=cv2.INTER_LINEAR)
        cv2.imshow('frame', frame)
        
    cv2.destroyAllWindows()
    return None
"""
       
def resize(mov_in, fx=1, fy=1, fz=1, interpolation=cv2.INTER_AREA):
        """
        Resizing caiman movie into a new one. Note that the temporal
        dimension is controlled by fz and fx, fy, fz correspond to
        magnification factors. For example to downsample in time by
        a factor of 2, you need to set fz = 0.5.

        Args:
            fx (float):
                Magnification factor along x-dimension

            fy (float):
                Magnification factor along y-dimension

            fz (float):
                Magnification factor along temporal dimension

        Returns:
            self (caiman movie)
        """
        T, d1, d2 = mov_in.shape
        d = d1 * d2
        elm = d * T
        max_els = 2**61 - 1    # the bug for sizes >= 2**31 is appears to be fixed now
        if elm > max_els:
            chunk_size = old_div((max_els), d)
            new_m: List = []
            logging.debug('Resizing in chunks because of opencv bug')
            for chunk in range(0, T, chunk_size):
                logging.debug([chunk, np.minimum(chunk + chunk_size, T)])
                m_tmp = mov_in[chunk:np.minimum(chunk + chunk_size, T)].copy()
                m_tmp = m_tmp.resize(fx=fx, fy=fy, fz=fz, interpolation=interpolation)
                if len(new_m) == 0:
                    new_m = m_tmp
                else:
                    new_m = timeseries.concatenate([new_m, m_tmp], axis=0)

            return new_m
        else:
            if fx != 1 or fy != 1:
                logging.debug("reshaping along x and y")
                t, h, w = mov_in.shape
                newshape = (int(w * fy), int(h * fx))
                mov = []
                logging.debug("New shape is " + str(newshape))
                for frame in mov_in:
                    mov.append(cv2.resize(frame, newshape, fx=fx, fy=fy, interpolation=interpolation))
                mov_in = np.asarray(mov)
            if fz != 1:
                logging.debug("reshaping along z")
                t, h, w = mov_in.shape
                mov_in = np.reshape(mov_in, (t, h * w))
                mov = cv2.resize(mov_in, (h * w, int(fz * t)), fx=1, fy=fz, interpolation=interpolation)
                mov = np.reshape(mov, (np.maximum(1, int(fz * t)), h, w))
                mov_in = np.asarray(mov)                

        return self       
           
def gaussian_blur_2D(movie_in,
                         kernel_size_x=5,
                         kernel_size_y=5,
                         kernel_std_x=1,
                         kernel_std_y=1,
                         borderType=cv2.BORDER_REPLICATE):
        """
        Compute gaussian blut in 2D. Might be useful when motion correcting

        Args:
            kernel_size: double
                see opencv documentation of GaussianBlur
            kernel_std_: double
                see opencv documentation of GaussianBlur
            borderType: int
                see opencv documentation of GaussianBlur

        Returns:
            self: ndarray
                blurred movie
        """
        movie_out = np.zeros_like(movie_in)
        for idx, fr in enumerate(movie_in):
            movie_out[idx] = cv2.GaussianBlur(fr,
                                         ksize=(kernel_size_x, kernel_size_y),
                                         sigmaX=kernel_std_x,
                                         sigmaY=kernel_std_y,
                                         borderType=borderType)

        return movie_out

def resize(mov_in, fx=1, fy=1, fz=1, interpolation=cv2.INTER_AREA):
        """
        Resizing caiman movie into a new one. Note that the temporal
        dimension is controlled by fz and fx, fy, fz correspond to
        magnification factors. For example to downsample in time by
        a factor of 2, you need to set fz = 0.5.

        Args:
            fx (float):
                Magnification factor along x-dimension

            fy (float):
                Magnification factor along y-dimension

            fz (float):
                Magnification factor along temporal dimension

        Returns:
            mov_in (caiman movie)
        """
        T, d1, d2 = mov_in.shape
        d = d1 * d2
        elm = d * T
        max_els = 2**61 - 1    # the bug for sizes >= 2**31 is appears to be fixed now
        if elm > max_els:
            chunk_size = old_div((max_els), d)
            new_m = []
            for chunk in range(0, T, chunk_size):
                m_tmp = mov_in[chunk:np.minimum(chunk + chunk_size, T)].copy()
                m_tmp = m_tmp.resize(fx=fx, fy=fy, fz=fz, interpolation=interpolation)
                if len(new_m) == 0:
                    new_m = m_tmp
                else:
                    new_m = np.concatenate([new_m, m_tmp], axis=0)

            return new_m
        else:
            if fx != 1 or fy != 1:
                t, h, w = mov_in.shape
                newshape = (int(w * fy), int(h * fx))
                mov = []
                for frame in mov_in:
                    mov.append(cv2.resize(frame, newshape, fx=fx, fy=fy, interpolation=interpolation))
                mov_out = np.asarray(mov)
            if fz != 1:
                t, h, w = mov_in.shape
                mov_in = np.reshape(mov_in, (t, h * w))
                mov = cv2.resize(mov_in, (h * w, int(fz * t)), fx=1, fy=fz, interpolation=interpolation)
                mov = np.reshape(mov, (np.maximum(1, int(fz * t)), h, w))
                mov_out = mov

        return mov_out

def to_2D(mov, order='F') -> np.ndarray:
        [T, d1, d2] = mov.shape
        d = d1 * d2
        return np.reshape(mov, (T, d), order=order)

def to_3D(mov2D, shape, order='F'):
    """
    transform a vectorized movie into a 3D shape
    """
    return np.reshape(mov2D, shape, order=order)

def bin_median(mat, window=10, exclude_nans=True):
    """ compute median of 3D array in along axis o by binning values
    Args:
        mat: ndarray
            input 3D matrix, time along first dimension
        window: int
            number of frames in a bin
    Returns:
        img:
            median image
    Raises:
        Exception 'Path to template does not exist:'+template
    """
    T, d1, d2 = np.shape(mat)
    if T < window:
        window = T
    num_windows = np.int(old_div(T, window))
    num_frames = num_windows * window
    if exclude_nans:
        img = np.nanmedian(np.nanmean(np.reshape(
            mat[:num_frames], (window, num_windows, d1, d2)), axis=0), axis=0)
    else:
        img = np.median(np.mean(np.reshape(
            mat[:num_frames], (window, num_windows, d1, d2)), axis=0), axis=0)
    return img

def signal_filter(sg, freq, fr, order=3, mode='high'):
    """
    Function for high/low passing the signal with butterworth filter
    
    Args:
        sg: 1-d array
            input signal
            
        freq: float
            cutoff frequency
        
        order: int
            order of the filter
        
        mode: str
            'high' for high-pass filtering, 'low' for low-pass filtering
            
    Returns:
        sg: 1-d array
            signal after filtering            
    """
    normFreq = freq / (fr / 2)
    b, a = signal.butter(order, normFreq, mode)
    #print([order, normFreq, mode])
    sg = np.single(signal.filtfilt(b, a, sg, padtype='odd', padlen=3 * (max(len(b), len(a)) - 1)))
    return sg

def get_thresh(pks, clip, pnorm=0.5, min_spikes=30):
    """ Function for deciding threshold given heights of all peaks.

    Args:
        pks: 1-d array
            height of all peaks

        clip: int
            maximum number of spikes for producing templates

        pnorm: float, between 0 and 1, default is 0.5
            a variable deciding the amount of spikes chosen
            
        min_spikes: int
            minimal number of spikes to be detected

    Returns:
        thresh: float
            threshold for choosing spikes

        falsePosRate: float
            possibility of misclassify noise as real spikes

        detectionRate: float
            possibility of real spikes being detected

        low_spikes: boolean
            true if number of spikes is smaller than minimal value
    """
    # find median of the kernel density estimation of peak heights
    spread = np.array([pks.min(), pks.max()])
    spread = spread + np.diff(spread) * np.array([-0.05, 0.05])
    low_spikes = False
    pts = np.linspace(spread[0], spread[1], 2001)
    kde = stats.gaussian_kde(pks)
    f = kde(pts)    
    xi = pts
    center = np.where(xi > np.median(pks))[0][0]
    
    fmodel = np.concatenate([f[0:center + 1], np.flipud(f[0:center])])
    if len(fmodel) < len(f):
        fmodel = np.append(fmodel, np.ones(len(f) - len(fmodel)) * min(fmodel))
    else:
        fmodel = fmodel[0:len(f)]

    # adjust the model so it doesn't exceed the data:
    csf = np.cumsum(f) / np.sum(f)
    csmodel = np.cumsum(fmodel) / np.max([np.sum(f), np.sum(fmodel)])
    lastpt = np.where(np.logical_and(csf[0:-1] > csmodel[0:-1] + np.spacing(1), csf[1:] < csmodel[1:]))[0]
    if not lastpt.size:
        lastpt = center
    else:
        lastpt = lastpt[0]
    fmodel[0:lastpt + 1] = f[0:lastpt + 1]
    fmodel[lastpt:] = np.minimum(fmodel[lastpt:], f[lastpt:])
    
    # find threshold
    csf = np.cumsum(f)
    csmodel = np.cumsum(fmodel)
    csf2 = csf[-1] - csf
    csmodel2 = csmodel[-1] - csmodel
    obj = csf2 ** pnorm - csmodel2 ** pnorm
    maxind = np.argmax(obj)
    thresh = xi[maxind]
    
    thresh_negative = -np.percentile(pks, 0.1)
    print(f'adaptive thresholding: {thresh}')
    print(f'thresholding negative value: {thresh_negative}')
    
    plt.figure(); plt.plot(pts, f); plt.plot(pts[:len(f)], fmodel); plt.vlines(thresh, 0, np.max(f), 'r')
    plt.vlines(thresh_negative, 0, np.max(f), 'b')
    plt.figure(); plt.plot(csf2); plt.plot(csmodel2)
    
    thresh = np.maximum(thresh, thresh_negative)

    
    """
    if np.sum(pks > thresh) < min_spikes:
        low_spikes = True
        logging.warning(f'Few spikes were detected. Adjusting threshold to take {min_spikes} largest spikes')
        thresh = np.percentile(pks, 100 * (1 - min_spikes / len(pks)))
    elif ((np.sum(pks > thresh) > clip) & (clip > 0)):
        logging.warning(f'Selecting top {min_spikes} spikes for template')
        thresh = np.percentile(pks, 100 * (1 - clip / len(pks)))
    """
    ix = np.argmin(np.abs(xi - thresh))
    falsePosRate = csmodel2[ix] / csf2[ix]
    detectionRate = (csf2[ix] - csmodel2[ix]) / np.max(csf2 - csmodel2)
    return thresh, falsePosRate, detectionRate, low_spikes
