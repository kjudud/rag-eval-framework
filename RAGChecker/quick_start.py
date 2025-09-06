import argparse
import os
from ragchecker import RAGResults, RAGChecker
from ragchecker.metrics import all_metrics


def main():
    # 명령행 인자 파서 생성
    parser = argparse.ArgumentParser(description='RAGChecker Evaluation')
    parser.add_argument('--input_file', type=str, default='../results_for_eval.json',
                       help='입력 RAG 결과 JSON 파일 경로')
    parser.add_argument('--output_file', type=str, default='results/result_rag-framework.json',
                       help='출력 평가 결과 JSON 파일 경로')
    parser.add_argument('--metrics', type=str, default='all_metrics',
                       help='평가할 메트릭 (all_metrics, retriever_metrics, generator_metrics)')
    parser.add_argument('--extractor_name', type=str, default='openai/gpt-4o-mini',
                       help='추출기 모델 이름')
    parser.add_argument('--checker_name', type=str, default='openai/gpt-4o-mini',
                       help='체커 모델 이름')
    args = parser.parse_args()
    
    print(f"PROGRESS:0:RAGChecker 평가 시작...", flush=True)
    
    # 입력 파일 확인
    if not os.path.exists(args.input_file):
        print(f"ERROR: 입력 파일을 찾을 수 없습니다: {args.input_file}", flush=True)
        return
    
    print(f"PROGRESS:10:RAG 결과 로드 중...", flush=True)
    # initialize ragresults from json/dict
    with open(args.input_file) as fp:
        rag_results = RAGResults.from_json(fp.read())
    
    print(f"PROGRESS:20:평가기 설정 중...", flush=True)
    # set-up the evaluator
    evaluator = RAGChecker(
        extractor_name=args.extractor_name,
        checker_name=args.checker_name,
        batch_size_extractor=32,
        batch_size_checker=32
    )
    
    print(f"PROGRESS:30:평가 실행 중...", flush=True)
    # evaluate results with selected metrics or certain groups, e.g., retriever_metrics, generator_metrics, all_metrics
    evaluator.evaluate(rag_results, args.metrics, args.output_file)
    
    print(f"PROGRESS:100:평가 완료! 결과가 {args.output_file}에 저장되었습니다.", flush=True)
    print(rag_results)

if __name__ == "__main__":
    main()