"""
QA Generator 테스트 코드
ocr_output 디렉토리를 입력으로 사용하여 QA 생성 수행
"""

import os
from qa_generator import Qwen3vlQaConfig, run_qa_generation


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("QA Generator 테스트 시작")
    print("=" * 60)

    # 입력 디렉토리 설정
    ocr_output_dir = "ocr_output"
    output_file = "data/test_qa_results.json"

    # 디렉토리 존재 확인
    if not os.path.exists(ocr_output_dir):
        print(f"✗ 오류: '{ocr_output_dir}' 디렉토리가 존재하지 않습니다.")
        return

    # ocr_output 디렉토리 구조 확인
    pdf_dirs = [
        d
        for d in os.listdir(ocr_output_dir)
        if os.path.isdir(os.path.join(ocr_output_dir, d))
    ]

    if not pdf_dirs:
        print(f"✗ 오류: '{ocr_output_dir}' 디렉토리에 PDF 디렉토리가 없습니다.")
        return

    print(f"\n입력 디렉토리: {ocr_output_dir}")
    print(f"출력 파일: {output_file}")
    print(f"발견된 PDF 디렉토리: {len(pdf_dirs)}개")

    # 각 PDF 디렉토리의 페이지 수 확인
    total_pages = 0
    for pdf_dir in pdf_dirs:
        pdf_path = os.path.join(ocr_output_dir, pdf_dir)
        page_dirs = [
            d for d in os.listdir(pdf_path) if os.path.isdir(os.path.join(pdf_path, d))
        ]
        page_count = len(page_dirs)
        total_pages += page_count
        print(f"  - {pdf_dir}: {page_count}개 페이지")

    print(f"\n총 {total_pages}개 페이지 발견")

    # Config 설정
    print("\n" + "-" * 60)
    print("QA Generator 설정")
    print("-" * 60)
    config = Qwen3vlQaConfig(
        input_path=ocr_output_dir,
        output_path=output_file,
        num_questions_per_document=1,  # 테스트용으로 1개만 생성
        max_new_tokens=256,
    )
    print(f"모델: {config.model_name}")
    print(f"입력 경로: {config.input_path}")
    print(f"출력 경로: {config.output_path}")
    print(f"문서당 질문 수: {config.num_questions_per_document}")
    print(f"최대 생성 토큰 수: {config.max_new_tokens}")
    print(f"설정 파일: {config.config_file}")

    # QA 생성 실행
    print("\n" + "-" * 60)
    print("QA 생성 시작")
    print("-" * 60)

    try:
        # run_qa_generation 함수 호출
        run_qa_generation(config)


        print("\n✓ QA 생성 완료")

        # 결과 확인
        print("\n" + "-" * 60)
        print("처리 결과 확인")
        print("-" * 60)

        if os.path.exists(output_file):
            print(f"✓ 출력 파일 생성: {output_file}")
            import json

            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            total_docs = len(data)
            total_qa_pairs = sum(
                len(doc.get("generated_qa_pairs", [])) for doc in data
            )

            print(f"처리된 문서 수: {total_docs}개")
            print(f"생성된 QA 쌍 수: {total_qa_pairs}개")

            # 샘플 QA 쌍 출력
            if total_qa_pairs > 0:
                print("\n샘플 QA 쌍:")
                sample_count = 0
                for doc in data:
                    qa_pairs = doc.get("generated_qa_pairs", [])
                    if qa_pairs:
                        qa = qa_pairs[0]
                        print(f"\n  문서 ID: {doc.get('id', 'unknown')}")
                        print(f"  질문: {qa.get('question', 'N/A')[:100]}...")
                        print(f"  답변: {qa.get('answer', 'N/A')[:100]}...")
                        sample_count += 1
                        if sample_count >= 3:  # 최대 3개만 표시
                            break

    except Exception as e:
        print(f"\n✗ QA 생성 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
