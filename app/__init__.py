from flask import Flask
from flask_cors import CORS
import os


def create_app():
    # 앱 인스턴스 생성
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    # 리스폰스 헤더용 미들웨어 설정
    @app.after_request
    def add_header(response):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response

    # 환경 설정에 따라 CORS origins 설정
    if os.environ.get("FLASK_ENV") == "production":
        origins = ["https://op-ic-magician.vercel.app"]
    else:
        origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

    CORS(
        app,
        resources={r"/*": {"origins": origins}},
    )

    # 블루프린트 등록
    from app.controllers.text_controller import text_bp
    from app.controllers.audio_controller import audio_bp
    from app.controllers.test_controller import test_bp

    app.register_blueprint(text_bp)
    app.register_blueprint(audio_bp)
    app.register_blueprint(test_bp)

    return app
