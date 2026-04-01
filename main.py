"""AI-Agents.Naite CLI 엔트리 포인트.

python main.py 로 직접 실행합니다.
파일 상태를 확인하고, 준비가 완료되면 자동으로 면접 스크립트를 생성합니다.
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
    SHIBOU_DOUKI_PROMPT,
    KONGO_NANIKA_PROMPT,
    GYAKU_SHITSUMON_PROMPT,
    PDF_CONVERSION_PROMPT,
    SYSTEM_PROMPT,
)


def _print_header():
    print("=" * 60)
    print("  面接準備エージェント / 면접 준비 에이전트")
    print("  AI-Agents.Naite v1.0")
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

    # ── 스텝 2: 지원동기 생성 ──
    _print_step(2, "志望動機の作成", "지원동기 작성")
    print("  🤖 生成中... / 생성 중...")

    shibou_response = _call_llm(SYSTEM_PROMPT, SHIBOU_DOUKI_PROMPT + "\n\n" + context)
    shibou_yaml = _parse_yaml_from_response(shibou_response)

    try:
        shibou_data = yaml.safe_load(shibou_yaml)
    except yaml.YAMLError:
        shibou_data = {"ja": shibou_yaml, "ko": "(パース失敗)"}

    if isinstance(shibou_data, dict) and "shibou_douki" in shibou_data:
        sd = shibou_data["shibou_douki"]
    else:
        sd = shibou_data if isinstance(shibou_data, dict) else {"ja": str(shibou_data), "ko": ""}

    save_output_yaml(
        output_type="shibou_douki",
        ja_text=sd.get("ja", ""),
        ko_text=sd.get("ko", ""),
        key_points=sd.get("key_points", []),
        estimated_duration=sd.get("estimated_duration", ""),
    )
    print("  ✅ output/shibou_douki.yaml 保存完了")

    # ── 스텝 3: 향후 목표 생성 ──
    _print_step(3, "今後何がしたいかの作成", "향후 목표 작성")
    print("  🤖 生成中... / 생성 중...")

    kongo_response = _call_llm(SYSTEM_PROMPT, KONGO_NANIKA_PROMPT + "\n\n" + context)
    kongo_yaml = _parse_yaml_from_response(kongo_response)

    try:
        kongo_data = yaml.safe_load(kongo_yaml)
    except yaml.YAMLError:
        kongo_data = {"ja": kongo_yaml, "ko": "(パース失敗)"}

    if isinstance(kongo_data, dict) and "kongo_nanika" in kongo_data:
        kn = kongo_data["kongo_nanika"]
    else:
        kn = kongo_data if isinstance(kongo_data, dict) else {"ja": str(kongo_data), "ko": ""}

    save_output_yaml(
        output_type="kongo_nanika",
        ja_text=kn.get("ja", ""),
        ko_text=kn.get("ko", ""),
        key_points=kn.get("key_points", []),
    )
    print("  ✅ output/kongo_nanika.yaml 保存完了")

    # ── 스텝 4: 역질문 생성 ──
    _print_step(4, "逆質問の作成", "역질문 작성")
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
            ja_text="",
            ko_text="",
            questions_ja=[q.get("ja", "") for q in questions],
            questions_ko=[q.get("ko", "") for q in questions],
        )
    else:
        # fallback: 파싱 실패 시 원본 텍스트 저장
        save_output_yaml(
            output_type="gyaku_shitsumon",
            ja_text="",
            ko_text="",
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
    print("  - output/shibou_douki.yaml   (志望動機 / 지원동기)")
    print("  - output/kongo_nanika.yaml   (今後何がしたいか / 향후 목표)")
    print("  - output/gyaku_shitsumon.yaml (逆質問 / 역질문)")
    print()


if __name__ == "__main__":
    main()
