# app.py

from flask import Flask, request, Response, jsonify, render_template_string, stream_with_context
from flask_cors import CORS
from nano_tts import NanoAITTS
import threading
import time
import base64
import json

# --- 配置 ---
STATIC_API_KEY = "sk-123456"
CACHE_DURATION_SECONDS = 2 * 60 * 60

# --- 缓存管理器 ---
class ModelCache:
    def __init__(self, tts_engine):
        self._tts_engine = tts_engine
        self._cache = {}
        self._last_updated = 0
        self._lock = threading.Lock()

    def get_models(self):
        with self._lock:
            current_time = time.time()
            if not self._cache or (current_time - self._last_updated > CACHE_DURATION_SECONDS):
                print("缓存过期或为空，正在刷新模型列表...")
                try:
                    self._tts_engine.load_voices()
                    self._cache = {tag: info['name'] for tag, info in self._tts_engine.voices.items()}
                    self._last_updated = current_time
                    print(f"模型列表刷新成功，共找到 {len(self._cache)} 个模型。")
                except Exception as e:
                    print(f"刷新模型列表失败: {e}")
            return self._cache

# --- 初始化 ---
app = Flask(__name__)
CORS(app)  # 启用 CORS 支持

try:
    print("正在初始化 TTS 引擎...")
    tts_engine = NanoAITTS()
    print("TTS 引擎初始化完毕。")
    model_cache = ModelCache(tts_engine)
except Exception as e:
    print(f"FATAL: TTS 引擎初始化失败: {e}")
    tts_engine = None
    model_cache = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>纳米AI TTS - OpenAI 兼容接口</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 800px;
            width: 100%;
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .header p {
            opacity: 0.9;
            font-size: 14px;
        }

        .content {
            padding: 30px;
        }

        .section {
            margin-bottom: 25px;
        }

        .section-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            font-size: 14px;
            color: #555;
            margin-bottom: 8px;
            font-weight: 500;
        }

        input[type="text"],
        input[type="password"],
        textarea,
        select {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s;
            font-family: inherit;
        }

        /* 密码框容器样式 */
        .password-wrapper {
            position: relative;
            display: flex;
            align-items: center;
        }

        .password-wrapper input {
            padding-right: 45px;
        }

        .toggle-password {
            position: absolute;
            right: 12px;
            cursor: pointer;
            font-size: 20px;
            user-select: none;
            transition: opacity 0.2s;
        }

        .toggle-password:hover {
            opacity: 0.7;
        }

        input:focus,
        textarea:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        textarea {
            resize: vertical;
            min-height: 120px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 30px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .btn-secondary {
            background: #6c757d;
            margin-top: 10px;
        }

        .status {
            padding: 12px 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: none;
            align-items: center;
            gap: 10px;
        }

        .status.show {
            display: flex;
        }

        .status.info {
            background: #e3f2fd;
            color: #1976d2;
            border: 1px solid #90caf9;
        }

        .status.success {
            background: #e8f5e9;
            color: #388e3c;
            border: 1px solid #81c784;
        }

        .status.error {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #e57373;
        }

        .models-list {
            max-height: 300px;
            overflow-y: auto;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
        }

        .model-item {
            padding: 10px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s;
        }

        .model-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }

        .model-item.selected {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .model-id {
            font-weight: 600;
            font-size: 13px;
        }

        .model-name {
            font-size: 12px;
            opacity: 0.8;
        }

        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .audio-player {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
        }

        .audio-player.show {
            display: block;
        }

        audio {
            width: 100%;
            margin-top: 10px;
        }

        .char-count {
            text-align: right;
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }

        .api-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            font-size: 13px;
            line-height: 1.6;
            color: #555;
        }

        .api-info code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎙️ 纳米AI TTS</h1>
            <p>OpenAI 兼容接口 - 本地语音合成服务</p>
        </div>

        <div class="content">
            <!-- 状态提示 -->
            <div id="status" class="status"></div>

            <!-- 配置区域 -->
            <div class="section">
                <div class="section-title">⚙️ 服务配置</div>
                <div class="form-group">
                    <label>API 地址</label>
                    <input type="text" id="apiBase" value="" placeholder="">
                </div>
                <div class="form-group">
                    <label>API 密钥</label>
                    <div class="password-wrapper">
                        <input type="password" id="apiKey" value="sk-nanoai-your-secret-key" placeholder="sk-nanoai-your-secret-key">
                        <span class="toggle-password" onclick="togglePasswordVisibility()" id="toggleIcon">👁️</span>
                    </div>
                </div>
                <button class="btn btn-secondary" onclick="loadModels()">
                    <span id="loadModelsIcon">🔄</span>
                    <span>加载模型列表</span>
                </button>
            </div>

            <!-- 模型选择 -->
            <div class="section">
                <div class="section-title">🎵 选择声音模型</div>
                <div id="modelsList" class="models-list">
                    <div style="text-align: center; color: #999; padding: 20px;">
                        点击上方"加载模型列表"按钮获取可用声音
                    </div>
                </div>
            </div>

            <!-- 文本输入 -->
            <div class="section">
                <div class="section-title">📝 输入文本</div>
                <div class="form-group">
                    <textarea id="textInput" placeholder="请输入要转换为语音的文本..." oninput="updateCharCount()"></textarea>
                    <div class="char-count" id="charCount">字符数: 0</div>
                </div>
            </div>

            <!-- 生成按钮 -->
            <button class="btn" id="generateBtn" onclick="generateSpeech()">
                <span>🎵</span>
                <span>生成语音</span>
            </button>

            <!-- 音频播放器 -->
            <div id="audioPlayer" class="audio-player">
                <div class="section-title">🔊 生成的语音</div>
                <audio id="audio" controls preload="metadata"></audio>
                <button class="btn btn-secondary" onclick="downloadAudio()" style="margin-top: 10px;">
                    <span>💾</span>
                    <span>下载音频</span>
                </button>
            </div>

            <!-- API 信息 -->
            <div class="section" style="margin-top: 30px;">
                <div class="section-title">ℹ️ API 使用说明</div>
                <div class="api-info">
                    <p><strong>接口地址：</strong> <code>POST /v1/audio/speech</code></p>
                    <p><strong>请求示例：</strong></p>
                    <pre style="background: #e9ecef; padding: 10px; border-radius: 5px; margin-top: 5px; overflow-x: auto;">curl http://127.0.0.1:5001/v1/audio/speech \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "DeepSeek", "input": "测试文本"}' \\
  --output speech.mp3</pre>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedModel = null;
        let currentAudioBlob = null;
        let currentAudioUrl = null;

        function updateCharCount() {
            const text = document.getElementById('textInput').value;
            document.getElementById('charCount').textContent = `字符数: ${text.length}`;
        }

        function togglePasswordVisibility() {
            const apiKeyInput = document.getElementById('apiKey');
            const toggleIcon = document.getElementById('toggleIcon');
            
            if (apiKeyInput.type === 'password') {
                apiKeyInput.type = 'text';
                toggleIcon.textContent = '🔓';
                toggleIcon.style.opacity = '1';
            } else {
                apiKeyInput.type = 'password';
                toggleIcon.textContent = '👁️';
                toggleIcon.style.opacity = '0.6';
            }
        }

        function showStatus(message, type = 'info') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status ${type} show`;
            
            if (type === 'success' || type === 'error') {
                setTimeout(() => {
                    status.classList.remove('show');
                }, 5000);
            }
        }

        async function loadModels() {
            const apiBase = document.getElementById('apiBase').value;
            const btn = event.target;
            const icon = document.getElementById('loadModelsIcon');
            
            btn.disabled = true;
            icon.innerHTML = '<span class="spinner"></span>';
            showStatus('正在加载模型列表...', 'info');

            try {
                const response = await fetch(`${apiBase}/v1/models`);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                const models = data.data || [];

                if (models.length === 0) {
                    throw new Error('未找到可用模型');
                }

                renderModels(models);
                showStatus(`✓ 成功加载 ${models.length} 个模型`, 'success');
            } catch (error) {
                showStatus(`❌ 加载失败: ${error.message}`, 'error');
                console.error('加载模型失败:', error);
            } finally {
                btn.disabled = false;
                icon.textContent = '🔄';
            }
        }

        function renderModels(models) {
            const container = document.getElementById('modelsList');
            container.innerHTML = models.map(model => `
                <div class="model-item" onclick="selectModel('${model.id}')">
                    <div>
                        <div class="model-id">${model.id}</div>
                        <div class="model-name">${model.description || model.id}</div>
                    </div>
                    <div style="font-size: 20px;">🎤</div>
                </div>
            `).join('');
        }

        function selectModel(modelId) {
            selectedModel = modelId;
            document.querySelectorAll('.model-item').forEach(item => {
                item.classList.remove('selected');
            });
            event.currentTarget.classList.add('selected');
            showStatus(`✓ 已选择模型: ${modelId}`, 'success');
        }

        // 清理旧的音频URL
        function cleanupAudioUrl() {
            if (currentAudioUrl) {
                try {
                    URL.revokeObjectURL(currentAudioUrl);
                } catch (e) {
                    console.warn('清理音频URL失败:', e);
                }
                currentAudioUrl = null;
            }
        }

        async function generateSpeech() {
            const apiBase = document.getElementById('apiBase').value;
            const apiKey = document.getElementById('apiKey').value;
            const textInput = document.getElementById('textInput').value.trim();
            const btn = document.getElementById('generateBtn');

            if (!selectedModel) {
                showStatus('❌ 请先选择一个声音模型', 'error');
                return;
            }

            if (!textInput) {
                showStatus('❌ 请输入要转换的文本', 'error');
                return;
            }

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span><span>生成中...</span>';
            showStatus('正在生成语音...', 'info');

            // 清理旧的音频资源
            cleanupAudioUrl();

            try {
                const response = await fetch(`${apiBase}/v1/audio/speech`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${apiKey}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        model: selectedModel,
                        input: textInput
                    })
                });

                if (!response.ok) {
                    let errorMsg = `HTTP ${response.status}`;
                    try {
                        const errorData = await response.json();
                        errorMsg = errorData.error || errorMsg;
                    } catch (e) {
                        // 如果无法解析JSON错误，使用默认错误消息
                    }
                    throw new Error(errorMsg);
                }

                // 获取音频数据
                const audioBlob = await response.blob();
                
                // 验证blob类型
                if (!audioBlob.type.startsWith('audio/')) {
                    console.warn('警告: 返回的数据可能不是音频格式:', audioBlob.type);
                }
                
                currentAudioBlob = audioBlob;
                
                // 创建Blob URL - 兼容老旧浏览器
                try {
                    currentAudioUrl = (window.URL || window.webkitURL).createObjectURL(audioBlob);
                } catch (e) {
                    throw new Error('浏览器不支持创建音频URL，请升级浏览器');
                }
                
                const audioElement = document.getElementById('audio');
                
                // 清理旧的audio source
                audioElement.pause();
                audioElement.src = '';
                audioElement.load();
                
                // 设置新的音频源
                audioElement.src = currentAudioUrl;
                
                // 添加错误处理
                audioElement.onerror = function(e) {
                    console.error('音频加载错误:', e);
                    showStatus('❌ 音频播放失败，请尝试下载后播放', 'error');
                };
                
                // 音频加载完成后的处理
                audioElement.onloadedmetadata = function() {
                    console.log('音频元数据加载完成');
                };
                
                // 确保音频可以播放
                audioElement.load();
                
                document.getElementById('audioPlayer').classList.add('show');
                showStatus('✓ 语音生成成功！', 'success');
                
                // 尝试自动播放（某些浏览器可能会阻止）
                try {
                    const playPromise = audioElement.play();
                    if (playPromise !== undefined) {
                        playPromise.catch(function(error) {
                            console.warn('自动播放被阻止:', error);
                            showStatus('✓ 语音已生成，请手动点击播放', 'success');
                        });
                    }
                } catch (e) {
                    console.warn('播放失败:', e);
                }
                
            } catch (error) {
                showStatus(`❌ 生成失败: ${error.message}`, 'error');
                console.error('生成语音失败:', error);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span>🎵</span><span>生成语音</span>';
            }
        }

        function downloadAudio() {
            if (!currentAudioBlob) {
                showStatus('❌ 没有可下载的音频', 'error');
                return;
            }

            try {
                const url = (window.URL || window.webkitURL).createObjectURL(currentAudioBlob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `nanoai_speech_${Date.now()}.mp3`;
                document.body.appendChild(a);
                a.click();
                
                // 延迟清理，确保下载开始
                setTimeout(() => {
                    document.body.removeChild(a);
                    (window.URL || window.webkitURL).revokeObjectURL(url);
                }, 100);
                
                showStatus('✓ 音频下载成功', 'success');
            } catch (error) {
                console.error('下载失败:', error);
                showStatus('❌ 下载失败: ' + error.message, 'error');
            }
        }

        // 页面卸载时清理资源
        window.addEventListener('beforeunload', function() {
            cleanupAudioUrl();
        });

        // 页面加载时初始化
        window.addEventListener('load', () => {
            // 设置初始密码图标透明度
            document.getElementById('toggleIcon').style.opacity = '0.6';
        });
    </script>
</body>
</html>
"""


# 路由：显示 HTML 页面
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# --- API 端点 ---
@app.route('/v1/audio/speech', methods=['POST'])
def create_speech():
    if not tts_engine:
        return jsonify({"error": "TTS engine is not available due to initialization failure."}), 503

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header is missing or invalid"}), 401
    
    provided_key = auth_header.split(' ')[1]
    if provided_key != STATIC_API_KEY:
        return jsonify({"error": "Invalid API Key"}), 401

    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    model_id = data.get('model') or data.get('voice')
    text_input = data.get('input')

    if not model_id or not text_input:
        return jsonify({"error": "Missing required fields: 'model' and 'input'"}), 400

    available_models = model_cache.get_models()
    if model_id not in available_models:
        return jsonify({"error": f"Model '{model_id}' not found. Please use the /v1/models endpoint to see available models."}), 404

    # --- 参数处理 ---
    # 兼容 speed 和 pitch 参数（目前忽略）
    speed = data.get('speed')
    pitch = data.get('pitch')
    
    # 处理 cleaning_options
    cleaning_options = data.get('cleaning_options', {})
    custom_keywords = cleaning_options.get('custom_keywords', '')
    
    # 文本清理逻辑
    if custom_keywords:
        keywords = [k.strip() for k in custom_keywords.split(',') if k.strip()]
        for keyword in keywords:
            text_input = text_input.replace(keyword, '')
            
    # 处理 stream 参数
    stream = data.get('stream', False)

    print(f"收到请求: model='{model_id}', input='{text_input[:30]}...', stream={stream}")

    try:
        if stream:
            # 流式响应
            upstream_response = tts_engine.get_audio(text_input, voice=model_id, stream=True)
            
            def generate():
                # 发送初始 SSE 事件（可选，模拟 OpenAI 格式）
                # yield f"data: {json.dumps({'choices': [{'delta': {'content': ''}}]})}\n\n"
                
                chunk_size = 4096 # 每次读取的块大小
                while True:
                    chunk = upstream_response.read(chunk_size)
                    if not chunk:
                        break
                    
                    # 将音频块编码为 base64
                    audio_base64 = base64.b64encode(chunk).decode('utf-8')
                    
                    # 构造 SSE 事件数据
                    event_data = {
                        "type": "speech.audio.delta",
                        "audio": audio_base64
                    }
                    
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                # 发送结束标记（如果需要）
                # yield "data: [DONE]\n\n"

            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        else:
            # 非流式响应
            audio_data = tts_engine.get_audio(text_input, voice=model_id, stream=False)
            return Response(audio_data, mimetype='audio/mpeg')

    except Exception as e:
        print(f"TTS 引擎错误: {e}")
        return jsonify({"error": f"Failed to generate audio: {e}"}), 500

@app.route('/v1/models', methods=['GET'])
def list_models():
    if not model_cache:
        return jsonify({"error": "TTS engine is not available due to initialization failure."}), 503

    available_models = model_cache.get_models()
    
    models_data = [
        {
            "id": model_id,
            "object": "model",
            "created": int(model_cache._last_updated),
            "owned_by": "nanoai",
            "description": model_name
        }
        for model_id, model_name in available_models.items()
    ]
    return jsonify({"object": "list", "data": models_data})

@app.route('/health', methods=['GET'])
def health_check():
    if tts_engine and model_cache:
        return jsonify({"status": "ok", "models_in_cache": len(model_cache.get_models())}), 200
    else:
        return jsonify({"status": "error", "message": "TTS engine not initialized"}), 503

# --- 启动服务 ---
if __name__ == '__main__':
    if tts_engine:
        print("正在预热模型缓存...")
        model_cache.get_models()
        print("服务准备就绪。")
        app.run(host='0.0.0.0', port=5050, debug=False)
    else:
        print("无法启动 Flask 服务，因为 TTS 引擎初始化失败。")