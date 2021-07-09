# `aiida-ase`
AiiDA plugin for ASE

# Installation

1. From PyPI 

```
pip install aiida-ase
```

2. From this repository (useful for development):

```
git clone https://github.com/aiidateam/aiida-ase 
pip install aiida-ase
```

# Usage

The main goal of this plugin is to be a wrap around for ASE. 

To make it easy to setup the calculation generate a `builder` as follows

```
## Use the CalculationFactory for ASE
ASECalculation = CalculationFactory('ase.ase')
## get the builder
builder = ASECalculation.get_builder()
```

The main parameters for the builder that need to be specified are:

1. Code 

```
code = load_code('your-code-here@your-computer-here')
builder.code = code
```
NOTE: If using GPAW, there are two possibilities to set up the calculator
	a. Specify the Python executable with specific module loaded for GPAW
	b. Specify directly the GPAW executable. In this case a CMDLINE parameter will be needed (see below).

2. Structure
```
builder.structure = structure 
```

3. _k_-points data
```
kpoints = KpointsData()
kpoints.set_kpoints_mesh([2,2,2]) ## choose the right mesh here
builder.kpoints = kpoints 
``` 

4. Parameters

An example parameter set for GPAW is shown here in parts. See the `examples` folder for specific examples for other functionality (will be constantly updated).

Define a calculator for a `PW` calculation with GPAW. Here the `name` of the calculator is set to GPAW, `args` is the equivalent of arguments passed into the calculator used in ASE. Note that the `@function` functionality enables passing arguments to a function inside the calculators. In this example the equivalent ASE command is `PW(300)`. Other arguments such as `convergence` and `occupations` can be added. 
```
calculator = {\
		"name":"gpaw",
		"args":{\
		"mode":{"@function":"PW",
			"args":{"ecut":300}},
		"convergence":{'energy':1e-9},
		"occupations":{'name':'fermi-dirac', 'width':0.05}
		}
```

Add here tags that will be written as `atoms.get_xyz()`, so for example the first item will be `atoms.get_temperature()`. 
```
atoms_getters  = ["temperature",
		 ["forces",{'apply_constraint':True}],
		 ["masses",{}],
		 ]
```

Same tags but for `calc.get_xyz()`.
```
calculator_getters =   [["potential_energy",{}],
			"spin_polarized",
			["stress",['atoms']],
			],
```

Some addition utility functions are:

1. `pre_lines`: list of lines to added to the start of the python file
2. `post_lines`: list of lines to added to the end of the python file
3. `extra_imports`: list of extra imports as separated strings, for example `["numpy", "array"]` will lead to `from numpy import array`

# Note about choosing a code

1. If using GPAW it is possible to run parallel calculations using `/path/to/execut/gpaw python run_gpaw.py`. Set up the code through AiiDA by adding in the `gpaw` executable. The add the `python` tag using the command line option
```
settings = {"CMDLINE":"python"}
builder.settings = orm.Dict(dict=settings)
```

2. If the code you are interested in is present in this plugin registry it might make more sense to use that https://aiidateam.github.io/aiida-registry/


# Documentation
The documentation for this package can be found on Read the Docs at
http://aiida-ase.readthedocs.io/en/latest/
