import wget
import os
import re

if not os.path.exists('tablebase'):
    os.makedirs('tablebase')

if not os.path.exists('tablebase/3-4-5'):
    os.makedirs('tablebase/3-4-5')

if not os.path.exists('tablebase/3-4-5/3-4-5.txt'):
    wget.download(
        'https://tablebase.lichess.ovh/tables/standard/3-4-5/3-4-5.txt',
        'tablebase/3-4-5/3-4-5.txt'
    )

with open('tablebase/3-4-5/3-4-5.txt', 'r') as file:
    to_download_list = map(
        lambda x: x[11:-11],
        re.findall('########## .* ##########', file.read())
    )

for to_download_file in to_download_list:
    if len(to_download_file) > 6: continue
    if os.path.exists('tablebase/3-4-5/{}.rtbz'.format(to_download_file)): continue
    wget.download(
        'https://tablebase.lichess.ovh/tables/standard/3-4-5/{}.rtbz'.format(to_download_file),
        'tablebase/3-4-5/{}.rtbz'.format(to_download_file)
    )
    if os.path.exists('tablebase/3-4-5/{}.rtbw'.format(to_download_file)): continue
    wget.download(
        'https://tablebase.lichess.ovh/tables/standard/3-4-5/{}.rtbw'.format(to_download_file),
        'tablebase/3-4-5/{}.rtbz'.format(to_download_file)
    )
    