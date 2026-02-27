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
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    AnnSearchRequest,
    WeightedRanker,
)
import uuid
import threading
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        self.embedding_dim = None
        self.collection = None
        self.is_initialized = False

        # RecursiveCharacterTextSplitter 초기화
        # text-embedding-3-small 최대 토큰: 8191 토큰 ≈ 2500 문자 (안전하게 2000자로 설정)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2200,  # 최대 청크 크기 (문자 수)
            chunk_overlap=220,  # 청크 간 겹치는 길이
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],  # 분리 우선순위
        )

    def initialize(self):
        """RAG 시스템 초기화"""
        try:
            logger.info("RAG 시스템 초기화 시작...")

            # 클라이언트 초기화
            self.openai_client = OpenAI()

            # 임베딩 차원 확인
            test_embedding = self.emb_dense("This is a test")
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

    def emb_dense(self, text: str):
        """텍스트를 dense embedding으로 변환"""
        return (
            self.openai_client.embeddings.create(
                input=text, model="text-embedding-3-small"
            )
            .data[0]
            .embedding
        )

    def emb_sparse(self, text: str):
        """텍스트를 sparse vector로 변환 (간단한 TF-IDF 방식)"""
        import re
        from collections import Counter

        # 텍스트 전처리
        words = re.findall(r"\b\w+\b", text.lower())

        # 단어 빈도 계산
        word_counts = Counter(words)
        total_words = len(words)

        # TF-IDF 계산 (간단한 TF만 사용)
        sparse_dict = {}
        for word, count in word_counts.items():
            if len(word) > 2:  # 2글자 이상만 사용
                tf = count / total_words
                sparse_dict[hash(word) % 10000] = tf  # 해시를 인덱스로 사용

        return sparse_dict

    def load_json(self, file_path: str):
        """학술 논문 청크 데이터 로드"""
        with open(file_path, "r", encoding="utf-8") as f:
            json_list = json.load(f)
        logger.info(f"총 {len(json_list)}길이의 json 리스트를 로드했습니다.")
        return json_list

    def create_milvus_collection(self):
        """Milvus 컬렉션 생성"""
        # Milvus 연결
        connections.connect("default", uri=self.milvus_db_path)

        dense_dim = self.embedding_dim

        self.fields = [
            # Primary key field
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
            # Dense vector field for embeddings
            FieldSchema(
                name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=dense_dim
            ),
            # Sparse vector field for hybrid search
            FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
            # Content field
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=10000),
            # Title field
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=1000),
            # Original ID field
            FieldSchema(name="original_id", dtype=DataType.VARCHAR, max_length=100),
        ]
        self.schema = CollectionSchema(self.fields)

        if utility.has_collection(self.collection_name):
            Collection(self.collection_name).drop()
        self.collection = Collection(
            self.collection_name, self.schema, consistency_level="Bounded"
        )

        # Dense vector index
        dense_index = {"index_type": "AUTOINDEX", "metric_type": "IP"}
        self.collection.create_index("dense_vector", dense_index)

        # Sparse vector index
        sparse_index = {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"}
        self.collection.create_index("sparse_vector", sparse_index)
        self.collection.load()

        logger.info(f"새로운 컬렉션 '{self.collection_name}'을 생성했습니다.")

    def insert_chunks_to_milvus(self, json_list: List[Dict]):
        """청크들을 Milvus에 삽입"""
        data = []
        skipped_count = 0
        chunked_count = 0
        num_workers = 5  # 하드코딩된 워커 수

        # Thread-safe 카운터와 Lock
        doc_id_counter = 0
        counter_lock = threading.Lock()
        data_lock = threading.Lock()

        def process_text_chunk(chunk_info: tuple) -> List[Dict]:
            """단일 텍스트 청크 처리 함수"""
            nonlocal doc_id_counter, skipped_count, chunked_count

            i, chunk, text_chunk, chunk_idx, total_chunks, is_chunked = chunk_info
            original_id = chunk.get("id", "")
            title = chunk.get("title", "")

            try:
                # content를 dense embedding으로 변환
                dense_embedding = self.emb_dense(text_chunk)
                # content를 sparse vector로 변환
                sparse_vector = self.emb_sparse(text_chunk)

                # 데이터 준비
                chunk_title = (
                    f"{title} (청크 {chunk_idx + 1}/{total_chunks})"
                    if is_chunked
                    else title
                )
                chunk_original_id = (
                    f"{original_id}_chunk_{chunk_idx}" if is_chunked else original_id
                )

                # Thread-safe ID 할당
                with counter_lock:
                    current_id = doc_id_counter
                    doc_id_counter += 1

                return {
                    "id": current_id,
                    "dense_vector": dense_embedding,
                    "sparse_vector": sparse_vector,
                    "content": text_chunk,
                    "title": chunk_title,
                    "original_id": chunk_original_id,
                }
            except Exception as e:
                error_msg = str(e)
                # 컨텍스트 길이 초과 에러 처리
                if (
                    "maximum context length" in error_msg
                    or "context_length_exceeded" in error_msg
                ):
                    logger.warning(
                        f"청크 {i}의 하위 청크 {chunk_idx} 임베딩 생성 실패: 컨텍스트 길이 초과. 건너뜁니다."
                    )
                    with counter_lock:
                        skipped_count += 1
                else:
                    logger.error(
                        f"청크 {i}의 하위 청크 {chunk_idx} 처리 중 오류: {error_msg}"
                    )
                    with counter_lock:
                        skipped_count += 1
                return None

        # 모든 텍스트 청크를 수집
        all_chunk_infos = []
        for i, chunk in enumerate(json_list):
            try:
                content = chunk.get("content", "")
                original_id = chunk.get("id", "")

                # content가 비어있으면 건너뛰기
                if not content:
                    skipped_count += 1
                    continue

                # RecursiveCharacterTextSplitter를 사용하여 텍스트 청킹
                text_chunks = self.text_splitter.split_text(content)

                # 원본이 여러 청크로 나뉘었는지 확인
                is_chunked = len(text_chunks) > 1
                if is_chunked:
                    chunked_count += len(text_chunks) - 1
                    logger.info(
                        f"청크 {i} (ID: {original_id})가 {len(text_chunks)}개의 하위 청크로 분할되었습니다."
                    )

                # 각 텍스트 청크를 처리 작업으로 추가
                for chunk_idx, text_chunk in enumerate(text_chunks):
                    all_chunk_infos.append(
                        (i, chunk, text_chunk, chunk_idx, len(text_chunks), is_chunked)
                    )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"청크 {i} 처리 중 예상치 못한 오류: {error_msg}")
                skipped_count += 1

        # 병렬 처리로 임베딩 생성
        logger.info(
            f"총 {len(all_chunk_infos)}개의 텍스트 청크를 병렬 처리합니다 (num_workers={num_workers})"
        )
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_chunk = {
                executor.submit(process_text_chunk, chunk_info): chunk_info
                for chunk_info in all_chunk_infos
            }

            completed = 0
            for future in as_completed(future_to_chunk):
                try:
                    result = future.result()
                    if result is not None:
                        with data_lock:
                            data.append(result)
                    completed += 1

                    # 진행률 로깅
                    if completed % 50 == 0 or completed == len(all_chunk_infos):
                        logger.info(
                            f"임베딩 생성 진행률: {completed}/{len(all_chunk_infos)}"
                        )
                except Exception as e:
                    logger.error(f"청크 처리 결과 수집 중 오류: {str(e)}")

        # Milvus에 삽입 (ID 순서대로 정렬)
        if data:
            data.sort(key=lambda x: x["id"])
            self.collection.insert(data)
            self.collection.flush()
            logger.info(
                f"총 {len(data)}개의 청크를 Milvus에 삽입했습니다. (원본 {len(json_list)}개 중 {chunked_count}개 청킹됨, {skipped_count}개 건너뜀)"
            )
        else:
            logger.warning(
                f"삽입할 청크가 없습니다. 모든 청크가 건너뛰어졌습니다. ({skipped_count}개 건너뜀)"
            )

    def search_similar_chunks(
        self,
        question: str,
        limit: int = 3,
        sparse_weight: float = 0.3,
        dense_weight: float = 0.7,
    ):
        """Hybrid search (dense + sparse vector) using AnnSearchRequest and WeightedRanker"""
        # 질문을 dense embedding으로 변환
        question_dense_embedding = self.emb_dense(question)

        # 질문을 sparse vector로 변환
        question_sparse_vector = self.emb_sparse(question)

        # Dense vector search request
        dense_search_params = {"metric_type": "IP", "params": {}}
        dense_req = AnnSearchRequest(
            [question_dense_embedding], "dense_vector", dense_search_params, limit=limit
        )

        # Sparse vector search request
        sparse_search_params = {"metric_type": "IP", "params": {}}
        sparse_req = AnnSearchRequest(
            [question_sparse_vector], "sparse_vector", sparse_search_params, limit=limit
        )

        # Weighted ranker for hybrid search
        rerank = WeightedRanker(sparse_weight, dense_weight)

        # Hybrid search 실행
        results = self.collection.hybrid_search(
            [sparse_req, dense_req],
            rerank=rerank,
            limit=limit,
            output_fields=["content", "title"],
        )[0]

        return results

    def generate_answer(self, question: str, retrieved_chunks: List[Dict]):
        """검색된 청크를 바탕으로 답변 생성"""
        # 검색된 청크들을 컨텍스트로 결합
        context = "\n\n".join(
            [
                f"[출처: {chunk['entity']['title']}]\n{chunk['entity']['content']}"
                for chunk in retrieved_chunks
            ]
        )

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
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content

    def process_question(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """단일 질문 처리"""
        if not self.is_initialized:
            raise Exception("RAG 시스템이 초기화되지 않았습니다.")

        start_time = time.time()

        # Hybrid search 실행
        retrieved_chunks = self.search_similar_chunks(question, top_k)

        # 검색된 컨텍스트를 결과 형식에 맞게 저장
        retrieved_context = []
        for chunk in retrieved_chunks:
            retrieved_context.append(
                {
                    "doc_id": chunk["id"],  # 자동 생성된 ID 사용
                    "text": chunk["entity"]["content"],
                    "title": chunk["entity"]["title"],
                    "distance": chunk["distance"],
                }
            )

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
                "timestamp": time.time(),
            },
        }

    def process_batch_questions(
        self, questions: List[str], top_k: int = 3
    ) -> Dict[str, Any]:
        """배치 질문 처리"""
        if not self.is_initialized:
            raise Exception("RAG 시스템이 초기화되지 않았습니다.")

        logger.info(f"배치 질문 처리 시작: {len(questions)}개 질문")

        results = []
        total_processing_time = 0

        for i, question in enumerate(questions):
            try:
                result = self.process_question(question, top_k)
                result["metadata"]["query_index"] = i
                results.append(result)
                total_processing_time += result["metadata"]["processing_time"]

                # 진행률 로깅
                if (i + 1) % 5 == 0 or i == len(questions) - 1:
                    logger.info(f"배치 처리 진행률: {i + 1}/{len(questions)}")

            except Exception as e:
                logger.error(f"질문 {i+1} 처리 실패: {str(e)}")
                # 실패한 질문도 결과에 포함
                results.append(
                    {
                        "query": question,
                        "answer": f"처리 실패: {str(e)}",
                        "retrieved_documents": [],
                        "metadata": {
                            "processing_time": 0,
                            "num_retrieved": 0,
                            "query_index": i,
                            "error": str(e),
                        },
                    }
                )

        return {
            "results": results,
            "summary": {
                "total_queries": len(questions),
                "total_processing_time": round(total_processing_time, 2),
                "average_processing_time": round(
                    total_processing_time / len(questions), 2
                ),
                "model": "gpt-3.5-turbo",
                "timestamp": time.time(),
            },
        }


# 전역 RAG 시스템 인스턴스
rag_system = None
rag_system_chunks_file = None  # 현재 사용 중인 chunks_file 저장
initialization_lock = threading.Lock()


def get_rag_system(chunks_file: str = None):
    """RAG 시스템 인스턴스 반환 (싱글톤)

    Args:
        chunks_file: 청크 파일 경로 (기본값: 'streamlit/uploaded_files/academic_chunks_sample_mini.json')
    """
    global rag_system, rag_system_chunks_file

    # 기본값 설정
    if chunks_file is None:
        chunks_file = "uploaded_files/academic_chunks_sample_mini.json"
    # chunks_file이 변경되었거나 초기화되지 않은 경우
    if rag_system is None:
        with initialization_lock:
            if rag_system is None:
                # Milvus DB 경로 생성 (chunks_file과 같은 디렉토리에 .db 파일 생성)
                chunks_file_dir = os.path.dirname(os.path.abspath(chunks_file))
                chunks_file_basename = os.path.basename(chunks_file)
                chunks_file_name_without_ext = os.path.splitext(chunks_file_basename)[0]
                milvus_db_path = os.path.join(
                    chunks_file_dir, f"{chunks_file_name_without_ext}.db"
                )

                logger.info(
                    f"RAG 시스템 초기화: chunks_file={chunks_file}, milvus_db_path={milvus_db_path}"
                )

                rag_system = AcademicRAGSystem(chunks_file, milvus_db_path)
                rag_system.initialize()
                rag_system_chunks_file = chunks_file

    return rag_system


@app.route("/health", methods=["GET"])
def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # chunks_file 파라미터 받기
        chunks_file = request.args.get("chunks_file", None)
        # chunks_file이 제공된 경우 해당 파일로 초기화
        system = get_rag_system(chunks_file=chunks_file)

        return jsonify(
            {
                "status": "healthy",
                "message": "Academic RAG API 서버가 정상적으로 실행 중입니다.",
                "version": "1.0.0",
                "initialized": system.is_initialized,
                "chunks_file": system.chunks_file,
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "message": f"RAG 시스템 초기화 실패: {str(e)}",
                    "version": "1.0.0",
                }
            ),
            500,
        )


@app.route("/api/rag/query", methods=["POST"])
def rag_query():
    """단일 질의응답 API 엔드포인트"""
    try:
        data = request.get_json()

        if not data or "query" not in data:
            return (
                jsonify({"error": "잘못된 요청입니다. 'query' 필드가 필요합니다."}),
                400,
            )

        query = data["query"]
        top_k = data.get("top_k", 3)
        chunks_file = request.args.get("chunks_file", None)

        logger.info(f"단일 질의 수신: {query}")

        system = get_rag_system(chunks_file=chunks_file)
        result = system.process_question(query, top_k)

        logger.info(f"단일 질의 처리 완료: {len(result['answer'])}자 답변")

        return jsonify(result)

    except Exception as e:
        logger.error(f"단일 질의 처리 중 오류: {str(e)}")
        return jsonify({"error": f"서버 내부 오류가 발생했습니다: {str(e)}"}), 500


@app.route("/api/rag/batch", methods=["POST"])
def rag_batch():
    """배치 질의응답 API 엔드포인트"""
    try:
        data = request.get_json()

        if not data or "queries" not in data:
            return (
                jsonify({"error": "잘못된 요청입니다. 'queries' 필드가 필요합니다."}),
                400,
            )

        queries = data["queries"]
        top_k = data.get("top_k", 3)
        chunks_file = data.get("chunks_file", None) or request.args.get(
            "chunks_file", None
        )

        if not isinstance(queries, list):
            return jsonify({"error": "'queries'는 리스트 형태여야 합니다."}), 400

        logger.info(f"배치 질의 수신: {len(queries)}개 질문")

        system = get_rag_system(chunks_file=chunks_file)
        result = system.process_batch_questions(queries, top_k)

        logger.info(f"배치 질의 처리 완료: {len(queries)}개 질문")

        return jsonify(result)

    except Exception as e:
        logger.error(f"배치 질의 처리 중 오류: {str(e)}")
        return jsonify({"error": f"서버 내부 오류가 발생했습니다: {str(e)}"}), 500


@app.route("/api/rag/config", methods=["GET"])
def get_config():
    """API 설정 정보 반환"""
    return jsonify(
        {
            "api_version": "1.0.0",
            "supported_endpoints": [
                "/api/rag/query",
                "/api/rag/batch",
                "/api/rag/config",
                "/health",
            ],
            "max_batch_size": 100,
            "max_query_length": 1000,
            "supported_languages": ["ko", "en"],
            "default_top_k": 3,
            "max_top_k": 10,
            "model": "gpt-3.5-turbo",
            "embedding_model": "text-embedding-3-small",
        }
    )


if __name__ == "__main__":
    print("🚀 Academic RAG API 서버를 시작합니다...")
    print("📡 API 엔드포인트:")
    print("  - GET  /health - 헬스 체크")
    print("  - POST /api/rag/query - 단일 질의응답")
    print("  - POST /api/rag/batch - 배치 질의응답")
    print("  - GET  /api/rag/config - API 설정 정보")
    print("🌐 서버 주소: http://0.0.0.0:5000")
    print("🌐 WSL에서 접근: http://localhost:5000")
    print("🌐 Windows에서 접근: http://[WSL_IP]:5000")
    print(
        "📚 사용법: curl -X POST http://localhost:5000/api/rag/query -H 'Content-Type: application/json' -d '{\"query\": \"인공지능이란?\"}'"
    )

    # WSL 환경에서의 포트 바인딩 설정
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
    # local환경에서 실행시 localhost
    # app.run(host='localhost', port=5000, debug=True, threaded=True)
