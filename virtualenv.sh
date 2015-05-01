#!/bin/bash

if [ ! -d ".virtual" ]
then
    virtualenv -p /usr/bin/python2.7 .virtual
    source .virtual/bin/activate
    python setup.py develop
    if [ ! -e "activate" ]
    then
        ln -s .virtual/bin/activate .
    fi
else
    echo "All done already"
    echo "  source activate -- activate virtual environment"
    echo "  deactivate      -- leave virtual environment"
fi
