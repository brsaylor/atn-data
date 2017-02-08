""" Provides access to installation-specific configuration properties.

The values of the properties listed in `valid_properties` are read from
the configuration file '~/.atn-tools/atn-tools.conf' and are accessible as
attributes of this module.
"""

import sys
import os.path


def filter_path(path):
    return os.path.expanduser(path)


def filter_positive_int(number):
    try:
        number = max(1, int(number))
    except ValueError:
        number = 1
    return number


"""
Valid properties that may be included in configuration files.
Key: name of valid property
Value: dict with metadata about the property. Keys:
    - filter: a function through which to pass the property value when read
"""
valid_properties = {
    'DATA_HOME': {
        'filter': filter_path
    },
    'DEFAULT_CLASS_ATTRIBUTE': {},
    'WEKA_JAR_PATH': {
        'filter': filter_path
    },
    'WOB_SERVER_HOME': {
        'filter': filter_path
    },
    'DEFAULT_SIMULATION_THREADS': {
        'filter': filter_positive_int
    }
}

# Check that the configuration file exists
conf_file_path = os.path.expanduser('~/.atn-tools/atn-tools.conf')
if not os.path.isfile(conf_file_path):
    print("Error: configuration file {} not found. Please create it, using atn-tools.conf.example as a template."
          .format(conf_file_path), file=sys.stderr)
    sys.exit(1)

# Open and parse the configuration file
conf_file = open(conf_file_path)
for line in conf_file:
    line = line.strip()
    if line == '' or line.startswith('#'):
        continue
    split_line = [s.strip() for s in line.split('=')]
    if len(split_line) != 2 or '' in split_line:
        print("Warning: Invalid configuration line \"{}\"".format(line), file=sys.stderr)
        continue
    prop, value = split_line
    if prop not in valid_properties:
        print("Warning: {}: {} is not a valid configuration property.".format(conf_file_path, prop), file=sys.stderr)
        continue

    # Valid property: set it as a module attribute, first applying a filter (if any)
    filter_ = valid_properties[prop].get('filter')
    if filter_:
        value = filter_(value)
    globals()[prop] = value

conf_file.close()


def print_configuration():
    """ Print all configuration properties and values to stdout.

    Each line has the form PROPERTY=VALUE so that the output is valid
    shell script for setting environment variables.
    """
    for prop in sorted(valid_properties.keys()):
        print('{}={}'.format(prop, globals()[prop]))
