import os
import sys
import csv
import json
from glob import iglob as glob
from itertools import izip, groupby
import re

import cPickle as pickle

def _config(**kwargs):
    INPUT_DIR = kwargs.get('INPUT_DIR') or 'run1'
    INPUT_FILES = 'viewHist_*.txt'
    
    INPUT_FILES_RE = re.compile(INPUT_FILES.replace('*','(.*)'))
    INPUT_CACHE = os.path.join(INPUT_DIR, 'viewHist.pickle')
    
    OUTPUT_DIR = INPUT_DIR
    OUTPUT_TPL = 'viewHistStats_%s.txt'
    
    ALWAYS_READ_FROM_CACHE = kwargs.get('ALWAYS_READ_FROM_CACHE') or False
    
    for k, v in locals().iteritems():
        if k != 'kwargs':
            globals()[k] = v

_config()

def get_outpath(path, tpl):
    fname = os.path.basename(path)
    dirname = os.path.dirname(path)
    new_fname = tpl % INPUT_FILES_RE.match(fname).group(1)
    return os.path.join(dirname, new_fname)
    

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


def splitBy(iterable, f):
    return [list(g) for k, g in groupby(iterable, f) if not k]


def main():
    # path -> [hist]
    histograms = {}         # raw
    
    load_from_cache = os.path.exists(INPUT_CACHE) and (ALWAYS_READ_FROM_CACHE or query_yes_no('CACHE detected. Load from cache?'))
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
    
    # compute histogram stats
    print 'Computing stats...',
    for path in histograms:
        print '\rComputing stats...', path,
        
        outpath = get_outpath(path, OUTPUT_TPL)
        
        with open(outpath, 'w') as fh:
            for h in histograms[path]:
                sessionLength = sum(h) # scipy.signal.medfilt ?
                segments = splitBy(h, lambda x: x == 0)
                
                print >>fh, '\t'.join(map(str, [sessionLength, len(segments)]))
    
    
    print '\nDone'
        
if __name__ == '__main__':
    main()
