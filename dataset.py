import os
import re
from pathlib import Path
import glob
import numpy as np
import h5py

import dataset_compute

class Dataset:

    def __init__(self, ID, name):
        """
        Parameters
        ----------
        ID : str
            identifier of the simulation data -- should be equivalent to
            the directory name of the snapshot
        name : str
            label of the data set
        """

        self.ID = ID
        self.name = name
        self.grp_file = 'groups_{}.hdf5'.format(name)
        self.part_file = 'particles_{}.hdf5'.format(name)
        self.make_group_file()
        self.make_part_file()

    def make_group_file(self):
        """ Create a combined group data file and add links to all the
        actual data files """

        # Create the file object with links to all the files:
        with h5py.File(self.grp_file,'a') as grpf:
            path = self.get_data_path('group')
    
            # Iterate through group files (and dismiss irrelevant files in the
            # directory):
            for i,filename in \
            enumerate(glob.glob(os.path.join(path,'eagle_subfind_tab*'))):
                # Make an external link:
                if not 'link{}'.format(i) in grpf:
                    grpf['link{}'.format(i)] = h5py.ExternalLink(filename,'/')
        
    def make_part_file(self):
        """ Create a combined particle data file and add links to all 
        the actual data files """

        # Create the file object with links to all the files:
        with h5py.File(self.part_file,'a') as partf:
            path = self.get_data_path('part')
    
            # Iterate through data files (and dismiss irrelevant files in the
            # directory):
            for i,filename in \
            enumerate(glob.glob(os.path.join(path,'snap_*.hdf5'))):
                # Make an external link:
                if not 'link{}'.format(i) in partf:
                    partf['link{}'.format(i)] = \
                            h5py.ExternalLink(filename,'/')

    def get_data_path(self, datatype):
        """ Constructs the path to data directory. 
        
        Paramaters
        ----------
        datatype : str
            recognized values are: part and group

        Returns
        -------
        path : str
            path to data directory
        """

        home = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(home,"snapshots",self.ID)
        direc = ""
        if datatype == "part":
            direc = "snapshot_"
        elif datatype == "group":
            direc += "groups_"
        else:
            return None

        fields = self.ID.split("_")
        direc += fields[-2] + "_" + fields[-1]

        return os.path.join(path,direc)

    def get_subhalos(self, attr, divided=True):
        """ Retrieves the given attribute values for subhaloes in the
        dataset.
        
        Parameters
        ----------
        attr : str
            attribute to be retrieved
        divided : bool, optional
            if True (default), output is divided into satellites and 
            isolated galaxies

        Returns
        -------
        data : tuple of HDF5 datasets
            tuple of one or two entries, depending on the value of the
            argument "divided". If divided == True, return satellite data
            in the first entry and isolated galaxies data in the second.
        """

        data = self.read_subhalo_attr(attr)

        if divided:
            SGNs = self.read_subhalo_attr('SubGroupNumber')

            # Divide into satellites and isolated galaxies:
            dataSat = data[SGNs != 0]
            dataIsol = data[SGNs == 0]

            return (dataSat,dataIsol)
        else:
            return (data,)

    def read_subhalo_attr(self, attr):
        """ Reads the data files for the attribute "attr" of each subhalo.
        
        Parameters
        ----------
        attr : str
            attribute to be retrieved

        Returns
        -------
        out : HDF5 dataset
            dataset of the values of attribute "attr" for each subhalo
        """

        # Output array.
        out = []

        is_extension = False
        with h5py.File(self.grp_file,'r') as grpf:
            if attr not in grpf['link1/Subhalo']:
                is_extension = True

        if is_extension:

           out = self.read_subhalo_extended_attr(attr)

        else:
    
            with h5py.File(self.grp_file,'r') as grpf:

                # Loop over each file and extract the data.
                links = (f for (name,f) in grpf.items() \
                        if ('link' in name))
                for f in links:
                    tmp = f['Subhalo/{}'.format(attr)][...]
                    out.append(tmp)
            
                # Get conversion factors.
                cgs     = grpf['link1/Subhalo/{}'.format(attr)].attrs\
                        .get('CGSConversionFactor')
                aexp    = grpf['link1/Subhalo/{}'.format(attr)].attrs\
                        .get('aexp-scale-exponent')
                hexp    = grpf['link1/Subhalo/{}'.format(attr)].attrs\
                        .get('h-scale-exponent')
            
                # Get expansion factor and Hubble parameter from the 
                # header.
                a       = grpf['link1/Header'].attrs.get('Time')
                h       = grpf['link1/Header'].attrs.get('HubbleParam')
        
                # Combine to a single array.
                if len(out[0].shape) > 1:
                    out = np.vstack(out)
                else:
                    out = np.concatenate(out)
        
                # Convert to physical and return in cgs units.
                if out.dtype != np.int32 and out.dtype != np.int64:
                    out = np.multiply(out, cgs * a**aexp * h**hexp, dtype='f8')

        return out

    def read_subhalo_extended_attr(self,attr):
        """ Retrieves dataset corresponding to attr from file if it is
        already calculated. If not, calculates it and then returns it.

        Paramaters
        ----------
        datatype : attr
            (extended) attribute to be retrieved

        Returns
        -------
        out : HDF5 dataset
            dataset of the values of attribute "attr" for each subhalo
        """

        out = []

        # Check if velocities at 1kpc are already stored in grpf:
        attr_in_grpf = False
        with h5py.File(self.grp_file,'r') as grpf:
            if 'extended/{}'.format(attr) in grpf:
                out = grpf['extended/{}'.format(attr)][...]
                attr_in_grpf = True

        if not attr_in_grpf:

            out = dataset_compute.calculate_attr(self,attr)

            # Create dataset in grpf:
            with h5py.File(self.grp_file,'r+') as grpf:
                if '/extended' not in grpf:
                    ext = grpf.create_group('extended')
                    attr_dataset = \
                            ext.create_dataset(attr, data=out)
                else:
                    attr_dataset = grpf.create_dataset(\
                            '/extended/{}'.format(attr), data=out)

        return out

    def get_particles(self, attr, part_type=[0,1,4,5]):
        """ Reads the data files for the attribute "attr" of each particle.
        
        Parameters
        ----------
        attr : str
            attribute to be retrieved
        part_type : list of int, optional
            types of particles, whose attribute values are retrieved (the
            default is all of them)

        Returns
        -------
        out : HDF5 dataset
            dataset of the values of attribute "attr" for each particle 
        """

        # Output array.
        out = []

        # Get particle file:
        with h5py.File(self.part_file,'r') as partf:
    
            # Loop over each file and extract the data.
            for f in partf.values():
                
                # Loop over particle types:
                for pt in part_type:
                    if attr in f['PartType{}'.format(pt)].keys():
                        tmp = f['PartType{}/{}'.format(pt,attr)][...]
                        out.append(tmp)

        # Combine to a single array.
        if len(out[0].shape) > 1:
            out = np.vstack(out)
        else:
            out = np.concatenate(out)
            
        out = self.convert_to_cgs_part(out,attr)
            
        return out

    def convert_to_cgs_part(self,data,attr):

        converted = data

        with h5py.File(self.part_file,'r') as partf:

            # Get conversion factors (same for all types):
            cgs     = partf['link1/PartType0/{}'.format(attr)]\
                    .attrs.get('CGSConversionFactor')
            aexp    = partf['link1/PartType0/{}'.format(attr)]\
                    .attrs.get('aexp-scale-exponent')
            hexp    = partf['link1/PartType0/{}'.format(attr)]\
                    .attrs.get('h-scale-exponent')
            
            # Get expansion factor and Hubble parameter from the header:
            a       = partf['link1/Header'].attrs.get('Time')
            h       = partf['link1/Header'].attrs.get('HubbleParam')
        
            # Convert to physical and return in cgs units.
            if data.dtype != np.int32 and data.dtype != np.int64:
                converted = np.multiply(data, cgs * a**aexp * h**hexp, dtype='f8')

        return converted

    def get_particle_masses(self,part_type=[0,1,4,5]):
        """ Reads particle masses, ignoring types 2,3!!
        
        Returns
        -------
        mass : HDF5 dataset
            masses of each particle
        """

        mass = []

        for pt in part_type:
            if pt in [1,2,3]:
                # Get dm particle masses:
                with h5py.File(self.part_file,'r') as partf:
                    dm_mass = partf['link1/Header']\
                            .attrs.get('MassTable')[1]
                    dm_n = partf['link1/Header']\
                            .attrs.get('NumPart_Total')[1]
                    mass = np.concatenate((mass,\
                                np.ones(dm_n, dtype='f8')*dm_mass))
            else:
                mass = np.concatenate((mass,\
                        self.get_particles('Masses',part_type=[4])))

        mass = self.convert_to_cgs_part(mass,'Masses')

        return mass
