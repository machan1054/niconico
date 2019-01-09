import json
import os
import pickle
import re
import time
import urllib.parse

import requests

from bs4 import BeautifulSoup
from ntools import utils


class Nico:
    nvURL = "http://www.nicovideo.jp"

    login_file = "nlogin.bin"
    download_path = "download/"

    login_error = {
        'cant_login': "Nico.Login: メールアドレスまたはパスワードが間違っています。",
        'login_lock': "Nico.Login: アカウントロックのためログインできません。"
    }

    def __init__(self):
        """ニコニコ"""
        self.__getflvURL = "http://flapi.nicovideo.jp/api/getflv/"
        self.__loginURL = \
            "https://secure.nicovideo.jp/secure/login?site=niconico"
        self.Video = Nico.video(self)
        self.Mylist = Nico.mylist(self)
        self.Nmail = ''
        self.Npassword = ''
        self.cookies = ''
        self.login_check()

    def getUserName(self):
        """ユーザー名を取得する"""
        res = requests.get(self.__getflvURL + "sm9", cookies=self.cookies)
        if res.text == "closed=1&done=true":
            raise Exception("getUserName: 失敗")
        searched = re.search("nickname=(.*)&time", res.text)
        if searched is not None:
            userdata = urllib.parse.unquote(searched.groups()[0])
            return userdata

    def Login(self, mail, passwd):
        """ニコニコにログイン
            mail: ログインするメールアドレス
            passwd: パスワード"""
        self.Nmail = mail
        self.Npassword = passwd
        return self.login_check(retry=True)

    def login_check(self, retry=False):
        """ログイン済みかどうかをチェックしてログイン"""
        try:
            with open(Nico.login_file, 'rb') as f:
                self.cookies = pickle.load(f)
            userdata = self.getUserName()
            return userdata
        except:
            if retry is True:
                print('再ログインを試みます...')
                self.LoginPost()
                return self.getUserName()
            return None

    def save_login(self):
        """ログイン情報をファイルに保存する"""
        with open(Nico.login_file, 'wb') as f:
            pickle.dump(self.cookies, f)

    def LoginPost(self):
        """ニコニコ動画にログインする"""
        if self.Nmail == '' or self.Npassword == '':
            raise Exception('LoginPost: ログイン情報が指定されていません。')
        payload = {'mail_tel': self.Nmail, 'password': self.Npassword}
        res = requests.post(
            self.__loginURL, data=payload, allow_redirects=False)
        for err, msg in Nico.login_error.items():
            if res.headers['Location'].find(err) != -1:
                raise Exception(msg)
        self.cookies = res.cookies
        self.save_login()
        return res.cookies

    @staticmethod
    def url2vid(vURL):
        """URLから動画IDを抽出する"""
        if vURL.startswith("http"):
            searched = re.search("nicovideo.jp/watch/([a-z0-9]*)", vURL)
            assert searched is not None, "url2vid: URL中に動画IDが見つかりませんでした"
            vURL = searched.groups()[0]
        return vURL

    class video:
        def __init__(self, out):
            self.nico = out
            self.__videoURL = Nico.nvURL + "/watch/"

            self.__getflvURL = "http://flapi.nicovideo.jp/api/getflv/"
            self.Vurl = ''
            self.__Vdata = ''
            self.videoID = ''

        def GetsmileURL(self, videoID=''):
            """smileサーバーの動画URLを取得する"""
            res = self.getData(videoID)
            return res['video']['smileInfo']['url']

        def GetthumbnailURL(self, videoID=''):
            res = self.getData(videoID)
            return res['video']['thumbnailURL']

        def getData(self, videoID=''):
            """動画情報が取得済みかどうか判定。必要に応じて取得して返す"""
            self.nico.login_check(retry=True)
            self.setID(videoID)
            if self.__Vdata != "":
                if self.__Vdata['video']['id'] == self.videoID:
                    return self.__Vdata
            return self.GetdmcData()

        def setID(self, videoID):
            videoID = Nico.url2vid(videoID)
            if videoID == '':
                if self.videoID == '':
                    raise Exception('setVideoID: 動画IDが指定されていません。')
            else:
                self.videoID = videoID

        def GetdmcData(self, videoID=''):
            """動画ページから動画情報を取得する
            a
            """
            self.setID(videoID)
            res = requests.get(
                self.__videoURL + self.videoID, cookies=self.nico.cookies)
            if res.status_code != 200:
                print("60秒後にリトライします。")
                time.sleep(61)
                res = requests.get(
                    self.__videoURL + self.videoID, cookies=self.nico.cookies)
                if res.status_code != 200:
                    raise Exception('GetdmcData: 動画が見つかりません。', self.videoID)
            self.nico.cookies = res.cookies
            soup = BeautifulSoup(urllib.parse.unquote(res.text), "lxml")
            data = soup.find(id='js-initial-watch-data').get('data-api-data')
            data = re.sub("' data-environment='.*$", "", data)
            json_data = json.loads(data)
            self.__Vdata = json_data
            with open(self.videoID + '.json', 'w') as f:
                json.dump(json_data, f, indent=4)
            return json_data

        def getDLdata(self, videoID='', mode='smile'):
            self.__Vdata = ''
            # 動画データを取得
            if mode == 'smile':
                self.Vurl = self.GetsmileURL(videoID)
            elif mode == 'dmc':
                pass
            else:
                return
            if self.Vurl == '':
                raise Exception("download: 動画URLが取得できませんでした。", self.videoID)
            data = self.__Vdata
            self.title = data['video']['title']
            self.category = data["tags"][0]["name"]
            try:
                self.owner = data['owner']['nickname'].replace(' さん', '')
            except TypeError:
                self.owner = data['channel']['name']
            self.postdate = data['video']['postedDateTime']
            try:
                self.type = '.' + data['video']['movieType']
            except KeyError:
                temp = requests.head(
                    self.Vurl,
                    cookies=self.nico.cookies,
                    headers={
                        'Referer': self.__videoURL + self.videoID
                    }).headers['Content-Disposition']
                self.type = os.path.splitext(temp.replace('"', ''))[1]

            savepath = Nico.download_path + \
                re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', self.owner)
            low = ''
            if self.Vurl.find('low') != -1:
                low = '[eco]'
            filename = low + \
                re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', self.title) + self.type
            return (savepath, filename)

        def download(self, videoID='', mode='smile'):
            """動画をダウンロードする"""
            if self.Vurl == '' or videoID != '':
                self.getDLdata(videoID, mode)
            savepath = Nico.download_path + \
                re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', self.owner)
            low = ''
            if self.Vurl.find('low') != -1:
                low = '[eco]'
            filename = low + \
                re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', self.title) + self.type

            utils.HTTPdownload(
                file_url=self.Vurl,
                dir_path=savepath,
                file_name=filename,
                Cookies=self.nico.cookies,
                Referer=self.__videoURL + self.videoID)
            return os.path.join(savepath, filename)

    class mylist:
        def __init__(self, out):
            self.nico = out
            self.__mylistURL = Nico.nvURL + "/my/mylist/#/"
            self.__mylisturl = Nico.nvURL + "/mylist/{0}?rss=2.0"
            self.__mylistAPI = Nico.nvURL + "/api/mylist/"

            self.MylistNo = ''
            self.IDlist = {}

        def setMylistNo(self, mylistNo):
            if mylistNo == '':
                if self.MylistNo == '':
                    raise Exception('setVideoID: マイリストが指定されていません。')
            else:
                self.MylistNo = mylistNo

        def get(self, mylistNo=''):
            """マイリストの動画IDを取得してディクショナリで返します。"""
            self.setMylistNo(mylistNo)
            self.nico.login_check(retry=True)
            res = requests.get(
                self.__mylistAPI + 'list?group_id=' + self.MylistNo,
                cookies=self.nico.cookies)
            if res.status_code != 200:
                raise Exception('getMylist: マイリストが見つかりません。', self.MylistNo)
            data = json.loads(urllib.parse.unquote(res.text))
            return data

        def get_name(self, mylistNo=''):
            if mylistNo == '':
                mylistNo = self.MylistNo
            self.nico.login_check(retry=True)
            res = requests.get(
                self.__mylisturl.format(mylistNo), cookies=self.nico.cookies)
            if res.status_code != 200:
                raise Exception('getMylist: マイリストが見つかりません。', mylistNo)
            for x in res.text.splitlines():
                searched = re.search('<title>マイリスト (.*)‐ニコニコ動画</title>$', x)
                if searched is not None:
                    return searched.groups()[0]

        def videoList(self, mylistNo=''):
            data = self.get(mylistNo)['mylistitem']
            result = []
            self.IDlist = {}
            for vid in data:
                result.append(vid['item_data']['video_id'])
                self.IDlist[vid['item_data']['video_id']] = vid['item_id']
            return result

        def __getToken(self):
            self.nico.login_check(retry=True)
            res = requests.get(
                self.__mylistURL + 'list?group_id=' + self.MylistNo,
                cookies=self.nico.cookies)
            if res.status_code != 200:
                raise Exception('getMylist: マイリストが見つかりません。')
            for x in res.text.splitlines():
                searched = re.search('NicoAPI.token = "(.*)";$', x)
                if searched is not None:
                    return searched.groups()[0]

        def move(self, Targetml, videoID='', mylistNo=''):
            self.setMylistNo(mylistNo)
            self.nico.login_check(retry=True)
            if videoID == '':
                videoID = self.nico.Video.videoID
            if mylistNo != '':
                self.videoList()
            token = self.__getToken()
            payload = {
                'group_id': self.MylistNo,
                'target_group_id': Targetml,
                'token': token,
                'id_list[0][]': [self.IDlist[videoID]]
            }
            res = requests.post(
                self.__mylistAPI + 'move',
                data=payload,
                cookies=self.nico.cookies,
                allow_redirects=False)
            data = json.loads(urllib.parse.unquote(res.text))
            if data['duplicates'] == [] and data['targets'] != []:
                return True
            else:
                return False

        def copy(self, Targetml, videoID='', mylistNo=''):
            self.setMylistNo(mylistNo)
            self.nico.login_check(retry=True)
            token = self.__getToken()
            if videoID == '':
                videoID = self.nico.Video.videoID
            if mylistNo != '':
                self.videoList()
            payload = {
                'group_id': self.MylistNo,
                'target_group_id': Targetml,
                'token': token,
                'id_list[0][]': [self.IDlist[videoID]]
            }
            res = requests.post(
                self.__mylistAPI + 'copy',
                data=payload,
                cookies=self.nico.cookies,
                allow_redirects=False)
            data = json.loads(urllib.parse.unquote(res.text))
            if data['duplicates'] == [] and data['targets'] != []:
                return True
            else:
                return False

        def delete(self, videoID='', mylistNo=''):
            self.setMylistNo(mylistNo)
            self.nico.login_check(retry=True)
            token = self.__getToken()
            if videoID == '':
                videoID = self.nico.Video.videoID
            if mylistNo != '':
                self.videoList()
            payload = {
                'group_id': self.MylistNo,
                'token': token,
                'id_list[0][]': [self.IDlist[videoID]]
            }
            res = requests.post(
                self.__mylistAPI + 'delete',
                data=payload,
                cookies=self.nico.cookies,
                allow_redirects=False)
            data = json.loads(urllib.parse.unquote(res.text))
            return data
