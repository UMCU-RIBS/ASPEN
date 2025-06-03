#!/bin/bash


apt install python3-pyqt5  python3-pyqt5.qtsql  python3-numpy  python3-pandas python3-ldap3


# Pull the code
mkdir -p /usr/local/aspen
cd /usr/local/aspen
if [ -d ASPEN ]; then
	cd ASPEN
	git pull
else
	git clone https://github.com/UMCU-RIBS/ASPEN.git
	cd ASPEN
fi
git checkout master


cd /usr/local/bin/
ln -s /usr/local/aspen/ASPEN/StartAspen.py aspen
