"""결과물 YAML 저장 도구.

自己紹介, 志望動機, 転職理由, 自己PR, 今後何がしたいか, 逆質問을 YAML 파일로 저장합니다.
커스텀 YAML writer를 사용하여 필드 순서 보존 + | block scalar를 보장합니다.
"""

import os
import yaml


# ──────────────────────────────────────────────────────────────
# 커스텀 YAML Writer: 필드 순서 보존 + | block scalar
# ──────────────────────────────────────────────────────────────

def _write_block_scalar(value: str, indent: int = 4) -> str:
    """여러 줄 문자열을 YAML | block scalar 형태로 변환합니다."""
    prefix = " " * indent
    lines = value.strip().split("\n")
    return "|\n" + "\n".join(f"{prefix}{line}" for line in lines) + "\n"


def _write_list(items: list, indent: int = 4) -> str:
    """리스트를 YAML 형태로 변환합니다."""
    prefix = " " * indent
    return "\n".join(f"{prefix}- {item}" for item in items) + "\n"


def _write_standard_yaml(root_key: str, data: dict) -> str:
    """표준 면접 답변 YAML을 지정된 필드 순서로 작성합니다.

    필드 순서: ja → key_points_ja → ko → key_points_ko
    모든 multiline 문자열은 | block scalar를 사용합니다.
    field_order에 없는 키도 마지막에 fallback으로 출력합니다.
    """
    lines = [f"{root_key}:"]

    if not data or not isinstance(data, dict):
        return "\n".join(lines)

    # 정의된 필드 순서
    field_order = ["ja", "key_points_ja", "ko", "key_points_ko"]
    written_fields = set()

    for field in field_order:
        if field not in data:
            continue
        written_fields.add(field)
        value = data[field]
        if isinstance(value, str):
            lines.append(f"  {field}: {_write_block_scalar(value)}")
        elif isinstance(value, list):
            lines.append(f"  {field}:")
            lines.append(_write_list(value))
        else:
            lines.append(f"  {field}: {value}")

    # field_order에 없는 나머지 키도 출력 (데이터 유실 방지)
    for field, value in data.items():
        if field in written_fields:
            continue
        if isinstance(value, str):
            lines.append(f"  {field}: {_write_block_scalar(value)}")
        elif isinstance(value, list):
            lines.append(f"  {field}:")
            lines.append(_write_list(value))
        elif isinstance(value, dict):
            # 중첩 dict는 yaml.dump로 fallback
            import yaml
            nested = yaml.dump(value, allow_unicode=True, default_flow_style=False, width=1000)
            indented = "\n".join(f"    {l}" for l in nested.strip().split("\n"))
            lines.append(f"  {field}:")
            lines.append(indented)
            lines.append("")
        else:
            lines.append(f"  {field}: {value}")

    return "\n".join(lines)


def _write_gyaku_shitsumon_yaml(data: dict) -> str:
    """역질문(逆質問) YAML을 번호 레이어 구조로 작성합니다.

    출력 형식:
      gyaku_shitsumon:
        questions:
          q1:
            ja: |
              ...
            intent_ja: |
              ...
            ko: |
              ...
            intent_ko: |
              ...
    """
    lines = ["gyaku_shitsumon:", "  questions:"]

    raw_questions = data.get("gyaku_shitsumon", data).get("questions", {})

    # list 형태 (하위 호환) → dict 변환
    if isinstance(raw_questions, list):
        questions = {f"q{i+1}": q for i, q in enumerate(raw_questions)}
    elif isinstance(raw_questions, dict):
        questions = raw_questions
    else:
        questions = {}

    # 필드 순서: ja → intent_ja → ko → intent_ko
    field_order = ["ja", "intent_ja", "ko", "intent_ko"]

    for q_key in sorted(questions.keys()):
        q = questions[q_key]
        lines.append(f"    {q_key}:")

        for field in field_order:
            if field not in q:
                continue
            value = str(q[field]).strip()
            if "\n" in value or len(value) > 60:
                lines.append(f"      {field}: {_write_block_scalar(value, indent=8)}")
            else:
                lines.append(f"      {field}: |")
                lines.append(f"        {value}")
                lines.append("")

    return "\n".join(lines) + "\n"


def _serialize_yaml(output_type: str, content: dict) -> str:
    """output_type에 따라 적절한 YAML serializer를 선택합니다."""
    if output_type == "gyaku_shitsumon":
        return _write_gyaku_shitsumon_yaml(content)

    # 표준 형식: root_key → {ja, key_points_ja, ko, key_points_ko}
    root_key = output_type
    if output_type in content and isinstance(content[output_type], dict):
        data = content[output_type]
    else:
        data = content

    return _write_standard_yaml(root_key, data)


# ──────────────────────────────────────────────────────────────
# 메인 저장 함수
# ──────────────────────────────────────────────────────────────

def save_output_yaml(
    output_type: str,
    raw_data: dict | None = None,
    ja_text: str = "",
    ko_text: str = "",
    key_points: list[str] | None = None,
    key_points_ja: list[str] | None = None,
    key_points_ko: list[str] | None = None,
    questions_ja: list[str] | None = None,
    questions_ko: list[str] | None = None,
    questions_intent: list[str] | None = None,
    estimated_duration: str | None = None,
) -> dict:
    """면접 준비 결과물을 YAML 파일로 저장합니다.

    Args:
        output_type: 결과물 타입.
        raw_data: LLM 응답에서 파싱된 원본 데이터 (이 값이 있으면 다른 필드 무시)
        ja_text: 일본어 원문
        ko_text: 한국어 번역
        key_points: 핵심 포인트 목록 (단일 언어)
        key_points_ja: 핵심 포인트 일본어 목록
        key_points_ko: 핵심 포인트 한국어 목록
        questions_ja: 역질문 일본어 목록
        questions_ko: 역질문 한국어 목록
        questions_intent: 역질문 의도 목록
        estimated_duration: 예상 소요 시간

    Returns:
        저장 결과 정보를 담은 dict
    """
    valid_types = {
        "jiko_shoukai": "00. 自己紹介(자기소개)",
        "jiko_pr": "01. 自己PR(자기PR)",
        "tsuyomi_yowami": "02. 自身の強みと弱み(강점과 약점)",
        "yarigai": "03. やりがいを感じる時(일의 보람)",
        "konnan_keiken": "04. 最も困難だった経験(가장 어려웠던 경험)",
        "tensyoku_jiku": "05. 転職軸(전직축)",
        "tensyoku_riyuu": "06. 転職理由(전직이유)",
        "shibou_douki": "07. 志望動機(지원동기)",
        "kongo_nanika": "08. 今後何がしたいか(향후 목표)",
        "gyaku_shitsumon": "09. 逆質問(역질문)",
    }
    if output_type not in valid_types:
        return {
            "status": "error",
            "message": f"無効なoutput_typeです。有効な値: {list(valid_types.keys())}",
        }

    file_name = valid_types[output_type]

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{file_name}.yaml")

    # raw_data가 제공된 경우 그대로 사용 (LLM 파싱 결과를 직접 저장)
    if raw_data is not None:
        content = raw_data
    elif output_type == "gyaku_shitsumon":
        # 逆質問: 질문 리스트 구조
        if not questions_ja or not questions_ko:
            return {
                "status": "error",
                "message": "逆質問にはquestions_jaとquestions_koが必要です。",
            }
        questions = []
        for i, (qj, qk) in enumerate(zip(questions_ja, questions_ko)):
            q = {"ja": qj, "ko": qk}
            if questions_intent and i < len(questions_intent):
                q["intent"] = questions_intent[i]
            questions.append(q)
        content = {"gyaku_shitsumon": {"questions": questions}}
    else:
        # 일반 텍스트 기반 결과물
        content = {
            output_type: {
                "ja": ja_text,
                "ko": ko_text,
            }
        }
        if key_points_ja:
            content[output_type]["key_points_ja"] = key_points_ja
        if key_points_ko:
            content[output_type]["key_points_ko"] = key_points_ko
        if key_points and not key_points_ja and not key_points_ko:
            content[output_type]["key_points"] = key_points
        if estimated_duration:
            content[output_type]["estimated_duration"] = estimated_duration

    try:
        yaml_str = _serialize_yaml(output_type, content)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        return {
            "status": "success",
            "output_path": f"output/{file_name}.yaml",
            "message": f"{file_name}.yaml を output/ フォルダに保存しました。",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"ファイル保存エラー: {str(e)}",
        }
