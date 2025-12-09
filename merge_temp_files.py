#!/usr/bin/env python3
"""
임시 파일들을 하나로 합치는 스크립트
generated_qa_data.json_temp*.json 파일들을 찾아서 합칩니다.
"""

import json
import glob
import os
import argparse
from typing import List, Dict, Any


def merge_temp_files(output_dir: str = "streamlit", output_name: str = "generated_qa_data.json"):
    """임시 파일들을 찾아서 하나로 합칩니다.
    
    Args:
        output_dir: 임시 파일이 있는 디렉토리
        output_name: 최종 출력 파일명
    """
    # 임시 파일 패턴
    pattern = os.path.join(output_dir, f"{output_name}_temp*.json")
    temp_files = sorted(glob.glob(pattern))
    
    if not temp_files:
        print(f"❌ 임시 파일을 찾을 수 없습니다: {pattern}")
        return
    
    print(f"📁 {len(temp_files)}개의 임시 파일을 찾았습니다:")
    for temp_file in temp_files:
        print(f"  - {os.path.basename(temp_file)}")
    
    # 모든 임시 파일을 합치기
    merged_results = []
    
    for temp_file in temp_files:
        try:
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if isinstance(data, list):
                    merged_results.extend(data)
            
        except Exception as e:
            print(f"❌ 파일 로드 실패 ({os.path.basename(temp_file)}): {e}")
    
    # 중복 제거 (같은 id를 가진 문서는 하나만 유지)
    seen_ids = set()
    unique_results = []
    duplicate_count = 0
    
    for doc in merged_results:
        doc_id = doc.get('id', '')
        if doc_id in seen_ids:
            duplicate_count += 1
            continue
        if doc_id:
            seen_ids.add(doc_id)
        unique_results.append(doc)
    
    if duplicate_count > 0:
        print(f"⚠️  중복 문서 {duplicate_count}개 제거됨")
    
    # 최종 파일로 저장
    final_output_path = os.path.join(output_dir, "merged_qa_data.json")
    
    try:
        with open(final_output_path, 'w', encoding='utf-8') as f:
            json.dump(unique_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 병합 완료!")
        print(f"📊 통계:")
        print(f"  - 총 문서 수: {len(unique_results)}")
        print(f"  - 최종 파일: {final_output_path}")
        print(f"  - 파일 크기: {os.path.getsize(final_output_path):,} bytes")
        
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")


def main():
    parser = argparse.ArgumentParser(description='임시 파일들을 하나로 합치는 스크립트')
    parser.add_argument('--output_dir', type=str, default='streamlit',
                       help='임시 파일이 있는 디렉토리 (기본값: streamlit)')
    parser.add_argument('--output_name', type=str, default='generated_qa_data.json',
                       help='최종 출력 파일명 (기본값: generated_qa_data.json)')
    args = parser.parse_args()
    
    merge_temp_files(args.output_dir, args.output_name)


if __name__ == "__main__":
    main()

