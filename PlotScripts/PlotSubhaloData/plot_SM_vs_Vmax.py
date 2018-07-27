import os, sys
import numpy as np
import h5py
import time
import astropy.units as u
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReadData"))
import read_data
from calc_median import calc_median_trend

class SM_vs_Vmax_data:

    def __init__(self, dataset):

        self.dataset = dataset
        self.reader = read_data.read_data(dataset=self.dataset.dir, nfiles_part=self.dataset.nfiles_part, nfiles_group=self.dataset.nfiles_group)

        self.read_galaxies()

    def read_galaxies(self):

        # Read subhalo data:
        vmax = self.reader.read_subhaloData('Vmax') / 100000   # cm/s to km/s
        SM = self.reader.read_subhaloData('Stars/Mass') * u.g.to(u.Msun)
        SGNs = self.reader.read_subhaloData('SubGroupNumber')

        # Divide into satellites and isolated galaxies:
        maskSat = np.logical_and.reduce((vmax > 0, SM > 0, SGNs != 0))
        maskIsol = np.logical_and.reduce((vmax > 0, SM > 0, SGNs == 0))

        self.vmaxSat = vmax[maskSat]
        self.SMSat = SM[maskSat]
        self.vmaxIsol = vmax[maskIsol]
        self.SMIsol = SM[maskIsol]


class plot_SM_vs_Vmax:

    def __init__(self):
        """ Create new figure with stellar mass on y-axis and Vmax on x-axis. """
    
        self.fig, self.axes = plt.subplots()
        self.set_axes()
        self.set_labels()
        
    def set_axes(self):
        """ Set shapes for axes. """

        self.axes.set_xscale('log')
        self.axes.set_yscale('log')
        self.axes.set_xlim(10, 100)
        self.axes.set_ylim(10**6, 10**10)
        
    def set_labels(self):
        """ Set labels. """

        self.axes.set_xlabel('$v_{max}[\mathrm{km s^{-1}}]$')
        self.axes.set_ylabel('$M_*[\mathrm{M_\odot}]$')
        self.axes.set_title('Stellar mass of luminous subhaloes')

    def add_data(self, data, satellites, col):
        """ Plot data (object of type SM_vs_Vmax_data) into an existing figure. Satellites is a boolean variable with value 1, if satellites are to be plotted, and 0, if instead isolated galaxies are to be plotted. """

        x = 0; y = 0
        if satellites:
            x = data.vmaxSat; y = data.SMSat
        else:
            x = data.vmaxIsol; y = data.SMIsol

        self.axes.scatter(x, y, s=3, c=col, edgecolor='none', label=data.dataset.name)
        median = calc_median_trend(x, y, points_per_bar=7)
        self.axes.plot(median[0], median[1], c=col, linestyle='--')
        #self.axes.scatter(median[0], median[1], s=5)
    
    def save_figure(self):
        """ Save figure. """
        
        self.axes.legend(loc=0)
        plt.show()
        self.fig.savefig('../Figures/Comparisons_082_z001p941/SM_vs_Vmax.png')
        plt.close()

#
#plot = plot_SM_vs_Vmax()
#LCDM = SM_vs_Vmax_data(dataset='V1_MR_fix_082_z001p941', nfiles_part=16, nfiles_group=192)
#curvaton = SM_vs_Vmax_data(dataset='V1_MR_mock_1_fix_082_z001p941', nfiles_part=1, nfiles_group=64)
#
#plot.add_data(LCDM, 1, 'red')
#plot.add_data(curvaton, 1, 'blue')
#plot.save_figure() 
    
