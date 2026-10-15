# observability.py

from __future__ import annotations

import json
import time

import logfire

from langchain_core.embeddings import Embeddings
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker

from langchain_classic.retrievers import ContextualCompressionRetriever

# ============================================================
# EXISTING RAG METRICS
#
# IMPORTANT:
# These names are deliberately kept exactly the same
# as your existing app.py variables.
# ============================================================

request_counter = logfire.metric_counter(
    "rag.requests",
    unit="1",
    description="Total number of RAG requests",
)


error_counter = logfire.metric_counter(
    "rag.errors",
    unit="1",
    description="Total number of failed RAG requests",
)


active_requests = logfire.metric_up_down_counter(
    "rag.active_requests",
    unit="1",
    description="Number of active RAG requests",
)


request_duration = logfire.metric_histogram(
    "rag.request.duration",
    unit="ms",
    description="End-to-end RAG request duration",
)


retrieval_duration = logfire.metric_histogram(
    "rag.retrieval.duration",
    unit="ms",
    description="Retrieval and reranking duration",
)


llm_duration = logfire.metric_histogram(
    "rag.llm.duration",
    unit="ms",
    description="LLM answer generation duration",
)


documents_retrieved = logfire.metric_histogram(
    "rag.documents.retrieved",
    unit="1",
    description="Number of documents returned after reranking",
)


# ============================================================
# NEW METRICS
# ============================================================

reranker_duration = logfire.metric_histogram(
    "rag.reranker.duration",
    unit="ms",
    description="Cross-encoder reranking duration",
)


embedding_duration = logfire.metric_histogram(
    "rag.embedding.duration",
    unit="ms",
    description="Embedding model execution duration",
)


query_router_duration = logfire.metric_histogram(
    "rag.query_router.duration",
    unit="ms",
    description="Query router execution duration",
)


query_transformation_duration = logfire.metric_histogram(
    "rag.query_transformation.duration",
    unit="ms",
    description="Query transformation execution duration",
)


llm_error_counter = logfire.metric_counter(
    "rag.llm.errors",
    unit="1",
    description="Total number of LLM generation failures",
)


vector_db_error_counter = logfire.metric_counter(
    "rag.vector_db.errors",
    unit="1",
    description="Total number of vector database errors",
)


reranker_error_counter = logfire.metric_counter(
    "rag.reranker.errors",
    unit="1",
    description="Total number of reranker errors",
)


embedding_error_counter = logfire.metric_counter(
    "rag.embedding.errors",
    unit="1",
    description="Total number of embedding errors",
)


# ============================================================
# FULL RAG OBSERVABILITY LOG EVENTS
#
# These contain:
#
# - user query
# - retrieved document
# - metadata
# - generated answer
#
# They are NOT Prometheus labels.
#
# They are emitted as structured log records so that:
#
# Python logging
#       |
#       v
# Logfire
#       |
#       v
# OpenTelemetry
#       |
#       v
# OpenSearch
# ============================================================

def log_rag_query(
    logging,
    query: str,
    user_id=None,
) -> None:

    """
    Record the complete user query.

    This information can later be searched
    from Logfire and OpenSearch.
    """

    logging.info(
        "RAG user query received",
        extra={
            "rag_event":
                "rag.query",

            "rag_query":
                query,

            "rag_user_id":
                (
                    str(user_id)
                    if user_id is not None
                    else ""
                ),
        },
    )


def log_retrieved_documents(
    logging,
    query: str,
    retrieved_documents,
) -> None:

    """
    Record every final retrieved document.

    The full document.page_content is included
    because the user explicitly wants retrieval
    evidence available to the observability agent.
    """

    for rank, document in enumerate(
        retrieved_documents,
        start=1,
    ):

        source = document.metadata.get(
            "source",
            "Unknown source",
        )


        page_numbers = document.metadata.get(
            "page_numbers",
            [],
        )


        headings = document.metadata.get(
            "headings",
            [],
        )


        chunk_id = document.metadata.get(
            "chunk_id",
            "Unknown chunk",
        )


        rrf_score = document.metadata.get(
            "rrf_score"
        )


        logging.info(
            "RAG retrieved document",
            extra={
                "rag_event":
                    "rag.retrieved_document",

                "rag_query":
                    query,

                "retrieval_rank":
                    rank,

                "source":
                    str(source),

                "page_numbers":
                    json.dumps(
                        page_numbers,
                        ensure_ascii=False,
                    ),

                "headings":
                    json.dumps(
                        headings,
                        ensure_ascii=False,
                    ),

                "chunk_id":
                    str(chunk_id),

                "rrf_score":
                    (
                        float(rrf_score)
                        if rrf_score is not None
                        else 0.0
                    ),

                # FULL retrieved document
                "document_content":
                    document.page_content,
            },
        )


def log_generated_answer(
    logging,
    query: str,
    answer: str,
    document_count: int,
    retrieval_ms: float,
    generation_ms: float,
) -> None:

    """
    Record the complete final generated answer.
    """

    logging.info(
        "RAG generated answer",
        extra={
            "rag_event":
                "rag.generated_answer",

            "rag_query":
                query,

            "generated_answer":
                answer,

            "document_count":
                document_count,

            "retrieval_ms":
                retrieval_ms,

            "generation_ms":
                generation_ms,
        },
    )


# ============================================================
# TIMED EMBEDDING WRAPPER
# ============================================================

class TimedEmbeddings(Embeddings):

    def __init__(
        self,
        embeddings,
    ):

        self.embeddings = embeddings


    def embed_query(
        self,
        text: str,
    ):

        start = time.perf_counter()


        try:

            with logfire.span(
                "rag.embedding.query",
                text_length=len(text),
            ):

                return (
                    self.embeddings
                    .embed_query(text)
                )


        except Exception:

            embedding_error_counter.add(
                1
            )

            raise


        finally:

            duration_ms = (
                time.perf_counter()
                -
                start
            ) * 1000


            embedding_duration.record(
                duration_ms
            )


    def embed_documents(
        self,
        texts: list[str],
    ):

        start = time.perf_counter()


        try:

            with logfire.span(
                "rag.embedding.documents",
                document_count=
                    len(texts),
            ):

                return (
                    self.embeddings
                    .embed_documents(
                        texts
                    )
                )


        except Exception:

            embedding_error_counter.add(
                1
            )

            raise


        finally:

            duration_ms = (
                time.perf_counter()
                -
                start
            ) * 1000


            embedding_duration.record(
                duration_ms
            )


# ============================================================
# TIMED CROSS-ENCODER RERANKER
# ============================================================

class TimedCrossEncoderReranker(
    CrossEncoderReranker
):

    def compress_documents(
        self,
        documents,
        query,
        callbacks=None,
    ):

        start = time.perf_counter()


        try:

            with logfire.span(
                "rag.cross_encoder_rerank",
                candidate_count=
                    len(documents),
                rag_query=
                    query,
            ):

                return super().compress_documents(
                    documents=documents,
                    query=query,
                    callbacks=callbacks,
                )


        except Exception:

            reranker_error_counter.add(
                1
            )

            raise


        finally:

            duration_ms = (
                time.perf_counter()
                -
                start
            ) * 1000


            reranker_duration.record(
                duration_ms
            )
llm_prompt_tokens = logfire.metric_counter(
    "rag.llm.prompt_tokens",
    unit="1",
    description="Total LLM prompt tokens",
)

llm_completion_tokens = logfire.metric_counter(
    "rag.llm.completion_tokens",
    unit="1",
    description="Total LLM completion tokens",
)

llm_total_tokens = logfire.metric_counter(
    "rag.llm.tokens",
    unit="1",
    description="Total LLM tokens",
)

llm_cost_usd = logfire.metric_counter(
    "rag.llm.cost_usd",
    unit="USD",
    description="Estimated cumulative LLM cost in USD",
)