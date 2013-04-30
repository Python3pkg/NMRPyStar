'''
Created on Apr 29, 2013

@author: mattf
'''

class Peak(object):
    
    def __init__(self, shifts, tags, atomtypes):
        self.shifts = shifts
        self.tags = tags
        self.atomtypes = atomtypes
        
    def __repr__(self):
        return repr(self.__dict__)


class Spectrum(object):
    '''
    Hmmm, guess this isn't so much a spectrum as
    it is a bunch of peaks from the same spectrum
    type.  Seems like it's still distinct from the
    traditional meaning of 'peaklist', though, in 
    that multiple normal peaklists would all end
    up in the same 'spectrum', and the tags would
    be responsible for splitting them up into sep
    things.
    '''
    
    def __init__(self, axes, peaks):
        for (_, pk) in peaks.iteritems():
            if len(pk.shifts) != len(axes):
                raise ValueError('peak dimensions must match spectral axes')
        self.axes = axes
        self.peaks = peaks
        
    def __repr__(self):
        return repr(self.__dict__)
        
        
class Project(object):
    
    def __init__(self, name, spectra):
        '''
        Who knows what name means?  It's just there to appease the
        NMR-Star gods.
        '''
        if not isinstance(spectra, dict):
            raise ValueError('Project needs dict of spectral name - spectra')
        self.name = name
        self.spectra = spectra
        
    def __repr__(self):
        return repr(self.__dict__)
