#!/usr/bin/env python3
"""
kor_medical 디렉토리의 JSON 파일들을 합치는 스크립트
10개 중 1개만 샘플링하여 id, content, title 필드를 가진 하나의 JSON 파일로 생성
"""

import json
import os
from pathlib import Path
import random

def merge_kor_medical_json(input_dir, output_file, sample_ratio=0.1):
    """
    kor_medical 디렉토리의 JSON 파일들을 합치는 함수
    
    Args:
        input_dir: 입력 디렉토리 경로 (datasets/kor_medical)
        output_file: 출력 JSON 파일 경로
        sample_ratio: 샘플링 비율 (기본값: 0.1 = 10개 중 1개)
    """
    input_path = Path(input_dir)
    merged_data = []
    
    # 모든 JSON 파일 찾기
    json_files = list(input_path.rglob("*.json"))
    print(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.")
    
    # 샘플링 (10개 중 1개)
    sample_size = int(len(json_files) * sample_ratio)
    sampled_files = random.sample(json_files, sample_size)
    print(f"{sample_size}개의 파일을 샘플링합니다.")
    
    # 각 JSON 파일 읽기
    for json_file in sampled_files:
        try:
            with open(json_file, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                
                # id, content, title 추출
                merged_item = {
                    "id": data.get("c_id", ""),
                    "content": data.get("content", ""),
                    "title": data.get("source_spec", "")  # source_spec을 title로 사용
                }
                
                # 필수 필드가 모두 있는 경우만 추가
                if merged_item["id"] and merged_item["content"]:
                    merged_data.append(merged_item)
                    
        except Exception as e:
            print(f"오류 발생 ({json_file}): {e}")
            continue
    
    # 결과를 JSON 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n완료! {len(merged_data)}개의 항목이 {output_file}에 저장되었습니다.")
    return len(merged_data)


if __name__ == "__main__":
    # 설정
    input_directory = "datasets/kor_medical"
    output_file = "datasets/kor_medical_merged.json"
    sample_ratio = 0.1  # 10개 중 1개
    
    # 재현성을 위한 시드 설정 (선택사항)
    # random.seed(42)
    
    # 실행
    merge_kor_medical_json(input_directory, output_file, sample_ratio)

