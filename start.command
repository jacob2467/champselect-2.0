#!/bin/bash
clear
cd "$(dirname "$0")"

python3 update.py
open frontend/page.html
python3 webapp.py

read -p ""