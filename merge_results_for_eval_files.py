#!/usr/bin/env python3
"""
generated_qa_data_1.json ~ generated_qa_data_5.json 파일들을 하나로 합치는 스크립트
"""

import json
import os
import argparse
from typing import List, Dict, Any


def merge_generated_qa_files(input_dir: str = "streamlit", output_file: str = "streamlit/results_for_eval.json"):
    """여러 generated_qa_data_*.json 파일들을 하나로 합칩니다.
    
    Args:
        input_dir: 입력 파일들이 있는 디렉토리
        output_file: 최종 출력 파일 경로
    """
    # 합칠 파일 목록
    file_names = [
        "results_for_eval_1.json",
        "results_for_eval_2.json",
        "results_for_eval_3.json",
        "results_for_eval_4.json",
        "results_for_eval_5.json"
    ]
    
    # 파일 경로 생성
    file_paths = [os.path.join(input_dir, name) for name in file_names]
    
    # 존재하는 파일만 필터링
    existing_files = [f for f in file_paths if os.path.exists(f)]
    
    if not existing_files:
        print(f"❌ 합칠 파일을 찾을 수 없습니다.")
        print(f"   찾은 디렉토리: {input_dir}")
        return
    
    print(f"📁 {len(existing_files)}개의 파일을 찾았습니다:")
    for file_path in existing_files:
        print(f"  - {os.path.basename(file_path)}")
    
    # 모든 파일을 합치기
    merged_results = []
    
    for file_path in existing_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data = data['results']
                if isinstance(data, list):
                    merged_results.extend(data)
                    print(f"✅ 로드 완료: {os.path.basename(file_path)} ({len(data)}개 항목)")
                else:
                    print(f"⚠️  {os.path.basename(file_path)}는 리스트 형식이 아닙니다.")
                    
        except Exception as e:
            print(f"❌ 파일 로드 실패 ({os.path.basename(file_path)}): {e}")
    
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
    try:
        # 출력 디렉토리 생성
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        unique_results = {'results': unique_results}
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unique_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 병합 완료!")
        print(f"📊 통계:")
        print(f"  - 총 문서 수: {len(unique_results)}")
        print(f"  - 최종 파일: {output_file}")
        print(f"  - 파일 크기: {os.path.getsize(output_file):,} bytes")
        
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")


def main():
    parser = argparse.ArgumentParser(description='여러 generated_qa_data_*.json 파일들을 하나로 합치는 스크립트')
    parser.add_argument('--input_dir', type=str, default='streamlit',
                       help='입력 파일들이 있는 디렉토리 (기본값: streamlit)')
    parser.add_argument('--output_file', type=str, default='streamlit/results_for_eval.json',
                       help='최종 출력 파일 경로 (기본값: streamlit/results_for_eval.json)')
    args = parser.parse_args()
    
    merge_generated_qa_files(args.input_dir, args.output_file)


if __name__ == "__main__":
    main()

