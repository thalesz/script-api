#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, 'script/src')
os.chdir('script/src')

from downloader import Downloader

d = Downloader()
print(f'AC existe no banco: {d._state_exists_in_db("AC")}')
print(f'AL existe no banco: {d._state_exists_in_db("AL")}')
print(f'SP existe no banco: {d._state_exists_in_db("SP")}')
