import os
import requests

from dotenv import load_dotenv

load_dotenv()
cloud_folder = os.environ['cloud_folder']
token = os.environ['token']

headers = {'Authorization': 'Bearer ' + token}

# you can adjust llm parameters here:
llm_url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
llm = 'yandexgpt-lite'
llm_max_tokens = 1000
llm_temperature = 0.6
llm_stream = False

# tts
tts_url = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'

def request_llm(system_prompt: str, user_prompt: str):
    """
    Sends a request to YandexGPT model, returns the text answer.
    Args:
        system_prompt (str):
        user_prompt (str):
    Returns:
        str: The model answer
    """
    
    data = {}
    data['modelUri'] = f'gpt://{cloud_folder}/{llm}'
    data['completionOptions'] = {'stream': llm_stream, 'temperature': llm_temperature, 'maxTokens': llm_max_tokens}
    data['messages'] = [
        {"role": "system", "text": system_prompt}, 
        {"role": "user", "text": user_prompt}
    ]
    response = requests.post(llm_url, headers=headers, json=data).json()
    return response['result']['alternatives'][0]['message']['text']


def request_tts(text: str, voice: str):
    """
    Sends a text-to-speech synthesis request to Yandex SpeechKit and returns the audio content.
    Args:
        text (str): The text to be synthesized into speech.
        voice (str): The name of the voice to use for synthesis (e.g., 'alena', 'oksana', 'ermil'). The full voices list: https://yandex.cloud/ru/docs/speechkit/tts/voices
    Returns:
        bytes: The synthesized speech audio in OGG Opus format.
    Raises:
        Exception: If the request to Yandex SpeechKit fails.
    """

    data = {
        'text': text,
        'lang': 'ru-RU',
        'voice': voice,
        'folderId': cloud_folder,
        'format': 'oggopus',
        'sampleRateHertz': 48000,
    }
    response = requests.post(tts_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"TTS error: {response.status_code} {response.text}")


if __name__ == "__main__":
    INIT_PROMPT_SYS = 'Расскажи о заданной теме, приводя как можно более необычные аналогии'
    INIT_PROMPT_USR = 'Классические алгоритмы машинного обучения'
    text = request_llm(INIT_PROMPT_SYS, INIT_PROMPT_USR)
    print(text)

    audio = request_tts(text, 'jane')
    with open('output.ogg', 'wb') as f:
        f.write(audio)
    print("Аудиофайл успешно сохранён как output.ogg")
