#!/usr/bin/env bash

PY_VERSION=`python --version | cut -f 2 -d ' '| awk -F. '{print "python"$1"."$2}'`
PY_BUILD=${PWD}/build/

if [ -d $PY_BUILD ] || [ -d $PWD/build ]; then rm -rf build; fi
mkdir -p $PY_BUILD
cp $1 $PY_BUILD/
cd build && zip -r9 ../function.zip .; cd -
rm -rf $PY_BUILD && rm -rf $PWD/build
