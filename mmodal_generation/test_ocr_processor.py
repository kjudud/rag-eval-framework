"""
OCR Processor 테스트 코드
PDF 디렉토리를 이미지로 변환하고 OCR 처리 수행
"""

import os
import argparse
from ocr_processor import OCRProcessor


def main(
    pdf_dir: str = "pdfs",
    pdfs_to_img_dir: str = "pdfs_to_img",
    output_base_dir: str = "ocr_output",
):
    """
    OCR Processor 테스트 메인 함수

    Args:
        pdf_dir: PDF 파일들이 있는 디렉토리 경로
        pdfs_to_img_dir: PDF를 이미지로 변환한 결과 저장 디렉토리 경로
        output_base_dir: OCR 처리 결과 출력 디렉토리 경로
    """
    print("=" * 60)

    # PDF 디렉토리 존재 확인
    if not os.path.exists(pdf_dir):
        print(f"✗ 오류: '{pdf_dir}' 디렉토리가 존재하지 않습니다.")
        return

    print(f"\nPDF 디렉토리: {pdf_dir}")
    print(f"OCR 출력 디렉토리: {output_base_dir}")
    print("\n" + "-" * 60)
    print("OCRProcessor 초기화")
    print("-" * 60)

    try:
        processor = OCRProcessor()
        print("✓ OCRProcessor 초기화 완료")
    except Exception as e:
        print(f"✗ OCRProcessor 초기화 실패: {e}")

        import traceback

        traceback.print_exc()
        print("\n✗ OCRProcessor 초기화가 실패하여 PDF 변환을 수행할 수 없습니다.")
        return

    # PDF를 이미지로 변환 (processor 초기화 성공 후에만 수행)
    print("\n" + "-" * 60)
    print("PDF를 이미지로 변환 시작")
    print("-" * 60)

    try:
        result = processor.convert_pdfs(
            pdf_dir=pdf_dir, output_dir=pdfs_to_img_dir, dpi=300
        )
        print("\n✓ PDF 변환 완료")
        print(f"  - 처리된 PDF 파일: {result['total_pdfs']}개")
        print(f"  - 생성된 이미지: {result['total_images']}개")

    except Exception as e:
        print(f"\n✗ PDF 변환 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return

    # pdfs_to_img 디렉토리 구조 확인
    if not os.path.exists(pdfs_to_img_dir):
        print(f"\n✗ 오류: '{pdfs_to_img_dir}' 디렉토리가 생성되지 않았습니다.")
        return

    pdf_dirs = [
        d
        for d in os.listdir(pdfs_to_img_dir)
        if os.path.isdir(os.path.join(pdfs_to_img_dir, d))
    ]

    if not pdf_dirs:
        print(f"\n✗ 오류: '{pdfs_to_img_dir}' 디렉토리에 이미지 디렉토리가 없습니다.")
        return

    print(f"\n변환된 이미지 디렉토리: {len(pdf_dirs)}개")
    for pdf_dir_name in pdf_dirs:
        pdf_path = os.path.join(pdfs_to_img_dir, pdf_dir_name)
        image_files = [
            f
            for f in os.listdir(pdf_path)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp"))
        ]
        print(f"  - {pdf_dir_name}: {len(image_files)}개 이미지 파일")

    # OCR 처리 실행
    print("\n" + "-" * 60)
    print("OCR 처리 시작")
    print("-" * 60)

    try:
        # process_pdfs 메서드 사용
        processor.process_pdfs(pdfs_dir=pdfs_to_img_dir, output_dir=output_base_dir)

        print("\n✓ OCR 처리 완료")

        # 결과 확인
        print("\n" + "-" * 60)
        print("처리 결과 확인")
        print("-" * 60)

        if os.path.exists(output_base_dir):
            output_dirs = [
                d
                for d in os.listdir(output_base_dir)
                if os.path.isdir(os.path.join(output_base_dir, d))
            ]
            print(f"생성된 출력 디렉토리: {len(output_dirs)}개")
            for out_dir in output_dirs:
                out_path = os.path.join(output_base_dir, out_dir)
                files = os.listdir(out_path) if os.path.exists(out_path) else []
                print(f"  - {out_dir}: {len(files)}개 파일")
        else:
            print(f"⚠ 출력 디렉토리가 생성되지 않았습니다: {output_base_dir}")
            print("  ocr_processor.py의 process_pdfs 메서드를 확인하세요.")

    except Exception as e:
        print(f"\n✗ OCR 처리 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OCR Processor 테스트: PDF를 이미지로 변환하고 OCR 처리 수행"
    )
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="pdfs",
        help="PDF 파일들이 있는 디렉토리 경로 (기본값: pdfs)",
    )
    parser.add_argument(
        "--pdfs-to-img-dir",
        type=str,
        default="pdfs_to_img",
        help="PDF를 이미지로 변환한 결과 저장 디렉토리 경로 (기본값: pdfs_to_img)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="ocr_output",
        help="OCR 처리 결과 출력 디렉토리 경로 (기본값: ocr_output)",
    )

    args = parser.parse_args()

    main(
        pdf_dir=args.pdf_dir,
        pdfs_to_img_dir=args.pdfs_to_img_dir,
        output_base_dir=args.output_dir,
    )
