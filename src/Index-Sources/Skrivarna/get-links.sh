#!/bin/bash

cd index-files
for link in $(../get-links.py)
do
wget $link
done
