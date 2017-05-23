# atn-tools

Tools for running and analyzing ATN simulation data
from [ATN Simulator](https://github.com/brsaylor/atn-simulator) or
[World of Balance](https://github.com/worldofbalance/wob-server).

I wrote this code for my master's thesis work,
and I make no guarantees about its general usefulness.

## Installation

1. Clone the atn-tools git repository.
2. Install [Miniconda](https://conda.io/miniconda.html).
3. Set up the atn-tools Conda environment:
    ```
    cd atn-tools
    conda env create -f environment.yml
    ```
4. Activate the environment:
    ```
    source activate atn-tools
    ```
5. Install the atn-tools package:
    ```
    python setup.py install
    ```
6. Copy `atn-tools.conf.example` to `$HOME/atn-tools/atn-tools.conf`
   and edit as desired.

After making any changes to the code or any updates,
repeat step 5 to update the installed version.

## Commands

atn-tools provides a number commands implemented as Python scripts.
They are installed into the `bin` directory of the Conda environment.
Each script is prefixed with `atn-`.
A good way to see the list of commands is by using tab-completion,
typing `atn-`(tab) in a shell.
Each command is somewhat documented -- provide the `-h` argument to see the help.
For example:

```
(atn-tools) atn-tools $ atn-generate-food-web.py -h
usage: atn-generate-food-web.py [-h] [--parent-dir PARENT_DIR]
                                [--figsize FIGSIZE FIGSIZE] [--dpi DPI]
                                {generate,regenerate,from-node-ids} ...

Generates a plot and JSON file describing a food web. Files are stored in a
directory named based on the species in the food web. If --parent-dir is not
specified, the parent directory is determined automatically based on
DATA_HOME.

positional arguments:
  {generate,regenerate,from-node-ids}
    generate            Generate a new food web and save plot and JSON
    regenerate          Regenerate files in existing food web directory
    from-node-ids       Generate plot and JSON from given node IDs

optional arguments:
  -h, --help            show this help message and exit
  --parent-dir PARENT_DIR
                        Parent directory to use instead of automatically-
                        determined directory under DATA_HOME
  --figsize FIGSIZE FIGSIZE
                        Width and height of the food web plot, in inches
                        (combine with --dpi)
  --dpi DPI             Image resolution (dots per inch)
```

## Author

Ben Saylor
