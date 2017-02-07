import pandas as pd
import h5py

from .nodeconfigs import parse_node_config, node_config_to_params


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
    node_config_list : list
        The node configuration parsed by nodeconfigs.parse_node_config()
    node_config_attributes : dict
        A dictionary with one key-value pair for each node-parameter pair, where
        the keys are named with the parameter name with the node ID appended
    stop_event : str
        The event (if any) that stopped the simulation. Possible values:
            NONE
            UNKNOWN_EVENT
            TOTAL_EXTINCTION
            CONSTANT_BIOMASS
            OSCILLATING_STEADY_STATE
    """

    def __init__(self, filename):

        with h5py.File(filename, 'r') as f:

            self.biomass = pd.DataFrame(
                f['biomass'][:, :],
                columns=list(f['node_ids']))

            self.node_config = f.attrs['node_config'].decode('utf-8')
            self.node_config_list = parse_node_config(self.node_config)
            self.node_config_attributes = node_config_to_params(self.node_config_list)

            self.stop_event = f.attrs['stop_event'].decode('utf-8')
