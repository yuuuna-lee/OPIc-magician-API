from flask import Blueprint, request, jsonify, current_app
from app.services.text_service import analyze_text, generate_sentences
from app.exception import ValidationError, APIError

text_bp = Blueprint("text", __name__)


@text_bp.route("/analyze-text", methods=["POST"])
def analyze_text_route():
    try:
        data = request.json
        text = data.get("text", "")

        if not text:
            raise ValidationError("텍스트가 제공되지 않았습니다")

        result = analyze_text(text)
        return jsonify(result)
    except ValidationError as e:
        current_app.logger.error(f"Validation error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except APIError:
        raise
    except Exception as e:
        current_app.logger.error(f"Analyze text error: {str(e)}")
        raise APIError(f"텍스트 분석 중 오류가 발생했습니다: {str(e)}")


@text_bp.route("/generate-sentences", methods=["POST"])
def generate_sentences_route():
    try:
        data = request.json
        analysis = data.get("analysis", {})

        if not analysis:
            raise ValidationError("분석 데이터가 제공되지 않았습니다")

        result = generate_sentences(analysis)
        return jsonify(result)
    except ValidationError as e:
        current_app.logger.error(f"Validation error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except APIError:
        raise
    except Exception as e:
        current_app.logger.error(f"Generate sentences error: {str(e)}")
        raise APIError(f"문장 생성 중 오류가 발생했습니다: {str(e)}")
