# OpenAI-Compatible TTS API

这是一个基于 OpenAI API 规范的统一 TTS（文本转语音）服务，整合了 Edge-TTS 和 Nano-TTS 两个 TTS 系统。

## 项目特点

- **双 TTS 系统支持**：同时支持 Edge-TTS 和 Nano-TTS，自动路由到相应系统
- **OpenAI 兼容接口**：完全兼容 OpenAI 的 `/v1/audio/speech` 端点规范
- **智能重试和降级**：当 Nano-TTS 请求失败时自动重试，失败两次后降级到 Edge-TTS
- **SSE 流式支持**：支持 Server-Sent Events 实时音频推流
- **多格式支持**：支持 mp3、opus、aac、flac、wav、pcm 等多种音频格式
- **速度调节**：支持 0.25x 至 4.0x 的播放速度调整
- **免费使用**：Edge-TTS 基于 Microsoft Edge 的在线语音服务，完全免费

## 系统架构

项目采用统一入口设计，通过 `main.py` 整合两个 TTS 系统：

- **Edge-TTS**：使用带连字符的声音名称（如 `zh-CN-XiaoxiaoNeural`）
- **Nano-TTS**：使用不带连字符的声音名称（如 `DeepSeek`、`Kimi`）

系统会根据 `voice` 参数是否包含连字符自动路由到对应的 TTS 引擎。

## 快速开始

### 使用 Python 运行

1. 克隆仓库：
```bash
git clone https://github.com/travisvn/openai-edge-nano-tts.git
cd openai-edge-nano-tts
```

2. 安装依赖：
```bash
pip install uv
uv venv --python 3.12
.venv\Scripts\activate 
uv sync
```

3. 创建环境配置文件 `.env`：
```bash
cp .env.example .env
```

4. 启动服务：
```bash
python main.py
```

服务将在 `http://localhost:5050` 启动。

### 使用 Docker 运行

```bash
docker run -d -p 5050:5050 julienol/openai-edge-nano-tts:latest
```

## 环境变量配置

在 `.env` 文件中可以配置以下参数：

```env
API_KEY=your_api_key_here
PORT=5050

DEFAULT_VOICE=zh-CN-XiaoxiaoNeural
DEFAULT_RESPONSE_FORMAT=mp3
DEFAULT_SPEED=1.0

REQUIRE_API_KEY=True
REMOVE_FILTER=False
EXPAND_API=True
DETAILED_ERROR_LOGGING=True
```

## API 端点

### 1. 文本转语音 - `/v1/audio/speech`

**请求方式**：POST

**请求参数**：

- `input` (必填): 要转换为语音的文本，最多 4096 个字符
- `voice` (可选): 语音名称，默认为 `zh-CN-XiaoxiaoNeural`
  - Edge-TTS 声音：包含连字符，如 `zh-CN-XiaoxiaoNeural`、`en-US-JennyNeural`
  - Nano-TTS 声音：不含连字符，如 `DeepSeek`、`Kimi`、`zhipu`
- `model` (可选): TTS 模型，兼容 OpenAI 参数
- `response_format` (可选): 音频格式，可选值：`mp3`、`opus`、`aac`、`flac`、`wav`、`pcm`，默认 `mp3`
- `speed` (可选): 播放速度，范围 0.25 - 4.0，默认 1.0
- `stream` (可选): 是否使用 SSE 流式传输，设为 `true` 启用
- `stream_format` (可选): 流式格式，可选 `audio` 或 `sse`

**示例 1：使用 Edge-TTS（中文女声）**

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "你好，我是你的 AI 助手。",
    "voice": "zh-CN-XiaoxiaoNeural",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  --output speech.mp3
```

**示例 2：使用 Nano-TTS（DeepSeek 声音）**

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "这是使用 Nano-TTS 生成的语音。",
    "voice": "DeepSeek"
  }' \
  --output speech.mp3
```

**示例 3：SSE 流式传输**

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "这是流式传输的示例。",
    "voice": "zh-CN-XiaoxiaoNeural",
    "stream": true
  }'
```

**示例 4：直接播放（需要 ffplay）**

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "这将立即播放而不保存到文件。",
    "voice": "zh-CN-YunxiNeural"
  }' | ffplay -autoexit -nodisp -i -
```

### 2. 模型列表 - `/v1/models`

**请求方式**：GET

返回所有可用的 TTS 模型（声音）列表。

**示例**：

```bash
curl http://localhost:5050/v1/models
```

**响应示例**：

```json
{
  "object": "list",
  "data": [
    {
      "id": "zh-CN-XiaoxiaoNeural",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai-edge-nano-tts",
      "description": "中文女声 (晓晓)"
    },
    {
      "id": "DeepSeek",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai-nano-tts",
      "description": "（女生）DeepSeek"
    }
  ]
}
```

### 3. 其他兼容端点

- `POST /v1/audio/models` - 获取 TTS 模型列表（别名）
- `POST /v1/voices` - 获取指定语言的声音列表
- `POST /v1/voices/all` - 获取所有可用声音

## 智能重试机制

当请求 Nano-TTS 系统（voice 不包含连字符）时，系统会自动进行容错处理：

1. **第一次尝试**：正常调用 Nano-TTS
2. **失败重试**：如果第一次失败，自动重试一次
3. **智能降级**：如果两次都失败，自动切换到 Edge-TTS 使用默认声音 `zh-CN-XiaoxiaoNeural`

这确保了服务的高可用性，即使某个 TTS 系统出现问题，也能保证语音生成服务不中断。

## 可用声音列表

### Edge-TTS 声音（部分）

**中文声音**：
- `zh-CN-XiaoxiaoNeural` - 中文女声（晓晓）
- `zh-CN-YunxiNeural` - 中文男声（云希）
- `zh-CN-YunyangNeural` - 中文男声（云扬）
- `zh-CN-XiaoyiNeural` - 中文女声（晓伊）

**英文声音**：
- `en-US-JennyNeural` - 英文女声（Jenny）
- `en-US-GuyNeural` - 英文男声（Guy）
- `en-US-AriaNeural` - 英文女声（Aria）
- `en-US-DavisNeural` - 英文男声（Davis）

更多声音请查看 `voice.json` 文件。

### Nano-TTS 声音

- `DeepSeek` - 女生声音
- `Kimi` - 女生声音
- `zhipu` - 智谱清言（女生）
- `tongyi` - 通义千问（男声）
- `doubao` - 豆包（女生）
- `hunyuan` - 腾讯混元（男声）
- `wenxin` - 文心一言（男声）
- `MiniMax` - MiniMax（女生）
- `shangtang` - 商汤（女生）
- `baixiaoying` - 百小应（女生）
- `xunfei` - 讯飞星火（男声）
- `stepspark` - 阶跃星辰（女生）

## JavaScript 使用示例

```javascript
async function generateSpeech(text, voice = 'zh-CN-XiaoxiaoNeural') {
  const response = await fetch('http://localhost:5050/v1/audio/speech', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer your_api_key_here'
    },
    body: JSON.stringify({
      input: text,
      voice: voice,
      response_format: 'mp3'
    })
  });

  const audioBlob = await response.blob();
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);
  audio.play();
}

// 使用示例
generateSpeech('你好，世界！');
```

## SSE 流式传输示例（JavaScript）

```javascript
async function streamTTS(text) {
  const response = await fetch('http://localhost:5050/v1/audio/speech', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer your_api_key_here'
    },
    body: JSON.stringify({
      input: text,
      voice: 'zh-CN-XiaoxiaoNeural',
      stream: true
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const audioChunks = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));

        if (data.type === 'speech.audio.delta') {
          const audioData = atob(data.audio);
          const audioArray = new Uint8Array(audioData.length);
          for (let i = 0; i < audioData.length; i++) {
            audioArray[i] = audioData.charCodeAt(i);
          }
          audioChunks.push(audioArray);
        } else if (data.type === 'speech.audio.done') {
          console.log('语音合成完成', data.usage);
          
          // 合并所有音频块并播放
          const totalLength = audioChunks.reduce((sum, chunk) => sum + chunk.length, 0);
          const combinedArray = new Uint8Array(totalLength);
          let offset = 0;
          for (const chunk of audioChunks) {
            combinedArray.set(chunk, offset);
            offset += chunk.length;
          }

          const audioBlob = new Blob([combinedArray], { type: 'audio/mpeg' });
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          audio.play();
          return;
        }
      }
    }
  }
}

// 使用示例
streamTTS('这是流式传输的示例');
```

## 项目文件结构

```
openai-edge-nano-tts/
├── main.py                 # 统一入口，整合双 TTS 系统
├── voice.json             # 声音配置列表
├── app/                   # Edge-TTS 系统
│   ├── server.py         # Edge-TTS 服务器
│   ├── config.py         # 配置文件
│   ├── handle_text.py    # 文本处理
│   ├── tts_handler.py    # TTS 处理逻辑
│   └── utils.py          # 工具函数
├── nano-tts/             # Nano-TTS 系统
│   ├── app.py           # Nano-TTS 服务器
│   └── nano_tts/        # Nano-TTS 核心
├── requirements.txt      # Python 依赖
├── .env.example         # 环境变量示例
└── README.md           # 本文档
```

## 注意事项

1. **API Key**：`your_api_key_here` 仅用于兼容性，可以使用任意字符串
2. **网络要求**：Edge-TTS 需要访问 Microsoft 的在线服务
3. **FFmpeg**：如果需要使用 mp3 以外的音频格式，需要安装 ffmpeg
4. **端口配置**：默认端口为 5050，可通过环境变量 `PORT` 修改

## 故障排除

### 服务无法启动

检查端口是否被占用：
```bash
# Windows
netstat -ano | findstr :5050

# Linux/Mac
lsof -i :5050
```

### Nano-TTS 频繁失败

系统会自动降级到 Edge-TTS，但建议检查 Nano-TTS 服务是否正常运行。

### 音频格式转换失败

确保已安装 ffmpeg：
```bash
# Windows (使用 chocolatey)
choco install ffmpeg

# Linux
sudo apt-get install ffmpeg

# Mac
brew install ffmpeg
```

## 许可证

本项目基于 GNU General Public License v3.0 (GPL-3.0) 许可证，适用于个人使用。

## 贡献

欢迎提交 Pull Request 或报告 Issues！
