"""결과물 YAML 저장 도구.

志望動機, 今後何がしたいか, 逆質問을 YAML 파일로 저장합니다.
"""

import os
import yaml


def save_output_yaml(
    output_type: str,
    ja_text: str,
    ko_text: str,
    key_points: list[str] | None = None,
    questions_ja: list[str] | None = None,
    questions_ko: list[str] | None = None,
    estimated_duration: str | None = None,
) -> dict:
    """면접 준비 결과물을 YAML 파일로 저장합니다.

    Args:
        output_type: 결과물 타입. "shibou_douki" | "kongo_nanika" | "gyaku_shitsumon"
        ja_text: 일본어 원문 (志望動機, 今後何がしたいか에 사용)
        ko_text: 한국어 번역 (志望動機, 今後何がしたいか에 사용)
        key_points: 핵심 포인트 목록 (志望動機, 今後何がしたいか에 사용)
        questions_ja: 역질문 일본어 목록 (逆質問에 사용)
        questions_ko: 역질문 한국어 목록 (逆質問에 사용)
        estimated_duration: 예상 소요 시간 (선택)

    Returns:
        저장 결과 정보를 담은 dict
    """
    valid_types = {"shibou_douki", "kongo_nanika", "gyaku_shitsumon"}
    if output_type not in valid_types:
        return {
            "status": "error",
            "message": f"無効なoutput_typeです。有効な値: {valid_types}",
        }

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{output_type}.yaml")

    # 결과물 타입에 따른 YAML 구조 생성
    if output_type == "gyaku_shitsumon":
        if not questions_ja or not questions_ko:
            return {
                "status": "error",
                "message": "逆質問にはquestions_jaとquestions_koが必要です。",
            }
        content = {
            "gyaku_shitsumon": {
                "questions": [
                    {"ja": qj, "ko": qk}
                    for qj, qk in zip(questions_ja, questions_ko)
                ]
            }
        }
    else:
        content = {
            output_type: {
                "ja": ja_text,
                "ko": ko_text,
            }
        }
        if key_points:
            content[output_type]["key_points"] = key_points
        if estimated_duration:
            content[output_type]["estimated_duration"] = estimated_duration

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                content,
                f,
                allow_unicode=True,
                default_flow_style=False,
                width=1000,
            )
        return {
            "status": "success",
            "output_path": f"output/{output_type}.yaml",
            "message": f"{output_type}.yaml を output/ フォルダに保存しました。",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"ファイル保存エラー: {str(e)}",
        }
