#!/usr/bin/env python3
"""
result_medical_*.json 파일들에서 metrics를 추출하여 평균을 계산하는 스크립트
"""

import json
import glob
import os
from collections import defaultdict
from typing import Dict, List

def load_metrics_from_files(pattern: str = "result_medical_*.json") -> List[Dict]:
    """모든 result_medical_*.json 파일에서 metrics를 로드"""
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"⚠️  {pattern} 패턴에 맞는 파일을 찾을 수 없습니다.")
        return []
    
    print(f"📁 찾은 파일: {len(files)}개")
    for f in files:
        print(f"  - {os.path.basename(f)}")
    
    all_metrics = []
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'metrics' in data:
                all_metrics.append({
                    'file': os.path.basename(file_path),
                    'metrics': data['metrics']
                })
                print(f"✅ {os.path.basename(file_path)}: metrics 로드 완료")
            else:
                print(f"⚠️  {os.path.basename(file_path)}: metrics 키가 없습니다.")
        except Exception as e:
            print(f"❌ {os.path.basename(file_path)} 로드 실패: {e}")
    
    return all_metrics


def calculate_average_metrics(all_metrics: List[Dict]) -> Dict:
    """모든 파일의 metrics 평균 계산"""
    if not all_metrics:
        return {}
    
    # 모든 metric 값들을 수집
    metric_values = defaultdict(list)
    
    for item in all_metrics:
        metrics = item['metrics']
        for group_name, group_metrics in metrics.items():
            if isinstance(group_metrics, dict):
                for metric_name, metric_value in group_metrics.items():
                    key = f"{group_name}.{metric_name}"
                    if isinstance(metric_value, (int, float)):
                        metric_values[key].append(metric_value)
    
    # 평균 계산
    average_metrics = {}
    for key, values in metric_values.items():
        if values:
            group_name, metric_name = key.split('.', 1)
            if group_name not in average_metrics:
                average_metrics[group_name] = {}
            average_metrics[group_name][metric_name] = round(sum(values) / len(values), 2)
    
    return average_metrics


def print_metrics_summary(all_metrics: List[Dict], average_metrics: Dict):
    """metrics 요약 출력"""
    print("\n" + "="*60)
    print("📊 Metrics 요약")
    print("="*60)
    
    # 개별 파일 metrics
    print("\n📁 개별 파일 metrics:")
    for item in all_metrics:
        print(f"\n  {item['file']}:")
        metrics = item['metrics']
        for group_name, group_metrics in metrics.items():
            if isinstance(group_metrics, dict):
                print(f"    {group_name}:")
                for metric_name, metric_value in group_metrics.items():
                    print(f"      {metric_name}: {metric_value}")
    
    # 평균 metrics
    print("\n" + "="*60)
    print("📈 평균 Metrics (모든 파일)")
    print("="*60)
    for group_name, group_metrics in sorted(average_metrics.items()):
        print(f"\n{group_name}:")
        for metric_name, avg_value in sorted(group_metrics.items()):
            print(f"  {metric_name}: {avg_value}")
    
    # 통계
    print("\n" + "="*60)
    print("📊 통계")
    print("="*60)
    print(f"  총 파일 수: {len(all_metrics)}")
    print(f"  평균 계산된 metric 그룹 수: {len(average_metrics)}")
    total_metrics = sum(len(g) for g in average_metrics.values())
    print(f"  총 metric 수: {total_metrics}")


def save_average_metrics(average_metrics: Dict, output_file: str = "result_medical_average_metrics.json"):
    """평균 metrics를 JSON 파일로 저장"""
    output_data = {
        "source_files": sorted(glob.glob("result_medical_*.json")),
        "file_count": len(sorted(glob.glob("result_medical_*.json"))),
        "average_metrics": average_metrics
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 평균 metrics가 {output_file}에 저장되었습니다.")


def main():
    print("="*60)
    print("🔬 Medical Metrics 집계 도구")
    print("="*60)
    
    # metrics 로드
    all_metrics = load_metrics_from_files("result_medical_*.json")
    
    if not all_metrics:
        print("\n❌ 로드할 metrics가 없습니다.")
        return
    
    # 평균 계산
    print("\n📊 평균 계산 중...")
    average_metrics = calculate_average_metrics(all_metrics)
    
    # 결과 출력
    print_metrics_summary(all_metrics, average_metrics)
    
    # 파일 저장
    save_average_metrics(average_metrics)
    
    print("\n✅ 완료!")


if __name__ == "__main__":
    main()

