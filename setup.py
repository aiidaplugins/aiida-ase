# -*- coding: utf-8 -*-
"""Define the setup for the `aiida-ase` plugin."""
try:
    import fastentrypoints  # pylint: disable=unused-import
except ImportError:
    # This should only occur when building the package, i.e. for `python setup.py sdist/bdist_wheel`
    pass


def setup_package():
    """Install the `aiida-ase` package."""
    import json
    from setuptools import setup, find_packages

    filename_setup_json = 'setup.json'
    filename_description = 'README.md'

    with open(filename_setup_json, 'r', encoding='utf-8', errors='ignore') as handle:
        setup_json = json.load(handle)

    with open(filename_description, 'r', encoding='utf-8', errors='ignore') as handle:
        description = handle.read()

    setup(
        include_package_data=True,
        packages=find_packages(),
        long_description=description,
        long_description_content_type='text/markdown',
        **setup_json
    )


if __name__ == '__main__':
    setup_package()
