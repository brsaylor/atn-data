import pandas as pd
import h5py
from cached_property import cached_property


# ATNEngine extinction threshold is 1e-15.
# It scales biomass by 1000 for output, so our extinction threshold is:
EXTINCT = 1e-12


class SimulationData(object):
    """ ATN simulation data from an HDF5 file produced by WoB Server.

    Parameters
    ----------
    filename : str
        The name of the HDF5 file

    Attributes
    ----------
    biomass : pandas.DataFrame
        Biomass by species over time. The columns are node IDs and the index is
        the timeteps of the simulation.
    node_config : str
        The node configuration string
    stop_event : str
        The event (if any) that stopped the simulation. Possible values:
            NONE
            UNKNOWN_EVENT
            TOTAL_EXTINCTION
            CONSTANT_BIOMASS_PRODUCERS_ONLY
            CONSTANT_BIOMASS_WITH_CONSUMERS
            OSCILLATING_STEADY_STATE
    """

    def __init__(self, filename):

        self.filename = filename

        # Read all data other than biomass array
        with h5py.File(filename, 'r') as f:
            if 'node_config' in f.attrs:
                self.format_version = 1
                self.node_config = f.attrs['node_config'].decode('utf-8')
                try:
                    self.stop_event = f.attrs['stop_event'].decode('utf-8')
                except KeyError:
                    self.stop_event = None
            else:
                self.format_version = 2

            self.node_ids = f['node_ids'][:]

            if self.format_version == 2:
                self.node_config = f['node_config'][()].decode('utf-8')
                self.stop_event = f['stop_event'][()].decode('utf-8')
                self.extinction_timesteps = pd.Series(
                    f['extinction_timesteps'][:], index=self.node_ids)
                self.extinction_count = self.extinction_timesteps[self.extinction_timesteps > -1].count()
                self.final_biomass = pd.Series(
                    f['final_biomass'][:], index=self.node_ids)
                self.timesteps_simulated = f['timesteps_simulated'][()]

    # Read biomass data once when first accessed, since it is large and
    # expensive to read
    @cached_property
    def biomass(self):
        _biomass = None
        with h5py.File(self.filename, 'r') as f:
            if 'biomass' in f:
                _biomass = pd.DataFrame(
                    f['biomass'][:, :],
                    columns=self.node_ids)

                if self.format_version == 2:
                    _biomass *= 1000

        return _biomass
