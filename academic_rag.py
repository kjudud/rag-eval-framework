import os
import json
import argparse
from openai import OpenAI
from pymilvus import MilvusClient
from tqdm import tqdm
import uuid


def emb_text(text, openai_client):
    """텍스트를 임베딩으로 변환"""
    return (
        openai_client.embeddings.create(input=text, model="text-embedding-3-small")
        .data[0]
        .embedding
    )


def load_json(file_path):
    """학술 논문 청크 데이터 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        json_list = json.load(f)  # JSON 배열을 리스트로 로드
    print(f"총 {len(json_list)}길이의 json 리스트를 로드했습니다.")
    return json_list


def load_qa_data(file_path):
    """Load QA data and extract questions"""
    with open(file_path, 'r', encoding='utf-8') as f:
        qa_data = json.load(f)
    
    questions = []
    for chunk in qa_data:
        if 'generated_qa_pairs' in chunk:
            for qa_pair in chunk['generated_qa_pairs']:
                questions.append({
                    'question': qa_pair['question'],
                    'answer': qa_pair['answer'],
                    'document_id': qa_pair['document_id']
                })
    
    print(f"Loaded {len(questions)} questions from QA data.")
    return questions


def create_milvus_collection(milvus_client, collection_name, embedding_dim):
    """Milvus 컬렉션 생성"""
    if milvus_client.has_collection(collection_name):
        milvus_client.drop_collection(collection_name)
        print(f"기존 컬렉션 '{collection_name}'을 삭제했습니다.")
    
    milvus_client.create_collection(
        collection_name=collection_name,
        dimension=embedding_dim,
        metric_type="IP",  # Inner product distance
        consistency_level="Bounded",
    )
    print(f"새로운 컬렉션 '{collection_name}'을 생성했습니다.")


def insert_chunks_to_milvus(json_list, milvus_client, collection_name, openai_client):
    """청크들을 Milvus에 삽입"""
    data = []
    
    for i, chunk in enumerate(tqdm(json_list, desc="청크 임베딩 생성 및 삽입")):
        # content를 임베딩으로 변환
        embedding = emb_text(chunk['content'], openai_client)
        
        # 데이터 준비 - 정수 ID 사용
        data.append({
            "id": i,  # 순차적 정수 ID 사용
            "vector": embedding,
            "content": chunk['content'],
            "title": chunk['title'],
            "original_id": chunk['id']  # 원본 UUID를 별도 필드로 저장
        })
    
    # Milvus에 삽입
    milvus_client.insert(collection_name=collection_name, data=data)
    print(f"총 {len(data)}개의 청크를 Milvus에 삽입했습니다.")


def search_similar_chunks(question, milvus_client, collection_name, openai_client, limit=3):
    """유사한 청크 검색"""
    # 질문을 임베딩으로 변환
    question_embedding = emb_text(question, openai_client)
    
    # 검색 실행
    search_results = milvus_client.search(
        collection_name=collection_name,
        data=[question_embedding],
        limit=limit,
        search_params={"metric_type": "IP", "params": {}},
        output_fields=["content", "title", "id", "original_id"]
    )
    
    return search_results[0]


def generate_answer(question, retrieved_chunks, openai_client):
    """검색된 청크를 바탕으로 답변 생성"""
    # 검색된 청크들을 컨텍스트로 결합
    context = "\n\n".join([
        f"[출처: {chunk['entity']['title']}]\n{chunk['entity']['content']}"
        for chunk in retrieved_chunks
    ])
    
    system_prompt = """
    Human: You are an AI assistant. You are able to find answers to the questions from the contextual passage snippets provided.
    """
    
    user_prompt = f"""
    Use the following pieces of information enclosed in <context> tags to provide an answer to the question enclosed in <question> tags.
    <context>
    {context}
    </context>
    <question>
    {question}
    </question>
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content


def main():
    # 명령행 인자 파서 생성
    parser = argparse.ArgumentParser(description='Academic RAG System')
    parser.add_argument('--chunks_file', type=str, default='datamorgana/data/academic_chunks_sample.json',
                       help='학술 논문 청크 JSON 파일 경로')
    parser.add_argument('--qa_file', type=str, default='generated_qa_data.json',
                       help='QA 데이터 JSON 파일 경로')
    parser.add_argument('--output_file', type=str, default='results_for_eval.json',
                       help='결과를 저장할 파일 경로')
    parser.add_argument('--num_questions', type=int, default=10,
                       help='테스트할 질문 개수')
    args = parser.parse_args()
    
    print(f"PROGRESS:0:RAG 시스템 초기화 중...", flush=True)
    
    # 설정정
    milvus_db_path = "./academic_milvus.db"
    collection_name = "academic_chunks"
    chunks_file = args.chunks_file
    
    # 클라이언트 초기화
    openai_client = OpenAI()
    milvus_client = MilvusClient(uri=milvus_db_path)
    
    # 임베딩 차원 확인
    test_embedding = emb_text("This is a test", openai_client)
    embedding_dim = len(test_embedding)
    print(f"임베딩 차원: {embedding_dim}")
    
    # 학술 논문 청크 로드
    print(f"PROGRESS:3:학술 논문 청크 로드 중...", flush=True)
    chunks_list = load_json(chunks_file)
    
    # Milvus 컬렉션 생성
    print(f"PROGRESS:6:Milvus 컬렉션 생성 중...", flush=True)
    create_milvus_collection(milvus_client, collection_name, embedding_dim)
    
    # 청크들을 Milvus에 삽입
    print(f"PROGRESS:9:청크들을 Milvus에 삽입 중...", flush=True)
    insert_chunks_to_milvus(chunks_list, milvus_client, collection_name, openai_client)
    
    # QA 데이터 로드 및 테스트 질문 추출
    print(f"PROGRESS:20:QA 데이터 로드 중...", flush=True)
    qa_file = args.qa_file
    qa_data = load_qa_data(qa_file)
    
    # 지정된 개수만큼 질문 선택
    test_questions = qa_data[:args.num_questions]
    
    print(f"PROGRESS:25:RAG 시스템 테스트 시작 - {len(test_questions)}개 질문", flush=True)
    results = []
    
    for i, qa_item in enumerate(test_questions, 1):
        question = qa_item['question']
        expected_answer = qa_item['answer']
        document_id = qa_item['document_id']
        
        progress = 25 + int((i / len(test_questions)) * 70)
        print(f"PROGRESS:{progress}:질문 {i}/{len(test_questions)} 처리 중...", flush=True)
        
        print(f"\n[{i}/{len(test_questions)}] 질문: {question}")
        print(f"예상 답변: {expected_answer}")
        print(f"문서 ID: {document_id}")
        print("-" * 50)
        
        # 유사한 청크 검색
        retrieved_chunks = search_similar_chunks(question, milvus_client, collection_name, openai_client)
        
        # 검색 결과 출력
        print("검색된 관련 청크들:")
        retrieved_context = []
        for j, chunk in enumerate(retrieved_chunks, 1):
            print(f"{j}. [출처: {chunk['entity']['title']}] (유사도: {chunk['distance']:.4f})")
            print(f"   내용: {chunk['entity']['content'][:200]}...")
            print()
            
            # 검색된 컨텍스트를 결과 형식에 맞게 저장
            retrieved_context.append({
                "doc_id": chunk['entity']['original_id'],  # 원본 UUID 사용
                "text": chunk['entity']['content']
            })
        
        # 답변 생성
        answer = generate_answer(question, retrieved_chunks, openai_client)
        print(f"생성된 답변: {answer}")
        print("=" * 80)
        
        # 결과 저장
        result_item = {
            "query_id": str(i-1),
            "query": question,
            "gt_answer": expected_answer,
            "response": answer,
            "retrieved_context": retrieved_context
        }
        results.append(result_item)
    
    # 결과를 JSON 파일로 저장
    print(f"PROGRESS:95:결과 저장 중...", flush=True)
    output_file = args.output_file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"results": results}, f, ensure_ascii=False, indent=2)
    
    print(f"PROGRESS:100:RAG 실행 완료! 결과가 {output_file}에 저장되었습니다.", flush=True)
    print(f"총 {len(results)}개의 질문-답변 쌍이 저장되었습니다.")


if __name__ == "__main__":
    main()
