"""AI-Agents.Naite CLI 엔트리 포인트.

python main.py 로 직접 실행합니다.
파일 상태를 확인하고, 준비가 완료되면 자동으로 면접 스크립트를 생성합니다.

v2.0 — 面接対策資料ナレッジ注入による高品質版
  新規追加: 自己紹介, 転職理由, 自己PR
  高度化: 志望動機, 今後何がしたいか, 逆質問
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
    GYAKU_SHITSUMON_PROMPT,
    PDF_CONVERSION_PROMPT,
    SYSTEM_PROMPT,
)


def _print_header():
    print("=" * 60)
    print("  面接準備エージェント / 면접 준비 에이전트")
    print("  AI-Agents.Naite v2.0 — 高品質版")
    print("=" * 60)
    print()


def _print_step(num: int, title_ja: str, title_ko: str):
    print(f"\n{'─' * 50}")
    print(f"  ステップ{num} / 스텝{num}: {title_ja} / {title_ko}")
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
                print(f"  ⚠️ 無料APIの制限(Rate Limit)に達しました。{wait_time}秒待機してから再試行します... ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print("  ❌ API制限(Rate Limit)による再試行上限に達しました。")
                raise e


def _build_context(resume: dict, career: dict, company: dict) -> str:
    """이력서, 직무경력서, 기업정보를 하나의 컨텍스트 문자열로 합성합니다."""
    return (
        "## 履歴書（이력서）\n"
        f"```yaml\n{yaml.dump(resume, allow_unicode=True, default_flow_style=False)}```\n\n"
        "## 職務経歴書（직무경력서）\n"
        f"```yaml\n{yaml.dump(career, allow_unicode=True, default_flow_style=False)}```\n\n"
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
) -> dict:
    """표준 생성 항목(자기소개, 지원동기, 전직이유, 향후목표)을 처리합니다."""
    _print_step(step_num, f"{title_ja}の作成", f"{title_ko} 작성")
    print("  🤖 生成中... / 생성 중...")

    response = _call_llm(SYSTEM_PROMPT, prompt + "\n\n" + context)
    response_yaml = _parse_yaml_from_response(response)

    try:
        data = yaml.safe_load(response_yaml)
    except yaml.YAMLError:
        data = {"ja": response_yaml, "ko": "(パース失敗)"}

    if isinstance(data, dict) and output_type in data:
        item = data[output_type]
    else:
        item = data if isinstance(data, dict) else {"ja": str(data), "ko": ""}

    save_output_yaml(
        output_type=output_type,
        ja_text=item.get("ja", ""),
        ko_text=item.get("ko", ""),
        key_points=item.get("key_points", []),
        estimated_duration=item.get("estimated_duration", ""),
    )
    print(f"  ✅ output/{output_type}.yaml 保存完了")
    return item


def main():
    _print_header()

    # ── 스텝 0: 준비 상태 확인 ──
    print("🔍 準備状態を確認中... / 준비 상태 확인 중...")
    status = check_preparation_status()

    if not status["ready"]:
        # 파일 부족 → 안내 메시지 출력 후 종료
        print("\n⚠️  面接準備に必要なファイルが不足しています。")
        print("⚠️  면접 준비에 필요한 파일이 부족합니다.\n")
        for msg in status["missing"]:
            print(f"  {msg}")
        print("\n準備ができたら、再度実行してください。")
        print("준비가 되면 다시 실행해주세요.")
        sys.exit(1)

    # ── PDF 변환이 필요한 경우 ──
    if status["needs_pdf_conversion"]:
        _print_step(0, "PDF変換", "PDF 변환")

        for stem in ["resume", "career"]:
            if status["status"].get(f"{stem}_pdf") and not status["status"].get(f"{stem}_yaml"):
                print(f"  🔄 {stem}.pdf → YAML 変換中...")
                result = convert_pdf_to_yaml(f"{stem}.pdf")

                if result["status"] == "error":
                    print(f"  ❌ エラー: {result['message']}")
                    sys.exit(1)

                # LLM을 사용하여 추출된 텍스트를 구조화된 YAML로 변환
                print(f"  🤖 LLMで構造化中...")
                prompt = PDF_CONVERSION_PROMPT.format(
                    doc_type=result["doc_type"],
                    text=result["extracted_text"],
                )
                structured = _call_llm(SYSTEM_PROMPT, prompt)
                yaml_content = _parse_yaml_from_response(structured)

                # 구조화된 YAML 저장
                import os
                base_dir = os.path.dirname(os.path.abspath(__file__))
                yaml_path = os.path.join(base_dir, "data", f"{stem}.yaml")
                with open(yaml_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)
                print(f"  ✅ data/{stem}.yaml 保存完了")

    # ── 스텝 1: 데이터 로드 ──
    _print_step(1, "データ読み込み", "데이터 로드")

    resume_result = load_yaml_data("data/resume.yaml")
    career_result = load_yaml_data("data/career.yaml")
    company_result = load_yaml_data("data/target_company.yaml")

    for name, r in [("履歴書", resume_result), ("職務経歴書", career_result), ("企業情報", company_result)]:
        if r["status"] == "error":
            print(f"  ❌ {name}: {r['message']}")
            sys.exit(1)
        print(f"  ✅ {name} 読み込み完了")

    context = _build_context(
        resume_result["data"],
        career_result["data"],
        company_result["data"],
    )

    # ── 스텝 2: 자기소개 생성 (신규) ──
    _generate_standard_item(2, "自己紹介", "자기소개", "jiko_shoukai", JIKO_SHOUKAI_PROMPT, context)

    # ── 스텝 3: 지원동기 생성 (고도화) ──
    _generate_standard_item(3, "志望動機", "지원동기", "shibou_douki", SHIBOU_DOUKI_PROMPT, context)

    # ── 스텝 4: 전직이유 생성 (신규) ──
    _generate_standard_item(4, "転職理由", "전직이유", "tensyoku_riyuu", TENSYOKU_RIYUU_PROMPT, context)

    # ── 스텝 5: 자기PR 생성 (신규) ──
    _print_step(5, "自己PRの作成", "자기PR 작성")
    print("  🤖 生成中... / 생성 중...")

    jiko_pr_response = _call_llm(SYSTEM_PROMPT, JIKO_PR_PROMPT + "\n\n" + context)
    jiko_pr_yaml = _parse_yaml_from_response(jiko_pr_response)

    try:
        jiko_pr_data = yaml.safe_load(jiko_pr_yaml)
    except yaml.YAMLError:
        jiko_pr_data = {"jiko_pr": {"strengths": {"ja": jiko_pr_yaml, "ko": "(パース失敗)"}}}

    if isinstance(jiko_pr_data, dict) and "jiko_pr" in jiko_pr_data:
        jp = jiko_pr_data["jiko_pr"]
    else:
        jp = jiko_pr_data if isinstance(jiko_pr_data, dict) else {}

    # jiko_pr는 strengths/weakness 복합 구조이므로 raw_data로 저장
    save_output_yaml(output_type="jiko_pr", raw_data={"jiko_pr": jp})
    print("  ✅ output/jiko_pr.yaml 保存完了")

    # ── 스텝 6: 향후 목표 생성 (고도화) ──
    _generate_standard_item(6, "今後何がしたいか", "향후 목표", "kongo_nanika", KONGO_NANIKA_PROMPT, context)

    # ── 스텝 7: 역질문 생성 (고도화) ──
    _print_step(7, "逆質問の作成", "역질문 작성")
    print("  🤖 生成中... / 생성 중...")

    gyaku_response = _call_llm(SYSTEM_PROMPT, GYAKU_SHITSUMON_PROMPT + "\n\n" + context)
    gyaku_yaml = _parse_yaml_from_response(gyaku_response)

    try:
        gyaku_data = yaml.safe_load(gyaku_yaml)
    except yaml.YAMLError:
        gyaku_data = {}

    if isinstance(gyaku_data, dict) and "gyaku_shitsumon" in gyaku_data:
        gq = gyaku_data["gyaku_shitsumon"]
    else:
        gq = gyaku_data if isinstance(gyaku_data, dict) else {}

    questions = gq.get("questions", [])
    if questions:
        save_output_yaml(
            output_type="gyaku_shitsumon",
            questions_ja=[q.get("ja", "") for q in questions],
            questions_ko=[q.get("ko", "") for q in questions],
            questions_intent=[q.get("intent", "") for q in questions],
        )
    else:
        # fallback: 파싱 실패 시 원본 텍스트 저장
        save_output_yaml(
            output_type="gyaku_shitsumon",
            questions_ja=[gyaku_yaml],
            questions_ko=["(パース失敗)"],
        )
    print("  ✅ output/gyaku_shitsumon.yaml 保存完了")

    # ── 완료 ──
    print(f"\n{'=' * 60}")
    print("  ✅ すべての面接準備が完了しました！")
    print("  ✅ 모든 면접 준비가 완료되었습니다!")
    print(f"{'=' * 60}")
    print("\n📁 生成されたファイル / 생성된 파일:")
    print("  - output/jiko_shoukai.yaml    (自己紹介 / 자기소개)")
    print("  - output/shibou_douki.yaml    (志望動機 / 지원동기)")
    print("  - output/tensyoku_riyuu.yaml  (転職理由 / 전직이유)")
    print("  - output/jiko_pr.yaml         (自己PR / 자기PR)")
    print("  - output/kongo_nanika.yaml    (今後何がしたいか / 향후 목표)")
    print("  - output/gyaku_shitsumon.yaml (逆質問 / 역질문)")
    print()


if __name__ == "__main__":
    main()
