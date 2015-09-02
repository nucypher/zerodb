#!/bin/bash

if [ "$1" == "pypy" ]
then
    if [ ! -d "download" ]
    then
        mkdir download
        pushd download
        # We can probably download some other version for non-64 bits
        # http://pypy.org/download.html#default-with-a-jit-compiler
        wget https://bitbucket.org/pypy/pypy/downloads/pypy-2.6.0-linux64.tar.bz2 -O pypy.tar.bz2
        tar -xvjpf pypy.tar.bz2
        popd
    fi
    TOX_E="pypy"
else
    TOX_E="py27"
fi

if [ ! -d ".tox/$TOX_E" ]
then
    if [ ! -e "$(which tox)" ]
    then
        echo "You need to install tox"
        echo "Please do:"
        echo "  sudo pip install tox"
    else
        tox --develop --notest -e $TOX_E
        rm activate
        ln -s ".tox/$TOX_E/bin/activate" .
    fi
else
    echo "All done already"
    echo "  source activate -- activate virtual environment"
    echo "  deactivate      -- leave virtual environment"
fi
