"""AI-Agents.Naite CLI 엔트리 포인트.

python main.py 로 직접 실행합니다.
파일 상태를 확인하고, 준비가 완료되면 자동으로 면접 스크립트를 생성합니다.

v3.0 — 最終面接（役員面接）対応版
  追加: 転職軸, 最終面接モード（謙虚さ・未来テーマ）
  改善: 逆質問2バージョン（現場社員向け / 役員向け）
"""

import sys
import yaml
import litellm

from interview_agent.config import (
    LLM_PROVIDER,
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    LMSTUDIO_BASE_URL,
    LMSTUDIO_MODEL,
)
from interview_agent.tools.file_loader import check_preparation_status, load_yaml_data
from interview_agent.tools.pdf_converter import convert_pdf_to_yaml
from interview_agent.tools.output_writer import save_output_yaml
from interview_agent.prompts import (
    JIKO_SHOUKAI_PROMPT,
    SHIBOU_DOUKI_PROMPT,
    TENSYOKU_RIYUU_PROMPT,
    JIKO_PR_PROMPT,
    KONGO_NANIKA_PROMPT,
    GYAKU_SHITSUMON_PROMPT_EARLY,
    GYAKU_SHITSUMON_PROMPT_FINAL,
    TENSYOKU_JIKU_PROMPT,
    TSUYOMI_YOWAMI_PROMPT,
    YARIGAI_PROMPT,
    KONNAN_KEIKEN_PROMPT,
    PDF_CONVERSION_PROMPT,
    PDF_CONVERSION_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_FINAL,
    SELF_REVIEW_PROMPT,
)

def _print_header(is_final: bool = False):
    print("=" * 60)
    if is_final:
        print(" 最終面接準備エージェント / 최종 면접 준비 에이전트")
        print(" AI-Agents.Naite v3.0 — 役員面接対応版")
        print(" テーマ: 「未来」 — 謙虚さを重視した受け答え")
    else:
        print(" 面接準備エージェント / 면접 준비 에이전트")
        print(" AI-Agents.Naite v3.0")
    print("=" * 60)
    print()

def _print_step(num: int, title_ja: str, title_ko: str):
    print(f"\n{'─' * 50}")
    print(f" ステップ{num} / 스텝{num}: {title_ja} / {title_ko}")
    print(f"{'─' * 50}")

def _call_llm(system: str, user: str, max_retries: int = 3) -> str:
    """LLM API를 호출하여 응답 텍스트를 반환합니다. (Rate Limit 자동 대기 지원)"""
    import time
    from litellm.exceptions import RateLimitError

    for attempt in range(max_retries):
        try:
            if LLM_PROVIDER == "lmstudio":
                model = f"openai/{LMSTUDIO_MODEL}"
                response = litellm.completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    api_base=LMSTUDIO_BASE_URL,
                    api_key="not-needed",
                    temperature=0.7,
                )
            else:
                model = f"gemini/{GEMINI_MODEL}"
                response = litellm.completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    api_key=GOOGLE_API_KEY,
                    temperature=0.7,
                )
            return response.choices[0].message.content
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 45 * (attempt + 1)
                print(f" 無料APIの制限(Rate Limit)に達しました。{wait_time}秒待機してから再試行します... ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(" [Error] API 제한(Rate Limit)에 도달했습니다.")
                raise e

def _format_resume_context(resume: dict) -> str:
    """이력서 데이터를 면접 컨텍스트에 최적화된 가독성 높은 형태로 변환합니다."""
    lines = []

    # 개인정보
    personal = resume.get("personal", {})
    if personal:
        lines.append("### 基本情報（기본 정보）")
        lines.append(f"- 氏名: {personal.get('name', '')} ({personal.get('furigana', '')})")
        if personal.get("nationality"):
            lines.append(f"- 国籍: {personal.get('nationality', '')}")
        lines.append("")

    # 학력
    education = resume.get("education", [])
    if education:
        lines.append("### 学歴（학력）")
        for edu in education:
            inst = edu.get("institution", "")
            major = f" — {edu['major']}" if edu.get("major") else ""
            degree = f" ({edu['degree']})" if edu.get("degree") else ""
            lines.append(f"- {edu.get('period', '')}: {inst}{major}{degree}")
        lines.append("")

    # 자격
    qualifications = resume.get("qualifications", [])
    if qualifications:
        lines.append("### 資格（자격）")
        for q in qualifications:
            lines.append(f"- {q.get('date', '')}: {q.get('name', '')}")
        lines.append("")

    # 스킬
    skills = resume.get("skills", {})
    if skills:
        lines.append("### スキル（기술 스택）")
        if skills.get("languages"):
            lines.append(f"- 言語: {', '.join(skills['languages'])}")
        if skills.get("technical"):
            lines.append(f"- 技術: {', '.join(skills['technical'])}")
        lines.append("")

    # 경력 (resume 내 career_history)
    career = resume.get("career_history", [])
    if career:
        lines.append("### 職歴（직력）")
        for c in career:
            lines.append(f"- {c.get('period', '')}: {c.get('company', '')} {c.get('position', '')}")
            for r in c.get("responsibilities", []):
                lines.append(f" - {r}")
        lines.append("")

    # 자기PR
    if resume.get("self_pr"):
        lines.append("### 自己PR要約（자기PR 요약）")
        lines.append(resume["self_pr"])
        lines.append("")

    return "\n".join(lines)

def _format_career_context(career: dict) -> str:
    """직무경력서 데이터를 면접 컨텍스트에 최적화된 가독성 높은 형태로 변환합니다."""
    lines = []

    # 직무 요약
    if career.get("summary"):
        lines.append("### 職務要約（직무 요약）")
        lines.append(str(career["summary"]).strip())
        lines.append("")

    # 활용 가능한 경험·기술
    applicable = career.get("applicable_skills", {})
    if applicable:
        lines.append("### 活かせる経験・知識・技術（활용 가능한 경험·기술）")
        for category, items in applicable.items():
            if isinstance(items, list):
                for item in items:
                    lines.append(f"- {item}")
        lines.append("")

    # 경력 상세
    history = career.get("career_history", [])
    if history:
        lines.append("### 職務経歴（직무 경력 상세）")
        for i, h in enumerate(history, 1):
            lines.append(f"\n#### {i}社目: {h.get('company', '')} ({h.get('period', '')})")
            if h.get("position"):
                lines.append(f"- 役職: {h['position']}")
            if h.get("team_size"):
                lines.append(f"- チーム規模: {h['team_size']}")
            if h.get("responsibilities"):
                lines.append("- 主な業務:")
                for r in h["responsibilities"]:
                    lines.append(f" - {r}")
            if h.get("achievements"):
                lines.append("- 主な実績:")
                for a in h["achievements"]:
                    lines.append(f" - {a}")
            if h.get("additional_contributions"):
                lines.append("- 追加貢献:")
                for c in h["additional_contributions"]:
                    lines.append(f" - {c}")

            # 프로젝트 상세 (Livetoon 등)
            for proj in h.get("projects", []):
                lines.append(f"\n **プロジェクト: {proj.get('name', '')}**")
                if proj.get("period"):
                    lines.append(f" - 期間: {proj['period']}")
                if proj.get("overview"):
                    lines.append(f" - 概要: {proj['overview']}")
                if proj.get("achievements"):
                    lines.append(" - 成果:")
                    for a in proj["achievements"]:
                        lines.append(f" - {a}")
                if proj.get("technologies"):
                    lines.append(f" - 技術: {', '.join(proj['technologies'])}")

            if h.get("technologies"):
                lines.append(f"- 使用技術: {', '.join(h['technologies'])}")
        lines.append("")

    # 기술 스킬
    tech = career.get("technical_skills", {})
    if tech:
        lines.append("### 言語経験・スキル（기술 스택）")
        for category, items in tech.items():
            if isinstance(items, list) and items:
                cat_label = category.replace("_", " ").title()
                skills_str = ", ".join(
                    f"{s.get('name', '')}({s.get('years', '')}年)" if isinstance(s, dict) else str(s)
                    for s in items
                )
                lines.append(f"- {cat_label}: {skills_str}")
        lines.append("")

    # 자기PR
    if career.get("self_pr"):
        lines.append("### 自己PR（자기PR）")
        lines.append(str(career["self_pr"]).strip())
        lines.append("")

    return "\n".join(lines)

def _build_context(resume: dict, career: dict, company: dict) -> str:
    """이력서, 직무경력서, 기업정보를 면접 컨텍스트에 최적화된 문자열로 합성합니다.

    단순 yaml.dump가 아닌, 면접관 시점에서 핵심 정보를 빠르게 파악할 수 있도록
    구조화된 Markdown 형태로 변환합니다.
    """
    resume_ctx = _format_resume_context(resume)
    career_ctx = _format_career_context(career)

    return (
        "## 履歴書（이력서）\n"
        f"{resume_ctx}\n\n"
        "## 職務経歴書（직무경력서）\n"
        f"{career_ctx}\n\n"
        "## 応募先企業情報（지원 기업 정보）\n"
        f"```yaml\n{yaml.dump(company, allow_unicode=True, default_flow_style=False)}```"
    )

def _parse_yaml_from_response(text: str) -> str:
    """LLM 응답에서 ```yaml ... ``` 블록 내용을 추출합니다."""
    if "```yaml" in text:
        start = text.index("```yaml") + len("```yaml")
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    return text.strip()

def _generate_standard_item(
    step_num: int,
    title_ja: str,
    title_ko: str,
    output_type: str,
    prompt: str,
    context: str,
    system_prompt: str = None,
) -> dict:
    """표준 생성 항목(자기소개, 지원동기, 전직이유, 향후목표 등)을 처리합니다."""
    _print_step(step_num, f"{title_ja}の作成", f"{title_ko} 작성")
    print(" [AI] 생성 중...")

    sys_prompt = system_prompt or SYSTEM_PROMPT
    response = _call_llm(sys_prompt, prompt + "\n\n" + context)

    # --- Self-Review Step ---
    print(" [Review] 셀프 리뷰 진행 중...")
    review_prompt = f"{SELF_REVIEW_PROMPT}\n\n## レビュー対象の回答案:\n```yaml\n{_parse_yaml_from_response(response)}\n```\n\n## 面接コンテキスト:\n{context}"
    reviewed_response = _call_llm(sys_prompt, review_prompt)

    response_yaml = _parse_yaml_from_response(reviewed_response)

    try:
        data = yaml.safe_load(response_yaml)
    except yaml.YAMLError:
        data = {output_type: {"ja": response_yaml, "ko": "(パース失敗)"}}

    # output_type 키가 있으면 그대로 사용, 없으면 감싸줌
    if isinstance(data, dict) and output_type in data:
        save_data = data
    elif isinstance(data, dict):
        save_data = {output_type: data}
    else:
        save_data = {output_type: {"ja": str(data), "ko": ""}}

    # ja 필드가 비어있거나 없는 경우 → LLM 응답 원문으로 fallback
    inner = save_data.get(output_type, {})
    if isinstance(inner, dict) and not inner.get("ja"):
        print(f" ja フィールドが空です。LLM応答をfallbackとして使用します。")
        inner["ja"] = response_yaml
        if not inner.get("ko"):
            inner["ko"] = "(自動fallback — LLM応答からjaフィールドが抽出できませんでした)"
        save_data[output_type] = inner

    # raw_data로 직접 저장하여 필드 구조를 보존
    result = save_output_yaml(
        output_type=output_type,
        raw_data=save_data,
    )
    if result["status"] == "success":
        print(f" [OK] {result['output_path']} 저장 완료")
    else:
        print(f" [Error] 저장 실패: {result['message']}")
    return save_data.get(output_type, save_data)

def main():
    # 면접 단계 감지
    is_final = "--final" in sys.argv
    system_prompt = SYSTEM_PROMPT_FINAL if is_final else SYSTEM_PROMPT

    _print_header(is_final)

    # ── 스텝 0: 준비 상태 확인 ──
    print("[Check] 준비 상태 확인 중...")
    status = check_preparation_status()

    if not status["ready"]:
        # 파일 부족 → 안내 메시지 출력 후 종료
        print("\n[Warning] 면접 준비에 필요한 파일이 부족합니다.\n")
        for msg in status["missing"]:
            print(f" {msg}")
        print("\n準備ができたら、再度実行してください。")
        print("준비가 되면 다시 실행해주세요.")
        sys.exit(1)

    # ── PDF 변환이 필요한 경우 ──
    if status["needs_pdf_conversion"]:
        _print_step(0, "PDF変換", "PDF 변환")

        for stem in ["resume", "career"]:
            if status["status"].get(f"{stem}_pdf") and not status["status"].get(f"{stem}_yaml"):
                print(f" [Convert] {stem}.pdf -> YAML 변환 중...")
                result = convert_pdf_to_yaml(f"{stem}.pdf")

                if result["status"] == "error":
                    print(f" エラー: {result['message']}")
                    sys.exit(1)

                # LLM을 사용하여 추출된 텍스트를 구조화된 YAML로 변환
                print(f" [AI] LLM으로 구조화 중...")
                prompt = PDF_CONVERSION_PROMPT.format(
                    doc_type=result["doc_type"],
                    text=result["extracted_text"],
                )
                structured = _call_llm(PDF_CONVERSION_SYSTEM_PROMPT, prompt)
                yaml_content = _parse_yaml_from_response(structured)

                # 구조화된 YAML 저장
                import os
                base_dir = os.path.dirname(os.path.abspath(__file__))
                yaml_path = os.path.join(base_dir, "data", f"{stem}.yaml")
                with open(yaml_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)
                print(f" [OK] data/{stem}.yaml 저장 완료")

    # ── 스텝 1: 데이터 로드 ──
    _print_step(1, "データ読み込み", "데이터 로드")

    resume_result = load_yaml_data("data/resume.yaml")
    career_result = load_yaml_data("data/career.yaml")
    company_result = load_yaml_data("data/target_company.yaml")

    for name, r in [("履歴書", resume_result), ("職務経歴書", career_result), ("企業情報", company_result)]:
        if r["status"] == "error":
            print(f" {name}: {r['message']}")
            sys.exit(1)
        print(f" [OK] {name} 로드 완료")

    context = _build_context(
        resume_result["data"],
        career_result["data"],
        company_result["data"],
    )

    # ── 스텝 2 (00): 자기소개 ──
    _generate_standard_item(2, "自己紹介", "자기소개", "jiko_shoukai", JIKO_SHOUKAI_PROMPT, context, system_prompt)

    # ── 스텝 3 (01): 자기PR ──
    _generate_standard_item(3, "自己PR", "자기PR", "jiko_pr", JIKO_PR_PROMPT, context, system_prompt)

    # ── 스텝 4 (02): 강점과 약점 ──
    _generate_standard_item(4, "自身の強みと弱み", "자신의 강점과 약점", "tsuyomi_yowami", TSUYOMI_YOWAMI_PROMPT, context, system_prompt)

    # ── 스텝 5 (03): 보람을 느끼는 순간 ──
    _generate_standard_item(5, "やりがいを感じる時", "보람을 느끼는 순간", "yarigai", YARIGAI_PROMPT, context, system_prompt)

    # ── 스텝 6 (04): 가장 어려웠던 경험 ──
    _generate_standard_item(6, "最も困難だった経験", "가장 어려웠던 경험", "konnan_keiken", KONNAN_KEIKEN_PROMPT, context, system_prompt)

    # ── 스텝 7 (05): 전직축 ──
    _generate_standard_item(7, "転職軸", "전직축", "tensyoku_jiku", TENSYOKU_JIKU_PROMPT, context, system_prompt)

    # ── 스텝 8 (06): 전직이유 ──
    _generate_standard_item(8, "転職理由", "전직이유", "tensyoku_riyuu", TENSYOKU_RIYUU_PROMPT, context, system_prompt)

    # ── 스텝 9 (07): 지원동기 ──
    _generate_standard_item(9, "志望動機", "지원동기", "shibou_douki", SHIBOU_DOUKI_PROMPT, context, system_prompt)

    # ── 스텝 10 (08): 향후 목표 ──
    _generate_standard_item(10, "今後何がしたいか", "향후 목표", "kongo_nanika", KONGO_NANIKA_PROMPT, context, system_prompt)

    # ── 스텝 11 (09): 역질문 ──
    gyaku_prompt = GYAKU_SHITSUMON_PROMPT_FINAL if is_final else GYAKU_SHITSUMON_PROMPT_EARLY
    gyaku_label = "最終面接用逆質問" if is_final else "逆質問"
    gyaku_label_ko = "최종면접용 역질문" if is_final else "역질문"
    _print_step(11, f"{gyaku_label}の作成", f"{gyaku_label_ko} 작성")
    print(" [AI] 생성 중...")

    gyaku_response = _call_llm(system_prompt, gyaku_prompt + "\n\n" + context)

    # --- Self-Review Step ---
    print(" [Review] 셀프 리뷰 진행 중...")
    gyaku_review_prompt = f"{SELF_REVIEW_PROMPT}\n\n## レビュー対象の回答案:\n```yaml\n{_parse_yaml_from_response(gyaku_response)}\n```\n\n## 面接コンテキスト:\n{context}"
    gyaku_reviewed_response = _call_llm(system_prompt, gyaku_review_prompt)

    gyaku_yaml = _parse_yaml_from_response(gyaku_reviewed_response)

    try:
        gyaku_data = yaml.safe_load(gyaku_yaml)
    except yaml.YAMLError:
        gyaku_data = {}

    if isinstance(gyaku_data, dict) and "gyaku_shitsumon" in gyaku_data:
        save_gq = gyaku_data
    elif isinstance(gyaku_data, dict):
        save_gq = {"gyaku_shitsumon": gyaku_data}
    else:
        save_gq = {"gyaku_shitsumon": {"questions": [{"ja": gyaku_yaml, "ko": "(パース失敗)"}]}}

    result_gq = save_output_yaml(
        output_type="gyaku_shitsumon",
        raw_data=save_gq,
    )

    if result_gq["status"] == "success":
        print(f" [OK] {result_gq['output_path']} 저장 완료")
    else:
        print(f" [Error] 저장 실패: {result_gq['message']}")

    # ── 완료 ──
    mode_label = "最終面接" if is_final else "面接"
    print(f"\n{'=' * 60}")
    print(f"すべての{mode_label}準備が完了しました！")
    print(f"모든 {'최종 ' if is_final else ''}면접 준비가 완료되었습니다!")
    print(f"{'=' * 60}")
    print("\n[File] 생성된 파일:")
    print(" - output/00. 自己紹介(자기소개).yaml")
    print(" - output/01. 自己PR(자기PR).yaml")
    print(" - output/02. 自身の強みと弱み(강점과 약점).yaml")
    print(" - output/03. やりがいを感じる時(일의 보람).yaml")
    print(" - output/04. 最も困難だった経験(가장 어려웠던 경험).yaml")
    print(" - output/05. 転職軸(전직축).yaml")
    print(" - output/06. 転職理由(전직이유).yaml")
    print(" - output/07. 志望動機(지원동기).yaml")
    print(" - output/08. 今後何がしたいか(향후 목표).yaml")
    print(" - output/09. 逆質問(역질문).yaml")
    if is_final:
        print("\n [Mode] 최종면접 모드: 겸손함을 중시한 미래지향 답변을 생성했습니다")
    print()

if __name__ == "__main__":
    main()
