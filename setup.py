#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

import sys

from setuptools import find_packages, setup

if sys.version_info < (3, 6):
    raise ValueError("Requires Python 3.6 or superior")

from ees_microsoft_teams import __version__  # NOQA

install_requires = [
    "msal",
    "cerberus",
    "tika",
    "ecs_logging",
    "elastic_enterprise_search",
    "pytest",
    "pyyaml",
    "beautifulsoup4",
    "pandas",
    "iteration_utilities",
    "cached_property==1.5.2; python_version < '3.8'",
    "pytest-cov",
    "flake8",
    "mock",
    "requests-mock",
    "more_itertools"
]

description = ""

with open("README.md", encoding='utf-8') as readme_file:
    description += readme_file.read() + "\n\n"


classifiers = [
    "Programming Language :: Python",
    "Development Status :: 5 - Production/Stable",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
]


setup(
    name="ees-microsoft-teams",
    version=__version__,
    url="someurl",
    packages=find_packages(),
    long_description=description.strip(),
    description=("This is a python project for an Enterprise Search Microsoft Teams Connector."),
    author="author",
    author_email="email",
    include_package_data=True,
    zip_safe=False,
    classifiers=classifiers,
    install_requires=install_requires,
    data_files=[("config", ["microsoft_teams_connector.yml"])],
    entry_points="""
      [console_scripts]
      ees_microsoft_teams = ees_microsoft_teams.cli:main
      """,
)
