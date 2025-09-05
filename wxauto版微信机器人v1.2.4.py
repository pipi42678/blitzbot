from wxauto import WeChat
from wxauto.msgs import FriendMessage
import os
import time
import random
from openai import OpenAI
from rapidocr_onnxruntime import RapidOCR
import shutil
import sys
import traceback


if os.path.exists(os.getcwd() + "\wxauto_logs"):
    shutil.rmtree(os.getcwd() + "\wxauto_logs")
    print("wxauto_logs:删除成功！")
else:
    print("wxauto_logs:文件夹不存在!")

if os.path.exists(os.getcwd() + "\wxauto文件下载"):
    shutil.rmtree(os.getcwd() + "\wxauto文件下载")
    print("wxauto文件下载:删除成功！")
else:
    print("wxauto文件下载:文件夹不存在!")

wx = WeChat()
ocr_engine = RapidOCR()


with open("Robot_data\机器人信息.txt", "r", encoding="utf-8") as f:  # 读入机器人的基本信息
    robot_data = f.read()
with open("Config\主动发送开始限制.txt","r",encoding="utf-8") as f:
    start_wait = int(f.read())
with open("Config\主动发送末尾限制.txt","r",encoding="utf-8") as f:
    end_wait = int(f.read())
with open("Config\表情包发送开始限制.txt","r",encoding="utf-8") as f:
    start_emoji_wait = int(f.read())
with open("Config\表情包发送末尾限制.txt","r",encoding="utf-8") as f:
    end_emoji_wait = int(f.read())
with open("ApiKey_Data\AI_api_key.txt","r",encoding="utf-8") as f:
    deepseek_api_key = f.read()
with open("群名.txt","r",encoding="utf-8") as f:
    receiver_name = f.read()
with open("Robot_Data\机器人提出话题.txt","r",encoding="utf-8") as f:
    topic = f.read()
with open("Config\是否主动提出话题.txt","r",encoding="utf-8") as f:
    enable_robot_send = True if f.read() == "True" else False
with open("Config\每类表情包数量.txt","r",encoding="utf-8") as f:
    emotion_num = int(f.read())
with open("群名.txt","r",encoding="utf-8") as f:
    group_name = f.read()
with open("Config\是否打开图像消息接收.txt","r",encoding="utf-8") as f:
    enable_image = True if f.read() == "True" else False
with open("Config\是否打开语音消息接收.txt","r",encoding="utf-8") as f:
    enable_voice = True if f.read() == "True" else False


text_AI_messages = [
    {"role": "system", "content": robot_data},  # 系统消息包含人设
    {"role": "assistant", "content": "好，我明白了"}
]  # 用来存放deepseek的历史对话记录


emoji_wait_time = random.randint(start_emoji_wait, end_emoji_wait)
robot_send_time = random.randint(start_wait, end_wait)  # 机器人发送消息的时间，以分钟为单位
temp_content = ""
emotion_id = ""
enable_emotion = True
deepseek_return = ""
emotion_cnt = 0
robot_name = "spit"
AI_msg = ""
sep = ""
cut_str = "/e/"
start_h = int(time.strftime("%H", time.localtime()))
start_m = int(time.strftime("%M", time.localtime()))


def handle_exception(exc_type, exc_value, exc_traceback): #用于处理程序出错的函数
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
    print("\n程序出错！您可以向开发者联系。\n请按回车键退出...", file=sys.stderr)
    input()  # 等待回车
    sys.exit(1)  # 退出


def reset_time(): #获取当前的时间
    global start_h, start_m
    start_h = int(time.strftime("%H", time.localtime()))
    start_m = int(time.strftime("%M", time.localtime()))


def get_path(name): #用于获取当前位置的函数
    return os.getcwd() + name


def delete_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print("删除成功！")
    else:
        print("文件夹不存在!")


def ocr_rapidocr(img_path):
    result = ocr_engine(img_path)
    content, elapse = result
    return content


def time_diff_minutes():  # 计算当前时间到上次发送时间的间隔分钟数
    global start_h, start_m
    end_h = int(time.strftime("%H", time.localtime()))
    end_m = int(time.strftime("%M", time.localtime()))
    start_total = start_h * 60 + start_m
    end_total = end_h * 60 + end_m

    if end_total >= start_total:
        return end_total - start_total
    else:
        # 处理跨天情况
        return (24 * 60 - start_total) + end_total


def auto_send_task(): #让机器人主动发送消息的函数
    global robot_send_time, start_h, start_m, deepseek_return, start_wait, end_wait, AI_msg
    if enable_robot_send:
        time_dist = time_diff_minutes()
        if time_dist >= robot_send_time:
            AI_msg = "{请提出一个话题+" + topic + "}"
            deepseek_return = deepseek_api_use(AI_msg, deepseek_api_key)
            print("机器人提出话题:" + deepseek_return)
            send_split_messages(deepseek_return, receiver_name, cut_str)
            reset_time()
            robot_send_time = random.randint(start_wait, end_wait)


def send_split_messages(combined_str, receiver, cut_str):  # 处理回复的文本，将其分成多个部分依次发送，形成发送多个消息的效果
    content, sep ,AI_emotion = combined_str.partition("/emotion/")
    send_msg = content.split(cut_str)

    for msg in send_msg:
        cleaned_msg = msg.strip()
        if cleaned_msg:
            #s = random.randint(1, 2)
            #time.sleep(s)
            wx.SendMsg(cleaned_msg, receiver)

    if len(AI_emotion) != 0 and enable_emotion:
        print("发送表情" + AI_emotion + "\n")
        send_emotion(emotion_id, AI_emotion)


def deepseek_api_use(user_input, user_deepseek_api_key):  # DeepSeek的调用，输入和输出
    global text_AI_messages
    text_AI_messages.append({"role": "user", "content": user_input})
    client = OpenAI(api_key=user_deepseek_api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=text_AI_messages,
        stream=False
    )
    ai_reply = response.choices[0].message.content
    text_AI_messages.append({"role": "assistant", "content": ai_reply})
    return ai_reply


def send_emotion(emotion_address, emotion_content): #发送表情包
    global receiver_name, emoji_wait_time, start_emoji_wait, end_emoji_wait,emotion_num

    emotion_kind = emotion_content
    emoji_wait_time = random.randint(start_emoji_wait, end_emoji_wait)
    str_num = str(random.randint(1, emotion_num))
    emotion_place = emotion_address + "\e" + emotion_kind + "\e" + str_num

    if os.path.exists(emotion_place + ".gif"):
        wx.SendFiles(emotion_place + ".gif", receiver_name)
        print(emotion_place + ".gif" + "\n")
    elif os.path.exists(emotion_place + ".jfif"):
        wx.SendFiles(emotion_place + ".jfif", receiver_name)
        print(emotion_place + ".jfif" + "\n")
    else:
        return


def process_emotion(emotion):
    global enable_emotion, emotion_cnt
    if len(emotion) != 0 and enable_emotion:  # 发送表情，如果表情数够等待数了就发送
        emotion_cnt += 1
        if emotion_cnt >= emoji_wait_time:
            emotion_cnt = 0
            print("发送表情" + emotion + "\n")
            send_emotion(emotion_id, emotion)


def on_message(msg, chat): #比较重要的信息模块，主要作用是接收消息并发送给deepseek得到回复，然后再发送给群里
    global emotion_cnt, emoji_wait_time, enable_emotion, temp_content, robot_send_time, receiver_name
    global enable_robot_send, start_h, start_m, start_emoji_wait, end_emoji_wait, deepseek_return, robot_name
    global AI_msg

    if isinstance(msg, FriendMessage):

        if msg.type == 'text' or msg.type == 'quote': #对文本消息和引用消息的处理

            if msg.content == "[动画表情]":
                return

            result = msg.content  # 获取消息内容

            sender_id = msg.sender  # 获取发送者的昵称
            send_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) #获取消息发送的时间
            AI_msg = send_time + " " + group_name + ": " + sender_id + ":" + str(result) #拼凑消息

            if msg.type == 'quote': #如果消息是引用消息，处理被引用的部分
                AI_msg = AI_msg + " 引用:" + "引用内容:" + msg.quote_content

            print(AI_msg + "\n")  # 输出消息内容

        elif msg.type == 'image': #对图片消息的处理

            if not enable_image:
                return

            img_path = msg.download()
            print(img_path)
            ocr_result = ocr_rapidocr(img_path)
            print(ocr_result)

            sender_id = msg.sender  # 获取发送者的昵称
            send_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 获取消息发送的时间
            AI_msg = send_time + " " + group_name + ": " + sender_id + ":" + str(ocr_result)  # 拼凑消息

        elif msg.type == 'voice':

            if not enable_voice:
                return

            voice_result = msg.to_text()
            print("语音识别结果:" + voice_result)

            sender_id = msg.sender  # 获取发送者的昵称
            send_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 获取消息发送的时间
            AI_msg = send_time + " " + group_name + ": " + sender_id + ":" + str(voice_result)  # 拼凑消息
            print(AI_msg + "\n")  # 输出消息内容

        else:
            return


        deepseek_return = deepseek_api_use(AI_msg, deepseek_api_key)  # 获得deepseek的回复

        if deepseek_return == "1" or deepseek_return == "...1":
            print("机器人不回答\n")
            return

        # 如果已经回复了，就不主动提出问题，避免出现冲突的情况
        reset_time()
        AI_content, sep, AI_emotion = deepseek_return.partition("/emotion/")

        send_split_messages(AI_content, receiver_name, cut_str)
        print("AI回复:" + AI_content.replace("/e/", " ") + "\n")

        process_emotion(AI_emotion)


if __name__ == "__main__":
    sys.excepthook = handle_exception
    emotion_id = get_path("\emotion") #得出当前文件夹中表情包的路径
    wx.AddListenChat(nickname=receiver_name, callback=on_message) #增加监听列表
    while True:
        wx.StartListening()
        time.sleep(0.05)
        auto_send_task()
        time.sleep(0.05)

