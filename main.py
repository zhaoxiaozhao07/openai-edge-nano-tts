import sys
import os
import json
from flask import Flask, request, jsonify, Response, render_template_string
from flask_cors import CORS

# Add directories to sys.path to allow imports
# We add 'app' directory to path so we can import 'server' and its dependencies (config, handle_text, etc.)
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
# We add 'nano-tts' directory to path so we can import 'app' (as nano_app) and 'nano_tts'
sys.path.append(os.path.join(os.path.dirname(__file__), 'nano-tts'))

# Import the existing modules
# Note: These imports will execute the module-level code in those files, 
# including creating their own Flask app instances (which we will ignore)
# and initializing their TTS engines.
try:
    import server as existing_server
    print("Successfully imported existing openai-edge-tts server module.")
except ImportError as e:
    print(f"Error importing existing server: {e}")
    sys.exit(1)

try:
    import app as nano_server
    print("Successfully imported nano-tts app module.")
except ImportError as e:
    print(f"Error importing nano-tts app: {e}")
    sys.exit(1)

# Initialize the unified Flask app
app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    # Serve the nano-tts UI as the main UI, as it's the only one with a web interface
    return nano_server.index()

@app.route('/v1/audio/speech', methods=['POST'])
def create_speech():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        # Clean inputs: remove leading/trailing whitespace
        if isinstance(data.get('voice'), str):
            data['voice'] = data['voice'].strip()
        if isinstance(data.get('model'), str):
            data['model'] = data['model'].strip()

        # OpenAI API compatibility: 
        # If 'voice' is provided, it takes precedence and should be treated as the model ID
        # because standard OpenAI clients send {"model": "tts-1", "voice": "target_voice"}
        if data.get('voice'):
            data['model'] = data.get('voice')
            
        voice = data.get('voice') or data.get('model')
        
        if not voice:
            return jsonify({"error": "Missing 'voice' or 'model' parameter"}), 400

        # Routing logic
        if '-' in voice:
            # Route to existing openai-edge-tts (no retry needed)
            print(f"Routing to openai-edge-tts for voice: {voice}")
            return existing_server.text_to_speech()
        else:
            # Route to nano-tts with retry and fallback logic
            print(f"Routing to nano-tts for voice: {voice}")
            
            # First attempt
            try:
                response = nano_server.create_speech()
                # Check if response is successful (status code 200-299)
                if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                    return response
                elif isinstance(response, tuple) and len(response) > 1:
                    # Handle (response, status_code) tuple
                    if 200 <= response[1] < 300:
                        return response
                else:
                    # Not a tuple, assume it's successful if no exception
                    return response
            except Exception as e:
                print(f"First nano-tts attempt failed: {e}")
            
            # Second attempt (retry)
            print(f"Retrying nano-tts for voice: {voice}")
            try:
                response = nano_server.create_speech()
                # Check if response is successful
                if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                    return response
                elif isinstance(response, tuple) and len(response) > 1:
                    if 200 <= response[1] < 300:
                        return response
                else:
                    return response
            except Exception as e:
                print(f"Second nano-tts attempt failed: {e}")
            
            # Fallback to edge-tts with default voice
            print(f"Falling back to edge-tts with default voice: zh-CN-XiaoxiaoNeural")
            # Modify request data to use edge-tts default voice
            original_voice = voice
            data['voice'] = 'zh-CN-XiaoxiaoNeural'
            # Update the request context with modified data
            from flask import g
            g._original_voice = original_voice
            
            return existing_server.text_to_speech()
            
    except Exception as e:
        print(f"Error in unified dispatch: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/v1/models', methods=['GET'])
def list_models():
    """
    Pseudo endpoint that reads voice.json and returns it as a model list.
    This provides a simple, consistent model list from the centralized voice configuration.
    """
    try:
        # Read voice.json from the project root
        voice_json_path = os.path.join(os.path.dirname(__file__), 'voice.json')
        with open(voice_json_path, 'r', encoding='utf-8') as f:
            voices = json.load(f)
        
        # Convert voice entries to OpenAI-compatible model format
        models = []
        for voice in voices:
            model_name = voice.get("model_name")
            
            # Determine owned_by based on whether model_name contains '-'
            # This matches the routing logic in /v1/audio/speech
            owned_by = "openai-edge-tts" if '-' in model_name else "openai-nano-tts"
            
            model = {
                "id": model_name,
                "object": "model",
                "created": 1677610602,  # Fake timestamp for compatibility
                "owned_by": owned_by
            }
            # Optionally add the label as description if needed
            if "label" in voice:
                model["description"] = voice["label"]
            
            models.append(model)
        
        return jsonify({"object": "list", "data": models})
        
    except Exception as e:
        print(f"Error loading voice.json: {e}")
        # Fallback to empty list on error
        return jsonify({"object": "list", "data": []})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5050))
    print(f"Unified TTS Server running on port {port}")
    app.run(host='0.0.0.0', port=port)
