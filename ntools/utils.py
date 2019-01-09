import os
import re

import requests
from tqdm import tqdm


def save_file_at_new_dir(new_dir_path,
                         new_filename,
                         new_file_content,
                         mode='w'):
    os.makedirs(new_dir_path, exist_ok=True)
    with open(os.path.join(new_dir_path, new_filename), mode) as f:
        f.write(new_file_content)


def HTTPdownload(file_url, dir_path, file_name, Cookies, Referer):
    headers = {'Referer': Referer}
    file_size = int(
        requests.head(file_url, cookies=Cookies,
                      headers=headers).headers["content-length"])
    res = requests.get(file_url, cookies=Cookies, headers=headers, stream=True)
    pbar = tqdm(total=file_size, unit="B", unit_scale=True)
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, file_name), 'wb') as file:
        for chunk in res.iter_content(chunk_size=1024):
            file.write(chunk)
            pbar.update(len(chunk))
        pbar.close()


def str2dic(x):
    x = x.split('&')
    data = {}
    for i in x:
        temp = re.search('([^=]+)=(.+)$', i)
        data[temp.groups()[0]] = temp.groups()[1]
    return data
