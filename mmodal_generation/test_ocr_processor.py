"""
OCR Processor 테스트 코드
PDF 디렉토리를 이미지로 변환하고 OCR 처리 수행
"""

import os
import json
import argparse
import time
import fitz
from ocr_processor import OCRProcessor


def analyze_pdfs(pdf_dir: str):
    """PDF 디렉토리의 총 페이지 수 및 파일 크기 분포 분석"""
    pdf_files = sorted(
        [
            f
            for f in os.listdir(pdf_dir)
            if os.path.isfile(os.path.join(pdf_dir, f)) and f.lower().endswith(".pdf")
        ]
    )
    if not pdf_files:
        print("  PDF 파일 없음")
        return

    total_pages = 0
    file_sizes_mb = []

    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        file_sizes_mb.append(os.path.getsize(pdf_path) / (1024 * 1024))
        try:
            doc = fitz.open(pdf_path)
            total_pages += len(doc)
            doc.close()
        except Exception as e:
            print(f"  ⚠ {pdf_file} 분석 실패: {e}")

    total_mb = sum(file_sizes_mb)
    avg_mb = total_mb / len(file_sizes_mb)

    print(f"  총 PDF 파일 수: {len(pdf_files)}개")
    print(f"  총 페이지 수: {total_pages}페이지")

    buckets = [
        ("<1 MB",    lambda s: s < 1),
        ("1~5 MB",   lambda s: 1 <= s < 5),
        ("5~10 MB",  lambda s: 5 <= s < 10),
        ("10~20 MB", lambda s: 10 <= s < 20),
        ("≥20 MB",   lambda s: s >= 20),
    ]
    size_dist = {label: sum(1 for s in file_sizes_mb if cond(s)) for label, cond in buckets}

    print(f"\n  [파일 크기 분포]")
    for label, count in size_dist.items():
        if count:
            print(f"    {label}: {count}개")
    print(
        f"    → 평균: {avg_mb:.1f} MB  최소: {min(file_sizes_mb):.1f} MB  "
        f"최대: {max(file_sizes_mb):.1f} MB  합계: {total_mb:.1f} MB"
    )

    # Streamlit 파싱용 JSON 마커 출력
    stats = {
        "total_pdfs": len(pdf_files),
        "total_pages": total_pages,
        "avg_mb": round(avg_mb, 1),
        "min_mb": round(min(file_sizes_mb), 1),
        "max_mb": round(max(file_sizes_mb), 1),
        "total_mb": round(total_mb, 1),
        "size_dist": {k: v for k, v in size_dist.items() if v > 0},
    }
    print(f"PDF_STATS:{json.dumps(stats, ensure_ascii=False)}", flush=True)


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

    # PDF 분석 (OCR 전에 수행)
    print("\n" + "-" * 60)
    print("PDF 분석")
    print("-" * 60)
    analyze_pdfs(pdf_dir)

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
    total_start = time.time()
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

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 60)
    print(f"총 소요 시간: {total_elapsed:.1f}초 ({total_elapsed/60:.1f}분)")
    print("=" * 60)
    print(f"TIMING:total:{total_elapsed:.1f}", flush=True)


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
