from flask import Blueprint, request, jsonify, current_app
from app.services.test_service import get_test_questions, get_feedback
from app.exception import ValidationError, APIError

test_bp = Blueprint("test", __name__)


@test_bp.route("/get-test-questions", methods=["GET"])
def get_test_questions_route():
    try:
        questions = get_test_questions()
        return jsonify(questions)
    except ValidationError as e:
        current_app.logger.error(f"Validation error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except APIError:
        raise
    except Exception as e:
        current_app.logger.error(f"Get test questions error: {str(e)}")
        raise APIError(f"테스트 질문을 가져오는 중 오류가 발생했습니다: {str(e)}")


@test_bp.route("/get-feedback", methods=["POST"])
def get_feedback_route():
    try:
        answers = request.json.get("answers")
        if not answers:
            raise ValidationError("답변이 제공되지 않았습니다")

        result = get_feedback(answers)
        return jsonify(result)
    except ValidationError as e:
        current_app.logger.error(f"Validation error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except APIError:
        raise
    except Exception as e:
        current_app.logger.error(f"Get feedback error: {str(e)}")
        raise APIError(f"피드백을 생성하는 중 오류가 발생했습니다: {str(e)}")
