"""
OCR 처리 모듈 - DeepSeek-OCR을 사용하여 이미지를 markdown으로 변환
"""

import os
import torch
from transformers import AutoModel, AutoTokenizer
from dataclasses import dataclass


@dataclass
class DeepSeekOCRConfig:
    # infer(self, tokenizer, prompt='', image_file='', output_path = ' ', base_size = 1024, image_size = 640, crop_mode = True, test_compress = False, save_results = False):

    # Tiny: base_size = 512, image_size = 512, crop_mode = False
    # Small: base_size = 640, image_size = 640, crop_mode = False
    # Base: base_size = 1024, image_size = 1024, crop_mode = False
    # Large: base_size = 1280, image_size = 1280, crop_mode = False
    # Gundam: base_size = 1024, image_size = 640, crop_mode = True
    model_name: str = "deepseek-ai/DeepSeek-OCR"
    base_size: int = 1024
    image_size: int = 1024
    crop_mode: bool = False
    cuda_visible_devices: str = "0"  # default to first GPU


class OCRProcessor:
    def __init__(self, config: DeepSeekOCRConfig | None = None):
        if config is None:
            config = DeepSeekOCRConfig()
        self.config = config
        """OCR 모델 초기화"""
        os.environ["CUDA_VISIBLE_DEVICES"] = self.config.cuda_visible_devices

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name, trust_remote_code=True
        )
        self.model = AutoModel.from_pretrained(
            self.config.model_name,
            _attn_implementation="flash_attention_2",
            trust_remote_code=True,
            use_safetensors=True,
        )
        self.model = self.model.eval().cuda().to(torch.bfloat16)

    def process_pdf_page(
        self, pdf_page_path: str, output_dir: str, prompt: str = None
    ) -> dict:
        """
        단일 이미지를 markdown으로 변환

        Args:
            image_file: 입력 이미지 파일 경로
            output_path: 출력 디렉토리 경로
            prompt: OCR 프롬프트 (기본값: markdown 변환 프롬프트)

        Returns:
            {
                "markdown_path": "ocr_output/result.mmd",
                "images_dir": "ocr_output/images/",
                "original_image": "원본 이미지 경로"
            }
        """
        prompt = "<image>\n<|grounding|>Convert the document to markdown."

        # 출력 디렉토리 생성
        # 파일 이름만 가져오기 (확장자 제외)
        pdf_page_name = os.path.splitext(os.path.basename(pdf_page_path))[0]
        output_path = os.path.join(output_dir, pdf_page_name)
        os.makedirs(output_path, exist_ok=True)

        # OCR 실행
        self.model.infer(
            self.tokenizer,
            prompt=prompt,
            image_file=pdf_page_path,
            output_path=output_path,
            base_size=self.config.base_size,
            image_size=self.config.image_size,
            crop_mode=self.config.crop_mode,
            save_results=True,
            test_compress=True,
        )

    def process_pdf_pages(self, pdf_dir: str, output_dir: str) -> list:
        """
        여러 이미지를 배치 처리

        Args:
            image_files: 입력 이미지 파일 경로 리스트
            output_base_dir: 출력 기본 디렉토리

        Returns:
            각 이미지의 처리 결과 리스트
        """
        for page in os.listdir(pdf_dir):
            pdf_page_path = os.path.join(pdf_dir, page)
            self.process_pdf_page(pdf_page_path, output_dir)

    def process_pdfs(self, pdfs_dir: str, output_dir: str) -> None:
        for pdf_dir in os.listdir(pdfs_dir):
            pdf_dir_path = os.path.join(pdfs_dir, pdf_dir)
            if os.path.isdir(pdf_dir_path):
                output_pdf_dir = os.path.join(output_dir, pdf_dir)
                self.process_pdf_pages(pdf_dir_path, output_pdf_dir)
