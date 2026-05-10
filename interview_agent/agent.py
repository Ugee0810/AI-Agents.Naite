"""InterviewAssistant 메인 에이전트 정의.

일본 전직 면접 준비를 위한 AI 코치 에이전트입니다.

v2.0 — 面接対策資料ナレッジ注入による高品質版
  6つの面接回答（自己紹介、志望動機、転職理由、自己PR、今後の展望、逆質問）を自動生成
"""

from google.adk.agents import Agent

from .config import get_model_name
from .prompts import INTERVIEW_COACH_PROMPT
from .tools.pdf_converter import convert_pdf_to_yaml
from .tools.file_loader import check_preparation_status, load_yaml_data
from .tools.output_writer import save_output_yaml

root_agent = Agent(
    model=get_model_name(),
    name="interview_coach",
    description=(
        "日本での転職面接準備を支援するAIコーチ。"
        "面接対策のプロが監修したナレッジベースに基づき、"
        "自己紹介・志望動機・転職理由・自己PR・今後の展望・逆質問を高品質で自動生成します。"
    ),
    instruction=INTERVIEW_COACH_PROMPT,
    tools=[
        check_preparation_status,
        convert_pdf_to_yaml,
        load_yaml_data,
        save_output_yaml,
    ],
)
