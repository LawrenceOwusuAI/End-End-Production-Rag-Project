from __future__ import annotations
import asyncio
import csv
import json
import os
import statistics
import math
import sys
import time
from pinecone import Pinecone
from langchain_huggingface import HuggingFaceEmbeddings

import types
from pathlib import Path
from dotenv import load_dotenv
#from openai import AsyncOpenAI
from langchain_pinecone import PineconeVectorStore


# ============================================================
# RAGAS / LANGCHAIN COMPATIBILITY SHIM
# ============================================================
# Your RAGAS 0.3.9 environment may try to import the older
# VertexAI integrations. We are not using VertexAI.
# ============================================================

try:
    from langchain_community.chat_models.vertexai import ChatVertexAI

except ModuleNotFoundError:

    vertex_chat_module = types.ModuleType(
        "langchain_community.chat_models.vertexai"
    )

    class ChatVertexAI:
        pass

    vertex_chat_module.ChatVertexAI = ChatVertexAI

    sys.modules[
        "langchain_community.chat_models.vertexai"
    ] = vertex_chat_module


try:
    from langchain_community.llms import VertexAI

except (ImportError, ModuleNotFoundError):

    import langchain_community.llms as lc_llms

    class VertexAI:
        pass

    lc_llms.VertexAI = VertexAI


# ============================================================
# RAGAS IMPORTS
# ============================================================

#from ragas.llms import llm_factory

#from ragas.embeddings.base import embedding_factory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas import SingleTurnSample

from ragas.metrics import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    FactualCorrectness,
    Faithfulness,
)

from vectorstore import INDEX_NAME,create_embedding_model,create_pinecone_client
from reranker import create_advanced_retriever

from llm_gateway import (
    create_portkey_llm,
)

from langchain_core.prompts import ChatPromptTemplate

from logger import logging


load_dotenv(override=True)


# ============================================================
# CONFIGURATION
# ============================================================

CHUNKS_PATH = Path(
    os.getenv(
        "RAGAS_CHUNKS_PATH",
        "output/chunks/wildfire_paper-chunks.jsonl",
    )
)

RESULTS_PATH = Path(
    os.getenv(
        "RAGAS_RESULTS_PATH",
        "ragas_offline_results.csv",
    )
)

SUMMARY_PATH = Path(
    os.getenv(
        "RAGAS_SUMMARY_PATH",
        "ragas_offline_summary.json",
    )
)

EVAL_NAMESPACE = os.getenv(
    "EVAL_NAMESPACE",
    "wildfire_paper",
)

RAG_MODEL = os.getenv(
    "RAG_MODEL",
    "gpt-4.1-mini",
)

RAGAS_EVALUATOR_MODEL = os.getenv(
    "RAGAS_EVALUATOR_MODEL",
    "gpt-4.1-mini",
)

RAGAS_EMBEDDING_MODEL = os.getenv(
    "RAGAS_EMBEDDING_MODEL",
    "text-embedding-3-small",
)

# 0 = run every golden question.
# For initial testing:
#
# RAGAS_MAX_SAMPLES=3
#
MAX_SAMPLES = int(
    os.getenv(
        "RAGAS_MAX_SAMPLES",
        "0",
    )
)


# ============================================================
# OFFLINE QUALITY THRESHOLDS
# ============================================================

THRESHOLDS = {
    # Deterministic retrieval metrics
    "hit_at_4": 0.70,
    "recall_at_4": 0.70,
    "mrr": 0.70,
    "ndcg_at_4": 0.70,

    # RAGAS semantic retrieval/generation metrics
    "context_precision": 0.70,
    "context_recall": 0.70,
    "faithfulness": 0.70,
    "answer_relevancy": 0.70,
    "factual_correctness": 0.70,
}


# ============================================================
# GOLDEN DATASET
# ============================================================
#
# These questions/references were prepared from the actual
# wildfire JSONL chunks.
#
# expected_chunk_ids are used for deterministic retrieval
# Hit@4, Recall@4, MRR, and nDCG@4.
#
# ============================================================

GOLDENS = [


    {
        "question":
            "What dataset was used in the study and how many images does it contain?",

        "reference":
            (
                "The study used the DeepFire dataset from Kaggle. "
                "It contains 1,900 images: 950 fire images and "
                "950 no-fire images."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00023",
        ],
    },

    {
        "question":
            "How is the DeepFire dataset divided into training, validation, and test sets?",

        "reference":
            (
                "The training set contains 1,300 images, including 642 forest-fire "
                "images and 658 no-fire images. The validation set contains 220 "
                "images, including 107 fire and 113 no-fire images. "
                "The test set contains 380 images, with 190 images from each class."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00024",
        ],
    },

    {
        "question":
            "What preprocessing was applied to the wildfire images before model training?",

        "reference":
            (
                "The images were resized to 224 by 224 pixels with three RGB "
                "channels and normalized. Normalization was used to support "
                "backpropagation, improve convergence speed, and improve model "
                "performance."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00025",
        ],
    },

    {
        "question":
            "Which pretrained CNN models were selected to construct the ensemble models?",

        "reference":
            (
                "The study selected VGGNet or VGG16, InceptionV3, and ResNet50 "
                "as the pretrained CNN models used to construct the ensemble and "
                "weighted ensemble wildfire detection models."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00026",
        ],
    },

    {
        "question":
            "Why does ResNet50 use residual blocks and skip connections?",

        "reference":
            (
                "ResNet50 uses residual blocks and skip connections to address "
                "vanishing or exploding gradients, improve gradient flow, preserve "
                "learned information, and improve model performance."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00027",
        ],
    },

    {
        "question":
            "What architectural techniques make InceptionV3 computationally efficient?",

        "reference":
            (
                "InceptionV3 uses techniques including factorized convolutions, "
                "regularization, spatial factorization, dimension reduction, "
                "auxiliary classifiers, and parallel computations. Its improved "
                "inception module performs parallel multi-scale convolutions to "
                "capture diverse patterns."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00028",
        ],
    },

    {
        "question":
            "What is the basic architecture of VGG16 described in the paper?",

        "reference":
            (
                "VGG16 consists of 13 convolutional layers, two fully connected "
                "layers, and one SoftMax classifier. It primarily uses multiple "
                "3 by 3 convolutional filters and max-pooling layers."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00029",
        ],
    },

    {
        "question":
            "What optimizer, loss function, epochs, batch size, and learning rate were used to train the models?",

        "reference":
            (
                "The models were trained for 50 epochs using the Adam optimizer, "
                "binary cross-entropy loss, a batch size of 32, and a learning "
                "rate of 0.001. ReLU was used in the network and sigmoid was used "
                "for the output layer."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00031",
        ],
    },

    {
        "question":
            "What computing environment and major software packages were used for the experiments?",

        "reference":
            (
                "The experiments were performed in Google Colab using an "
                "NVIDIA-SMI 535.104.05 TP4 GPU. The environment used Python "
                "3.10.12, TensorFlow 2.15.0, Keras, NumPy 1.25.2, Pandas 2.0.3, "
                "Seaborn 0.13.1, Matplotlib 3.7.1, and OpenCV 4.8.0."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00033",
        ],
    },

    {
        "question":
            "Why were ResNet50, InceptionV3, and VGG16 first trained individually?",

        "reference":
            (
                "The three models were first trained individually to establish "
                "baseline performance. Their results served as benchmarks for "
                "evaluating the proposed ensemble and weighted ensemble models."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00034",
        ],
    },

    {
        "question":
            "Which performance metrics were used to evaluate the wildfire classifiers?",

        "reference":
            (
                "The classifiers were evaluated using accuracy, precision, recall, "
                "F1-score, ROC-AUC, false positive rate, false negative rate, "
                "and error rate."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00035",
        ],
    },

    {
        "question":
            "What false negative rates were obtained by ResNet50, InceptionV3, and VGG16?",

        "reference":
            (
                "ResNet50 had a false negative rate of 12.6%, while both "
                "InceptionV3 and VGG16 had false negative rates of 1.1%."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00038",
        ],
    },

    {
        "question":
            "What test accuracies were achieved by ResNet50, InceptionV3, VGG16, and the ensemble models?",

        "reference":
            (
                "ResNet50 achieved 86.3% accuracy, InceptionV3 achieved 96.6%, "
                "VGG16 achieved 99.5%, and both the ensemble and weighted ensemble "
                "models achieved 99.7% accuracy."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00039",
        ],
    },

    {
        "question":
            "What precision, recall, and F1-score did the proposed ensemble models achieve?",

        "reference":
            (
                "Both proposed ensemble models achieved 99.5% precision, "
                "100% recall, and a 99.8% F1-score."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00039",
        ],
    },

    {
        "question":
            "What was the false negative rate of the ensemble and weighted ensemble models?",

        "reference":
            (
                "Both the ensemble and weighted ensemble models achieved a "
                "false negative rate of 0.00%, meaning they correctly identified "
                "all wildfire instances in the test set."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00041",
        ],
    },

    {
        "question":
            "How were weights selected for the weighted ensemble model?",

        "reference":
            (
                "Weights from 1 through 20 were systematically tested. Different "
                "weight combinations for the individual models were evaluated on "
                "the test dataset, and the combination that maximized performance "
                "was selected."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00044",
        ],
    },

    {
        "question":
            "How did the ensemble models' error rate compare with the best individual model?",

        "reference":
            (
                "The ensemble models achieved an error rate of 0.3%, compared "
                "with 0.5% for VGG16, the best-performing individual model."
            ),

        "expected_chunk_ids": [
            "wildfire_paper-chunk-00045",
        ],
    }

    
   

]


# ============================================================
# LOAD / VALIDATE JSONL CHUNKS
# ============================================================

def load_chunks() -> dict[str, dict]:

    if not CHUNKS_PATH.exists():

        raise FileNotFoundError(
            f"Chunk JSONL was not found: "
            f"{CHUNKS_PATH.resolve()}"
        )


    chunks = {}


    with CHUNKS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1,
        ):

            line = line.strip()

            if not line:
                continue


            record = json.loads(
                line
            )


            chunk_id = (
                record.get("id")
                or
                record.get(
                    "metadata",
                    {}
                ).get(
                    "chunk_id"
                )
            )


            if not chunk_id:

                raise ValueError(
                    f"Missing chunk ID on "
                    f"JSONL line {line_number}"
                )


            chunks[
                chunk_id
            ] = record


    print(
        f"Loaded {len(chunks)} chunks "
        f"from {CHUNKS_PATH}"
    )


    return chunks


# ============================================================
# VALIDATE GOLDEN CHUNK IDS
# ============================================================

def validate_goldens(
    chunk_lookup: dict[str, dict],
) -> None:

    known_ids = set(
        chunk_lookup.keys()
    )


    for number, sample in enumerate(
        GOLDENS,
        start=1,
    ):

        expected_ids = set(
            sample[
                "expected_chunk_ids"
            ]
        )


        missing = (
            expected_ids
            -
            known_ids
        )


        if missing:

            raise ValueError(
                f"Golden sample {number} "
                f"contains unknown chunk IDs: "
                f"{sorted(missing)}"
            )


    print(
        f"Validated {len(GOLDENS)} golden samples "
        f"against the chunk JSONL."
    )

def create_answer_prompt():

    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a question-answering assistant for a
Retrieval-Augmented Generation (RAG) system.

Answer the user's question using only the provided
retrieved document context.

RULES:

1. Use only information contained in the retrieved context.

2. Do not introduce unsupported facts.

3. Combine information from multiple retrieved chunks
   when necessary.

4. Provide a clear, coherent, and concise answer.

5. If the answer is not supported by the retrieved context,
   say that the information is not available in the context.

Retrieved context:
{context}
""",
            ),
            (
                "human",
                "{query}",
            ),
        ]
    )
# ============================================================
# CREATE RAG PIPELINE
# ============================================================

def create_rag_pipeline():

    logging.info(
        "Initializing offline RAG evaluation pipeline"
    )


    # --------------------------------------------------------
    # SAME EMBEDDING MODEL AS PRODUCTION RAG
    # --------------------------------------------------------

    embeddings = (
        create_embedding_model()
    )


    # --------------------------------------------------------
    # SAME PINECONE INDEX
    # --------------------------------------------------------

    pc = (
        create_pinecone_client()
    )


    index = pc.Index(
        INDEX_NAME
    )


    stats = (
        index.describe_index_stats()
    )


    namespace_names = set()


    try:

        namespace_names = set(
            stats.namespaces.keys()
        )

    except Exception:

        try:

            namespace_names = set(
                stats[
                    "namespaces"
                ].keys()
            )

        except Exception:

            pass


    if (
        namespace_names
        and
        EVAL_NAMESPACE
        not in namespace_names
    ):

        raise ValueError(
            f"Pinecone namespace "
            f"'{EVAL_NAMESPACE}' was not found. "
            f"Available namespaces: "
            f"{sorted(namespace_names)}"
        )


    vector_store = (
        PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace=EVAL_NAMESPACE,
        )
    )


    # --------------------------------------------------------
    # SAME ADVANCED RETRIEVER
    #
    # query rewriting
    # query expansion
    # query decomposition
    # Pinecone
    # RRF
    # cross-encoder reranking
    # --------------------------------------------------------

    retriever = (
        create_advanced_retriever(
            vector_store
        )
    )


    # --------------------------------------------------------
    # SAME GENERATION PIPELINE
    # --------------------------------------------------------

    llm = (
        create_portkey_llm(
            model=RAG_MODEL,
            component="ragas-offline-generator",
        )
    )


    answer_chain = (
        create_answer_prompt()
        |
        llm
    )


    return (
        retriever,
        answer_chain,
    )


# ============================================================
# CREATE RAGAS EVALUATORS
# ============================================================
def create_ragas_metrics():

    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY was not found."
        )

    # ========================================================
    # RAGAS 0.3.9 EVALUATOR LLM
    # ========================================================

    langchain_evaluator_llm = ChatOpenAI(
        model=RAGAS_EVALUATOR_MODEL,
        temperature=0,
        api_key=openai_api_key,
    )

    evaluator_llm = LangchainLLMWrapper(
        langchain_evaluator_llm
    )

    # ========================================================
    # RAGAS 0.3.9 EVALUATOR EMBEDDINGS
    # ========================================================

    langchain_evaluator_embeddings = OpenAIEmbeddings(
        model=RAGAS_EMBEDDING_MODEL,
        api_key=openai_api_key,
    )

    evaluator_embeddings = LangchainEmbeddingsWrapper(
        langchain_evaluator_embeddings
    )

    # ========================================================
    # METRICS
    # ========================================================

    return {

        "context_precision": ContextPrecision(
            llm=evaluator_llm
        ),

        "context_recall": ContextRecall(
            llm=evaluator_llm
        ),

        "faithfulness": Faithfulness(
            llm=evaluator_llm
        ),

        "answer_relevancy": AnswerRelevancy(
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        ),

        "factual_correctness": FactualCorrectness(
            llm=evaluator_llm,
            mode="f1",
        ),
    }



# ============================================================
# BUILD GENERATION CONTEXT
# ============================================================

def build_context(
    retrieved_documents,
) -> str:

    parts = []


    for document in retrieved_documents:

        metadata = (
            document.metadata
        )


        parts.append(
            f"""
SOURCE: {metadata.get("source", "Unknown source")}
PAGE(S): {metadata.get("page_numbers", [])}
SECTION: {metadata.get("headings", [])}
CHUNK ID: {metadata.get("chunk_id", "Unknown chunk")}

CONTENT:
{document.page_content}
"""
        )


    return "\n\n".join(
        parts
    )


# ============================================================
# RUN ONE QUESTION THROUGH REAL RAG
# ============================================================

def run_rag(
    question,
    retriever,
    answer_chain,
):

    start_time = (
        time.perf_counter()
    )


    retrieved_documents = (
        retriever.invoke(
            question
        )
    )


    retrieved_contexts = [

        document.page_content

        for document
        in retrieved_documents
    ]


    retrieved_chunk_ids = [

        document.metadata.get(
            "chunk_id",
            "",
        )

        for document
        in retrieved_documents
    ]


    context = (
        build_context(
            retrieved_documents
        )
    )


    response = (
        answer_chain.invoke(
            {
                "query":
                    question,

                "context":
                    context,
            }
        )
    )


    latency_seconds = (
        time.perf_counter()
        -
        start_time
    )


    return (
        response.content,
        retrieved_contexts,
        retrieved_chunk_ids,
        retrieved_documents,
        latency_seconds,
    )


# ============================================================
# DETERMINISTIC RETRIEVAL METRICS
# ============================================================


def hit_at_k(
    retrieved_chunk_ids,
    expected_chunk_ids,
    k=4,
):
    """
    1.0 if at least one expected chunk appears
    in the top-k retrieved chunks.
    """

    retrieved_top_k = retrieved_chunk_ids[:k]
    expected = set(expected_chunk_ids)

    return float(
        any(
            chunk_id in expected
            for chunk_id in retrieved_top_k
        )
    )


def recall_at_k(
    retrieved_chunk_ids,
    expected_chunk_ids,
    k=4,
):
    """
    Fraction of expected chunks retrieved
    within the top-k results.
    """

    if not expected_chunk_ids:
        return None

    retrieved_top_k = set(
        retrieved_chunk_ids[:k]
    )

    expected = set(
        expected_chunk_ids
    )

    relevant_found = (
        retrieved_top_k & expected
    )

    return (
        len(relevant_found)
        / len(expected)
    )


def reciprocal_rank(
    retrieved_chunk_ids,
    expected_chunk_ids,
    k=4,
):
    """
    Reciprocal rank of the first relevant
    document in the top-k results.
    """

    expected = set(
        expected_chunk_ids
    )

    for rank, chunk_id in enumerate(
        retrieved_chunk_ids[:k],
        start=1,
    ):

        if chunk_id in expected:
            return 1.0 / rank

    return 0.0


def ndcg_at_k(
    retrieved_chunk_ids,
    expected_chunk_ids,
    k=4,
):
    """
    Binary-relevance nDCG@k.
    """

    if not expected_chunk_ids:
        return None

    expected = set(
        expected_chunk_ids
    )

    retrieved_top_k = (
        retrieved_chunk_ids[:k]
    )

    # -----------------------------
    # DCG
    # -----------------------------

    dcg = 0.0

    for rank, chunk_id in enumerate(
        retrieved_top_k,
        start=1,
    ):

        relevance = (
            1.0
            if chunk_id in expected
            else 0.0
        )

        dcg += (
            relevance
            / math.log2(rank + 1)
        )

    # -----------------------------
    # IDEAL DCG
    # -----------------------------

    number_of_relevant_documents = min(
        len(expected),
        k,
    )

    idcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(
            1,
            number_of_relevant_documents + 1,
        )
    )

    if idcg == 0:
        return 0.0

    return dcg / idcg
# ============================================================
# RAGAS SCORE HELPERS
# ============================================================

def score_value(
    result,
):

    if result is None:
        return None


    value = getattr(
        result,
        "value",
        result,
    )


    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


async def safe_score(
    metric_name,
    metric,
    **kwargs,
):
    try:

        sample = SingleTurnSample(
            **kwargs
        )

        result = await metric.single_turn_ascore(
            sample
        )

        return score_value(result)

    except Exception as error:

        logging.exception(
            "RAGAS metric failed: %s",
            metric_name,
        )

        print(
            f"WARNING: {metric_name} failed: "
            f"{error}"
        )

        return None



# ============================================================
# RAGAS EVALUATION FOR ONE SAMPLE
# ============================================================

async def evaluate_sample(
    question,
    reference,
    response,
    retrieved_contexts,
    metrics,
):

    context_precision = await safe_score(

        "context_precision",

        metrics[
            "context_precision"
        ],

        user_input=
            question,

        reference=
            reference,

        retrieved_contexts=
            retrieved_contexts,
    )


    context_recall = await safe_score(

        "context_recall",

        metrics[
            "context_recall"
        ],

        user_input=
            question,

        reference=
            reference,

        retrieved_contexts=
            retrieved_contexts,
    )


    faithfulness = await safe_score(

        "faithfulness",

        metrics[
            "faithfulness"
        ],

        user_input=
            question,

        response=
            response,

        retrieved_contexts=
            retrieved_contexts,
    )


    answer_relevancy = await safe_score(

        "answer_relevancy",

        metrics[
            "answer_relevancy"
        ],

        user_input=
            question,

        response=
            response,
    )


    factual_correctness = await safe_score(

        "factual_correctness",

        metrics[
            "factual_correctness"
        ],

        response=
            response,

        reference=
            reference,
    )


    return {

        "context_precision":
            context_precision,

        "context_recall":
            context_recall,

        "faithfulness":
            faithfulness,

        "answer_relevancy":
            answer_relevancy,

        "factual_correctness":
            factual_correctness,
    }


# ============================================================
# SAVE DETAILED RESULTS
# ============================================================

def save_results(
    results,
):

    if not results:
        return


    fieldnames = [
        "question",
        "reference",
        "expected_chunk_ids",
        "retrieved_chunk_ids",
        "response",

        # Deterministic ranked retrieval metrics
        "hit_at_4",
        "recall_at_4",
        "mrr",
        "ndcg_at_4",

        # RAGAS metrics
        "context_precision",
        "context_recall",
        "faithfulness",
        "answer_relevancy",
        "factual_correctness",

        "rag_latency_seconds",
        "retrieved_context_count",

        # Pass/fail flags
        "pass_hit_at_4",
        "pass_recall_at_4",
        "pass_mrr",
        "pass_ndcg_at_4",
        "pass_context_precision",
        "pass_context_recall",
        "pass_faithfulness",
        "pass_answer_relevancy",
        "pass_factual_correctness",
    ]


    with RESULTS_PATH.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )


        writer.writeheader()


        writer.writerows(
            results
        )


# ============================================================
# AVERAGE HELPER
# ============================================================

def average_metric(
    results,
    metric_name,
):

    values = [

        row[
            metric_name
        ]

        for row
        in results

        if row.get(
            metric_name
        ) is not None
    ]


    if not values:

        return None


    return statistics.mean(
        values
    )


# ============================================================
# PASS / FAIL
# ============================================================

def passed_threshold(
    metric_name,
    score,
):

    if score is None:
        return False


    threshold = (
        THRESHOLDS[
            metric_name
        ]
    )


    return (
        score
        >=
        threshold
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "\n============================================="
    )

    print(
        "OFFLINE RAGAS EVALUATION"
    )

    print(
        "=============================================\n"
    )


    # --------------------------------------------------------
    # LOAD ACTUAL JSONL
    # --------------------------------------------------------

    chunk_lookup = (
        load_chunks()
    )


    validate_goldens(
        chunk_lookup
    )


    # --------------------------------------------------------
    # LIMIT SAMPLES FOR SMOKE TEST
    # --------------------------------------------------------

    testset = list(
        GOLDENS
    )


    if MAX_SAMPLES > 0:

        testset = (
            testset[
                :MAX_SAMPLES
            ]
        )


    print(
        f"Evaluation questions: "
        f"{len(testset)}"
    )


    # --------------------------------------------------------
    # INITIALIZE REAL RAG
    # --------------------------------------------------------

    (
        retriever,
        answer_chain,
    ) = create_rag_pipeline()


    # --------------------------------------------------------
    # INITIALIZE RAGAS ONCE
    # --------------------------------------------------------

    metrics = (
        create_ragas_metrics()
    )


    results = []


    # --------------------------------------------------------
    # EVALUATE EACH GOLDEN
    # --------------------------------------------------------

    for number, sample in enumerate(
        testset,
        start=1,
    ):

        question = (
            sample[
                "question"
            ]
        )


        reference = (
            sample[
                "reference"
            ]
        )


        expected_chunk_ids = (
            sample[
                "expected_chunk_ids"
            ]
        )


        print(
            "\n\n============================================="
        )

        print(
            f"QUESTION "
            f"{number}/"
            f"{len(testset)}"
        )

        print(
            "============================================="
        )


        print(
            f"\nQuestion:\n"
            f"{question}"
        )


        print(
            f"\nReference:\n"
            f"{reference}"
        )


        print(
            f"\nExpected chunks:\n"
            f"{expected_chunk_ids}"
        )


        (
            response,
            retrieved_contexts,
            retrieved_chunk_ids,
            retrieved_documents,
            rag_latency,
        ) = run_rag(

            question=
                question,

            retriever=
                retriever,

            answer_chain=
                answer_chain,
        )

        


        print(
            f"\nRAG answer:\n"
            f"{response}"
        )


        print(
            f"\nRetrieved chunks:\n"
            f"{retrieved_chunk_ids}"
        )


        # ----------------------------------------------------
        # DETERMINISTIC RETRIEVAL METRICS
        # ----------------------------------------------------
        #
        # The production retriever returns FINAL_TOP_N=4 chunks.
        # These metrics therefore evaluate the ranked top-4 list:
        #
        # Hit@4    -> did we retrieve at least one gold chunk?
        # Recall@4 -> what fraction of all gold chunks were retrieved?
        # MRR      -> how highly was the first gold chunk ranked?
        # nDCG@4   -> how well were all gold chunks ranked?
        # ----------------------------------------------------

        exact_scores = {
            "hit_at_4": hit_at_k(
                retrieved_chunk_ids,
                expected_chunk_ids,
                k=4,
            ),

            "recall_at_4": recall_at_k(
                retrieved_chunk_ids,
                expected_chunk_ids,
                k=4,
            ),

            "mrr": reciprocal_rank(
                retrieved_chunk_ids,
                expected_chunk_ids,
                k=4,
            ),

            "ndcg_at_4": ndcg_at_k(
                retrieved_chunk_ids,
                expected_chunk_ids,
                k=4,
            ),
        }


        # ----------------------------------------------------
        # RAGAS METRICS
        # ----------------------------------------------------

        ragas_scores = await evaluate_sample(

            question=
                question,

            reference=
                reference,

            response=
                response,

            retrieved_contexts=
                retrieved_contexts,

            metrics=
                metrics,
        )


        scores = {
            **exact_scores,
            **ragas_scores,
        }


        print(
            "\nScores:"
        )


        for metric_name, score in (
            scores.items()
        ):

            if score is None:

                print(
                    f"  "
                    f"{metric_name:24s}: "
                    f"ERROR"
                )

            else:

                print(
                    f"  "
                    f"{metric_name:24s}: "
                    f"{score:.4f}"
                )


        result_row = {

            "question":
                question,

            "reference":
                reference,

            "expected_chunk_ids":
                json.dumps(
                    expected_chunk_ids
                ),

            "retrieved_chunk_ids":
                json.dumps(
                    retrieved_chunk_ids
                ),

            "response":
                response,

            **scores,

            "rag_latency_seconds":
                round(
                    rag_latency,
                    4,
                ),

            "retrieved_context_count":
                len(
                    retrieved_contexts
                ),
        }


        # ----------------------------------------------------
        # PASS / FAIL FLAGS
        # ----------------------------------------------------

        for metric_name in (
            THRESHOLDS.keys()
        ):

            result_row[
                f"pass_{metric_name}"
            ] = passed_threshold(
                metric_name,
                scores.get(
                    metric_name
                ),
            )


        results.append(
            result_row
        )


        # Save after every sample
        save_results(
            results
        )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print(
        "\n\n============================================="
    )

    print(
        "FINAL OFFLINE RAGAS SUMMARY"
    )

    print(
        "============================================="
    )


    summary = {}


    for metric_name in [
        "hit_at_4",
        "recall_at_4",
        "mrr",
        "ndcg_at_4",
        "context_precision",
        "context_recall",
        "faithfulness",
        "answer_relevancy",
        "factual_correctness",
    ]:

        mean_score = (
            average_metric(
                results,
                metric_name,
            )
        )


        summary[
            metric_name
        ] = mean_score


        threshold = (
            THRESHOLDS[
                metric_name
            ]
        )


        if mean_score is None:

            print(
                f"{metric_name:24s}: "
                f"ERROR"
            )

        else:

            status = (
                "PASS"
                if mean_score >= threshold
                else
                "FAIL"
            )


            print(
                f"{metric_name:24s}: "
                f"{mean_score:.4f} "
                f"(threshold={threshold:.2f}) "
                f"{status}"
            )


    # --------------------------------------------------------
    # LATENCY
    # --------------------------------------------------------

    if results:

        mean_latency = (
            statistics.mean(
                row[
                    "rag_latency_seconds"
                ]
                for row
                in results
            )
        )

    else:

        mean_latency = None


    summary[
        "average_rag_latency_seconds"
    ] = mean_latency


    summary[
        "evaluated_samples"
    ] = len(
        results
    )


    summary[
        "thresholds"
    ] = THRESHOLDS


    # --------------------------------------------------------
    # OVERALL QUALITY GATE
    # --------------------------------------------------------

    overall_pass = all(

        summary.get(
            metric_name
        ) is not None

        and

        summary[
            metric_name
        ]
        >=
        threshold

        for metric_name, threshold
        in THRESHOLDS.items()
    )


    summary[
        "overall_pass"
    ] = overall_pass


    # --------------------------------------------------------
    # SAVE JSON SUMMARY
    # --------------------------------------------------------

    with SUMMARY_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            indent=2,
        )


    print(
        f"Overall quality gate: "
        f"{'PASS' if overall_pass else 'FAIL'}"
    )


    if mean_latency is not None:

        print(
            f"Average RAG latency: "
            f"{mean_latency:.3f}s"
        )


    print(
        f"\nDetailed results:"
        f"\n{RESULTS_PATH.resolve()}"
    )


    print(
        f"\nSummary:"
        f"\n{SUMMARY_PATH.resolve()}"
    )


# ENTRY POINT

if __name__ == "__main__":
    asyncio.run(main())