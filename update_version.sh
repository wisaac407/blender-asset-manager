#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 new-version" >&2
    exit 1
fi

sed "s/version='[^']*'/version='$1'/" -i setup.py
sed "s/__version__\s*=\s*['\"][^']*['\"]/__version__ = '$1'/" -i bam/__init__.py

SHORTVER=$(echo -n $1 | sed 's/\.[^.]*$//')
sed "s/version = '[^']*'/version = '$SHORTVER'/" -i doc/source/conf.py
sed "s/release = '[^']*'/release = '$1'/" -i doc/source/conf.py

MODIFIED_FILES="setup.py bam/__init__.py doc/source/conf.py"

git diff $MODIFIED_FILES
echo
echo "Don't forget to commit and tag:"
echo git commit -m \'Bumped version to $1\' $MODIFIED_FILES
echo git tag -a v$1 -m \'Tagged version $1\'
