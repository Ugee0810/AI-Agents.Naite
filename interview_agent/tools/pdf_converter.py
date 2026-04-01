"""PDF → YAML 변환 도구.

pdfplumber로 PDF 텍스트를 추출하고, 에이전트가 구조화할 수 있도록 저장합니다.
"""

import os
import pdfplumber
import yaml


def convert_pdf_to_yaml(pdf_filename: str) -> dict:
    """PDF 파일을 읽어 텍스트를 추출하고, data/ 폴더에 YAML 파일로 저장합니다.

    Args:
        pdf_filename: data/ 폴더 내의 PDF 파일명 (예: "resume.pdf", "career.pdf")

    Returns:
        추출된 텍스트와 저장 경로 정보를 담은 dict
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pdf_path = os.path.join(base_dir, "data", pdf_filename)

    if not os.path.exists(pdf_path):
        return {
            "status": "error",
            "message": f"PDF 파일을 찾을 수 없습니다: data/{pdf_filename}",
        }

    # PDF에서 텍스트 추출
    extracted_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n\n"
    except Exception as e:
        return {
            "status": "error",
            "message": f"PDF 읽기 실패: {str(e)}",
        }

    if not extracted_text.strip():
        return {
            "status": "error",
            "message": "PDF에서 텍스트를 추출할 수 없습니다. 스캔된 이미지 PDF일 수 있습니다.",
        }

    # 추출된 원본 텍스트를 임시 YAML로 저장
    stem = os.path.splitext(pdf_filename)[0]
    raw_yaml_path = os.path.join(base_dir, "data", f"{stem}_raw.yaml")
    raw_data = {"source_file": pdf_filename, "extracted_text": extracted_text.strip()}

    with open(raw_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(raw_data, f, allow_unicode=True, default_flow_style=False)

    # 문서 타입 판별
    doc_type = "履歴書" if "resume" in stem.lower() else "職務経歴書"

    return {
        "status": "success",
        "doc_type": doc_type,
        "extracted_text": extracted_text.strip(),
        "raw_yaml_path": f"data/{stem}_raw.yaml",
        "message": (
            f"{doc_type}의 텍스트 추출이 완료되었습니다."
            f"추출 텍스트를 확인하고, 구조화된 YAML로 변환하십시오."
            f"변환 후에는 data/{stem}.yaml 로 저장하십시오."
        ),
    }
