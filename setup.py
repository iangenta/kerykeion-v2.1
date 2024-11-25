from setuptools import setup, find_packages
from pathlib import Path

def find_package_data(directory):
    package_data = []
    for path in Path(directory).rglob("*"):
        if path.is_file():
            package_data.append(str(path.relative_to(directory)))
    return package_data

setup(
    name='kerykeion-mod',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    package_data={'kerykeion': find_package_data('kerykeion')},
    install_requires=[
        'contourpy==1.2.1',
        'cycler==0.12.1',
        'fonttools==4.51.0',
        'kiwisolver==1.4.5',
        'matplotlib==3.8.4',
        'numpy==1.26.4',
        'packaging==24.0',
        'pillow==10.3.0',
        'pyparsing==3.1.2',
        'python-dateutil==2.9.0.post0',
        'pytz==2022.7',
        'six==1.16.0',
        'pyswisseph==2.10.3.1',
        'requests==2.28.1',
        'requests-cache==0.9.7',
        'pydantic==2.5',
        'terminaltables==3.1.10',
        'pytest == 7.2.0',
        'mypy == 0.991',
        'black == 22.12.0',
        'pdoc == 12.3.0',
        'types-requests == 2.28.11.7',
        'types-pytz == 2022.7.0.0',
        'poethepoet == 0.19.0',
        'flask==3.0.3'
    ],
    dependency_links=[
        'file:kerykeion'
    ]
)
