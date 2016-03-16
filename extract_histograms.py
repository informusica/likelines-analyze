import os
import sys
import csv
import json
from glob import iglob as glob
from itertools import izip

import numpy as np

import gc

from pprint import pprint

csv.field_size_limit(sys.maxsize)

def csv_with_header(filename):
    f = open(filename,'rb')
    reader = csv.reader(f)
    header = reader.next()
    for row in reader:
        d = dict(zip(header, row))
        if d: # skip empty lines
            yield d
    f.close()


def _config(**kwargs):
    INPUT_DIR = kwargs.get('INPUT_DIR') or 'run1'
    INPUT_FILES = kwargs.get('INPUT_FILES') or 'select_Batch_*_batch_results.csv'
    
    #INPUT_DIR = 'heatpilot1'
    #INPUT_FILES = 'heat_Batch_*_batch_results.csv'
    
    
    OUTPUT_DIR = INPUT_DIR
    OUTPUT_FILE_TPL = 'viewHist_%s.txt'
    
    LIKELINES_FIELD = 'likelines'
    
    for k, v in locals().iteritems():
        if k != 'kwargs':
            globals()[k] = v

_config()


def parse_events(events):
    # Return None, None, None on error
    try:
        debugflag = False
        
        viewTime = 0
        curSegment = None
        segments = []
        
        for event in json.loads('[%s]' % events):
            ts, evtType, tc, last_tc = event
            
            if curSegment is not None:
                curSegment[1] = last_tc
            
            if evtType in ['PLAYING', 'PAUSED', 'ENDED']:
                if curSegment is not None and curSegment[1] is not None:
                    segmentLength = (curSegment[1] - curSegment[0])
                    if segmentLength > 0:
                        viewTime += segmentLength
                        segments.append(curSegment)
                    else:
                        debugflag = True
                        #print >>sys.stderr, id(events), curSegment
                        
                if evtType == 'PLAYING':
                    curSegment = [tc, None]
                else:
                    curSegment = None
        
        if curSegment is not None and curSegment[1] is not None:
            segmentLength = (curSegment[1] - curSegment[0])
            if segmentLength > 0:
                viewTime += segmentLength
                segments.append(curSegment)
            else:
                debugflag = True
        
        return viewTime, segments, debugflag
    
    except ValueError:
        return None, None, None
    except:
        raise

def edit_assignment(assignment):
    viewTime, segments, debugflag = parse_events(assignment['Answer.%s' % LIKELINES_FIELD])
    return segments



def segments2bins(segments):
    N = max(int(end) for start, end in segments)
    bins = np.zeros(N+1)
    
    last_b = None
    
    for start, end in segments:
        a, b = int(start), int(end)
        
        if a == last_b:
            # prevent "weird" peaks" of near-adjacent segments
            a += 1
        
        for i in xrange(a, b+1):
            bins[i] += 1
        
        last_b = b
    
    return bins


def seeksFromPlayback(segments, threshold=0):
    seeks = []
    for (_, t1), (t2, _) in izip(segments, segments[1:]):
        diff = abs(t2 - t1)
        if diff >= threshold:
            seeks.append( (t1, t2) )
    
    return seeks



def main():
    histograms = {}
    
    for path in glob(os.path.join(INPUT_DIR, INPUT_FILES)):
        for assignment in csv_with_header(path):
            aid = assignment['AssignmentId']
            vid = assignment['Input.VIDEO']
            
            segments = edit_assignment(assignment)
            if segments:
                bins = segments2bins(segments)
                histograms.setdefault(vid, []).append(bins)
    
    for vid in histograms:
        outpath = os.path.join(OUTPUT_DIR, OUTPUT_FILE_TPL % vid)
        
        with open(outpath, 'w') as fh:
            for h in histograms[vid]:
                print >>fh, list(h)
    


if __name__ == '__main__':
    main()
