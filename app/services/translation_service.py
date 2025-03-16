from app.config import g4f_client, GPT_MODEL
from app.exception import ValidationError, APIError


def translate_to_english(text):
    try:
        if not text:
            raise ValidationError("번역할 텍스트가 제공되지 않았습니다")

        response = g4f_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator. Translate the given Korean text to natural English, maintaining the same meaning and nuance.",
                },
                {"role": "user", "content": f"Translate this to English: {text}"},
            ],
        )

        if not response or not response.choices or not response.choices[0].message:
            raise APIError("번역 API에서 올바른 응답을 받지 못했습니다")

        return response.choices[0].message.content

    except ValidationError:
        raise
    except Exception as e:
        print(f"Translation error: {str(e)}")
        raise APIError(f"번역 중 오류가 발생했습니다: {str(e)}")
