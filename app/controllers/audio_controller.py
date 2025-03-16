from flask import Blueprint, request, jsonify, current_app
from app.services.audio_service import generate_audio, transcribe_audio
from app.exception import ValidationError, APIError

audio_bp = Blueprint("audio", __name__)


@audio_bp.route("/generate-audio", methods=["POST"])
def generate_audio_route():
    try:
        data = request.json
        text = data.get("text")

        if not text:
            raise ValidationError("텍스트가 제공되지 않았습니다")

        result = generate_audio(text)
        return jsonify(result)
    except ValidationError as e:
        current_app.logger.error(f"Validation error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except APIError:
        raise
    except Exception as e:
        current_app.logger.error(f"Generate audio error: {str(e)}")
        raise APIError(f"오디오 생성 중 오류가 발생했습니다: {str(e)}")


@audio_bp.route("/transcribe", methods=["POST"])
def transcribe_audio_route():
    try:
        data = request.json
        if not data or "audio" not in data:
            raise ValidationError("오디오 데이터가 제공되지 않았습니다")

        result = transcribe_audio(data["audio"])
        return jsonify(result)
    except ValidationError as e:
        current_app.logger.error(f"Validation error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except APIError:
        raise
    except Exception as e:
        current_app.logger.error(f"Transcription error: {str(e)}")
        raise APIError(f"오디오 변환 중 오류가 발생했습니다: {str(e)}")
