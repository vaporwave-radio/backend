import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from collections import deque
import modules_api


characters = {
    'Диоген': {
        'description': """
        Диоген, древнегреческий философ. В своих ответах используй глубокие размышления, думай о высоком, используй примеры из времен древней греции.
        """,
        'voice': 'kirill',
    },
    'Строитель': {
        'description': """
        Строитель, простой человек нашего времени. В своих ответах используй прямоту, думай приземленно, говори о жизненном.
        """,
        'voice': 'ermil',
    }
}

FOLDER = os.getcwd()

app = Flask(__name__)
CORS(app)
front_manager = None 

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
    if front_manager is None:
        return jsonify({"error": "Диалог не инициализирован"}), 400

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
  return modules_api.request_tts(voice, replica)

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
          Представь что персонажи ведут подкаст. Проведи диалог двух персонажей в размере 5 реплик на каждого.
          Первый персонаж - {characters[self.name]["description"]}.
          Второй персонаж - {characters[self.companion]["description"]}.
          Оформи каждую реплику в виде **Имя**: Реплика.
          """
          user_prompt = "Приводить диалог к логическому завершению не нужно."

      elif user_prompt == 'stop':
          system_prompt = f"""
          Представь что персонажи ведут подкаст. Проведи диалог двух персонажей в размере 5 реплик на каждого.
          Первый персонаж - {characters[self.name]["description"]}.
          Второй персонаж - {characters[self.companion]["description"]}.
          Оформи каждую реплику в виде **Имя**: Реплика.
          Часть уже прошедшего подкаста:
          {history_str}
          """
          user_prompt = "Приведи диалог к логическому завершению."

      else:
          system_prompt = f"""
          Представь что персонажи ведут подкаст. Проведи диалог двух персонажей в размере 5 реплик на каждого.
          Первый персонаж - {characters[self.name]["description"]}.
          Второй персонаж - {characters[self.companion]["description"]}.
          Оформи каждую реплику в виде **Имя**: Реплика.
          Часть уже прошедшего подкаста:
          {history_str}
          """

          if user_prompt == '':
              user_prompt = "Продолжай тему разговора. Приводить диалог к логическому завершению не нужно."
          else:
              user_prompt = f"Продолжи диалог, постепенно сменив тему на: {user_prompt}. Приводить диалог к логическому завершению не нужно."

      return request_LLM(system_prompt, user_prompt)

  def parse_response(self, response: str) -> list[dict]:
      parsed = []
      lines = response.strip().split("\n")
      for line in lines:
          if line.startswith("**") and "**" in line[2:]:
              try:
                  name_end = line.find("**", 2)
                  speaker = line[2:name_end]
                  text = line[name_end+2:].strip()
                  parsed.append({"speaker": speaker, "text": text})
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
      with open(f'audio/{id}.ogg', 'wb') as f:
        f.write(audio)
      return FOLDER + f'/audio/{id}.ogg'


class FrontManager:
    def __init__(self, character_a: str, character_b: str):
        self.turn = 0
        self.character_a = character_a
        self.character_b = character_b
        self.dialogue = Dialogue(character_a, character_b)
        self.sound_id = 0
        self.tts = Sound()
        self.audio_queue = deque(maxlen=10)

    def next_turn(self, topic: str = ''):
        print("____________________BLA___________________________")
        print(len(self.dialogue.history))
        if len(self.dialogue.history) < 20:
            print("here")
            self.dialogue.response(topic)
            print("and here")

        while self.turn < len(self.dialogue.history) and len(self.audio_queue) < 10:
            r = self.dialogue.history[self.turn]
            audio = self.tts.voice(r['speaker'], r['text'], self.turn)
            self.audio_queue.append({
                "turn": self.turn,
                "speaker": r['speaker'],
                "text": r['text'],
                "audio": audio
            })
            self.turn += 1

    def get_next(self):
        self.sound_id += 1
        if not self.audio_queue:
            self.generate_audio()
        return self.audio_queue.popleft() if self.audio_queue else None

    def inject_topic(self, new_topic: str):
        self.dialogue.history = self.dialogue.history[:self.sound_id]
        self.next_turn(new_topic)

    def start(self):
        self.next_turn('start')

    def end(self):
        self.next_turn('stop')


