#!/usr/bin/env bash

PY_VERSION=`python --version | cut -f 2 -d ' '| awk -F. '{print "python"$1"."$2}'`
PY_BUILD=${PWD}/build/python/lib/${PY_VERSION}/site-packages

if [ -d $PY_BUILD ] || [ -d $PWD/build ]; then rm -rf build; fi
mkdir -p $PY_BUILD
pip install -r $PWD/requirements.txt --no-deps -t $PY_BUILD
cd build && zip -r9 ../layer.zip *; cd -
rm -rf $PY_BUILD && rm -rf $PWD/build

