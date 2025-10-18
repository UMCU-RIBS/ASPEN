from setuptools import setup, find_packages

setup(
    name='aspen',
    version='1.0.3',
    description='Database GUI',
    url='https://github.com/umcu-ribs/aspen',
    author="Gio Piantoni, Erdi Erdal",
    author_email='e.erdal@umcutrecht.nl',
    license='GPLv3',
    classifiers=[
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='database qt',
    packages=find_packages(),
    install_requires=[
        'numpy',
        'pandas',
        'PyQt5',
        'ldap3'
    ],
    package_data={
        'aspen': [
            'database/tables.json',
            ],
        },
    entry_points={
        'console_scripts': [
            'aspen=aspen.gui.main:main',
        ],
    },
)
