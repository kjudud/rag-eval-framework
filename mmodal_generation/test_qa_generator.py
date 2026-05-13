"""
QA Generator 테스트 코드
ocr_output 디렉토리를 입력으로 사용하여 QA 생성 수행

사용 방법:
cd mmodal_generation
python test_qa_generator.py --ocr-output-dir /home/jy/projects_wsl/02.RAG-eval-framework/mmodal_generation/ocr_output/test_2
"""

import os
import time
import argparse

from lora_tuned_qa_generator import Qwen3vlQaConfig, run_qa_generation

# from qa_generator import Qwen3vlQaConfig, run_qa_generation


def main(
    ocr_output_dir: str = "ocr_output",
    output_file: str = "data/qa_results.json",
    num_questions_per_document: int = 1,
    max_new_tokens: int = 1024,
    config_file: str = None,
):
    """메인 테스트 함수"""

    print("=" * 60)
    print("QA Generator 테스트 시작")
    print("=" * 60)

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
    print(f"발견된 PDF 수: {len(pdf_dirs)}개")

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

    print(f"\n총 PDF 수: {len(pdf_dirs)}개 / 총 페이지 수: {total_pages}개")

    # Config 설정
    print("\n" + "-" * 60)
    print("QA Generator 설정")
    print("-" * 60)
    config = Qwen3vlQaConfig(
        input_path=ocr_output_dir,
        output_path=output_file,
        num_questions_per_document=num_questions_per_document,
        max_new_tokens=max_new_tokens,
        config_file=config_file,
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
    total_start = time.time()

    try:
        # run_qa_generation 함수 호출
        qa_start = time.time()
        run_qa_generation(config)
        qa_elapsed = time.time() - qa_start
        total_elapsed = time.time() - total_start

        print("\n✓ QA 생성 완료")
        print(f"  QA 생성 소요 시간: {qa_elapsed:.1f}초 ({qa_elapsed/60:.1f}분)")

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
            total_qa_pairs = sum(len(doc.get("generated_qa_pairs", [])) for doc in data)

            print(f"처리된 문서 수: {total_docs}개")
            print(f"생성된 QA 쌍 수: {total_qa_pairs}개")
            if total_qa_pairs > 0:
                print(f"QA 쌍당 평균 생성 시간: {qa_elapsed/total_qa_pairs:.1f}초")

            # 시간 정보를 output_file에 기록

            timing_info = {
                "qa_elapsed_sec": round(qa_elapsed, 1),
                "total_elapsed_sec": round(total_elapsed, 1),
                "total_docs": total_docs,
                "total_qa_pairs": total_qa_pairs,
                "avg_sec_per_qa": (
                    round(qa_elapsed / total_qa_pairs, 1)
                    if total_qa_pairs > 0
                    else None
                ),
            }
            result_with_timing = {"timing": timing_info, "data": data}
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result_with_timing, f, ensure_ascii=False, indent=2)

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
        total_elapsed = time.time() - total_start
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("테스트 완료")
    print(f"총 소요 시간: {total_elapsed:.1f}초 ({total_elapsed/60:.1f}분)")
    print("=" * 60)
    print(f"TIMING:total:{total_elapsed:.1f}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="QA Generator 테스트: OCR 출력 디렉토리를 사용하여 QA 생성 수행"
    )
    parser.add_argument(
        "--ocr-output-dir",
        type=str,
        default="ocr_output",
        help="OCR 처리 결과 디렉토리 경로 (기본값: ocr_output)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="data/test_qa_results.json",
        help="QA 생성 결과 출력 파일 경로 (기본값: data/test_qa_results.json)",
    )
    parser.add_argument(
        "--num-questions",
        type=int,
        default=1,
        help="문서당 생성할 QA 쌍의 개수 (기본값: 1)",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=1024,
        help="최대 생성 토큰 수 (기본값: 1024)",
    )

    parser.add_argument(
        "--config-file",
        type=str,
        default=None,
        help="DataMorgana 설정 파일 경로 (기본값: datamorgana_config_template.json)",
    )

    args = parser.parse_args()

    main(
        ocr_output_dir=args.ocr_output_dir,
        output_file=args.output_file,
        num_questions_per_document=args.num_questions,
        max_new_tokens=args.max_new_tokens,
        config_file=args.config_file,
    )
