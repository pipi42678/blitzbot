from wxauto import WeChat
from wxauto.msgs import FriendMessage
import os
import time
import random
from openai import OpenAI
from rapidocr_onnxruntime import RapidOCR
from datetime import datetime
import shutil
import sys
import math
import traceback

# 检查并删除wxauto_logs文件夹
if os.path.exists(os.getcwd() + "\wxauto_logs"):
    shutil.rmtree(os.getcwd() + "\wxauto_logs")
    print("wxauto_logs:删除成功！")
else:
    print("wxauto_logs:文件夹不存在!")

# 检查并删除wxauto文件下载文件夹
if os.path.exists(os.getcwd() + "\wxauto文件下载"):
    shutil.rmtree(os.getcwd() + "\wxauto文件下载")
    print("wxauto文件下载:删除成功！")
else:
    print("wxauto文件下载:文件夹不存在!")

# 初始化微信客户端和OCR引擎
wx = WeChat()
ocr_engine = RapidOCR()

# 从文件中读取机器人配置信息
with open("Robot_data\机器人信息.txt", "r", encoding="utf-8") as f:
    #Fuck Robot Data which make me fixed so much times!
    robot_data = f.read()
with open("Config\主动发送开始限制.txt", "r", encoding="utf-8") as f:
    start_wait = int(f.read())
with open("Config\主动发送末尾限制.txt", "r", encoding="utf-8") as f:
    end_wait = int(f.read())
with open("Config\表情包发送开始限制.txt", "r", encoding="utf-8") as f:
    start_emoji_wait = int(f.read())
with open("Config\表情包发送末尾限制.txt", "r", encoding="utf-8") as f:
    end_emoji_wait = int(f.read())
with open("ApiKey_Data\AI_api_key.txt", "r", encoding="utf-8") as f:
    deepseek_api_key = f.read()
with open("群名.txt", "r", encoding="utf-8") as f:
    receiver_name = f.read()
with open("Robot_Data\机器人提出话题.txt", "r", encoding="utf-8") as f:
    topic = f.read()
with open("Config\是否主动提出话题.txt", "r", encoding="utf-8") as f:
    enable_robot_send = True if f.read() == "True" else False
with open("Config\每类表情包数量.txt", "r", encoding="utf-8") as f:
    emotion_num = int(f.read())
with open("群名.txt", "r", encoding="utf-8") as f:
    group_name = f.read()
with open("Config\是否打开图像消息接收.txt", "r", encoding="utf-8") as f:
    enable_image = True if f.read() == "True" else False
with open("Config\是否打开语音消息接收.txt", "r", encoding="utf-8") as f:
    enable_voice = True if f.read() == "True" else False
with open("Config\初始消息等待量.txt", "r", encoding="utf-8") as f:
    msg_send_wait = int(f.read())

# 初始化AI对话消息列表，包含系统角色设定和初始助手回复，用来存放和语言AI的历史对话记录
text_AI_messages = [
    {"role": "system", "content": robot_data},  # 系统消息包含人设
    {"role": "assistant", "content": "好，我明白了"}
]

# 初始化各种全局变量
emoji_wait_time = random.randint(start_emoji_wait, end_emoji_wait)  # 表情包发送等待时间
robot_send_time = random.randint(start_wait, end_wait)  # 机器人主动发送消息的时间间隔，以分钟为单位
temp_content = ""  # 临时存储消息内容
emotion_id = ""  # 表情包路径
enable_emotion = True  # 是否启用表情包功能
deepseek_return = ""  # DeepSeek API返回的内容
average_seconds_dist = 0  # 消息平均间隔时间（秒）
msg_cnt = 0  # 消息计数器
emotion_cnt = 0  # 表情包计数器
AI_msg = ""  # AI消息内容
sep = ""  # 分隔符（未使用）
dist_start = False  # 距离计算开始标志
cut_str = "/e/"  # 消息分割字符串
start_h = int(time.strftime("%H", time.localtime()))  # 起始小时
start_min = int(time.strftime("%M", time.localtime()))  # 起始分钟
average_cnt = 0  # 平均计数
now_msg_time = [0, 0, 0, 0, 0, 0]  # 当前消息时间数组[年,月,日,时,分,秒]
last_msg_time = [0, 0, 0, 0, 0, 0]  # 上一条消息时间数组[年,月,日,时,分,秒]
average_dist_list = []  # 平均距离列表
robot_names = [] # 机器人的名字


def msg_func(x):
    """
    根据消息间隔时间计算消息处理参数的数学函数

    参数:
    x: 消息间隔时间（秒）

    返回:
    计算后的消息处理参数值
    """
    return math.floor(2 + 4.5 / (1 + (x / 14.3) ** 1.5))


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    全局异常处理函数，当程序发生未捕获的异常时调用

    参数:
    exc_type: 异常类型
    exc_value: 异常值
    exc_traceback: 异常回溯信息
    """
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
    print("\n程序出错！您可以向开发者联系。\n请按回车键退出...", file=sys.stderr)
    input()  # 等待回车
    sys.exit(1)  # 退出


def extract_names(file_path):
    """
    从文件提取名字和昵称到数组
    只识别"五、昵称和名字:"后面的内容，名字X:格式的行提取冒号后内容
    昵称:格式的行提取内容前加@，支持任意数量的名字行

    参数: file_path 文件路径
    返回: 名字数组，昵称前加@
    """
    names = []
    found_section = False

    with open(file_path, 'r', encoding='utf-8') as fr:
        for line in fr:
            line = line.strip()

            # 找到"昵称和名字:" section才开始处理
            if "昵称和名字:" in line:
                found_section = True
                continue

            # 如果已经找到section，处理后续行
            if found_section:
                if not line:  # 空行跳过
                    continue

                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    if value:
                        if key.startswith('名字'):
                            names.append(value)
                        elif key == '昵称':
                            names.append('@' + value)
                else:
                    # 如果遇到没有冒号的行，可能是下一个section开始了
                    break

    print(names)
    return names


def find_matching_strings(text, string_array):
    """
    查找字符串中出现的所有数组中的字符串

    返回: 匹配到的字符串列表
    """
    return string_array in text


def reset_time():
    """
    重置起始时间为当前时间（小时和分钟）
    更新全局变量start_h和start_min
    """
    global start_h, start_min
    start_h = int(time.strftime("%H", time.localtime()))
    start_min = int(time.strftime("%M", time.localtime()))


def get_msg_time():
    """
    获取当前完整时间并更新全局变量now_msg_time
    时间格式为[年,月,日,时,分,秒]
    """
    global now_msg_time
    now_msg_time[0] = int(time.strftime("%Y", time.localtime()))
    now_msg_time[1] = int(time.strftime("%m", time.localtime()))
    now_msg_time[2] = int(time.strftime("%d", time.localtime()))
    now_msg_time[3] = int(time.strftime("%H", time.localtime()))
    now_msg_time[4] = int(time.strftime("%M", time.localtime()))
    now_msg_time[5] = int(time.strftime("%S", time.localtime()))


def get_path(name):
    """
    获取当前工作目录与给定名称组合的完整路径

    参数:
    name: 路径名称

    返回:
    组合后的完整路径
    """
    return os.getcwd() + name


def delete_folder(folder_path):
    """
    删除指定文件夹

    参数:
    folder_path: 要删除的文件夹路径
    """
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print("删除成功！")
    else:
        print("文件夹不存在!")


def ocr_rapidocr(img_path):
    """
    使用RapidOCR对指定图片进行OCR识别

    参数:
    img_path: 图片文件路径

    返回:
    OCR识别结果内容
    """
    result = ocr_engine(img_path)
    content, elapse = result
    return [item[1] for item in content if len(item) >= 2]


def time_diff_minutes():
    """
    计算当前时间与上次记录时间的间隔分钟数
    考虑跨天情况

    返回:
    时间间隔（分钟）
    """
    global start_h, start_min
    end_h = int(time.strftime("%H", time.localtime()))
    end_m = int(time.strftime("%M", time.localtime()))
    start_total = start_h * 60 + start_min
    end_total = end_h * 60 + end_m

    if end_total >= start_total:
        return end_total - start_total
    else:
        # 处理跨天情况
        return (24 * 60 - start_total) + end_total


def time_diff_seconds():
    """
    计算当前消息时间与上一条消息时间的间隔秒数

    返回:
    时间间隔（秒）
    """
    global last_msg_time, now_msg_time
    # 构造 datetime 对象
    t1 = datetime(*last_msg_time)
    t2 = datetime(*now_msg_time)
    # 直接计算差值
    delta = t2 - t1
    #print(t1)
    #print(t2)
    return int(delta.total_seconds())


def auto_send_task():
    """
    自动发送任务函数，检查是否到达机器人主动发送消息的时间
    如果到达设定时间，则调用DeepSeek API生成话题并发送
    """
    global robot_send_time, deepseek_return, start_wait, end_wait, AI_msg
    if enable_robot_send:
        time_dist = time_diff_minutes()
        if time_dist >= robot_send_time:
            AI_msg = "{请提出一个话题+" + topic + "}"
            deepseek_return = deepseek_api_use(AI_msg, deepseek_api_key)
            print("机器人提出话题:" + deepseek_return)
            send_split_messages(deepseek_return, receiver_name, cut_str)
            reset_time()
            robot_send_time = random.randint(start_wait, end_wait)


def send_split_messages(combined_str, receiver, cut_str):
    """
    将组合字符串按指定分隔符分割成多个消息并发送
    支持表情包发送功能

    参数:
    combined_str: 组合字符串，可能包含消息内容和表情包标识
    receiver: 消息接收者
    cut_str: 消息分割字符串
    """
    content, sep, AI_emotion = combined_str.partition("/emotion/")
    send_msg = content.split(cut_str)

    for msg in send_msg:
        cleaned_msg = msg.strip()
        if cleaned_msg:
            # s = random.randint(1, 2)
            # time.sleep(s)
            wx.SendMsg(cleaned_msg, receiver)

    if len(AI_emotion) != 0 and enable_emotion:
        print("发送表情" + AI_emotion + "\n")
        send_emotion(emotion_id, AI_emotion)


def deepseek_api_use(user_input, user_deepseek_api_key):
    """
    调用DeepSeek API进行对话生成

    参数:
    user_input: 用户输入内容
    user_deepseek_api_key: DeepSeek API密钥

    返回:
    AI生成的回复内容
    """
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


def send_emotion(emotion_address, emotion_content):
    """
    发送表情包函数，从指定路径随机选择表情包并发送

    参数:
    emotion_address: 表情包存储路径
    emotion_content: 表情包类型/名称
    """
    global receiver_name, emoji_wait_time, start_emoji_wait, end_emoji_wait, emotion_num

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
    """
    处理表情包发送逻辑，计数达到阈值时发送表情包

    参数:
    emotion: 表情包类型/名称
    """
    global enable_emotion, emotion_cnt
    if len(emotion) != 0 and enable_emotion:  # 发送表情，如果表情数够等待数了就发送
        emotion_cnt += 1
        if emotion_cnt >= emoji_wait_time:
            emotion_cnt = 0
            print("发送表情" + emotion + "\n")
            send_emotion(emotion_id, emotion)


def calculate_dist():
    """
    计算消息时间间隔并动态调整消息发送等待时间
    当收集到足够的时间间隔样本后，计算平均值并调整发送频率
    """
    global last_msg_time, now_msg_time, average_cnt, dist_start, msg_send_wait, average_seconds_dist

    # 检查是否有历史消息时间数据（不全为0）
    if not all(num == 0 for num in last_msg_time):
        # 计算时间间隔
        dist = time_diff_seconds()
        average_dist_list.append(dist)
        average_cnt += 1
        last_msg_time = now_msg_time[:]  # 更新最后消息时间为当前消息时间

        # 判断是否收集到足够样本进行计算
        if (average_cnt >= (msg_send_wait - 1) and dist_start) or (
                average_cnt >= msg_send_wait and dist_start == False):
            # 计算平均时间间隔
            average_seconds_dist = sum(average_dist_list) / len(average_dist_list)
            # 根据平均间隔调整发送等待时间
            msg_send_wait = msg_func(average_seconds_dist)

            # 重置计数器和列表
            average_cnt = 0
            average_dist_list.clear()

            # 处理异常情况（间隔接近0）
            if abs(average_seconds_dist) < 1e-6:
                msg_send_wait = 3
                print("新的消息接收区间:" + "3")
                print("平均间隔秒数:" + "ERR")
            else:
                print("新的消息接收区间:" + str(msg_send_wait))
                print("平均间隔秒数:" + str(average_seconds_dist) + "\n")

            dist_start = False  # 结束距离计算阶段

    else:
        # 初始化消息时间并开始距离计算
        last_msg_time = now_msg_time
        dist_start = True


def on_message(msg, chat):
    """
    消息处理回调函数，处理接收到的各种类型消息
    包括文本、引用、图片和语音消息

    参数:
    msg: 消息对象
    chat: 聊天对象
    """
    global emotion_cnt, emoji_wait_time, enable_emotion, temp_content, robot_send_time, receiver_name
    global enable_robot_send, start_h, start_min, start_emoji_wait, end_emoji_wait, deepseek_return
    global AI_msg, msg_cnt, msg_send_wait, now_msg_time, last_msg_time, robot_names
    global average_dist_list, average_seconds_dist, average_cnt, dist_start

    if isinstance(msg, FriendMessage):

        if msg.type == 'text' or msg.type == 'quote':  # 对文本消息和引用消息的处理

            if msg.content == "[动画表情]":
                return

            result = msg.content  # 获取消息内容

            sender_id = msg.sender  # 获取发送者的昵称
            send_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 获取消息发送的时间
            get_msg_time()
            AI_msg = send_time + " " + group_name + ": " + sender_id + ":" + str(result)  # 拼凑消息

            if msg.type == 'quote':  # 如果消息是引用消息，处理被引用的部分
                AI_msg = AI_msg + " 引用:" + "引用内容:" + msg.quote_content

            print(AI_msg + "\n")  # 输出消息内容

        elif msg.type == 'image':  # 对图片消息的处理

            if not enable_image:
                return

            img_path = msg.download()
            print(img_path)
            ocr_result = ocr_rapidocr(img_path)
            print(ocr_result)

            sender_id = msg.sender  # 获取发送者的昵称
            send_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 获取消息发送的时间
            get_msg_time()
            AI_msg = send_time + " " + group_name + ": " + sender_id + ":" + str(ocr_result)  # 拼凑消息

        elif msg.type == 'voice':

            if not enable_voice:
                return

            voice_result = msg.to_text()
            print("语音识别结果:" + voice_result)

            sender_id = msg.sender  # 获取发送者的昵称
            send_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 获取消息发送的时间
            get_msg_time()
            AI_msg = send_time + " " + group_name + ": " + sender_id + ":" + str(voice_result)  # 拼凑消息
            print(AI_msg + "\n")  # 输出消息内容

        else:
            return

        # 将消息添加到临时内容(消息列表)中
        temp_content += (AI_msg + "\n")
        msg_cnt += 1
        print("该消息已经录入列表！\n")


        for i in range(0,len(robot_names)):
            if find_matching_strings(AI_msg, robot_names[i]):
                msg_cnt = msg_send_wait
                average_cnt = msg_cnt
                if dist_start:
                    average_cnt -= 1


        if msg_cnt >= msg_send_wait:  # 如果消息量大于等于接受范围，就把消息合起来发给文本AI
            msg_cnt = 0
            # msg_send_wait = random.randint(start_msg_wait, end_msg_wait)
            print("消息列表:\n" + temp_content)

            deepseek_return = deepseek_api_use(temp_content, deepseek_api_key)  # 获得deepseek的回复
            # print(deepseek_return)
            temp_content = ""

            if deepseek_return == "RFSRPLY_001":
                print("机器人不回答\n")
                calculate_dist()
                return

            # 如果已经回复了，就不主动提出问题，避免出现冲突的情况
            # reset_time()
            AI_content, sep, AI_emotion = deepseek_return.partition("/emotion/")

            send_split_messages(AI_content, receiver_name, cut_str)
            print("AI回复:" + AI_content.replace("/e/", " ") + "\n")

            process_emotion(AI_emotion)

        calculate_dist()




# 程序主入口
if __name__ == "__main__":
    robot_names = extract_names("Robot_Data\机器人信息.txt")
    sys.excepthook = handle_exception  # 设置全局异常处理
    emotion_id = get_path("\emotion")  # 得出当前文件夹中表情包的路径
    wx.AddListenChat(nickname=receiver_name, callback=on_message)  # 增加监听列表
    # 主循环，持续监听消息并处理自动任务
    while True:
        wx.StartListening()
        time.sleep(0.05)
        auto_send_task()
        time.sleep(0.05)