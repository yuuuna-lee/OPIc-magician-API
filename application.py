from g4f.client import Client as G4FClient
from flask import Flask, request, jsonify
from flask_cors import CORS
from gradio_client import Client as GradioClient, handle_file
import os
import base64
import random
import tempfile
import time

# import sounddevice as sd
# import soundfile as sf
import numpy as np
import threading
import queue
from kiwipiepy import Kiwi
from collections import Counter
import re

app = Flask(__name__)
CORS(
    app,
    resources={
        r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173", "*"]}
    },
)

g4f_client = G4FClient(api_key="not needed")  # GPT 모델용
stt_client = GradioClient(
    "mindspark121/Whisper-STT",
    hf_token=None,  # Hugging Face 토큰이 있다면 여기에 추가
)
audio_queue = queue.Queue()
recording = False

# 먼저 사용 가능한 모델 목록을 가져오는 클라이언트
model_client = GradioClient("k2-fsa/text-to-speech")

# TTS 처리를 위한 클라이언트
tts_client = GradioClient("https://k2-fsa-text-to-speech.hf.space")  # TTS 모델용

# Kiwi 형태소 분석기 초기화
kiwi = Kiwi()


def translate_to_english(text):
    try:
        response = g4f_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator. Translate the given Korean text to natural English, maintaining the same meaning and nuance.",
                },
                {"role": "user", "content": f"Translate this to English: {text}"},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def load_questions_from_js():
    js_path = "./assets/Questions.js"
    try:
        print("Attempting to load questions from:", js_path)
        with open(js_path, "r", encoding="utf-8") as file:
            content = file.read()
            print("\nFile content preview:")
            print(content[:200])  # 파일 내용 앞부분 출력
            
            # JavaScript 객체에서 서베이 배열 찾기
            survey_start = content.find("서베이")  # ':' 제거
            if survey_start == -1:
                print("Could not find '서베이' in the file")
                return []

            # 배열 시작 찾기
            array_start = content.find("[", survey_start)
            if array_start == -1:
                print("Could not find opening bracket")
                return []
                
            array_start += 1  # Skip the opening bracket
            
            # 괄호 매칭을 사용하여 정확한 끝 위치 찾기
            bracket_count = 1
            array_end = array_start
            
            while bracket_count > 0 and array_end < len(content):
                if content[array_end] == "[":
                    bracket_count += 1
                elif content[array_end] == "]":
                    bracket_count -= 1
                array_end += 1
            
            questions_str = content[array_start:array_end-1]
            
            # 각 질문을 분리 (쌍따옴표로 둘러싸인 문자열 추출)
            questions = re.findall(r'"([^"]+)"', questions_str)
            
            # 주석과 빈 문자열 제거
            questions = [q.strip() for q in questions if q.strip() and not q.strip().startswith("//")]
            
            print(f"Total questions loaded: {len(questions)}")
            return questions
            
    except Exception as e:
        print(f"Error loading questions: {e}")
        return []


def audio_callback(indata, frames, time, status):
    if recording:
        audio_queue.put(indata.copy())


# def record_audio():
#     with sd.InputStream(callback=audio_callback, channels=1, samplerate=16000):
#         while recording:
#             sd.sleep(100)


@app.route("/analyze-text", methods=["POST"])
def analyze_text():
    data = request.json
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # 형태소 분석 및 품사 태깅
    pos_list = kiwi.analyze(text)[0][0]  # 첫 번째 분석 결과의 형태소 분석 결과

    # 품사별 단어 카운팅
    word_count_by_pos = {}
    for token in pos_list:
        pos = token.tag  # 품사
        word = token.form  # 단어

        if pos not in word_count_by_pos:
            word_count_by_pos[pos] = Counter()
        word_count_by_pos[pos][word] += 1

    # 각 품사별 상위 단어 추출
    result_by_pos = {}
    for pos, counter in word_count_by_pos.items():
        result_by_pos[pos] = counter.most_common(10)  # 상위 10개 단어

    return jsonify(
        {
            "total_words": len(pos_list),
            "unique_words": len(set(token.form for token in pos_list)),
            "word_count_by_pos": result_by_pos,
        }
    )


@app.route("/generate-sentences", methods=["POST"])
def generate_sentences():
    try:
        data = request.json
        analysis = data.get("analysis", {})

        # 분석 데이터에서 주요 단어 추출
        nouns = [
            word for word, _ in analysis.get("word_count_by_pos", {}).get("NNG", [])
        ]
        verbs = [
            word for word, _ in analysis.get("word_count_by_pos", {}).get("VV", [])
        ]
        adverbs = [
            word for word, _ in analysis.get("word_count_by_pos", {}).get("MAG", [])
        ]

        # GPT 프롬프트 구성
        prompt = f"""You are an expert OPIC tutor specializing in creating "Universal Sentences (만능문장)".

        Based on these frequently used Korean words from the student:
        Nouns: {', '.join(nouns[:5])}
        Verbs: {', '.join(verbs[:5])}
        Adverbs: {', '.join(adverbs[:5])}

        Create 10 pairs of OPIC universal sentences (만능문장) that meet these criteria:

        Key Requirements:
        1. REUSABILITY (재활용성)
        - Can be adapted to various similar situations
        - Easy to modify by changing key words
        - Flexible enough to use in multiple OPIC topics

        2. NATURALNESS (자연스러움)
        - Must use casual, spoken Korean (구어체) like '-요', '-거든요', '-는데요' endings
        - Avoid formal or written language patterns
        - Use everyday conversational expressions and fillers
        - Sound like natural daily conversation, as if talking to a friend
        - Use declarative sentences, NOT questions
        - Include common spoken expressions like '그래서', '사실은', '진짜' etc.

        3. EFFECTIVENESS (효과성)
        - Incorporate the student's frequently used words
        - Simple yet sophisticated enough for OPIC
        - Include useful expressions for scoring points
        - Focus on casual, spoken statements and descriptions

        4. PRACTICALITY (실용성)
        - Easy to memorize and use
        - Relevant to daily life experiences
        - Can be used as template sentences
        - Should be conversational declarative sentences that describe situations or express opinions
        - Must sound natural in spoken Korean

        Format each sentence pair as:
        {{
            "korean": "구어체 한국어 만능문장 (예: ~는데요, ~거든요, ~요 등의 말투)",
            "english": "Natural conversational English (casual speaking style)",
            "usage": "When and how to use this sentence (사용 상황 설명)"
        }}

        Return only the JSON array of 10 sentence pairs, focusing on creating truly reusable, natural, and effective universal sentences that reflect authentic spoken Korean."""

        # GPT로 문장 생성
        response = g4f_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an OPIC tutor who specializes in creating '만능문장' (universal sentences).
                    만능문장 are special sentences that:
                    - Are easy to remember
                    - Can be used in multiple situations
                    - Sound natural in conversation
                    - Help score higher on OPIC tests
                    Your goal is to create sentences that students can easily adapt and reuse.""",
                },
                {"role": "user", "content": prompt},
            ],
        )

        return jsonify(
            {
                "sentences": response.choices[0].message.content,
                "words": {
                    "nouns": nouns[:5],
                    "verbs": verbs[:5],
                    "adverbs": adverbs[:5],
                },
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate-audio", methods=["POST"])
def generate_audio():
    try:
        data = request.json
        text = data.get("text")

        if not text:
            raise ValueError("Text is required")

        print(f"Generating audio for text: {text}")

        # TTS 생성
        result = tts_client.predict(
            "English",  # language
            "csukuangfj/kokoro-en-v0_19|11 speakers",  # repo_id
            text,  # text
            "0",  # sid
            1.0,  # speed
            api_name="/process",
        )

        print("Raw TTS result:", result)  # 실제 결과값 확인

        # 결과가 파일 경로인 경우, 파일을 읽어서 직접 전송
        if isinstance(result, (tuple, list)):
            audio_path = result[0]
        else:
            audio_path = result

        print("Audio path:", audio_path)

        # 파일이 실제로 존재하는지 확인
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found at {audio_path}")

        # 파일을 바이너리로 읽어서 base64로 인코딩
        with open(audio_path, "rb") as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode("utf-8")

        return jsonify({"audio_data": audio_data, "content_type": "audio/wav"})

    except Exception as e:
        print(f"Detailed error in generate_audio: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 새로운 테스트 관련 라우트들
@app.route("/get-test-questions", methods=["GET"])
def get_questions():
    try:
        # Questions.js에서 문제 로드
        all_questions = load_questions_from_js()
        print("Total questions loaded:", len(all_questions))  # 로드된 전체 문제 수

        if not all_questions:
            print("No questions were loaded!")
            return jsonify({"error": "No questions available"}), 500

        # 랜덤하게 4개 선택
        selected_questions = random.sample(all_questions, min(4, len(all_questions)))
        print("Selected questions:", selected_questions)  # 선택된 문제들

        # 각 문제에 대해 영어 번역 수행
        questions = []
        for q in selected_questions:
            translated = translate_to_english(q)
            print(f"Original: {q}")  # 원본 문제
            print(f"Translated: {translated}")  # 번역된 문제
            questions.append({"korean": q, "english": translated})

        return jsonify(questions)
    except Exception as e:
        print(f"Error in get_questions: {e}")
        return jsonify({"error": str(e)}), 500


# @app.route("/start-recording", methods=["POST"])
# def start_recording():
#     global recording
#     recording = True
#     threading.Thread(target=record_audio).start()
#     return jsonify({"status": "recording started"})


@app.route("/stop-recording", methods=["POST"])
def stop_recording():
    global recording
    recording = False

    audio_data = []
    while not audio_queue.empty():
        audio_data.append(audio_queue.get())

    audio_data = np.concatenate(audio_data)
    sf.write("temp.wav", audio_data, 16000)

    return jsonify({"transcription": "Transcription not available with the new setup"})


@app.route("/get-feedback", methods=["POST"])
def get_feedback():
    answers = request.json.get("answers")
    feedback = {}

    for idx, answer in answers.items():
        response = g4f_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """당신은 OPIC 전문 채점관입니다. 
                다음 OPIC 채점 기준에 따라 학생의 답변을 평가하고, 친근하고 명확한 한국어로 피드백을 제공해주세요.

                ■ 평가 기준:
                1. 상황대처능력
                   - 주어진 상황과 질문에 맞는 적절한 답변
                   - 영어 유창함과 자신감
                
                2. 영어 스타일
                   - 발음, 억양, 표현방식
                   - 자연스러운 영어 구사력
                
                3. 문법
                   - 시제, 수일치 등 기본 문법
                   - 답변 내용의 문법적 정확성
                
                4. 답변구조
                   - 서론-본론-결론의 명확한 구성
                   - 답변 내용의 체계적 전개
                """,
                },
                {"role": "user", "content": f"다음 OPIC 답변을 평가해주세요: {answer}"},
            ],
        )
        feedback[idx] = response.choices[0].message.content

    return jsonify({"feedback": feedback})


@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    temp_file = None
    try:
        data = request.json
        if not data or 'audio' not in data:
            return jsonify({"error": "No audio data provided"}), 400

        # 임시 파일 생성
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        
        # base64 디코딩 및 파일 저장
        audio_data = base64.b64decode(data['audio'])
        with open(temp_path, 'wb') as f:
            f.write(audio_data)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # API 호출 시 큐 관련 파라미터 추가
                result = stt_client.predict(
                    audio=handle_file(temp_path),
                    api_name="/predict",
                    fn_index=0
                )
                
                # 결과가 None이 아닌지 확인
                if result is not None:
                    return jsonify({"transcription": result})
                else:
                    raise Exception("Transcription result is empty")
            
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:  # 마지막 시도였다면
                    raise
                time.sleep(2)  # 재시도 전 2초 대기
                
                # 클라이언트 재초기화 및 새로운 세션 시작
                global stt_client
                stt_client = GradioClient(
                    "mindspark121/Whisper-STT",
                    hf_token=None,  # Hugging Face 토큰이 있다면 여기에 추가
                )

    except Exception as e:
        print(f"Transcription error: {str(e)}")
        return jsonify({
            "error": "음성 변환에 실패했습니다. 다시 시도해주세요.",
            "details": str(e)
        }), 500

    finally:
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                print(f"Error removing temp file: {str(e)}")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
