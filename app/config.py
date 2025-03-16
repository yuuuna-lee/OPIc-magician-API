import os
from g4f.client import Client as G4FClient
from gradio_client import Client as GradioClient
from kiwipiepy import Kiwi

# 공통 클라이언트 초기화
g4f_client = G4FClient(api_key="not needed")  # GPT 모델용
stt_client = GradioClient("mindspark121/Whisper-STT")  # STT 모델용
tts_client = GradioClient("https://k2-fsa-text-to-speech.hf.space")  # TTS 모델용
model_client = GradioClient("k2-fsa/text-to-speech")  # 모델 목록 클라이언트

# Kiwi 형태소 분석기 초기화
kiwi = Kiwi()

# 설정값
GPT_MODEL = "gpt-4o-mini"
JS_PATH = "./app/assets/Questions.js"
