#!/usr/bin/env bash
# Installs this current plugin for Rhythmbox
# Taken from original file that is Copyright (C) 2016 Donagh Horgan <donagh.horgan@gmail.com>
# from https://raw.githubusercontent.com/donaghhorgan/rhythmbox-plugins-open-containing-folder/master/install.sh
# and generalized for easy reuse in multiple plugins.

name=$(basename $(pwd))
path=~/.local/share/rhythmbox/plugins/$name
mandatory_files=( $name.plugin $name.py )
optional_files=( LICENSE README.md )

if [ -d "$path" ]; then
  rm -rf $path
fi

mkdir -p $path

for file in "${mandatory_files[@]}"
do
  if [ ! -f $file ]
  then
    echo "ERROR: $file is a required plugin file"
    exit 1
  fi
  echo Copying $file to $path
  cp -p $file $path
done

for file in "${optional_files[@]}"
do
  if [ ! -f $file ]
  then
    echo "Skipping $file optional file"
  else
    echo Copying $file to $path
    cp -p $file $path
  fi
done
