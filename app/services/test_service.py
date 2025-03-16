import re
import random
import os
from app.config import g4f_client, GPT_MODEL, JS_PATH
from app.services.translation_service import translate_to_english
from app.exception import ValidationError, NotFoundError, APIError


def load_questions_from_js():
    try:
        print("Attempting to load questions from:", JS_PATH)

        if not os.path.exists(JS_PATH):
            raise NotFoundError(f"질문 파일을 찾을 수 없습니다: {JS_PATH}")

        with open(JS_PATH, "r", encoding="utf-8") as file:
            content = file.read()
            print("\nFile content preview:")
            print(content[:200])  # 파일 내용 앞부분 출력

            # JavaScript 객체에서 서베이 배열 찾기
            survey_start = content.find("서베이")  # ':' 제거
            if survey_start == -1:
                raise ValidationError("파일 내에서 '서베이' 항목을 찾을 수 없습니다")

            # 배열 시작 찾기
            array_start = content.find("[", survey_start)
            if array_start == -1:
                raise ValidationError("서베이 항목의 시작 괄호를 찾을 수 없습니다")

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

            questions_str = content[array_start : array_end - 1]

            # 각 질문을 분리 (쌍따옴표로 둘러싸인 문자열 추출)
            questions = re.findall(r'"([^"]+)"', questions_str)

            # 주석과 빈 문자열 제거
            questions = [
                q.strip()
                for q in questions
                if q.strip() and not q.strip().startswith("//")
            ]

            if not questions:
                raise ValidationError("질문 목록이 비어 있습니다")

            print(f"Total questions loaded: {len(questions)}")
            return questions

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        print(f"Error loading questions: {str(e)}")
        raise APIError(f"질문 파일 로드 중 오류가 발생했습니다: {str(e)}")


def get_test_questions():
    try:
        # Questions.js에서 문제 로드
        all_questions = load_questions_from_js()
        print("Total questions loaded:", len(all_questions))  # 로드된 전체 문제 수

        if not all_questions:
            raise ValidationError("이용 가능한 질문이 없습니다")

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

        return questions
    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        print(f"Error in get_test_questions: {str(e)}")
        raise APIError(f"테스트 질문을 가져오는 중 오류가 발생했습니다: {str(e)}")


def get_feedback(answers):
    try:
        if not answers:
            raise ValidationError("답변이 제공되지 않았습니다")

        feedback = {}

        for idx, answer in answers.items():
            if not answer:
                raise ValidationError(f"질문 {idx}에 대한 답변이 비어 있습니다")

            response = g4f_client.chat.completions.create(
                model=GPT_MODEL,
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

                    ■ 피드백 형식:

                    📌 종합 평가
                    [답변의 전반적인 강점과 인상적인 부분을 2-3줄로 요약]

                    💪 잘한 점
                    • [구체적인 예시와 함께 잘한 점 나열]
                    • [실제 답변에서 사용한 좋은 표현 인용]
                    
                    📝 개선할 점
                    • [개선이 필요한 부분을 구체적으로 설명]
                    • [실제 교정 예시 제시]

                    💡 학습 조언
                    • [실천 가능한 구체적인 학습 방법 제시]
                    • [다음 답변을 위한 핵심 표현 추천]

                    주의사항:
                    - 친근하고 격려하는 톤 유지
                    - 구체적인 예시와 함께 설명
                    - 중요한 영어 표현은 괄호 안에 병기
                    - 실천 가능한 구체적인 조언 제시
                    """,
                    },
                    {
                        "role": "user",
                        "content": f"다음 OPIC 답변을 평가해주세요: {answer}",
                    },
                ],
            )
            feedback[idx] = response.choices[0].message.content

        return {"feedback": feedback}
    except ValidationError:
        raise
    except Exception as e:
        print(f"Error in get_feedback: {str(e)}")
        raise APIError(f"피드백을 생성하는 중 오류가 발생했습니다: {str(e)}")
