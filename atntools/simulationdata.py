import pandas as pd
import h5py
from cached_property import cached_property


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
            self.node_config = f.attrs['node_config'].decode('utf-8')
            self.stop_event = f.attrs['stop_event'].decode('utf-8')

    # Read biomass data once when first accessed, since it is large and
    # expensive to read
    @cached_property
    def biomass(self):
        _biomass = None
        with h5py.File(self.filename, 'r') as f:
            _biomass = pd.DataFrame(
                f['biomass'][:, :],
                columns=list(f['node_ids']))
        return _biomass
