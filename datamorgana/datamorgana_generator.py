import json
import time
import random
import concurrent.futures
import argparse
import os
import threading
from dataclasses import dataclass
from loguru import logger
from typing import Optional, Dict, Any, List, Tuple
from openai import OpenAI
from tqdm import tqdm


@dataclass
class Config:
    api_key: str = os.getenv("OPENAI_API_KEY")
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"#"claude-sonnet-4-20250514"
    input_path: str = "data/academic_chunks_sample.json"
    output_path: str = "data/academic_chunks_sample_qa.json"
    config_path: str = "datamorgana_config_template.json"
    max_retries: int = 3
    retry_delay: int = 5
    api_call_delay: float = 7
    max_workers: int = 5
    num_questions_per_document: int = 1
    candidate_questions_per_call: int = 2

@dataclass
class Category:
    name: str
    probability: float
    description: str

@dataclass
class Categorization:
    name: str
    categories: List[Category]

class DataMorganaGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.user_categorizations: List[Categorization] = []
        self.question_categorizations: List[Categorization] = []
        
    def load_configuration(self, config_path: str):
        """Load DataMorgana configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Load user categorizations
            if 'user_categorizations' in config_data:
                for cat_data in config_data['user_categorizations']:
                    categories = [
                        Category(
                            name=cat['name'],
                            probability=cat['probability'],
                            description=cat['description']
                        )
                        for cat in cat_data['categories']
                    ]
                    self.user_categorizations.append(
                        Categorization(name=cat_data['name'], categories=categories)
                    )
            
            # Load question categorizations
            if 'question_categorizations' in config_data:
                for cat_data in config_data['question_categorizations']:
                    categories = [
                        Category(
                            name=cat['name'],
                            probability=cat['probability'],
                            description=cat['description']
                        )
                        for cat in cat_data['categories']
                    ]
                    self.question_categorizations.append(
                        Categorization(name=cat_data['name'], categories=categories)
                    )
                    
            logger.info(f"설정 불러오기 성공: {len(self.user_categorizations)}개의 사용자 분류, {len(self.question_categorizations)}개의 질문 분류")
            
        except Exception as e:
            logger.error(f"설정 파일 불러오기 실패: {e}")
            self._load_default_configuration()
    
    def _load_default_configuration(self):
        """Load default configuration (based on paper Table 1)"""
        logger.info("기본 설정 사용")
        
        # Default user categorization
        expert_novice = Categorization(
            name="expertise",
            categories=[
                Category("expert", 0.5, "a specialized user with deep understanding of the corpus"),
                Category("novice", 0.5, "a regular user with no understanding of specialized terms")
            ]
        )
        self.user_categorizations = [expert_novice]
        
        # Default question categorizations (based on paper Table 1)
        factuality = Categorization(
            name="factuality",
            categories=[
                Category("factoid", 0.4, "question seeking a specific, concise piece of information or a short fact about a particular subject, such as a name, date, or number"),
                Category("open-ended", 0.6, "question inviting detailed or exploratory responses, encouraging discussion or elaboration")
            ]
        )
        
        premise = Categorization(
            name="premise",
            categories=[
                Category("direct", 0.7, "question that does not contain any premise or any information about the user"),
                Category("with-premise", 0.3, "question starting with a very short premise, where the user reveals their needs or some information about himself")
            ]
        )
        
        phrasing = Categorization(
            name="phrasing",
            categories=[
                Category("concise-and-natural", 0.3, "phrased in the way people typically speak, reflecting everyday language use, without formal or artificial structure. It is a concise direct question consisting of less than 10 words"),
                Category("verbose-and-natural", 0.4, "phrased in the way people typically speak, reflecting everyday language use, without formal or artificial structure. It is a relatively long question consisting of more than 9 words"),
                Category("short-search-query", 0.15, "phrased as a typed web query for search engines (only keywords, without punctuation and without a natural-sounding structure). It consists of less than 7 words"),
                Category("long-search-query", 0.15, "phrased as a typed web query for search engines (only keywords, without punctuation and without a natural-sounding structure). It consists of more than 6 words")
            ]
        )
        
        linguistic_variation = Categorization(
            name="linguistic_variation",
            categories=[
                Category("similar-to-document", 0.4, "phrased using the same terminology and phrases appearing in the document"),
                Category("distance-from-document", 0.6, "phrased using terms completely different from the ones appearing in the document")
            ]
        )
        
        # Add language categorization
        language = Categorization(
            name="language",
            categories=[
                Category("chinese", 0.7, "generate questions and answers in Chinese language"),
                Category("english", 0.3, "generate questions and answers in English language")
            ]
        )
        
        self.question_categorizations = [factuality, premise, phrasing, linguistic_variation, language]
    
    def select_categories(self) -> Tuple[List[Category], List[Category]]:
        """Select user and question categories based on probability"""
        selected_user_categories = []
        selected_question_categories = []
        
        # Select one category for each user categorization
        for categorization in self.user_categorizations:
            categories = categorization.categories
            weights = [cat.probability for cat in categories]
            selected = random.choices(categories, weights=weights, k=1)[0]
            selected_user_categories.append(selected)
        
        # Select one category for each question categorization
        for categorization in self.question_categorizations:
            categories = categorization.categories
            weights = [cat.probability for cat in categories]
            selected = random.choices(categories, weights=weights, k=1)[0]
            selected_question_categories.append(selected)
            
        return selected_user_categories, selected_question_categories
    
    def build_prompt(self, document: str, user_categories: List[Category], 
                    question_categories: List[Category], num_questions: int = 2) -> str:
        """Build DataMorgana prompt template (based on paper)"""
        
        # Build user characteristic descriptions
        user_descriptions = []
        for cat in user_categories:
            # user_descriptions.append(f"They must be {cat.description}")
            user_descriptions.append(f"다음 특성을 가져야 합니다: {cat.description}")
        
        # Build question characteristic descriptions
        question_descriptions = []
        for cat in question_categories:
            # question_descriptions.append(f"It must be {cat.description}")
            question_descriptions.append(f"다음 특성을 가져야 합니다: {cat.description}")
        
#         prompt = f"""You are a user simulator that should generate {num_questions} candidate questions for starting a conversation.

# The {num_questions} questions must be about facts discussed in the documents you will now receive. When generating the questions, assume that the real users you must simulate, as well as the readers of the questions do not have access to these documents. Therefore, never refer to the author of the documents or the documents themselves. Also, assume that whoever reads the questions will read each question independently. The {num_questions} questions must be diverse and different from each other. Return only the questions without any preamble. Write each pair in a new line, in the following JSON format: {{"question": "<question>", "answer": "<answer>"}}.

# IMPORTANT: The questions MUST include specific ENTITIES, TERMS, CONCEPTS, or NAMES mentioned in the document. Avoid vague pronoun references like "this technology", "that method", "such system", or in Chinese "这种", "那种", "有种". Instead, use the actual names like "blockchain", "COVID-19", "artificial intelligence", etc. This makes the questions clearer and more specific.

# The generated questions should be about facts from the following document:
# {document}

# Each of the generated questions must reflect a user with the following characteristics:
# {chr(10).join(user_descriptions)}

# Each of the generated questions must have the following characteristics:
# {chr(10).join(question_descriptions)}"""

        prompt = f"""당신은 대화를 시작하기 위한 {num_questions}개의 후보 질문을 생성하는 사용자 시뮬레이터입니다.

{num_questions}개의 질문은 지금 받을 문서에서 제시된 사실에 관한 것이어야 합니다. 질문을 생성할 때, 시뮬레이션해야 하는 실제 사용자와 질문을 읽는 독자들이 이 문서에 접근할 수 없다고 가정하세요. 따라서 문서의 저자나 문서 자체를 언급하지 마세요. 또한 질문을 읽는 사람이 각 질문을 독립적으로 읽는다고 가정하세요. {num_questions}개의 질문은 서로 다양하고 달라야 합니다. 서문 없이 질문만 반환하세요. 각 쌍을 새 줄에 다음 JSON 형식으로 작성하세요: {{"question": "<question>", "answer": "<answer>"}}.

중요: 질문에는 반드시 문서에 언급된 구체적인 개체, 용어, 개념 또는 이름을 포함해야 합니다. "이 질병", "그 치료법", "그런 약물"과 같은 모호한 대명사 참조를 피하세요. 대신 "당뇨병", "PPARγ", "Lactobacillus casei" 등과 같은 실제 의료 용어나 개념 이름을 사용하세요. 이렇게 하면 질문이 더 명확하고 구체적이 됩니다.

생성된 질문은 다음 문서의 사실에 관한 것이어야 합니다:
{document}

생성된 각 질문은 다음 특성을 가진 사용자를 반영해야 합니다:
{chr(10).join(user_descriptions)}

생성된 각 질문은 다음 특성을 가져야 합니다:
{chr(10).join(question_descriptions)}"""

        return prompt
    
    def get_model_response(self, prompt: str) -> Optional[str]:
        """Call API to get model response"""
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    # temperature=0.7,
                )
                time.sleep(self.config.api_call_delay)
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"API 호출 실패 (시도 {attempt+1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    return None
        return None
    
    def parse_qa_pairs(self, response: str) -> List[Dict[str, str]]:
        """Parse Q&A pairs from model response"""
        qa_pairs = []
        
        try:
            # Try parsing JSON line by line
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and line.startswith('{') and line.endswith('}'):
                    try:
                        qa_pair = json.loads(line)
                        if 'question' in qa_pair and 'answer' in qa_pair:
                            qa_pairs.append(qa_pair)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"Q&A 쌍 파싱 실패: {e}")
        
        return qa_pairs
    
    def filter_qa_pairs(self, qa_pairs: List[Dict[str, str]], document: str) -> List[Dict[str, str]]:
        """Filter Q&A pairs to ensure quality (based on paper's filtering strategy)"""
        filtered_pairs = []
        
        for qa_pair in qa_pairs:
            question = qa_pair.get('question', '').strip()
            answer = qa_pair.get('answer', '').strip()
            
            # Basic quality check
            if len(question) < 3 or len(answer) < 3:  # Relaxed length limit
                continue
                
            # Check if document is referenced (violates context-free requirement)
            # Check English references
            english_refs = ['document', 'text', 'passage', 'author']
            # Check Korean references
            korean_refs = ['문서', '자료', '텍스트', '단락', '저자']
            
            question_lower = question.lower()
            if any(ref in question_lower for ref in english_refs) or any(ref in question for ref in korean_refs):
                continue
                
            # Check if question is reasonable (supports English and Korean)
            # English question words
            # english_question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'is', 'are', 'can', 'could', 'would', 'should', 'do', 'does', 'did']
            # # Korean question words
            # chinese_question_words = ['什么', '怎么', '如何', '为什么', '何时', '什么时候', '哪里', '哪儿', '谁', '哪个', '哪些', '是否', '能否', '可以', '是什么', '有哪些', '有什么']
            
            # # Check if contains question words or ends with question mark
            # has_english_question = any(word in question_lower for word in english_question_words) or question.endswith('?')
            # has_chinese_question = any(word in question for word in chinese_question_words) or question.endswith('？')
            
            # if not (has_english_question or has_chinese_question):
            #     continue
            
            filtered_pairs.append(qa_pair)
        
        return filtered_pairs
    
    def process_document(self, document_item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document and generate Q&A pairs"""
        try:
            document_id = document_item.get('id', 'unknown')
            document_content = document_item.get('content', [])
            document_content = '\n'.join(document_content)
            
            if not document_content:
                logger.warning(f"문서 {document_id} 내용이 비어 있습니다")
                return document_item
            generated_qa_pairs = []
            
            # Generate specified number of Q&A pairs
            for i in range(self.config.num_questions_per_document):
                # Select categories (Step 1)
                user_categories, question_categories = self.select_categories()
                
                # Build prompt (Step 2-3)
                prompt = self.build_prompt(
                    document_content,
                    user_categories,
                    question_categories,
                    self.config.candidate_questions_per_call
                )
                
                # Get model response
                response = self.get_model_response(prompt)
                if not response:
                    logger.warning(f"문서 {document_id} {i+1}번째 생성 실패")
                    continue
                
                # Parse Q&A pairs
                qa_pairs = self.parse_qa_pairs(response)
                
                # Filter Q&A pairs (Step 4)
                filtered_pairs = self.filter_qa_pairs(qa_pairs, document_content)
                
                # Select best Q&A pair
                if filtered_pairs:
                    selected_pair = random.choice(filtered_pairs)
                    selected_pair['user_categories'] = ', '.join([cat.name for cat in user_categories])
                    selected_pair['question_categories'] = ', '.join([cat.name for cat in question_categories])
                    selected_pair['document_id'] = document_id
                    generated_qa_pairs.append(selected_pair)
            
            document_item['generated_qa_pairs'] = generated_qa_pairs
            logger.debug(f"문서 {document_id}에서 {len(generated_qa_pairs)}개의 Q&A 쌍을 생성했습니다")
            
        except Exception as e:
            logger.error(f"문서를 처리하는 중 오류가 발생했습니다.: {e}")
        
        return document_item
    
    def generate_benchmark(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate entire benchmark dataset (using thread pool for acceleration)"""
        logger.info(f"벤치마크 데이터셋 생성을 시작합니다, 총 {len(documents)}개의 문서")
        
        results = []
        completed = 0
        
        # Shared counter for QA pairs (thread-safe)
        questions_count = 0
        save_counter = 0  # Counter for file naming (100, 200, 300, ...)
        counter_lock = threading.Lock()
        
        def save_results():
            """Save current results to temporary file (thread-safe)"""
            nonlocal save_counter
            try:
                save_counter += 1
                file_number = save_counter * 100
                temp_path = f"{self.config.output_path}_temp_{file_number}.json"
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                logger.error(f"중간 저장 실패: {e}")
        
        with tqdm(total=len(documents), desc="생성 진행 상황") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_doc = {executor.submit(self.process_document, doc): doc for doc in documents}
                for future in concurrent.futures.as_completed(future_to_doc):
                    result = future.result()
                    results.append(result)
                    
                    # Count QA pairs in this result (thread-safe)
                    qa_pairs_count = len(result.get('generated_qa_pairs', []))
                    
                    with counter_lock:
                        questions_count += qa_pairs_count
                        if questions_count >= 100:
                            save_results()
                            questions_count = 0
                    
                    completed += 1
                    progress = int((completed / len(documents)) * 100)
                    print(f"PROGRESS:{progress}:문서 처리 중... ({completed}/{len(documents)})", flush=True)
                    pbar.update(1)
        
        return results
    
    def save_configuration_template(self, output_path: str):
        """Save configuration file template"""
        template = {
            "user_categorizations": [
                {
                    "name": "expertise",
                    "categories": [
                        {
                            "name": "expert",
                            "probability": 0.5,
                            "description": "a specialized user with deep understanding of the corpus"
                        },
                        {
                            "name": "novice", 
                            "probability": 0.5,
                            "description": "a regular user with no understanding of specialized terms"
                        }
                    ]
                }
            ],
            "question_categorizations": [
                {
                    "name": "factuality",
                    "categories": [
                        {
                            "name": "factoid",
                            "probability": 0.4,
                            "description": "question seeking a specific, concise piece of information or a short fact about a particular subject, such as a name, date, or number"
                        },
                        {
                            "name": "open-ended",
                            "probability": 0.6,
                            "description": "question inviting detailed or exploratory responses, encouraging discussion or elaboration"
                        }
                    ]
                },
                {
                    "name": "premise",
                    "categories": [
                        {
                            "name": "direct",
                            "probability": 0.7,
                            "description": "question that does not contain any premise or any information about the user"
                        },
                        {
                            "name": "with-premise",
                            "probability": 0.3,
                            "description": "question starting with a very short premise, where the user reveals their needs or some information about himself"
                        }
                    ]
                },
                {
                    "name": "language",
                    "categories": [
                        {
                            "name": "chinese",
                            "probability": 0.7,
                            "description": "generate questions and answers in Chinese language"
                        },
                        {
                            "name": "english",
                            "probability": 0.3,
                            "description": "generate questions and answers in English language"
                        }
                    ]
                }
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        
        logger.info(f"설정 파일 템플릿이 저장되었습니다: {output_path}")

def main():
    # arg parsing
    parser = argparse.ArgumentParser(description='DataMorgana Generator')
    parser.add_argument('--input_file', type=str, default='data/academic_chunks_sample.json',
                       help='input JSON file path')
    parser.add_argument('--output_file', type=str, default='data/academic_chunks_sample_qa.json',
                       help='output JSON file path')
    parser.add_argument('--config_file', type=str, default=None,
                       help='config file path (optional)')
    parser.add_argument('--log_file', type=str, default=None,
                       help='log file path (optional, if not specified, logs go to stderr)')
    args = parser.parse_args()
    
    # 로그 파일 설정 (파일과 콘솔 둘 다 출력)
    if args.log_file:
        logger.add(args.log_file, rotation="10 MB", retention="7 days", encoding="utf-8", level="INFO", enqueue=False)
    
    config = Config()
    config.input_path = args.input_file
    config.output_path = args.output_file
    
    # Create generator
    generator = DataMorganaGenerator(config)
    
    # Use config file if specified, otherwise use default configuration
    if args.config_file:
        try:
            generator.load_configuration(args.config_file)
            logger.info(f"사용자 지정 설정 파일을 사용합니다: {args.config_file}")
        except FileNotFoundError:
            logger.error(f"지정된 설정 파일을 찾을 수 없습니다: {args.config_file}")
            logger.info("기본 설정을 사용합니다")
            generator._load_default_configuration()
    else:
        # If config file doesn't exist, create template
        try:
            generator.load_configuration(config.config_path)
        except FileNotFoundError:
            logger.info("설정 파일이 존재하지 않아, 기본 설정 템플릿을 생성합니다")
            generator.save_configuration_template(config.config_path)
            generator._load_default_configuration()
    
    # Load document data
    try:
        with open(config.input_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        # documents = documents[56:66] # for test
        logger.info(f"{len(documents)}개의 문서를 성공적으로 불러왔습니다")
    except FileNotFoundError:
        logger.error(f"입력 파일 {config.input_path} 이(가) 존재하지 않습니다")
        # Create example documents
        documents = [
            {
                "id": "doc1",
                "content": "인공지능(AI)**은 컴퓨터가 인간의 지능을 모방하도록 만드는 방법을 연구하는 과학 기술이다. 여기에는 기계학습, 딥러닝, 자연어 처리 등 여러 하위 분야가 포함된다. 최근에는 계산 능력의 향상과 빅데이터의 발전에 힘입어 AI 기술이 획기적인 발전을 이루었다."
            },
            {
                "id": "doc2", 
                "content": "기계학습(머신러닝)**은 인공지능의 중요한 한 분야로, 알고리즘을 통해 컴퓨터가 명시적인 프로그래밍 지시 없이도 데이터로부터 자동으로 학습하고 개선할 수 있도록 한다. 대표적인 기계학습 방법에는 지도학습, 비지도학습, 강화학습이 있다."
            }
        ]
        logger.info("예시 문서를 사용하여 시연합니다.")
    
    # Generate benchmark dataset
    print(f"PROGRESS:0:총 {len(documents)}개 문서 처리 시작", flush=True)
    results = generator.generate_benchmark(documents)
    print(f"PROGRESS:100:벤치마크 데이터셋 생성 완료", flush=True)
    
    # Save results
    # results = [i for i in results if i['generated_qa_pairs']]
    with open(config.output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Statistics of generated results
    total_qa_pairs = sum(len(doc.get('generated_qa_pairs', [])) for doc in results)
    logger.success(f"벤치마크 데이터셋 생성 완료!")
    logger.info(f"총 처리한 문서 수: {len(results)}")
    logger.info(f"총 생성된 Q&A 쌍 수: {total_qa_pairs}")
    logger.info(f"결과가 저장된 위치: {config.output_path}")

if __name__ == "__main__":
    main()