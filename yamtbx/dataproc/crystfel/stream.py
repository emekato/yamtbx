"""
CrystFEL stream format 2.2

Reflections measured after indexing
   h    k    l          I   sigma(I)       peak background  fs/px  ss/px
 -18   38  -15     -77.63      50.81      50.00      22.12  248.3  861.5


= CrystFEL stream format 2.3 =

----- Begin chunk -----
Image filename: /lfs01/iwata/nureki/2015-Apr-KEK-A/297151-0/run297151-0.h5
Event: tag-57375862//
Image serial number: 2
indexed_by = none
photon_energy_eV = 13026.000000
beam_divergence = 4.00e-04 rad
beam_bandwidth = 5.20e-03 (fraction)
hdf5/%/photon_energy_ev = 13026.000000
average_camera_length = 0.054939 m
num_peaks = 24
num_saturated_peaks = 0
Peaks from peak search
  fs/px   ss/px (1/d)/nm^-1   Intensity  Panel
 375.36 1165.47       2.02     3875.92   q2
...
End of peak list
--- Begin crystal
Cell parameters 5.79940 11.98424 14.28581 nm, 90.39531 89.16323 90.05762 deg
astar = +0.0579467 -0.1028938 +0.1256744 nm^-1
bstar = +0.0547752 -0.0339926 -0.0529833 nm^-1
cstar = +0.0472735 +0.0488341 +0.0167826 nm^-1
lattice_type = orthorhombic
centering = P
unique_axis = ?
profile_radius = 0.00429 nm^-1
predict_refine/det_shift x = 0.007 y = 0.003 mm
predict_refine/R old = 0.00356 new = 0.00429 nm^-1
diffraction_resolution_limit = 3.69 nm^-1 or 2.71 A
num_reflections = 3941
num_saturated_reflections = 0
num_implausible_reflections = 0
Reflections measured after indexing
   h    k    l          I   sigma(I)       peak background  fs/px  ss/px panel
 -50  -43  -10      -2.50      17.37      11.00       1.50  490.2 5107.3 q5
...
End of reflections
--- End crystal
----- End chunk -----
"""

import re

from libtbx import adopt_init_args
from cctbx import miller
from cctbx import crystal
from cctbx.array_family import flex

import cPickle as pickle
import sys
#import msgpack

re_abcstar = re.compile("([-\+][0-9\.]+ )([-\+][0-9\.]+ )([-\+][0-9\.]+ )")

class Chunk:
    def __init__(self):
        filename, event, serial = None, None, None
        indexed_by = None
        photon_e, beam_div, beam_bw = None, None, None
        avg_clen = None
        n_peaks = 0
        n_sat_peaks = 0
        cell = None # 
        astar, bstar, cstar = None, None, None
        latt_type, centering = None, None
        profile_radius = None
        res_lim = None
        det_shift = 0, 0
        n_refl = 0
        n_sat_refl = 0
        n_imp_refl = 0
        indices = []
        iobs = []
        sigma = []
        peak = []
        background, fs, ss, panel = [], [], [], []
        adopt_init_args(self, locals())

        self.parsing = None
    # __init__()

    def parse_line(self, l):
        if l.startswith("End of reflections"):
            self.parsing = None
        elif self.parsing == "hkls":
            sp = l.split()
            self.indices.append(tuple(map(int, sp[:3])))
            self.iobs.append(float(sp[3]))
            self.sigma.append(float(sp[4]))
            self.peak.append(float(sp[5]))
            self.background.append(float(sp[6]))
            self.fs.append(float(sp[7]))
            self.ss.append(float(sp[8]))
            if len(sp) > 9:
                self.panel.append(sp[9])
        elif l.startswith("   h    k    l"):
            self.parsing = "hkls"
        elif l.startswith("Image filename:"):
            self.filename = l[l.index(":")+1:].strip()
        elif l.startswith("Event:"):
            self.event = l[l.index(":")+1:].strip()
        elif l.startswith("Image serial number:"):
            self.serial = l[l.index(":")+1:].strip()
        elif l.startswith("indexed_by ="):
            tmp = l[l.index("=")+1:].strip()
            if tmp != "none": self.indexed_by = tmp
        elif l.startswith("photon_energy_eV ="):
            self.photon_e = float(l[l.index("=")+1:].strip())
        elif l.startswith("beam_divergence ="):
            tmp = l[l.index("=")+1:].strip().split()
            if len(tmp) == 2: assert tmp[1] == "rad"
            self.beam_div = float(tmp[0])
        elif l.startswith("beam_bandwidth ="):
            tmp = l[l.index("=")+1:].strip().split()
            if len(tmp) == 2: assert tmp[1] == "(fraction)"
            self.beam_bw = float(tmp[0])
        elif l.startswith("average_camera_length ="):
            tmp = l[l.index("=")+1:].strip().split()
            if len(tmp) == 2: assert tmp[1] == "m"
            self.avg_clen = float(tmp[0])
        elif l.startswith("num_peaks ="):
            self.n_peaks = int(l[l.index("=")+1:].strip())
        elif l.startswith("num_saturated_peaks ="):
            self.n_sat_peaks = int(l[l.index("=")+1:].strip())
        elif l.startswith("Cell parameters"):
            sp = l.split()
            self.cell = tuple(map(lambda x:float(x)*10., sp[2:5]) + map(float, sp[6:9]))
        elif l.startswith("astar ="):
            self.astar = map(lambda x:float(x)/10., re_abcstar.search(l).groups())
        elif l.startswith("bstar ="):
            self.bstar = map(lambda x:float(x)/10., re_abcstar.search(l).groups())
        elif l.startswith("cstar ="):
            self.cstar = map(lambda x:float(x)/10., re_abcstar.search(l).groups())
        elif l.startswith("lattice_type ="):
            self.latt_type = l[l.index("=")+1:].strip()
        elif l.startswith("centering ="):
            self.centering = l[l.index("=")+1:].strip()
        elif l.startswith("profile_radius ="):
            tmp = l[l.index("=")+1:].strip().split()
            assert len(tmp) == 2
            assert tmp[-1] == "nm^-1"
            self.profile_radius = float(tmp[0])/10.
        elif l.startswith("predict_refine/det_shift "):
            tmp = l[25:].strip().split()
            assert len(tmp) == 7
            assert tmp[-1] == "mm"
            self.det_shift = float(tmp[2])/1.e3, float(tmp[5])/1.e3 # to meter
        elif l.startswith("diffraction_resolution_limit ="):
            tmp = l.split()
            assert tmp[-1] == "A"
            self.res_lim = float(tmp[-2])
        elif l.startswith("num_reflections ="):
            self.n_refl = int(l[l.index("=")+1:].strip())
        elif l.startswith("num_saturated_reflections ="):
            self.n_sat_refl = int(l[l.index("=")+1:].strip())
    # parse_line()

    def miller_set(self, space_group, anomalous_flag):
        return miller.set(crystal_symmetry=crystal.symmetry(unit_cell=self.cell,
                                                            space_group=space_group,
                                                            assert_is_compatible_unit_cell=False),
                          indices=flex.miller_index(self.indices),
                          anomalous_flag=anomalous_flag)
    # miller_set()

    def data_array(self, space_group, anomalous_flag):
        return miller.array(self.miller_set(space_group, anomalous_flag),
                            data=flex.double(self.iobs),
                            sigmas=flex.double(self.sigma))
    # data_array()

    def make_lines(self, ver):
        ret = ["----- Begin chunk -----"]
        if self.filename is not None: ret.append("Image filename: %s" % self.filename)
        if self.event is not None: ret.append("Event: %s" % self.event)
        if self.serial is not None: ret.append("Image serial number: %s" % self.serial)
        if self.indexed_by is not None: ret.append("indexed_by = %s" % self.indexed_by)
        if self.photon_e is not None: ret.append("photon_energy_eV = %f" % self.photon_e)
        if self.beam_div is not None: ret.append("beam_divergence = %.2e rad" % self.beam_div)
        if self.beam_bw is not None: ret.append("beam_bandwidth = %.2e (fraction)" % self.beam_bw)
        if self.avg_clen is not None: ret.append("average_camera_length = %f m" % self.avg_clen)
        if self.n_peaks is not None: ret.append("num_peaks = %d" % self.n_peaks)
        if self.n_sat_peaks is not None: ret.append("num_saturated_peaks = %d" % self.n_sat_peaks)

        ret.append("--- Begin crystal")
        if self.cell is not None:
            tmp = tuple(map(lambda x: x/10, self.cell[:3])) + self.cell[3:]
            ret.append("Cell parameters %7.5f %7.5f %7.5f nm, %7.5f %7.5f %7.5f deg"% tmp)

        for i, d in enumerate((self.astar, self.bstar, self.cstar)):
            if d is not None:
                tmp = ("abc"[i],) + tuple(map(lambda x: x*10., d))
                ret.append("%sstar = %+9.7f %+9.7f %+9.7f nm^-1" % tmp)

        if self.latt_type is not None: ret.append("lattice_type = %s" % self.latt_type)
        if self.centering is not None: ret.append("centering = %s" % self.centering)
        if self.profile_radius is not None: ret.append("profile_radius = %.5f nm^-1" % self.profile_radius*10.)

        if self.res_lim is not None: ret.append("diffraction_resolution_limit = %.2f nm^-1 or %.2f A" % (10./self.res_lim, self.res_lim))
        if self.n_refl is not None: ret.append("num_reflections = %d" % self.n_refl)
        if self.n_sat_refl is not None: ret.append("num_saturated_reflections = %d" % self.n_sat_refl)
        if self.n_imp_refl is not None: ret.append("num_implausible_reflections = %d" % self.n_imp_refl)
        #if self. is not None: ret.append("%" % self.)

        ret.append("Reflections measured after indexing")
        if ver == "2.3":
            ret.append("   h    k    l          I   sigma(I)       peak background  fs/px  ss/px panel")
        else:
            raise "Never reaches here"

        for i in xrange(len(self.indices)):
            if ver == "2.3":
                h, k, l = self.indices[i]
                tmp = (h, k, l, self.iobs[i], self.sigma[i], 
                       self.peak[i], self.background[i],
                       self.fs[i], self.ss[i], self.panel[i])
                ret.append("%4i %4i %4i %10.2f %10.2f %10.2f %10.2f %6.1f %6.1f %s" % tmp)
            else:
                raise "Never reaches here"

        ret.append("End of reflections")
        ret.append("--- End crystal")
        ret.append("----- End chunk -----")

        return "\n".join(ret) + "\n"
    # make_lines()

    def set_sg(self, sg):
        # sg must be space_group object
        self.latt_type = sg.crystal_system().lower()
        self.centering = sg.conventional_centring_type_symbol()
# class Chunk

class Streamfile:
    def __init__(self, strin=None):
        self.chunks = []
        if strin is not None:
            self.read_file(strin)
    # __init__()

    def read_file(self, strin):
        fin = open(strin)
        line = fin.readline()
        format_ver = re.search("CrystFEL stream format ([0-9\.]+)", line).group(1)
        print "# format version:", format_ver
        assert format_ver == "2.2" # TODO support other version

        self.chunks = []
        read_flag = False
        for l in fin:
            if "----- Begin chunk -----" in l:
                read_flag = True
                self.chunks.append(Chunk())
            elif "----- End chunk -----" in l:
                read_flag = False
                sys.stderr.write("\rprocessed: %d" % len(self.chunks))
                sys.stderr.flush()
            elif read_flag:
                self.chunks[-1].parse_line(l)
        print >>sys.stderr, " done."
    # read_file()

    def dump_pickle(self, pklout):
        pickle.dump(self.chunks, open(pklout, "wb"), -1)
    # dump_pickle()

    def load_pickle(self, pklin):
        self.chunks = pickle.load(open(pklin, "rb"))
    # load_pickle()

    """
    def dump_msgpack(self, msgout):
        open(msgout, "wb").write(msgpack.packb(self.chunks))
    # dump_msgpack()

    def load_msgpack(self, msgin):
        self.chunks = msgpack.load(open(msgin, "rb"))
    # load_msgpack()
    """
# class Streamfile

if __name__ == "__main__":
    import sys
    import time

    t = time.time()
    stream = Streamfile(sys.argv[1])
    print "process time:", time.time() - t

    """    t = time.time()
    stream.dump_msgpack("junk.msg")
    print "msgpack dump time:", time.time() - t

    t = time.time()
    stream.load_msgpack("junk.msg")
    print "msgpack load time:", time.time() - t
"""

    t = time.time()
    stream.dump_pickle("junk.pkl")
    print "pickle dump time:", time.time() - t

    t = time.time()
    stream.load_pickle("junk.pkl")
    print "pickle load time:", time.time() - t
