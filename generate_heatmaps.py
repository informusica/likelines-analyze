import os
import sys
import csv
import json
from glob import iglob as glob
from itertools import izip
import re

import cPickle as pickle

import numpy as np
import scipy.signal



def _config(**kwargs):
    INPUT_DIR = kwargs.get('INPUT_DIR') or 'run1'
    INPUT_FILES = 'viewHist_*.txt'
    
    #INPUT_DIR = 'heatpilot1'
    
    INPUT_FILES_RE = re.compile(INPUT_FILES.replace('*','(.*)'))
    INPUT_CACHE = os.path.join(INPUT_DIR, 'viewHist.pickle')
    
    OUTPUT_DIR = INPUT_DIR
    
    # median
    SMOOTH_WINDOW_1 = 11
    #SMOOTH_WINDOW_2 = 25
    SMOOTH_WINDOW_2 = 5
    
    # Alan's paper, approximately, but it actually used a Kaiser filter
    #SMOOTH_WINDOW_1 = 27
    #SMOOTH_WINDOW_2 = 59
    
    
    # concensus
    CONCENSUS = 3
    
    for k, v in locals().iteritems():
        if k != 'kwargs':
            globals()[k] = v

_config()


def get_outpath(path, tpl):
    fname = os.path.basename(path)
    dirname = os.path.dirname(path)
    new_fname = tpl % INPUT_FILES_RE.match(fname).group(1)
    return os.path.join(dirname, new_fname)
    

def write_heatmap(path, tpl, heatmap):
    outpath = get_outpath(path, tpl)
    with open(outpath, 'w') as fh:
        for x in heatmap:
            print >>fh, x

def mustd_scaled(array):
    mu = np.mean(array)
    std = np.std(array)
    
    scaled = np.zeros(len(array))
    np.clip(array, 0, mu+std*2, scaled)
    scaled /= (mu+std*2)
    
    return scaled

# http://stackoverflow.com/a/3041990/399990
def query_yes_no(question, default="yes"):
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

def main():
    # path -> [hist]
    histograms = {}         # raw
    histograms_smooth = {}  # median and normalized
    histograms_binary = {}  # binary (1 = watched)
    
    # path -> [0|1]
    concensus = {}          # 1 = watched by <CONCENSUS> people
    
    load_from_cache = os.path.exists(INPUT_CACHE) and query_yes_no('CACHE detected. Load from cache?')
    
    if load_from_cache:
        print '!! Reading raw histograms from CACHE !!',
        with open(INPUT_CACHE, 'rb') as fh:
            histograms = pickle.load(fh)
    else:
        # read viewHist_*.txt
        print 'Reading raw histograms...',
        for path in glob(os.path.join(INPUT_DIR, INPUT_FILES)):
            print '\rReading raw histograms...', path,
            hists_for_cur_file = histograms[path] = []
            
            with open(path, 'r') as fh:
                for line in fh:
                    hists_for_cur_file.append( np.array(eval(line)) )
        
        with open(INPUT_CACHE, 'wb') as fh:
            pickle.dump(histograms, fh)
        
        print
    
    # compute histogram variants
    print 'Computing histograms...',
    for path in histograms:
        print '\rComputing histograms...', path,
        
        outpath = get_outpath(path, 'viewHistSmooth_%s.txt')
        outpath2 = get_outpath(path, 'viewHistSmoothNorm_%s.txt')
        
        with open(outpath, 'w') as fh:
            with open(outpath2, 'w') as fh2:
                for h in histograms[path]:
                    h2 = scipy.signal.medfilt(h, SMOOTH_WINDOW_1)
                    print >>fh, list(h2)
                    
                    s = np.max(h2)
                    h3 = h2 / (s if s else 1.0)
                    print >>fh2, list(h3)
                    histograms_smooth.setdefault(path, []).append(h3)
                    
                    h_binary = np.copy(h) # alt: h2?
                    h_binary[h_binary >= 1] = 1
                    histograms_binary.setdefault(path, []).append(h_binary)
                    
    print
    
    # consensus computation
    print 'Computing concensus...',
    for path in histograms_binary:
        print '\rComputing concensus...', path,
        W = len(max(histograms_binary[path], key=len))
        c = np.zeros(W)
        
        for h in histograms_binary[path]:
            c[:len(h)] += h
        
        c[c < CONCENSUS] = 0
        c[c >= CONCENSUS] = 1
        concensus[path] = c
        
    
    print
        
    
    
    
    
    #-----------------------------------------------------------------------
    
    heatmaps = {}
    for path in histograms_smooth:
        W = len(max(histograms_smooth[path], key=len))
        heatmap = np.zeros(W)
        
        for h in histograms_smooth[path]:
            heatmap[:len(h)] += h 
        
        write_heatmap(path, 'viewHistSmoothNormSum_%s.txt', heatmap)
        heatmaps[path] = heatmap
        
        heatmap_norm = mustd_scaled(heatmap)
        write_heatmap(path, 'viewHistSmoothNormSumNorm_%s.txt', heatmap_norm)
    
    heatmaps_nonsmoothed = {}
    heatmaps_smooth = {}
    heatmaps_scaled = {}
    heatmaps_concensus_smooth = {}
    heatmaps_concensus_scaled = {}
    
    for path, orig_heatmap in heatmaps.iteritems():
        orig_heatmap_scaled = mustd_scaled(orig_heatmap)
        heatmaps_nonsmoothed[path] = orig_heatmap_scaled
        
        
        heatmap = scipy.signal.medfilt(orig_heatmap, SMOOTH_WINDOW_2)
        heatmaps_smooth[path] = heatmap
        
        heatmap_scaled = mustd_scaled(heatmap)
        heatmaps_scaled[path] = heatmap_scaled
        
        write_heatmap(path, 'viewHistSmoothNormSumSmooth_%s.txt', heatmap)
        write_heatmap(path, 'viewHistSmoothNormSumSmoothNorm_%s.txt', heatmap_scaled)
        
        # concensus-based
        
        heatmap_c = orig_heatmap * concensus[path]
        heatmap_c = scipy.signal.medfilt(heatmap_c, SMOOTH_WINDOW_2)
        
        heatmap_c_scaled = mustd_scaled(heatmap_c)
        heatmaps_concensus_scaled[path] = heatmap_c_scaled
        
        write_heatmap(path, 'viewHistSmoothNormSumConcensus_%s.txt', heatmap_c)
        write_heatmap(path, 'viewHistSmoothNormSumConcensusSmooth_%s.txt', heatmap_c_scaled)

    print '\nDone'
        
if __name__ == '__main__':
    main()
