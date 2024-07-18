from setuptools import setup, find_packages

setup(
    name='xelo2',
    version='0.2',
    description='Database GUI',
    url='https://github.com/umcu-ribs/xelo2',
    author="Gio Piantoni",
    author_email='xelo2@gpiantoni.com',
    license='GPLv3',
    classifiers=[
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='database qt',
    packages=find_packages(),
    install_requires=[
        # 'numpy',
        # 'pandas',
        # 'nibabel',
        # 'wonambi',
        # 'bidso',
        # 'PyQt5'
    ],
    package_data={
        'xelo2': [
            'database/tables.json',
            ],
        },
    entry_points={
        'console_scripts': [
            'xelo2=xelo2.gui.main:main',
        ],
    },
)
