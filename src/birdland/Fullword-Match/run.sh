#!/bin/bash

python setup.py build
# python setup.py install --user
# python setup.py sdist
# python setup.py bdist_rpm
# python setup.py bdist_dumb
# python setup.py install
cp build/lib.linux-*/fullword.cpython-*.so .
cp build/lib.linux-*/fullword.cpython-*.so ..

test_fullword.py
