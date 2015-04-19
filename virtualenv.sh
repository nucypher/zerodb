#!/bin/bash

if [ ! -d ".virtual" ]
then
    virtualenv -p /usr/bin/python2.7 .virtual
    source .virtual/bin/activate
    python setup.py develop
else
    echo "All done already"
    echo "  source .virtual/bin/activate -- activate virtual environment"
    echo "  deactivate                   -- leave virtual environment"
fi
