#!/usr/bin/env python3
"""
Academic RAG API Server
academic_rag.py를 API 서버로 래핑한 버전
"""

import os
import json
import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from pymilvus import MilvusClient
import uuid
import threading
from typing import List, Dict, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class AcademicRAGSystem:
    """Academic RAG 시스템 클래스"""
    
    def __init__(self, chunks_file: str, milvus_db_path: str = "./academic_milvus.db"):
        self.chunks_file = chunks_file
        self.milvus_db_path = milvus_db_path
        self.collection_name = "academic_chunks"
        self.openai_client = None
        self.milvus_client = None
        self.embedding_dim = None
        self.is_initialized = False
        
    def initialize(self):
        """RAG 시스템 초기화"""
        try:
            logger.info("RAG 시스템 초기화 시작...")
            
            # 클라이언트 초기화
            self.openai_client = OpenAI()
            self.milvus_client = MilvusClient(uri=self.milvus_db_path)
            
            # 임베딩 차원 확인
            test_embedding = self.emb_text("This is a test")
            self.embedding_dim = len(test_embedding)
            logger.info(f"임베딩 차원: {self.embedding_dim}")
            
            # 학술 논문 청크 로드
            logger.info("학술 논문 청크 로드 중...")
            chunks_list = self.load_json(self.chunks_file)
            
            # Milvus 컬렉션 생성
            logger.info("Milvus 컬렉션 생성 중...")
            self.create_milvus_collection()
            
            # 청크들을 Milvus에 삽입
            logger.info("청크들을 Milvus에 삽입 중...")
            self.insert_chunks_to_milvus(chunks_list)
            
            self.is_initialized = True
            logger.info("RAG 시스템 초기화 완료!")
            
        except Exception as e:
            logger.error(f"RAG 시스템 초기화 실패: {str(e)}")
            raise
    
    def emb_text(self, text: str):
        """텍스트를 임베딩으로 변환"""
        return (
            self.openai_client.embeddings.create(input=text, model="text-embedding-3-small")
            .data[0]
            .embedding
        )
    
    def load_json(self, file_path: str):
        """학술 논문 청크 데이터 로드"""
        with open(file_path, 'r', encoding='utf-8') as f:
            json_list = json.load(f)
        logger.info(f"총 {len(json_list)}길이의 json 리스트를 로드했습니다.")
        return json_list
    
    def create_milvus_collection(self):
        """Milvus 컬렉션 생성"""
        if self.milvus_client.has_collection(self.collection_name):
            self.milvus_client.drop_collection(self.collection_name)
            logger.info(f"기존 컬렉션 '{self.collection_name}'을 삭제했습니다.")
        
        self.milvus_client.create_collection(
            collection_name=self.collection_name,
            dimension=self.embedding_dim,
            metric_type="IP",
            consistency_level="Bounded",
        )
        logger.info(f"새로운 컬렉션 '{self.collection_name}'을 생성했습니다.")
    
    def insert_chunks_to_milvus(self, json_list: List[Dict]):
        """청크들을 Milvus에 삽입"""
        data = []
        
        for i, chunk in enumerate(json_list):
            # content를 임베딩으로 변환
            embedding = self.emb_text(chunk['content'])
            
            # 데이터 준비 - 정수 ID 사용
            data.append({
                "id": i,
                "vector": embedding,
                "content": chunk['content'],
                "title": chunk['title'],
                "original_id": chunk['id']
            })
        
        # Milvus에 삽입
        self.milvus_client.insert(collection_name=self.collection_name, data=data)
        logger.info(f"총 {len(data)}개의 청크를 Milvus에 삽입했습니다.")
    
    def search_similar_chunks(self, question: str, limit: int = 3):
        """유사한 청크 검색"""
        # 질문을 임베딩으로 변환
        question_embedding = self.emb_text(question)
        
        # 검색 실행
        search_results = self.milvus_client.search(
            collection_name=self.collection_name,
            data=[question_embedding],
            limit=limit,
            search_params={"metric_type": "IP", "params": {}},
            output_fields=["content", "title", "id", "original_id"]
        )
        
        return search_results[0]
    
    def generate_answer(self, question: str, retrieved_chunks: List[Dict]):
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
        
        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def process_question(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """단일 질문 처리"""
        if not self.is_initialized:
            raise Exception("RAG 시스템이 초기화되지 않았습니다.")
        
        start_time = time.time()
        
        # 유사한 청크 검색
        retrieved_chunks = self.search_similar_chunks(question, top_k)
        
        # 검색된 컨텍스트를 결과 형식에 맞게 저장
        retrieved_context = []
        for chunk in retrieved_chunks:
            retrieved_context.append({
                "doc_id": chunk['entity']['original_id'],
                "text": chunk['entity']['content'],
                "title": chunk['entity']['title'],
                "distance": chunk['distance']
            })
        
        # 답변 생성
        answer = self.generate_answer(question, retrieved_chunks)
        
        processing_time = time.time() - start_time
        
        return {
            "query": question,
            "answer": answer,
            "retrieved_documents": retrieved_context,
            "metadata": {
                "processing_time": round(processing_time, 2),
                "num_retrieved": len(retrieved_context),
                "model": "gpt-3.5-turbo",
                "timestamp": time.time()
            }
        }
    
    def process_batch_questions(self, questions: List[str], top_k: int = 3) -> Dict[str, Any]:
        """배치 질문 처리"""
        if not self.is_initialized:
            raise Exception("RAG 시스템이 초기화되지 않았습니다.")
        
        logger.info(f"배치 질문 처리 시작: {len(questions)}개 질문")
        
        results = []
        total_processing_time = 0
        
        for i, question in enumerate(questions):
            try:
                result = self.process_question(question, top_k)
                result['metadata']['query_index'] = i
                results.append(result)
                total_processing_time += result['metadata']['processing_time']
                
                # 진행률 로깅
                if (i + 1) % 5 == 0 or i == len(questions) - 1:
                    logger.info(f"배치 처리 진행률: {i + 1}/{len(questions)}")
                    
            except Exception as e:
                logger.error(f"질문 {i+1} 처리 실패: {str(e)}")
                # 실패한 질문도 결과에 포함
                results.append({
                    "query": question,
                    "answer": f"처리 실패: {str(e)}",
                    "retrieved_documents": [],
                    "metadata": {
                        "processing_time": 0,
                        "num_retrieved": 0,
                        "query_index": i,
                        "error": str(e)
                    }
                })
        
        return {
            "results": results,
            "summary": {
                "total_queries": len(questions),
                "total_processing_time": round(total_processing_time, 2),
                "average_processing_time": round(total_processing_time / len(questions), 2),
                "model": "gpt-3.5-turbo",
                "timestamp": time.time()
            }
        }

# 전역 RAG 시스템 인스턴스
rag_system = None
initialization_lock = threading.Lock()

def get_rag_system():
    """RAG 시스템 인스턴스 반환 (싱글톤)"""
    global rag_system
    if rag_system is None:
        with initialization_lock:
            if rag_system is None:
                # 환경변수에서 설정 읽기
                chunks_file = os.getenv('CHUNKS_FILE', './datamorgana/data/academic_chunks_sample_mini.json')
                milvus_db_path = os.getenv('MILVUS_DB_PATH', './academic_milvus.db')
                
                rag_system = AcademicRAGSystem(chunks_file, milvus_db_path)
                rag_system.initialize()
    return rag_system

@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    try:
        system = get_rag_system()
        return jsonify({
            "status": "healthy",
            "message": "Academic RAG API 서버가 정상적으로 실행 중입니다.",
            "version": "1.0.0",
            "initialized": system.is_initialized
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "message": f"RAG 시스템 초기화 실패: {str(e)}",
            "version": "1.0.0"
        }), 500

@app.route('/api/rag/query', methods=['POST'])
def rag_query():
    """단일 질의응답 API 엔드포인트"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "error": "잘못된 요청입니다. 'query' 필드가 필요합니다."
            }), 400
        
        query = data['query']
        top_k = data.get('top_k', 3)
        
        logger.info(f"단일 질의 수신: {query}")
        
        system = get_rag_system()
        result = system.process_question(query, top_k)
        
        logger.info(f"단일 질의 처리 완료: {len(result['answer'])}자 답변")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"단일 질의 처리 중 오류: {str(e)}")
        return jsonify({
            "error": f"서버 내부 오류가 발생했습니다: {str(e)}"
        }), 500

@app.route('/api/rag/batch', methods=['POST'])
def rag_batch():
    """배치 질의응답 API 엔드포인트"""
    try:
        data = request.get_json()
        
        if not data or 'queries' not in data:
            return jsonify({
                "error": "잘못된 요청입니다. 'queries' 필드가 필요합니다."
            }), 400
        
        queries = data['queries']
        top_k = data.get('top_k', 3)
        
        if not isinstance(queries, list):
            return jsonify({
                "error": "'queries'는 리스트 형태여야 합니다."
            }), 400
        
        logger.info(f"배치 질의 수신: {len(queries)}개 질문")
        
        system = get_rag_system()
        result = system.process_batch_questions(queries, top_k)
        
        logger.info(f"배치 질의 처리 완료: {len(queries)}개 질문")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"배치 질의 처리 중 오류: {str(e)}")
        return jsonify({
            "error": f"서버 내부 오류가 발생했습니다: {str(e)}"
        }), 500

@app.route('/api/rag/config', methods=['GET'])
def get_config():
    """API 설정 정보 반환"""
    return jsonify({
        "api_version": "1.0.0",
        "supported_endpoints": [
            "/api/rag/query",
            "/api/rag/batch",
            "/api/rag/config",
            "/health"
        ],
        "max_batch_size": 100,
        "max_query_length": 1000,
        "supported_languages": ["ko", "en"],
        "default_top_k": 3,
        "max_top_k": 10,
        "model": "gpt-3.5-turbo",
        "embedding_model": "text-embedding-3-small"
    })

if __name__ == '__main__':
    print("🚀 Academic RAG API 서버를 시작합니다...")
    print("📡 API 엔드포인트:")
    print("  - GET  /health - 헬스 체크")
    print("  - POST /api/rag/query - 단일 질의응답")
    print("  - POST /api/rag/batch - 배치 질의응답")
    print("  - GET  /api/rag/config - API 설정 정보")
    print("🌐 서버 주소: http://0.0.0.0:5000")
    print("🌐 WSL에서 접근: http://localhost:5000")
    print("🌐 Windows에서 접근: http://[WSL_IP]:5000")
    print("📚 사용법: curl -X POST http://localhost:5000/api/rag/query -H 'Content-Type: application/json' -d '{\"query\": \"인공지능이란?\"}'")
    
    # WSL 환경에서의 포트 바인딩 설정
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
