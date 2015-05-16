#!/bin/bash

if [ ! -d ".tox" ]
then
    if [ ! -e "$(which tox)" ]
    then
        echo "You need to install tox"
        echo "Please do:"
        echo "  sudo pip install tox"
    else
        tox --develop --notest
        if [ ! -e "activate" ]
        then
            ln -s .tox/py27/bin/activate .
        fi
    fi
else
    echo "All done already"
    echo "  source activate -- activate virtual environment"
    echo "  deactivate      -- leave virtual environment"
fi
