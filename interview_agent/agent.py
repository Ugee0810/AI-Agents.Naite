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
