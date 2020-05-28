import re
import threading
import time

import requests
from ruamel import yaml

from utils import rtext

cp = update_message = ""
VERSION = 1
helpmessage = '''\u00A79=============== \u00A7a[Bilibili Parser]\u00A79 ===============
\u00A7b!!blbl video <链接/视频id>\u00A76 : 解析哔哩哔哩视频信息
\u00A79================================================'''.replace("\n", "\\n")


# 更新检查线程
class updateDetection(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server = server
        self.name = "Chat Bridge Update Detection Thread"
        self.flag = True

    def run(self):
        global update_message
        self.server.logger.info("开始检查更新")
        # 走github获取版本号
        result = requests.get("http://raw.githubusercontent.com/dogdie233/BilibiliParser/master/version.json")
        if result.status_code == 200:
            resultJson = result.json()
            if resultJson["latestVer"] > VERSION:
                self.server.logger.info("BilibiliParser 有新版本" + resultJson["verName"])
                update_message = "BilibiliParser 插件有新版本 " + resultJson["verName"]
        else:
            # 走coding获取版本号
            result = requests.get("http://dogdieself.coding.net/p/bilibiliparser/d/bilibiliparser/git/raw/master/version.json")
            if result.status_code == 200:
                resultJson = result.json()
                if resultJson["latestVer"] > VERSION:
                    self.server.logger.info("BilibiliParser 有新版本" + resultJson["verName"])
                    update_message = "BilibiliParser 插件有新版本 " + resultJson["verName"]
            else:
                self.server.logger.warning("无法连接到服务器，检测更新失败")


def on_load(server, old_module):
    global cp
    with open ("config.yml", "r", encoding="utf8") as f:
        cp = yaml.safe_load(f)["console_command_prefix"]
    server.add_help_message(cp + "blbl help", "查看 BilibiliParser 插件帮助")
    updateDetectionThread = updateDetection(server)
    updateDetectionThread.setDaemon(True)
    updateDetection.start(updateDetectionThread)


def on_player_joined(server, player):
    if update_message != "" and server.get_permission_level(player) >= 3:
        server.execute("tellraw " + player + " {\"text\":\"" + update_message + "\",\"color\":\"green\"}")


def on_info(server, info):
    if info.is_user:
        if info.content.startswith(cp):
            if info.content.startswith(cp + "blbl"):
                args = info.content.split(" ")
                del (args[0])
                on_command(server, info.player, args)
        else:
            vid = get_video_id(info.content)
            if vid is not None:
                message_checked = rtext.RText("检测到您发送的信息是bilibili视频链接,是否要解析视频内容?", color=rtext.RColor.green)
                message_yes = rtext.RText("[是]", color=rtext.RColor.aqua, styles=[rtext.RStyle.bold])
                message_yes.set_click_event(rtext.RAction.run_command, cp + "blbl video " + info.content)
                message_yes.set_hover_text("点击执行命令" + cp + "blbl video " + info.content)
                server.reply(info, rtext.RTextList(message_checked, rtext.RText(" "), message_yes))


def on_command (server, player, args):
    if args[0].lower() == "video":
        # 检查命令参数
        if len(args) != 2:
            server.execute("tellraw " + player + " {\"text\":\"参数错误,请使用 " + cp + "blbl help 获取帮助\", \"color\":\"red\"}")
            return
        # 获取视频id
        vid = get_video_id(args[1])
        if vid is None:
            server.execute("tellraw " + player + " {\"text\":\"这不是bilibili视频id或链接\", \"color\":\"red\"}")
            return
        if "bv" in vid.lower():
            response = requests.get("https://api.bilibili.com/x/web-interface/view?byid=" + vid)
        else:
            response = requests.get("https://api.bilibili.com/x/web-interface/view?aid=" + vid)
        # 判断是否成功获取
        if response.status_code != 200:
            server.execute("tellraw " + player + " {\"text\":\"网络连接错误,请稍后重试,错误码: " + str(response.status_code) + "\", \"color\":\"red\"}")
            return
        result = response.json()
        if result["code"] == 0:
            # 获取的code为0冇表示问题
            message = rtext.RText("========视频信息获取成功========\n", color=rtext.RColor.green, styles=[rtext.RStyle.bold])
            # av bv号和打开链接
            message_avtitle = rtext.RText("AV号: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold])
            message_av = rtext.RText("av" + str(result["data"]["aid"]), color=rtext.RColor.green)
            message_avlink = rtext.RText("[打开链接]", color=rtext.RColor.aqua)
            message_avlink.set_click_event(rtext.RAction.open_url, "http://www.bilibili.com/video/av" + str(result["data"]["aid"]))
            message_avlink.set_hover_text("打开链接: http://www.bilibili.com/video/av" + str(result["data"]["aid"]))
            message_bvtitle = rtext.RText("\nBV号: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold])
            message_bv = rtext.RText(result["data"]["bvid"], color=rtext.RColor.green)
            message_bvlink = rtext.RText("[打开链接]", color=rtext.RColor.aqua)
            message_bvlink.set_click_event(rtext.RAction.open_url, "http://www.bilibili.com/video/" + str(result["data"]["bvid"]))
            message_bvlink.set_hover_text("打开链接: http://www.bilibili.com/video/" + str(result["data"]["bvid"]))
            message = rtext.RTextList(message, message_avtitle, message_av, message_avlink, message_bvtitle, message_bv, message_bvlink, rtext.RText("\n"))
            # 标题信息
            message = rtext.RTextList(message, rtext.RText("标题: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(result["data"]["title"] + "\n", color=rtext.RColor.green))
            # 封面信息
            message = rtext.RTextList(message, rtext.RText("封面: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message_pic = rtext.RText("[查看图片]" + "\n", color=rtext.RColor.aqua)
            message_pic.set_click_event(rtext.RAction.open_url, result["data"]["pic"])
            message_pic.set_hover_text("打开链接: " + result["data"]["pic"])
            message = rtext.RTextList(message, message_pic)
            # 发布日期
            message = rtext.RTextList(message, rtext.RText("发布日期: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result["data"]["pubdate"])) + "\n", color=rtext.RColor.green))
            # 简介
            result["data"]["desc"] = result["data"]["desc"].replace("\n", "      \n")
            if len(result["data"]["desc"]) <= 60:
                message_desc = rtext.RText(result["data"]["desc"] + "\n", color=rtext.RColor.green)
            else:
                message_desc = rtext.RText(result["data"]["desc"][0:59] + "……", color=rtext.RColor.green)
                message_show_full_desc = rtext.RText("[查看完整简介]\n", color=rtext.RColor.aqua)
                message_show_full_desc.set_hover_text(result["data"]["desc"])
                message_desc = rtext.RTextList(message_desc, message_show_full_desc)
            message = rtext.RTextList(message, rtext.RText("简介: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]), message_desc)
            # 播放量
            message = rtext.RTextList(message, rtext.RText("播放量: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(str(result["data"]["stat"]["view"]) + "\n", color=rtext.RColor.green))
            # 弹幕总量
            message = rtext.RTextList(message, rtext.RText("弹幕总量: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(str(result["data"]["stat"]["danmaku"]) + "\n", color=rtext.RColor.green))
            # 点赞数量
            message = rtext.RTextList(message, rtext.RText("点赞数量: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(str(result["data"]["stat"]["like"]) + "\n", color=rtext.RColor.green))
            # 收获硬币
            message = rtext.RTextList(message, rtext.RText("收获硬币: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(str(result["data"]["stat"]["coin"]) + "\n", color=rtext.RColor.green))
            # 收藏数量
            message = rtext.RTextList(message, rtext.RText("收藏数量: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(str(result["data"]["stat"]["favorite"]) + "\n", color=rtext.RColor.green))
            # 转发数量
            message = rtext.RTextList(message, rtext.RText("转发数量: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(str(result["data"]["stat"]["share"]) + "\n", color=rtext.RColor.green))
            # 评论数量
            message = rtext.RTextList(message, rtext.RText("评论数量: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(str(result["data"]["stat"]["reply"]) + "\n", color=rtext.RColor.green))
            # 分part数量
            message = rtext.RTextList(message, rtext.RText("分part数量: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(str(len(result["data"]["pages"])) + "\n", color=rtext.RColor.green))
            # up主
            message = rtext.RTextList(message, rtext.RText("投稿人: ", color=rtext.RColor.blue, styles=[rtext.RStyle.bold]))
            message = rtext.RTextList(message, rtext.RText(result["data"]["owner"]["name"], color=rtext.RColor.green))
            message_owner_link = rtext.RText("[打开个人主页]", color=rtext.RColor.aqua)
            message_owner_link.set_click_event(rtext.RAction.open_url, "http://space.bilibili.com/" + str(result["data"]["owner"]["mid"]))
            message_owner_link.set_hover_text("打开链接: http://space.bilibili.com/" + str(result["data"]["owner"]["mid"]))
            message = rtext.RTextList(message, message_owner_link)
            server.say(message)
        else:
            server.execute("tellraw " + player + " {\"text\":\"Error发生,错误信息: " + result["message"].replace("\"", "\\\"") + "\", \"color\":\"red\"}")
    elif args[0].lower() == "help":
        server.execute("tellraw " + player + " {\"text\":\"" + helpmessage.replace("\"", "\\\"") + "\"}")


def get_video_id(url):
    match = re.match(r"(?:https?://)?(?:(?:www\.bilibili\.(?:(?:com)|(?:tv))/video/)|(?:b23\.tv/))?(?:(?:av(\d+))|(bv[0-9A-Za-z]+))$", url, re.I)
    if match is None:
        return None
    else:
        return match.group(2) if match.group(1) is None else match.group(1)