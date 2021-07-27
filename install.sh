#!/bin/sh
set -e
# hostname=$(cat ../.hostname)
# password=$(cat ../.password)
# mpfshell -o ws:$hostname,$password -n -c "putc $2"
port="/dev/ttyUSB0"
mpfshell -o ser:$port -n -c "putc $2"
mkdir -p "$1"
cp "$2" "$1"
touch "updated"
