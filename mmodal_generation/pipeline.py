"""
전체 파이프라인 - OCR 및 QA 생성 프로세스 오케스트레이션
"""
import os
import json
from typing import List, Dict
from ocr_processor import OCRProcessor
from qa_generator import QAGenerator
from config import OCR_OUTPUT_DIR, QA_OUTPUT_DIR, DEFAULT_QA_COUNT


class MultimodalQAPipeline:
    """멀티모달 QA 데이터셋 생성 파이프라인"""
    
    def __init__(self):
        """파이프라인 초기화"""
        self.ocr_processor = OCRProcessor()
        self.qa_generator = QAGenerator()
    
    def process_single_page(
        self,
        image_file: str,
        output_dir: str = None,
        qa_count: int = None,
        page_id: str = None
    ) -> Dict:
        """
        단일 페이지 처리
        
        Args:
            image_file: 입력 이미지 파일 경로
            output_dir: 출력 디렉토리 (기본값: OCR_OUTPUT_DIR)
            qa_count: 생성할 QA 개수
            page_id: 페이지 ID (기본값: 자동 생성)
        
        Returns:
            처리 결과 딕셔너리
        """
        if output_dir is None:
            output_dir = OCR_OUTPUT_DIR
        
        if qa_count is None:
            qa_count = DEFAULT_QA_COUNT
        
        print(f"처리 중: {image_file}")
        
        # 1. OCR 처리
        print("  - OCR 처리 중...")
        ocr_result = self.ocr_processor.process_image(
            image_file=image_file,
            output_path=output_dir
        )
        
        if page_id:
            ocr_result["page_id"] = page_id
        
        # 2. QA 생성
        print("  - QA 생성 중...")
        qa_pairs = self.qa_generator.generate_qa(
            markdown_path=ocr_result["markdown_path"],
            images_dir=ocr_result["images_dir"],
            original_image_path=ocr_result["original_image"],
            qa_count=qa_count
        )
        
        # 3. 결과 통합
        result = {
            "page_id": ocr_result.get("page_id", "page_1"),
            "original_image": ocr_result["original_image"],
            "markdown_path": ocr_result["markdown_path"],
            "images_dir": ocr_result["images_dir"],
            "qa_pairs": qa_pairs
        }
        
        print(f"  - 완료: {len(qa_pairs)}개의 QA 생성됨")
        
        return result
    
    def process_multiple_pages(
        self,
        image_files: List[str],
        output_base_dir: str = None,
        qa_count: int = None
    ) -> List[Dict]:
        """
        여러 페이지 배치 처리
        
        Args:
            image_files: 입력 이미지 파일 경로 리스트
            output_base_dir: 출력 기본 디렉토리
            qa_count: 각 페이지당 생성할 QA 개수
        
        Returns:
            처리 결과 리스트
        """
        if output_base_dir is None:
            output_base_dir = OCR_OUTPUT_DIR
        
        if qa_count is None:
            qa_count = DEFAULT_QA_COUNT
        
        results = []
        total_pages = len(image_files)
        
        print(f"총 {total_pages}개 페이지 처리 시작")
        
        for idx, image_file in enumerate(image_files):
            page_id = f"page_{idx + 1}"
            print(f"\n[{idx + 1}/{total_pages}] {page_id}")
            
            # 각 페이지별로 별도 디렉토리 사용
            page_output_dir = os.path.join(output_base_dir, page_id)
            
            try:
                result = self.process_single_page(
                    image_file=image_file,
                    output_dir=page_output_dir,
                    qa_count=qa_count,
                    page_id=page_id
                )
                results.append(result)
            except Exception as e:
                print(f"  오류 발생: {e}")
                # 오류가 발생해도 계속 진행
                results.append({
                    "page_id": page_id,
                    "original_image": image_file,
                    "error": str(e),
                    "qa_pairs": []
                })
        
        print(f"\n처리 완료: {len(results)}개 페이지")
        
        return results
    
    def save_dataset(self, results: List[Dict], output_path: str = None):
        """
        QA 데이터셋을 JSON 파일로 저장
        
        Args:
            results: 처리 결과 리스트
            output_path: 출력 파일 경로 (기본값: QA_OUTPUT_DIR/qa_dataset.json)
        """
        if output_path is None:
            os.makedirs(QA_OUTPUT_DIR, exist_ok=True)
            output_path = os.path.join(QA_OUTPUT_DIR, "qa_dataset.json")
        
        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # JSON 저장
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n데이터셋 저장 완료: {output_path}")
        print(f"총 {len(results)}개 페이지, {sum(len(r.get('qa_pairs', [])) for r in results)}개 QA")


def main():
    """메인 실행 함수"""
    import sys
    
    # 명령줄 인자 처리
    if len(sys.argv) < 2:
        print("사용법: python pipeline.py <이미지_파일1> [이미지_파일2] ...")
        print("예시: python pipeline.py image1.png image2.png")
        sys.exit(1)
    
    image_files = sys.argv[1:]
    
    # 파이프라인 실행
    pipeline = MultimodalQAPipeline()
    results = pipeline.process_multiple_pages(image_files)
    pipeline.save_dataset(results)


if __name__ == "__main__":
    main()

