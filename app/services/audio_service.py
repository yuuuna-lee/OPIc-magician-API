import os
import base64
import tempfile
from app.config import tts_client, stt_client
from gradio_client import handle_file
from app.exception import ValidationError, NotFoundError, APIError


def generate_audio(text):
    try:
        if not text:
            raise ValidationError("텍스트가 필요합니다")

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

        print("Raw TTS result:", result)

        # 결과가 파일 경로인 경우, 파일을 읽어서 직접 전송
        if isinstance(result, (tuple, list)):
            audio_path = result[0]
        else:
            audio_path = result

        print("Audio path:", audio_path)

        # 파일이 실제로 존재하는지 확인
        if not os.path.exists(audio_path):
            raise NotFoundError(f"오디오 파일을 찾을 수 없습니다: {audio_path}")

        # 파일을 바이너리로 읽어서 base64로 인코딩
        with open(audio_path, "rb") as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode("utf-8")

        return {"audio_data": audio_data, "content_type": "audio/wav"}

    except (ValidationError, NotFoundError):
        # 이미 정의된 API 에러는 그대로 전파
        raise
    except Exception as e:
        print(f"Detailed error in generate_audio: {str(e)}")
        raise APIError(f"오디오 생성 중 내부 오류: {str(e)}")


def transcribe_audio(audio_base64):
    temp_file = None
    temp_path = None

    try:
        if not audio_base64:
            raise ValidationError("오디오 데이터가 제공되지 않았습니다")

        # 시스템 임시 디렉토리에 파일 생성
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name

        # base64 디코딩 및 임시 파일 저장
        try:
            audio_data = base64.b64decode(audio_base64)
        except Exception:
            raise ValidationError("유효하지 않은 base64 인코딩 데이터입니다")

        with open(temp_path, "wb") as f:
            f.write(audio_data)

        # API 예제와 정확히 동일한 방식으로 호출
        result = stt_client.predict(
            audio=handle_file(temp_path), api_name="/predict"  # handle_file 사용
        )

        return {"transcription": result}

    except ValidationError:
        # 이미 정의된 API 에러는 그대로 전파
        raise
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        raise APIError(f"음성 변환 중 오류가 발생했습니다: {str(e)}")

    finally:
        if temp_file and temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                print(f"파일 삭제 중 오류: {str(e)}")
