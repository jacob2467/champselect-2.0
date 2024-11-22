#!/bin/bash
cd "$(dirname "$0")"

# Find all Python3 executables and sort by version number
PYTHON_CMD=$( \
  (ls /usr/local/bin/python3* /opt/homebrew/bin/python3* /Library/Frameworks/Python.framework/Versions/3.*/bin/python3 /usr/bin/python3* 2>/dev/null) | \
  grep -v "config\|m\|idle\|.pyo\|.pyc\|.pm\|debug" | \
  sort -V | \
  tail -n 1 \
)

if [ -x "$PYTHON_CMD" ]; then
    echo "Using Python at: $PYTHON_CMD"
    "$PYTHON_CMD" main.py
else
    echo "No Python 3 installation found"
fi

read -p "Press [Enter] key to continue..."