"""
OCR Processor 테스트 코드
pdfs_to_img 디렉토리를 입력으로 사용하여 OCR 처리 수행
"""

import os
from ocr_processor import OCRProcessor


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("OCR Processor 테스트 시작")
    print("=" * 60)

    # 입력 디렉토리 설정
    pdfs_to_img_dir = "pdfs_to_img"
    output_base_dir = "ocr_output"

    # 디렉토리 존재 확인
    if not os.path.exists(pdfs_to_img_dir):
        print(f"✗ 오류: '{pdfs_to_img_dir}' 디렉토리가 존재하지 않습니다.")
        return

    # pdfs_to_img 디렉토리 구조 확인
    pdf_dirs = [
        d
        for d in os.listdir(pdfs_to_img_dir)
        if os.path.isdir(os.path.join(pdfs_to_img_dir, d))
    ]

    if not pdf_dirs:
        print(f"✗ 오류: '{pdfs_to_img_dir}' 디렉토리에 PDF 디렉토리가 없습니다.")
        return

    print(f"\n입력 디렉토리: {pdfs_to_img_dir}")
    print(f"출력 디렉토리: {output_base_dir}")
    print(f"발견된 PDF 디렉토리: {len(pdf_dirs)}개")
    for pdf_dir in pdf_dirs:
        pdf_path = os.path.join(pdfs_to_img_dir, pdf_dir)
        image_files = [
            f
            for f in os.listdir(pdf_path)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp"))
        ]
        print(f"  - {pdf_dir}: {len(image_files)}개 이미지 파일")

    try:
        processor = OCRProcessor()
        print("✓ OCRProcessor 초기화 완료")
    except Exception as e:
        print(f"✗ OCRProcessor 초기화 실패: {e}")
        print("\n오류 원인:")
        print("  - GPU가 없거나 CUDA가 설치되지 않았을 수 있습니다.")
        print("  - 모델이 다운로드되지 않았을 수 있습니다.")
        print("  - 필요한 패키지가 설치되지 않았을 수 있습니다.")
        import traceback

        traceback.print_exc()
        return

    # OCR 처리 실행
    print("\n" + "-" * 60)
    print("OCR 처리 시작")
    print("-" * 60)

    try:
        # process_pdfs 메서드 사용
        # 주의: ocr_processor.py의 process_pdfs 메서드가 output_dir 파라미터를 제대로 사용하지 않을 수 있음
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
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
