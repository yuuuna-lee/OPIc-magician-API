from collections import Counter
from app.config import kiwi, g4f_client, GPT_MODEL
from app.exception import ValidationError, APIError


def analyze_text(text):
    try:
        if not text:
            raise ValidationError("분석할 텍스트가 제공되지 않았습니다")

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

        return {
            "total_words": len(pos_list),
            "unique_words": len(set(token.form for token in pos_list)),
            "word_count_by_pos": result_by_pos,
        }
    except ValidationError:
        raise
    except Exception as e:
        print(f"Error in analyze_text: {str(e)}")
        raise APIError(f"텍스트 분석 중 오류가 발생했습니다: {str(e)}")


def generate_sentences(analysis):
    try:
        if not analysis:
            raise ValidationError("분석 데이터가 제공되지 않았습니다")

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

        # 단어가 너무 적으면 경고
        if not nouns and not verbs and not adverbs:
            raise ValidationError("분석 데이터에서 충분한 단어를 추출할 수 없습니다")

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
            model=GPT_MODEL,
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

        return {
            "sentences": response.choices[0].message.content,
            "words": {
                "nouns": nouns[:5],
                "verbs": verbs[:5],
                "adverbs": adverbs[:5],
            },
        }
    except ValidationError:
        raise
    except Exception as e:
        print(f"Error in generate_sentences: {str(e)}")
        raise APIError(f"문장 생성 중 오류가 발생했습니다: {str(e)}")
