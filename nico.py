#!/usr/local/bin/python3
import os
import re
import subprocess
from getpass import getpass
from io import BytesIO

import requests
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image

from ntools.nicodl import Nico


def MylistDL(MylistNo, target_ml=''):
    N = Nico()
    Nico.download_path = "{0}/Downloads/Nvideo/".format(os.environ['HOME'])
    user = N.login_check()
    if user is None:
        print('ログイン情報を入力してください。')
        Nmail = input('メールアドレス >>')
        Npass = getpass('パスワード >>')
        user = N.Login(mail=Nmail, passwd=Npass)
    print(user, "でログインしています")
    data = N.Mylist.videoList(MylistNo)
    listname = N.Mylist.get_name()
    targetname = N.Mylist.get_name(target_ml)
    if not data:
        print('マイリスト "' + listname + '" に動画が登録されていません！')
        return
    print('Mylist:', listname, len(data), '件の動画が見つかりました')
    mvs = 0
    failed_m = []
    for video_id in data:
        print('+-' * 24 + '+')
        try:
            N.Video.getDLdata(video_id)
        except:
            print("getDLdata: 失敗", video_id)
            failed_m.append(video_id)
            continue
        low = ''
        if N.Video.Vurl.find('low') != -1:
            low = '[eco]'
        print(low + N.Video.title + ' (' + N.Video.videoID + ") type:",
              N.Video.type.replace('.', ''))
        print('ダウンロードを開始します...')
        savefile = N.Video.download()
        print('ダウンロード完了!')

        result = mv2m4a(savefile, N.Video.title, N.Video.owner,
                        N.Video.postdate.split('/')[0], N.Video.category)
        if result != 0:
            print('音声変換完了!')
            add_thumb(result, N.Video.GetthumbnailURL())
            print('サムネイル反映完了!')
            if target_ml != '':
                mv = N.Mylist.move(Targetml=target_ml)
                if mv is True:
                    print('動画をマイリスト "' + targetname + '" へ移動完了!')
                else:
                    print('動画をマイリスト "' + targetname + '" へ移動失敗')
            mvs += 1
        else:
            print('音声変換失敗... 理由は', result)
    if mvs != 0:
        print('+-' * 24 + '+')
        print(mvs, '件の動画をダウンロードしました！')
    if failed_m:
        print("以下の動画のダウンロードに失敗しています。")
        print(failed_m)


def add_thumb(file_path, thumbnail_url):
    coverart_page = requests.get(thumbnail_url + ".L")
    if coverart_page.status_code == 404:
        coverart_page = requests.get(thumbnail_url)
    if coverart_page.status_code == 404:
        raise Exception("404 Error")
    jpeg_file = BytesIO(coverart_page.content)
    image_processor = Image.open(jpeg_file)
    size = image_processor.size
    smaller, larger = size if size[0] < size[1] else size[::-1]
    box = ((larger - smaller) / 2, 0, (larger - smaller) / 2 + smaller,
           smaller)
    cropped = image_processor.crop(box)
    cropped.save("cover.jpg", format="JPEG")
    tag = MP4(file_path)
    with open("cover.jpg", "rb") as f:
        tag["covr"] = [MP4Cover(f.read(), imageformat=MP4Cover.FORMAT_JPEG)]
    tag.save()
    os.remove("cover.jpg")


def mv2m4a(inputfile, title, artist, date, genle):
    ext = os.path.splitext(inputfile)
    if ext[1] == '.mp4':
        opt = ' -acodec copy'
    else:
        opt = ' -ab 256k'
        print('音声変換開始...')
    cmd = 'ffmpeg -y -i "{0}"{1} -vn -loglevel fatal -metadata title="{2}" ' \
          '-metadata artist="{3}" -metadata album_artist="{3}" ' \
          '-metadata date="{4}" -metadata genre="{5}" "{6}.m4a"'

    result = subprocess.call(
        cmd.format(inputfile, opt, trim_title(title), artist, date, genle,
                   ext[0].replace('[eco]', '')),
        shell=True)
    if result == 0:
        os.remove(inputfile)
        return ext[0].replace('[eco]', '') + ".m4a"
    return 0


def trim_title(title):
    t = title
    rm_list = ["/.*$", "-.*$", "／.*$", "【[?!】]】", "\[[?!.*】]\]"]
    for x in rm_list:
        title = re.sub(x, "", title)

    if title.count("】") == 1:
        title = re.sub("【.*】", "", title)
    elif title.count("】") == 2:
        search = re.search(r'】(.*)【', title)
        title = search.groups()[0]
    if title.count("]") == 1:
        title = re.sub("\[.*\]", "", title)
    elif title.count("]") == 2:
        search = re.search(r'\](.*)\[', title)
        title = search.groups()[0]
    if title.count("「") == 1:
        search = re.search(r'「(.*)」', title)
        title = search.groups()[0]
    if title.count("『") == 1:
        search = re.search(r'『(.*)』', title)
        title = search.groups()[0]
    elif title.count("]") == 2:
        search = re.search(r'』(.*)『', title)
        title = search.groups()[0]

    title = title.strip()
    if title == "":
        title = t
    return title


if __name__ == '__main__':
    ml = '57275032'
    ml2 = '62944230'
    MylistDL(ml, ml2)
