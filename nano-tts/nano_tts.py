# nano_tts.py

import urllib.request
import urllib.parse
import hashlib
import json
import os
from datetime import datetime
import random
import time

class NanoAITTS:
    def __init__(self):
        self.name = '纳米AI'
        self.id = 'bot.n.cn'
        self.author = 'TTS Server'
        self.icon_url = 'https://bot.n.cn/favicon.ico'
        self.version = 2
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        self.voices = {}
        self.load_voices()
    
    def md5(self, msg):
        """MD5 哈希函数"""
        return hashlib.md5(msg.encode('utf-8')).hexdigest()
    
    def _e(self, nt):
        """生成哈希值"""
        HASH_MASK_1 = 268435455
        HASH_MASK_2 = 266338304
        
        at = 0
        for i in range(len(nt) - 1, -1, -1):
            st = ord(nt[i])
            at = ((at << 6) & HASH_MASK_1) + st + (st << 14)
            it = at & HASH_MASK_2
            if it != 0:
                at = at ^ (it >> 21)
        return at
    
    def generate_unique_hash(self):
        """生成唯一哈希"""
        lang = 'zh-CN'
        app_name = "chrome"
        ver = 1.0
        platform = "Win32"
        width = 1920
        height = 1080
        color_depth = 24
        referrer = "https://bot.n.cn/chat"
        
        nt = f"{app_name}{ver}{lang}{platform}{self.ua}{width}x{height}{color_depth}{referrer}"
        at = len(nt)
        it = 1
        while it:
            nt += str(it ^ at)
            it -= 1
            at += 1
        
        return (round(random.random() * 2147483647) ^ self._e(nt)) * 2147483647
    
    def generate_mid(self):
        """生成 MID"""
        domain = "https://bot.n.cn"
        rt = str(self._e(domain)) + str(self.generate_unique_hash()) + str(int(time.time() * 1000) + random.random() + random.random())
        formatted_rt = rt.replace('.', 'e')[:32]
        return formatted_rt
    
    def get_iso8601_time(self):
        """获取 ISO8601 时间格式"""
        now = datetime.now()
        return now.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    
    def get_headers(self):
        """生成请求头"""
        device = "Web"
        ver = "1.2"
        timestamp = self.get_iso8601_time()
        access_token = self.generate_mid()
        zm_ua = self.md5(self.ua)
        
        zm_token_str = f"{device}{timestamp}{ver}{access_token}{zm_ua}"
        zm_token = self.md5(zm_token_str)
        
        return {
            'device-platform': device,
            'timestamp': timestamp,
            'access-token': access_token,
            'zm-token': zm_token,
            'zm-ver': ver,
            'zm-ua': zm_ua,
            'User-Agent': self.ua
        }
    
    def http_get(self, url, headers):
        """使用标准库发送 GET 请求"""
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            raise Exception(f"HTTP GET 请求失败: {e}")
    
    def http_post(self, url, data, headers, stream=False):
        """使用标准库发送 POST 请求"""
        data_bytes = data.encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
        try:
            response = urllib.request.urlopen(req, timeout=30)
            if stream:
                return response
            with response as res:
                return res.read()
        except Exception as e:
            raise Exception(f"HTTP POST 请求失败: {e}")
    
    def load_voices(self):
        """加载声音列表"""
        filename = 'robots.json'
        
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                response_text = self.http_get('https://bot.n.cn/api/robot/platform', self.get_headers())
                data = json.loads(response_text)
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 清空旧的声音列表
            self.voices.clear()
            for item in data['data']['list']:
                self.voices[item['tag']] = {
                    'name': item['title'],
                    'iconUrl': item['icon']
                }
        except Exception as e:
            print(f"加载声音列表失败: {e}")
            self.voices.clear()
            # 如果网络请求失败，添加默认选项
            self.voices['DeepSeek'] = {'name': 'DeepSeek (默认)', 'iconUrl': ''}
    
    def get_audio(self, text, voice='DeepSeek', stream=False):
        """获取音频"""
        url = f'https://bot.n.cn/api/tts/v1?roleid={voice}'
        
        headers = self.get_headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        form_data = f'&text={urllib.parse.quote(text)}&audio_type=mp3&format=stream'
        
        try:
            response_data = self.http_post(url, form_data, headers, stream=stream)
            
            if stream:
                return response_data
            
            # 检查是否返回了 JSON 错误信息
            if response_data.startswith(b'{'):
                try:
                    error_json = json.loads(response_data)
                    if 'msg' in error_json and error_json['msg'] == 'Fail':
                         # 尝试解析更详细的错误原因
                        reason = error_json.get('data', {}).get('reason', '')
                        raise Exception(f"上游 API 错误: {reason or error_json}")
                    else:
                        # 可能是其他类型的 JSON 响应，打印警告但继续（或者也抛出异常）
                        print(f"警告: 上游返回了 JSON 数据而不是音频: {response_data[:100]}")
                        # 如果确定不是音频，可以抛出异常
                        # raise Exception(f"上游 API 返回错误: {response_data.decode('utf-8', errors='ignore')}")
                except json.JSONDecodeError:
                    pass # 不是 JSON，继续当作音频处理

            return response_data
        except Exception as e:
            print(f"获取音频失败: {e}")
            raise e