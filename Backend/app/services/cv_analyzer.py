"""
CV Analyzer — Local ML pipeline using lgbm_model.pkl + tfidf_vectorizer.pkl.
Ported from resume_nlp_v4.ipynb.

Provides:
  - CV scoring (0-100) via LightGBM model
  - Skill extraction via NLP + tech taxonomy
  - Strengths derived from impact/premium/seniority signals
  - Rule-based recommendations
  - Best-fit role inference from detected skills
"""
import re
import pickle
import logging
from pathlib import Path

import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── Resolve model paths ──────────────────────────────────────────────────────
# Point directly to the folder this script is currently in
_CURRENT_DIR = Path(__file__).resolve().parent

_lgbm_model = None
_tfidf_vectorizer = None


def _load_models():
    """Load lgbm model and tfidf vectorizer from disk (lazy, once)."""
    global _lgbm_model, _tfidf_vectorizer
    if _lgbm_model is not None:
        return

    import joblib

    # Look for the models in the exact same folder as cv_analyzer.py
    lgbm_path = _CURRENT_DIR / "lgbm_model.pkl"
    tfidf_path = _CURRENT_DIR / "tfidf_vectorizer.pkl"

    if not lgbm_path.exists():
        raise FileNotFoundError(f"LightGBM model not found at {lgbm_path}")
    if not tfidf_path.exists():
        raise FileNotFoundError(f"TF-IDF vectorizer not found at {tfidf_path}")

    logger.info("Loading lgbm_model.pkl ...")
    with open(lgbm_path, "rb") as f:
        _lgbm_model = pickle.load(f)

    logger.info("Loading tfidf_vectorizer.pkl ...")
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # suppress sklearn version warnings
        _tfidf_vectorizer = joblib.load(tfidf_path)

    logger.info("Models loaded successfully.")

# ══════════════════════════════════════════════════════════════════════════════
# TECH ALIASES  (from notebook cell 7)
# ══════════════════════════════════════════════════════════════════════════════

TECH_ALIASES = {
    # Languages
    'js': 'javascript', 'ts': 'typescript', 'py': 'python', 'rb': 'ruby',
    'golang': 'go', 'c#': 'csharp', 'c++': 'cpp', 'objective-c': 'objectivec',
    'kotlin': 'kotlin', 'swift': 'swift', 'php': 'php', 'scala': 'scala',
    'rust': 'rust', 'julia': 'julia', 'matlab': 'matlab', 'perl': 'perl',
    # ML / AI
    'ml': 'machine_learning', 'dl': 'deep_learning', 'ai': 'artificial_intelligence',
    'nlp': 'natural_language_processing', 'cv': 'computer_vision',
    'rl': 'reinforcement_learning', 'llm': 'large_language_model',
    'llms': 'large_language_model', 'genai': 'generative_ai',
    'gen ai': 'generative_ai', 'gpt': 'generative_pretrained_transformer',
    'bert': 'bert_transformer', 'xgb': 'xgboost', 'lgbm': 'lightgbm',
    'rf': 'random_forest', 'cnn': 'convolutional_neural_network',
    'rnn': 'recurrent_neural_network', 'lstm': 'long_short_term_memory',
    'gnn': 'graph_neural_network', 'gan': 'generative_adversarial_network',
    'vae': 'variational_autoencoder', 'svm': 'support_vector_machine',
    'knn': 'k_nearest_neighbors', 'pca': 'principal_component_analysis',
    'rag': 'retrieval_augmented_generation', 'mlops': 'machine_learning_operations',
    'sklearn': 'scikit_learn', 'scikit-learn': 'scikit_learn',
    'scikit learn': 'scikit_learn', 'pytorch': 'pytorch', 'torch': 'pytorch',
    'tensorflow': 'tensorflow', 'tf': 'tensorflow', 'keras': 'keras',
    'jax': 'jax', 'huggingface': 'hugging_face', 'hugging face': 'hugging_face',
    'hf': 'hugging_face', 'spacy': 'spacy', 'nltk': 'nltk',
    'openai': 'openai', 'langchain': 'langchain',
    # Cloud
    'aws': 'amazon_web_services', 'amazon web services': 'amazon_web_services',
    'gcp': 'google_cloud_platform', 'google cloud': 'google_cloud_platform',
    'azure': 'microsoft_azure', 'ec2': 'aws_ec2', 's3': 'aws_s3',
    'lambda': 'aws_lambda', 'sagemaker': 'aws_sagemaker',
    'gke': 'google_kubernetes_engine', 'bigquery': 'google_bigquery',
    'vertex ai': 'google_vertex_ai',
    # DevOps / Infra
    'k8s': 'kubernetes', 'k8': 'kubernetes', 'docker': 'docker',
    'ci/cd': 'cicd', 'ci cd': 'cicd', 'cicd': 'cicd',
    'iac': 'infrastructure_as_code', 'terraform': 'terraform',
    'ansible': 'ansible', 'helm': 'helm', 'jenkins': 'jenkins',
    'github actions': 'github_actions', 'gitlab ci': 'gitlab_ci',
    'argocd': 'argocd',
    # Databases
    'postgres': 'postgresql', 'pg': 'postgresql', 'mysql': 'mysql',
    'mssql': 'microsoft_sql_server', 'sql server': 'microsoft_sql_server',
    'mongo': 'mongodb', 'mongodb': 'mongodb', 'redis': 'redis',
    'elastic': 'elasticsearch', 'cassandra': 'apache_cassandra',
    'dynamo': 'amazon_dynamodb', 'dynamodb': 'amazon_dynamodb',
    'neo4j': 'neo4j', 'snowflake': 'snowflake', 'redshift': 'amazon_redshift',
    'databricks': 'databricks', 'spark': 'apache_spark', 'pyspark': 'apache_spark',
    'hadoop': 'apache_hadoop', 'hive': 'apache_hive', 'kafka': 'apache_kafka',
    'airflow': 'apache_airflow', 'dbt': 'data_build_tool',
    # Frontend / Web
    'react': 'reactjs', 'react.js': 'reactjs', 'react js': 'reactjs',
    'vue': 'vuejs', 'vue.js': 'vuejs', 'angular': 'angularjs',
    'next': 'nextjs', 'next.js': 'nextjs', 'node': 'nodejs',
    'node.js': 'nodejs', 'express': 'expressjs', 'rest': 'rest_api',
    'restful': 'rest_api', 'graphql': 'graphql', 'grpc': 'grpc',
    'html5': 'html', 'css3': 'css',
    # Version control / tools
    'git': 'git', 'github': 'github', 'gitlab': 'gitlab',
    'jira': 'jira', 'agile': 'agile', 'scrum': 'scrum', 'kanban': 'kanban',
    'oop': 'object_oriented_programming', 'tdd': 'test_driven_development',
    'bdd': 'behavior_driven_development',
    # Data / Analytics
    'bi': 'business_intelligence', 'etl': 'extract_transform_load',
    'elt': 'extract_load_transform', 'tableau': 'tableau',
    'powerbi': 'power_bi', 'power bi': 'power_bi', 'looker': 'looker',
    'matplotlib': 'matplotlib', 'seaborn': 'seaborn', 'plotly': 'plotly',
    'pandas': 'pandas', 'numpy': 'numpy', 'scipy': 'scipy',
    # Model optimization / serving
    'onnx': 'onnx_runtime', 'tensorrt': 'nvidia_tensorrt',
    'torchscript': 'torchscript', 'triton': 'triton_inference',
    'torchserve': 'torchserve', 'seldon': 'seldon_core',
    'kubeflow': 'kubeflow', 'mlflow': 'mlflow', 'feast': 'feast_feature_store',
    'bentoml': 'bentoml', 'ray': 'ray_distributed', 'deepspeed': 'deepspeed',
    'megatron': 'megatron_lm', 'vllm': 'vllm',
    # Monitoring
    'prometheus': 'prometheus_monitoring', 'grafana': 'grafana',
    'wandb': 'weights_and_biases', 'weights and biases': 'weights_and_biases',
    'neptune': 'neptune_ml', 'evidently': 'evidently_ai',
}

_ALIAS_SORTED = sorted(TECH_ALIASES.keys(), key=len, reverse=True)


def normalize_tech(text: str) -> str:
    """Normalize technology terms using alias mapping."""
    text = text.lower()
    for alias in _ALIAS_SORTED:
        text = re.sub(
            r'(?<![\w_])' + re.escape(alias) + r'(?![\w_])',
            TECH_ALIASES[alias], text
        )
    return text


# ══════════════════════════════════════════════════════════════════════════════
# NLP PROCESSING  (from notebook cell 13)
# ══════════════════════════════════════════════════════════════════════════════

# We use a simplified NLP pipeline that doesn't require NLTK data downloads
# for basic operation. Falls back gracefully if NLTK data is missing.

def _simple_lemmatize(word: str) -> str:
    """Basic suffix-stripping lemmatizer — no NLTK data needed."""
    if word.endswith('ies') and len(word) > 4:
        return word[:-3] + 'y'
    if word.endswith('ing') and len(word) > 5:
        return word[:-3]
    if word.endswith('tion') and len(word) > 5:
        return word
    if word.endswith('ed') and len(word) > 4:
        return word[:-2]
    if word.endswith('s') and not word.endswith('ss') and len(word) > 3:
        return word[:-1]
    return word


STOPWORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you',
    'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
    'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them',
    'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this',
    'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
    'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
    'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'into',
    'through', 'during', 'before', 'after', 'to', 'from', 'in', 'out', 'on',
    'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
    'there', 'when', 'where', 'why', 'how', 'all', 'both', 'each', 'few',
    'more', 'most', 'other', 'some', 'such', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should',
    'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn',
    'didn', 'doesn', 'hadn', 'hasn', 'haven', 'isn', 'ma', 'mightn', 'mustn',
    'needn', 'shan', 'shouldn', 'wasn', 'weren', 'won', 'wouldn',
}
# Keep negation words (important for context)
STOPWORDS -= {'no', 'not', 'nor'}


def nlp_process(text: str) -> str:
    """Tokenize, normalize tech terms, remove stopwords, lemmatize."""
    text = str(text)
    text = normalize_tech(text)
    text = text.lower()
    text = re.sub(r'[^a-z0-9_\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    tokens = text.split()
    tokens = [t for t in tokens if ('_' in t) or (t not in STOPWORDS and len(t) > 1)]
    # Simple lemmatization for non-compound tokens
    result = []
    for tok in tokens:
        if '_' in tok:
            result.append(tok)  # keep compound tokens as-is
        else:
            result.append(_simple_lemmatize(tok))
    return ' '.join(result)


# ══════════════════════════════════════════════════════════════════════════════
# IMPACT SCORE  (from notebook cell 9)
# ══════════════════════════════════════════════════════════════════════════════

IMPACT_PATTERNS = [
    # Revenue / growth
    r'(?:increased|improved|boosted|grew|raised)\s+(?:.*?\s+)?by\s+\d+\s*%',
    r'(?:generated|delivered|drove)\s+\$[\d,.]+\s*(?:m|k|million|billion)?',
    r'\d+\s*%\s+(?:increase|improvement|growth|reduction|decrease)',
    # Scale
    r'(?:served|handled|processed|managed)\s+(?:\d+[kmb]?\+?\s+)?(?:users?|requests?|transactions?|customers?)',
    r'(?:scaled|grew)\s+(?:to|from)\s+\d+',
    # Speed / efficiency
    r'(?:reduced|decreased|cut|lowered)\s+(?:.*?\s+)?(?:by\s+)?\d+\s*%',
    r'(?:reduced|decreased)\s+(?:latency|time|cost|errors?)\s+(?:by\s+)?\d+',
    r'\d+x\s+(?:faster|improvement|speedup)',
    # Team / leadership
    r'(?:led|managed|mentored|supervised)\s+(?:a\s+)?(?:team\s+of\s+)?\d+',
    # Leadership / mentoring
    r'mentored?\s+\d+\s+(?:engineer|developer|junior|team)',
    r'led\s+(?:team|development|deployment|project|migration)\s+of\s+\d+',
    r'managed\s+\d+\s+(?:engineer|developer|member)',
    # Certifications
    r'(?:aws|gcp|azure|tensorflow|pytorch|google|microsoft)\s+certif',
    # Publications
    r'(?:published|presented|authored)\s+(?:paper|research|article|blog)',
]


def compute_impact_score(text: str) -> float:
    """Returns a normalized impact score 0.0-1.0. Each match adds 0.04, capped at 0.20."""
    text_lower = str(text).lower()
    hits = sum(1 for pattern in IMPACT_PATTERNS if re.search(pattern, text_lower))
    return min(hits * 0.04, 0.20)


# ══════════════════════════════════════════════════════════════════════════════
# PREMIUM TECH SCORE  (from notebook cell 11)
# ══════════════════════════════════════════════════════════════════════════════

PREMIUM_TECH_GROUPS = {
    'model_optimization': {
        'tokens': {'nvidia_tensorrt', 'torchscript', 'onnx_runtime', 'triton_inference',
                   'torchserve', 'quantization', 'pruning', 'distillation',
                   'mixed_precision', 'deepspeed', 'megatron_lm', 'vllm'},
        'weight': 1.5,
    },
    'mlops_platform': {
        'tokens': {'kubeflow', 'seldon_core', 'mlflow', 'bentoml', 'ray_distributed',
                   'feast_feature_store', 'evidently_ai', 'neptune_ml', 'weights_and_biases'},
        'weight': 1.3,
    },
    'monitoring': {
        'tokens': {'prometheus_monitoring', 'grafana', 'opentelemetry',
                   'datadog', 'sentry', 'elk_stack'},
        'weight': 1.2,
    },
    'distributed_systems': {
        'tokens': {'apache_kafka', 'apache_spark', 'apache_flink', 'ray_distributed',
                   'distributed_training', 'pytorch_distributed'},
        'weight': 1.2,
    },
    'advanced_arch': {
        'tokens': {'bert_transformer', 'generative_adversarial_network',
                   'variational_autoencoder', 'retrieval_augmented_generation',
                   'graph_neural_network', 'large_language_model'},
        'weight': 1.1,
    },
}


def compute_premium_tech_score(text: str) -> float:
    """Weighted premium tech density score: 0.0-1.0, capped at 0.15."""
    tokens = set(text.lower().split())
    weighted_hits = 0.0
    for group in PREMIUM_TECH_GROUPS.values():
        hits = len(tokens & group['tokens'])
        weighted_hits += hits * group['weight']
    return min(weighted_hits / 10.0 * 0.15, 0.15)


# ══════════════════════════════════════════════════════════════════════════════
# SENIORITY DETECTION  (from notebook cell 11)
# ══════════════════════════════════════════════════════════════════════════════

SENIORITY_LEVELS = {
    'intern': 0,
    'junior': 1, 'jr': 1, 'entry': 1, 'associate': 1,
    'mid': 2, 'intermediate': 2,
    'senior': 3, 'sr': 3,
    'lead': 4, 'principal': 4, 'staff': 4,
    'architect': 5, 'director': 5, 'head of': 5, 'vp': 5,
}


def detect_seniority(text: str) -> int:
    """Returns seniority level 0 (intern) - 5 (architect/director)."""
    text_lower = text.lower()
    max_level = 0
    for keyword, level in SENIORITY_LEVELS.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            max_level = max(max_level, level)
    return max_level


# ══════════════════════════════════════════════════════════════════════════════
# YEARS EXTRACTION  (from notebook cell 17)
# ══════════════════════════════════════════════════════════════════════════════

_EXP_PATTERN = re.compile(r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience', re.I)


def extract_years(text: str) -> int:
    """Extract max years of experience mentioned in text."""
    matches = _EXP_PATTERN.findall(str(text))
    return max((int(m) for m in matches), default=0)


# ══════════════════════════════════════════════════════════════════════════════
# TECH CATEGORIES  (from notebook cell 15)
# ══════════════════════════════════════════════════════════════════════════════

TECH_CATEGORIES = {
    'languages': ['python', 'javascript', 'typescript', 'java', 'go', 'rust',
                  'cpp', 'csharp', 'ruby', 'scala', 'kotlin', 'swift', 'php',
                  'r_lang', 'matlab', 'julia', 'perl'],
    'ml_frameworks': ['pytorch', 'tensorflow', 'keras', 'scikit_learn', 'jax',
                      'xgboost', 'lightgbm', 'hugging_face', 'spacy', 'nltk',
                      'langchain', 'openai'],
    'ml_concepts': ['machine_learning', 'deep_learning', 'natural_language_processing',
                    'computer_vision', 'reinforcement_learning', 'large_language_model',
                    'generative_ai', 'convolutional_neural_network', 'recurrent_neural_network',
                    'long_short_term_memory', 'generative_adversarial_network',
                    'retrieval_augmented_generation', 'support_vector_machine',
                    'random_forest', 'principal_component_analysis',
                    'machine_learning_operations', 'bert_transformer'],
    'cloud': ['amazon_web_services', 'google_cloud_platform', 'microsoft_azure',
              'aws_ec2', 'aws_s3', 'aws_lambda', 'aws_sagemaker',
              'google_kubernetes_engine', 'google_bigquery', 'google_vertex_ai',
              'snowflake', 'databricks', 'amazon_redshift', 'amazon_dynamodb'],
    'databases': ['postgresql', 'mysql', 'microsoft_sql_server', 'mongodb',
                  'redis', 'elasticsearch', 'apache_cassandra', 'neo4j',
                  'apache_hive', 'hadoop_distributed_file_system'],
    'data_engineering': ['apache_spark', 'apache_hadoop', 'apache_kafka', 'apache_airflow',
                         'data_build_tool', 'extract_transform_load', 'extract_load_transform'],
    'devops': ['kubernetes', 'docker', 'cicd', 'terraform', 'ansible',
               'jenkins', 'github_actions', 'gitlab_ci', 'argocd', 'helm',
               'infrastructure_as_code'],
    'model_serving': ['nvidia_tensorrt', 'torchscript', 'onnx_runtime', 'triton_inference',
                      'torchserve', 'seldon_core', 'bentoml', 'mlflow', 'kubeflow',
                      'vllm', 'ray_distributed'],
    'web': ['reactjs', 'vuejs', 'angularjs', 'nextjs', 'nodejs', 'expressjs',
            'rest_api', 'graphql', 'grpc', 'html', 'css'],
    'tooling': ['git', 'github', 'gitlab', 'jira', 'agile', 'scrum',
                'docker', 'numpy', 'pandas', 'scipy',
                'prometheus_monitoring', 'grafana', 'weights_and_biases'],
}

# Reverse lookup: token -> human-readable name
_TOKEN_TO_READABLE = {}
for _alias, _normalized in TECH_ALIASES.items():
    if _normalized not in _TOKEN_TO_READABLE:
        # Pick the longest alias as the "readable" name
        _TOKEN_TO_READABLE[_normalized] = _alias
# Override with better readable names
_READABLE_OVERRIDES = {
    'python': 'Python', 'javascript': 'JavaScript', 'typescript': 'TypeScript',
    'java': 'Java', 'go': 'Go', 'rust': 'Rust', 'cpp': 'C++', 'csharp': 'C#',
    'ruby': 'Ruby', 'scala': 'Scala', 'kotlin': 'Kotlin', 'swift': 'Swift',
    'php': 'PHP', 'r_lang': 'R', 'matlab': 'MATLAB', 'julia': 'Julia', 'perl': 'Perl',
    'pytorch': 'PyTorch', 'tensorflow': 'TensorFlow', 'keras': 'Keras',
    'scikit_learn': 'Scikit-learn', 'jax': 'JAX', 'xgboost': 'XGBoost',
    'lightgbm': 'LightGBM', 'hugging_face': 'Hugging Face', 'spacy': 'spaCy',
    'nltk': 'NLTK', 'openai': 'OpenAI', 'langchain': 'LangChain',
    'machine_learning': 'Machine Learning', 'deep_learning': 'Deep Learning',
    'natural_language_processing': 'NLP', 'computer_vision': 'Computer Vision',
    'large_language_model': 'LLMs', 'generative_ai': 'Generative AI',
    'amazon_web_services': 'AWS', 'google_cloud_platform': 'GCP',
    'microsoft_azure': 'Azure', 'kubernetes': 'Kubernetes', 'docker': 'Docker',
    'cicd': 'CI/CD', 'terraform': 'Terraform', 'jenkins': 'Jenkins',
    'postgresql': 'PostgreSQL', 'mysql': 'MySQL', 'mongodb': 'MongoDB',
    'redis': 'Redis', 'elasticsearch': 'Elasticsearch', 'snowflake': 'Snowflake',
    'apache_spark': 'Apache Spark', 'apache_kafka': 'Apache Kafka',
    'apache_airflow': 'Apache Airflow', 'reactjs': 'React', 'vuejs': 'Vue.js',
    'angularjs': 'Angular', 'nextjs': 'Next.js', 'nodejs': 'Node.js',
    'expressjs': 'Express.js', 'rest_api': 'REST API', 'graphql': 'GraphQL',
    'git': 'Git', 'github': 'GitHub', 'gitlab': 'GitLab', 'jira': 'Jira',
    'agile': 'Agile', 'pandas': 'Pandas', 'numpy': 'NumPy',
    'mlflow': 'MLflow', 'kubeflow': 'Kubeflow', 'databricks': 'Databricks',
    'nvidia_tensorrt': 'TensorRT', 'onnx_runtime': 'ONNX',
    'aws_sagemaker': 'SageMaker', 'google_bigquery': 'BigQuery',
    'github_actions': 'GitHub Actions', 'gitlab_ci': 'GitLab CI',
    'apache_hadoop': 'Hadoop', 'data_build_tool': 'dbt',
    'machine_learning_operations': 'MLOps',
    'retrieval_augmented_generation': 'RAG',
    'bert_transformer': 'BERT',
    'helm': 'Helm', 'argocd': 'ArgoCD', 'ansible': 'Ansible',
    'grafana': 'Grafana', 'prometheus_monitoring': 'Prometheus',
    'weights_and_biases': 'W&B', 'scipy': 'SciPy',
    'infrastructure_as_code': 'IaC',
}
_TOKEN_TO_READABLE.update(_READABLE_OVERRIDES)


def _readable(token: str) -> str:
    """Convert a normalized token back to a human-readable name."""
    return _READABLE_OVERRIDES.get(token, token.replace('_', ' ').title())


def category_overlap_features(resume_text: str, job_text: str) -> dict:
    """Compute per-category overlap features between resume and job texts."""
    resume_tokens = set(resume_text.split())
    job_tokens = set(job_text.split())
    features = {}
    for cat, tokens in TECH_CATEGORIES.items():
        token_set = set(tokens)
        job_cat_tokens = token_set & job_tokens
        resume_cat_tokens = token_set & resume_tokens
        if job_cat_tokens:
            features[f'overlap_{cat}'] = len(resume_cat_tokens & job_cat_tokens) / len(job_cat_tokens)
        else:
            features[f'overlap_{cat}'] = 0.0
        features[f'resume_{cat}_count'] = len(resume_cat_tokens)
        features[f'job_{cat}_count'] = len(job_cat_tokens)
    return features


# ══════════════════════════════════════════════════════════════════════════════
# CALIBRATED SCORE  (from notebook cell 29)
# ══════════════════════════════════════════════════════════════════════════════

def calibrated_score(
    raw_score: float,
    sbert_cos: float,
    impact_score: float,
    premium_score: float,
    seniority_match: float,
) -> float:
    """Apply post-prediction calibration bonuses."""
    bonus = 0.0

    # Semantic bonus
    if sbert_cos > 0.6:
        bonus += (sbert_cos - 0.6) * 0.20

    # Impact bonus: quantified achievements
    bonus += impact_score * 0.60

    # Premium tech bonus
    bonus += premium_score * 0.67

    # Seniority fit
    bonus += seniority_match * 0.05

    # Amplify when raw score is already high
    if raw_score > 0.65:
        bonus *= 1.15

    return float(np.clip(raw_score + bonus, 0.0, 1.0))


# ══════════════════════════════════════════════════════════════════════════════
# GENERIC JOB DESCRIPTION — used as comparison target for standalone CV scoring
# ══════════════════════════════════════════════════════════════════════════════

GENERIC_JOB = {
    'job_position_name': 'Senior Software Engineer',
    'skills_required': (
        'Python, JavaScript, TypeScript, Java, SQL, '
        'React, Node.js, REST API, GraphQL, '
        'AWS, Docker, Kubernetes, CI/CD, Git, '
        'PostgreSQL, MongoDB, Redis, '
        'Machine Learning, Deep Learning, TensorFlow, PyTorch, '
        'Agile, Scrum, Team Leadership'
    ),
    'responsibilities': (
        'Design and develop scalable software systems. '
        'Lead technical projects and mentor junior engineers. '
        'Collaborate with cross-functional teams. '
        'Write clean, tested, maintainable code. '
        'Deploy and monitor production services.'
    ),
    'educationaL_requirements': (
        'Bachelor or Master degree in Computer Science, '
        'Software Engineering, or related field.'
    ),
}

# Category column order — must match training order for the model
_CAT_COLUMNS = []
for _cat in TECH_CATEGORIES:
    _CAT_COLUMNS.extend([
        f'overlap_{_cat}', f'resume_{_cat}_count', f'job_{_cat}_count'
    ])


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def extract_skills_from_text(text: str) -> list[str]:
    """
    Extract technical skills from CV text using normalize_tech + TECH_CATEGORIES.
    Returns human-readable skill names (max 12).
    """
    normalized = nlp_process(text)
    tokens = set(normalized.split())

    found_skills = []
    seen = set()

    # Check all category tokens
    for cat, cat_tokens in TECH_CATEGORIES.items():
        for token in cat_tokens:
            if token in tokens and token not in seen:
                readable = _readable(token)
                found_skills.append(readable)
                seen.add(token)

    # Sort by category importance (languages first, then frameworks, etc.)
    # and cap at 12
    return found_skills[:12]


def compute_cv_score(cv_text: str) -> dict:
    """
    Score a CV using the lgbm model against a generic job description.
    Returns dict with score (0-100) and component scores.
    """
    _load_models()

    # Build text blocks (mimicking notebook's predict_match_score)
    cv_full_raw = cv_text
    job_full_raw = ' '.join(filter(None, [
        GENERIC_JOB.get('job_position_name', ''),
        GENERIC_JOB.get('skills_required', ''),
        GENERIC_JOB.get('responsibilities', ''),
        GENERIC_JOB.get('educationaL_requirements', ''),
    ]))

    resume_p = nlp_process(cv_full_raw)
    job_p = nlp_process(job_full_raw)

    # TF-IDF features
    rv = _tfidf_vectorizer.transform([resume_p])
    jv = _tfidf_vectorizer.transform([job_p])
    tfidf_cos = float(cosine_similarity(rv, jv)[0][0])

    # Skip SBERT (heavy dependency) — use neutral value
    sbert_cos_val = 0.5

    # Bonus signals
    impact = compute_impact_score(cv_full_raw)
    premium = compute_premium_tech_score(resume_p)
    j_premium = compute_premium_tech_score(job_p)
    r_sen = detect_seniority(cv_full_raw)
    j_sen = detect_seniority(job_full_raw)
    sen_match = 1.0 - abs(r_sen - j_sen) / 5.0
    r_yrs = extract_years(cv_full_raw)
    j_yrs = extract_years(job_full_raw)

    # Category features
    cat_feats = category_overlap_features(resume_p, job_p)

    # Build category row in correct column order
    cat_values = [cat_feats.get(col, 0.0) for col in _CAT_COLUMNS]

    # Scalar block (must match notebook's column_stack order)
    scalars = np.array([[
        tfidf_cos, sbert_cos_val, impact, premium, j_premium,
        sen_match, r_sen / 5.0, j_sen / 5.0, r_yrs / 10.0, j_yrs / 10.0
    ]])

    # Assemble feature matrix: [resume_tfidf | job_tfidf | scalars | category_feats]
    X_new = hstack([rv, jv, csr_matrix(scalars), csr_matrix([cat_values])])

    # Predict with LightGBM
    raw_score = float(np.clip(_lgbm_model.predict(X_new)[0], 0.0, 1.0))

    # Calibrate
    final = calibrated_score(raw_score, sbert_cos_val, impact, premium, sen_match)

    # Scale to 0-100
    score_pct = int(round(final * 100))

    return {
        'score': score_pct,
        'raw_score': round(raw_score, 4),
        'tfidf_similarity': round(tfidf_cos, 4),
        'impact_score': round(impact, 4),
        'premium_tech_score': round(premium, 4),
        'seniority_level': r_sen,
        'years_experience': r_yrs,
    }


def generate_strengths(cv_text: str) -> list[str]:
    """Derive strengths from CV text using local NLP analysis."""
    strengths = []
    normalized = nlp_process(cv_text)

    impact = compute_impact_score(cv_text)
    premium = compute_premium_tech_score(normalized)
    seniority = detect_seniority(cv_text)
    years = extract_years(cv_text)

    if impact > 0.08:
        strengths.append("Strong quantified achievements with measurable impact")
    elif impact > 0.04:
        strengths.append("Some quantified achievements demonstrating results")

    if premium > 0.05:
        strengths.append("Expertise in advanced/premium technologies")
    elif premium > 0.02:
        strengths.append("Familiarity with modern tech stack")

    if seniority >= 4:
        strengths.append("Senior leadership experience (lead/principal level)")
    elif seniority >= 3:
        strengths.append("Senior-level professional experience")
    elif seniority >= 2:
        strengths.append("Mid-level professional experience")

    if years >= 5:
        strengths.append(f"Extensive experience ({years}+ years in the field)")
    elif years >= 3:
        strengths.append(f"Solid experience ({years}+ years in the field)")

    # Check category coverage
    tokens = set(normalized.split())
    strong_categories = []
    for cat, cat_tokens in TECH_CATEGORIES.items():
        count = len(set(cat_tokens) & tokens)
        if count >= 3:
            strong_categories.append(cat.replace('_', ' ').title())
    if strong_categories:
        strengths.append(f"Strong skills in: {', '.join(strong_categories[:3])}")

    # Ensure at least 3 strengths
    defaults = [
        "Technical skills relevant to industry demands",
        "Diverse skill set across multiple domains",
        "Professional experience in software development",
    ]
    while len(strengths) < 3:
        strengths.append(defaults[len(strengths)])

    return strengths[:3]


def generate_recommendations(cv_text: str, skills: list[str]) -> list[str]:
    """Generate rule-based improvement recommendations."""
    recommendations = []
    normalized = nlp_process(cv_text)
    impact = compute_impact_score(cv_text)
    years = extract_years(cv_text)
    tokens = set(normalized.split())

    # Check for quantified achievements
    if impact < 0.04:
        recommendations.append(
            "Add quantified achievements (e.g., 'Increased performance by 30%', "
            "'Managed team of 5 engineers')"
        )

    # Check for cloud skills
    cloud_tokens = set(TECH_CATEGORIES.get('cloud', []))
    if not (cloud_tokens & tokens):
        recommendations.append(
            "Add cloud platform experience (AWS, GCP, or Azure) — highly valued by employers"
        )

    # Check for DevOps
    devops_tokens = set(TECH_CATEGORIES.get('devops', []))
    if not (devops_tokens & tokens):
        recommendations.append(
            "Include DevOps/CI/CD experience (Docker, Kubernetes, GitHub Actions)"
        )

    # Check for years of experience mentioned
    if years == 0:
        recommendations.append(
            "Explicitly mention your years of experience for better ATS matching"
        )

    # Check for leadership signals
    seniority = detect_seniority(cv_text)
    if seniority < 2 and years >= 3:
        recommendations.append(
            "Highlight leadership or mentoring experience to signal career growth"
        )

    # General tips
    if len(skills) < 5:
        recommendations.append(
            "Expand your technical skills section — list specific tools and frameworks"
        )

    defaults = [
        "Tailor your CV to match specific job descriptions for better scoring",
        "Include relevant certifications or professional development",
        "Add a concise professional summary at the top of your CV",
        "Use action verbs and specific metrics to describe accomplishments",
    ]
    while len(recommendations) < 4:
        for d in defaults:
            if d not in recommendations and len(recommendations) < 4:
                recommendations.append(d)

    return recommendations[:4]


# ══════════════════════════════════════════════════════════════════════════════
# ROLE INFERENCE — maps detected skills to likely best-fit role
# ══════════════════════════════════════════════════════════════════════════════

_ROLE_MAP = [
    # (required_tokens, role_name, min_count)
    ({'machine_learning', 'deep_learning', 'pytorch', 'tensorflow', 'scikit_learn'},
     'Machine Learning Engineer', 2),
    ({'natural_language_processing', 'large_language_model', 'bert_transformer', 'hugging_face', 'langchain'},
     'NLP / AI Engineer', 2),
    ({'computer_vision', 'convolutional_neural_network'},
     'Computer Vision Engineer', 1),
    ({'apache_spark', 'apache_kafka', 'apache_airflow', 'data_build_tool', 'extract_transform_load'},
     'Data Engineer', 2),
    ({'reactjs', 'vuejs', 'angularjs', 'nextjs', 'html', 'css'},
     'Frontend Developer', 2),
    ({'nodejs', 'expressjs', 'rest_api', 'graphql', 'postgresql', 'mongodb'},
     'Backend Developer', 2),
    ({'kubernetes', 'docker', 'terraform', 'cicd', 'amazon_web_services', 'infrastructure_as_code'},
     'DevOps / Cloud Engineer', 2),
    ({'python', 'pandas', 'numpy', 'matplotlib', 'tableau', 'power_bi'},
     'Data Analyst / Data Scientist', 2),
    ({'reactjs', 'nodejs', 'postgresql', 'docker', 'rest_api'},
     'Full-Stack Developer', 2),
    ({'amazon_web_services', 'google_cloud_platform', 'microsoft_azure'},
     'Cloud Solutions Architect', 2),
]


def infer_best_fit_role(cv_text: str) -> str:
    """Infer best-fit job role from detected skills in CV text.

    Roles are chosen by *relative* match strength (overlap / category size)
    rather than a fixed minimum token count, so smaller-but-specific
    categories (e.g. Computer Vision) can compete fairly against larger
    ones, and a CV only needs to show *some* signal for a category — not
    an arbitrary exact count — to be matched to it. If no category has any
    overlap at all, we fall back to a generic role.
    """
    normalized = nlp_process(cv_text)
    tokens = set(normalized.split())

    best_role = None
    best_score = 0.0
    best_overlap = 0

    for role_tokens, role_name, _min_count in _ROLE_MAP:
        overlap = len(role_tokens & tokens)
        if overlap == 0:
            continue
        # Relative strength: how much of this role's skill set is present.
        score = overlap / len(role_tokens)
        if score > best_score or (score == best_score and overlap > best_overlap):
            best_score = score
            best_overlap = overlap
            best_role = role_name

    if best_role is None:
        best_role = 'Software Developer'

    # Only add a seniority prefix when the CV contains explicit evidence
    # (an actual seniority keyword) — never as a silent default.
    text_lower = cv_text.lower()
    matched_level = None
    for keyword, level in SENIORITY_LEVELS.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            if matched_level is None or level > matched_level:
                matched_level = level

    if matched_level is not None:
        if matched_level >= 4:
            best_role = f"Lead/Principal {best_role}"
        elif matched_level == 3:
            best_role = f"Senior {best_role}"
        elif matched_level == 1:
            best_role = f"Junior {best_role}"
        elif matched_level == 0:
            best_role = f"Intern {best_role}"
        # matched_level == 2 (mid-level) -> no prefix, same as before

    return best_role


def analyze_cv_local(cv_text: str) -> dict:
    """
    Full local CV analysis pipeline.
    Returns dict with: score, skills, strengths, recommendations, best_fit_role
    """
    try:
        # 1. Score using lgbm model
        score_result = compute_cv_score(cv_text)
        score = score_result['score']

        # 2. Extract skills
        skills = extract_skills_from_text(cv_text)

        # 3. Generate strengths
        strengths = generate_strengths(cv_text)

        # 4. Generate recommendations
        recommendations = generate_recommendations(cv_text, skills)

        # 5. Infer best-fit role
        best_fit_role = infer_best_fit_role(cv_text)

        logger.info(f"Local analysis complete: score={score}, skills={len(skills)}, role={best_fit_role}")

        return {
            'score': score,
            'skills': skills,
            'strengths': strengths,
            'recommendations': recommendations,
            'best_fit_role': best_fit_role,
        }
    except Exception as e:
        logger.error(f"Local CV analysis failed: {e}", exc_info=True)
        raise
