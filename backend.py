import os
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
from collections import deque
import modules_api

characters = {
    'Диоген': {
        'description': "Диоген, древнегреческий философ. В своих ответах используй глубокие размышления, думай о высоком, используй примеры из времен древней греции.",
        'voice': 'ermil',
    },
    'Строитель': {
        'description': "Строитель, простой человек нашего времени. В своих ответах используй прямоту, думай приземленно, говори о жизненном.",
        'voice': 'zahar',
    }
}

FOLDER = os.getcwd()
AUDIO_FOLDER = os.path.join(FOLDER, 'static', 'audio')
os.makedirs(AUDIO_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)
front_manager = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/audio/<path:filename>')
def audio_file(filename):
    return send_from_directory(AUDIO_FOLDER, filename)

@app.route('/signal', methods=['POST'])
def handle_signal():
    global front_manager
    data = request.get_json()
    if not data or 'type' not in data:
        return jsonify({'error': 'Missing type in request'}), 400

    signal_type = data['type']
    if signal_type == 'start':
        character_a = data.get('characterA', 'Диоген')
        character_b = data.get('characterB', 'Строитель')
        front_manager = FrontManager(character_a, character_b)
        front_manager.start()
    elif signal_type == 'stop' and front_manager:
        front_manager.end()
        front_manager = None
    else:
        return jsonify({'error': 'Invalid signal type'}), 400

    return jsonify({'status': 'ok'})

@app.route("/messages", methods=["GET"])
def get_audio():
    global front_manager
    if front_manager is None:
        return jsonify({"error": "Диалог не инициализирован"}), 400
    if front_manager.END and front_manager.turn - front_manager.END_turn == 10:
        front_manager = None
    data = front_manager.get_next()
    if data is None:
        return jsonify({"status": "пусто"}), 204

    return jsonify({
        "audioUrl": data["audio"],
        "text": data["text"],
        "speaker": data["speaker"]
    })

@app.post("/send-topic")
def inject_topic():
    data = request.get_json()
    topic = data.get("topic", "")
    if front_manager:
        front_manager.inject_topic(topic)
    return jsonify({"status": "ok"})

def start():
    global front_manager
    character_a = request.json.get("character_a", "Диоген")
    character_b = request.json.get("character_b", "Строитель")
    front_manager = FrontManager(character_a, character_b)
    front_manager.start()
    return 204

def stop():
    if front_manager:
        front_manager.end()
    return 204

def request_LLM(system_prompt: str, user_prompt: str) -> str:
    return modules_api.request_llm(system_prompt, user_prompt)

def request_TTS(voice: str, replica: str) -> bytes:
    return modules_api.request_tts(replica, voice)

def request_from_front():
    return ''

class Dialogue:
    def __init__(self, name: str, companion: str):
        self.name = name
        self.companion = companion
        self.history = []

    def call_llm_api(self, user_prompt: str) -> str:
        history_str = '\n'.join(self.history)

        if user_prompt == 'start':
            system_prompt = f"""
                Представь что персонажи ведут подкаст. Проведи диалог двух персонажей в размере 5 реплик на каждого.\n
                Первый персонаж - {characters[self.name]["description"]}\n
                Второй персонаж - {characters[self.companion]["description"]}\n
                Оформи каждую реплику в виде **Имя**: Реплика.\n
            """
            user_prompt = """
            Приводить диалог к логическому завершению не нужно.
            """

        elif user_prompt == 'stop':
            system_prompt = f"""
                Представь что персонажи ведут подкаст. Проведи диалог двух персонажей в размере 5 реплик на каждого.\n
                Первый персонаж - {characters[self.name]["description"]}.\n
                Второй персонаж - {characters[self.companion]["description"]}.\n
                Оформи каждую реплику в виде **Имя**: Реплика.\n
                Часть уже прошедшего подкаста: \n""" + \
                '\n'.join([f'{x[0]}: {x[1]}' for x in self.history])
            user_prompt = """
            Приведи диалог к логическому завершению.
            """

        else:
            system_prompt = f"""
                Представь что персонажи ведут подкаст. Проведи диалог двух персонажей в размере 5 реплик на каждого.\n
                Первый персонаж - {characters[self.name]["description"]}.\n
                Второй персонаж - {characters[self.companion]["description"]}.\n
                Оформи каждую реплику в виде **Имя**: Реплика.\n
                Часть уже прошедшего подкаста: \n""" + \
                '\n'.join([f'{x[0]}: {x[1]}' for x in self.history])

        if user_prompt == '':
            user_prompt = "Продолжай тему разговора. Приводить диалог к логическому завершению не нужно."
        else:
            user_prompt = f"Продолжи диалог, постепенно сменив тему на: {user_prompt}. Приводить диалог к логическому завершению не нужно."

        return request_LLM(system_prompt, user_prompt)

    def parse_response(self, response: str) -> list[dict]:
        parsed = []
        lines = response.strip().split("\n")

        for line in lines:
            line_clean = line.strip()
            if line_clean.startswith("**") and "**" in line_clean[2:]:
                try:
                    name_end = line_clean.find("**", 2)
                    speaker = line_clean[2:name_end]
                    if speaker[-1] == ":":
                        speaker = speaker[:-1]
                    text = line_clean[name_end+2:].strip()
                    parsed.append((speaker, text))
                except Exception:
                    continue
        return parsed

    def response(self, user_prompt: str):
        self.history += self.parse_response(self.call_llm_api(user_prompt))

class Sound:
    def __init__(self):
        pass

    def voice(self, speaker_name: str, text: str, id: int) -> str:
        audio = request_TTS(characters[speaker_name]['voice'], text)
        audio_path = os.path.join(AUDIO_FOLDER, f'{id}.ogg')
        with open(audio_path, 'wb') as f:
            f.write(audio)
        return f'/audio/{id}.ogg'

class FrontManager:
    def __init__(self, character_a: str, character_b: str):
        self.turn = 0
        self.character_a = character_a
        self.character_b = character_b
        self.dialogue = Dialogue(character_a, character_b)
        self.sound_id = 0
        self.tts = Sound()
        self.audio_queue = deque(maxlen=10)
        self.END = False
        self.END_turn = 0

    def next_turn(self, topic: str = ''):
        if topic == 'stop':
            self.dialogue.response(topic)
            self.END = True
        if not self.END:
            if len(self.dialogue.history) < 20:
                self.dialogue.response(topic)
        if self.END and self.END_turn == 0:
            self.END_turn = self.turn
        elif self.END and self.turn - self.END_turn == 10:
            return
        while self.turn < len(self.dialogue.history) and len(self.audio_queue) < 10:
            r = self.dialogue.history[self.turn]
            audio = self.tts.voice(r[0], r[1], self.turn)
            self.audio_queue.append({
                "turn": self.turn,
                "speaker": r[0],
                "text": r[1],
                "audio": audio
            })
            self.turn += 1

    def get_next(self):
        self.sound_id += 1
        if not self.audio_queue:
            self.next_turn()
        return self.audio_queue.popleft() if self.audio_queue else None

    def inject_topic(self, new_topic: str):
        self.dialogue.history = self.dialogue.history[:self.sound_id]
        self.next_turn(new_topic)

    def start(self):
        self.next_turn('start')

    def end(self):
        self.next_turn('stop')

if __name__ == '__main__':
    app.run(debug=True)
