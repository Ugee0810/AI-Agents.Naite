"""YAML 데이터 로드 및 준비 상태 확인 도구.

이력서, 직무경력서, 기업 정보 YAML 파일을 읽어 에이전트에게 제공합니다.
파일 존재 여부를 확인하여 에이전트가 자동으로 워크플로를 진행하도록 돕습니다.
"""

import os
import yaml


def _get_base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_preparation_status() -> dict:
    """면접 준비에 필요한 모든 파일의 존재 여부를 확인합니다.

    에이전트가 최초 실행 시 이 도구를 호출하여 현재 상태를 파악하고,
    누락된 파일에 대한 안내 메시지를 유저에게 전달합니다.

    Returns:
        각 파일의 존재 여부와 다음 단계 안내를 담은 dict.
    """
    base_dir = _get_base_dir()

    files = {
        "resume_pdf": os.path.join(base_dir, "data", "resume.pdf"),
        "career_pdf": os.path.join(base_dir, "data", "career.pdf"),
        "resume_yaml": os.path.join(base_dir, "data", "resume.yaml"),
        "career_yaml": os.path.join(base_dir, "data", "career.yaml"),
        "target_company": os.path.join(base_dir, "data", "target_company.yaml"),
    }

    status = {key: os.path.exists(path) for key, path in files.items()}

    # 다음 단계 결정
    missing = []

    # 이력서: YAML이 있으면 PDF 불필요 (스킵)
    if not status["resume_yaml"]:
        if not status["resume_pdf"]:
            missing.append(
                "📄 履歴書(이력서): data/resume.pdf 를 배치하십시오."
            )

    if not status["career_yaml"]:
        if not status["career_pdf"]:
            missing.append(
                "📄 職務経歴書(직무경력서): data/career.pdf 를 배치하십시오."
            )

    if not status["target_company"]:
        missing.append(
            "🏢 応募先企業情報(지원 기업 정보): "
            "templates/target_company_template.yaml 를 data/target_company.yaml 에 복사하여, "
            "내용을 기입하십시오."
        )

    ready = len(missing) == 0

    return {
        "status": status,
        "ready": ready,
        "missing": missing,
        "needs_pdf_conversion": (
            (status["resume_pdf"] and not status["resume_yaml"])
            or (status["career_pdf"] and not status["career_yaml"])
        ),
    }


def load_yaml_data(file_path: str) -> dict:
    """YAML 파일을 읽어 dict로 반환합니다.

    Args:
        file_path: 프로젝트 루트 기준 상대 경로 (예: "data/resume.yaml")

    Returns:
        YAML 파일의 내용을 담은 dict. 에러 시 에러 정보를 포함한 dict.
    """
    base_dir = _get_base_dir()
    abs_path = os.path.join(base_dir, file_path)

    if not os.path.exists(abs_path):
        return {
            "status": "error",
            "message": f"파일을 찾을 수 없습니다: {file_path}",
        }

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {
            "status": "success",
            "file_path": file_path,
            "data": data,
        }
    except yaml.YAMLError as e:
        return {
            "status": "error",
            "message": f"YAML 분석 에러: {str(e)}",
        }
