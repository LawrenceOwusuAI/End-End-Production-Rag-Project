from __future__ import annotations
import os
import random
from dataclasses import dataclass
from typing import Any
import logfire
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerRelevancy, ContextUtilization,Faithfulness

load_dotenv(override=False)

# CONFIGURATION
RAGAS_EVALUATOR_MODEL = os.getenv("RAGAS_EVALUATOR_MODEL","gpt-4.1-mini")
RAGAS_EMBEDDING_MODEL = os.getenv("RAGAS_EMBEDDING_MODEL","text-embedding-3-small")
QUALITY_EVAL_SAMPLE_RATE = float(os.getenv("QUALITY_EVAL_SAMPLE_RATE","0.10"))

# OTEL / PROMETHEUS METRICS
quality_evaluation_counter = logfire.metric_counter(
    "rag.quality.evaluations",
    unit="1",
    description="Number of online RAG quality evaluations.",
)

quality_evaluation_errors = logfire.metric_counter(
    "rag.quality.evaluation_errors",
    unit="1",
    description="Failed online RAG quality evaluations.",
)

quality_faithfulness = logfire.metric_histogram(
    "rag.quality.faithfulness",
    unit="1",
    description="RAGAS faithfulness score.",
)

quality_answer_relevancy = logfire.metric_histogram(
    "rag.quality.answer_relevancy",
    unit="1",
    description="RAGAS answer relevancy score.",
)

quality_context_utilization = logfire.metric_histogram(
    "rag.quality.context_utilization",
    unit="1",
    description="RAGAS context utilization score.",
)

quality_groundedness = logfire.metric_histogram(
    "rag.quality.groundedness",
    unit="1",
    description="Groundedness proxy based on faithfulness.",
)

quality_hallucination_rate = logfire.metric_histogram(
    "rag.quality.hallucination_rate",
    unit="1",
    description="Hallucination proxy: 1 - faithfulness.",
)

# RESULT
@dataclass
class OnlineQualityResult:
    faithfulness: float
    answer_relevancy: float
    context_utilization: float
    groundedness: float
    hallucination_rate: float

# RAGAS EVALUATOR
class RagasOnlineEvaluator:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for RAGAS quality monitoring.")
        client = AsyncOpenAI(api_key=api_key)
        self.llm = llm_factory( RAGAS_EVALUATOR_MODEL,client=client)
        self.embeddings = embedding_factory("openai",model=RAGAS_EMBEDDING_MODEL,client=client)
        self.faithfulness = Faithfulness(llm=self.llm)
        self.answer_relevancy = AnswerRelevancy(llm=self.llm,embeddings=self.embeddings)
        self.context_utilization = ContextUtilization(llm=self.llm)
        
_evaluator: RagasOnlineEvaluator | None = None

def get_evaluator() -> RagasOnlineEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = RagasOnlineEvaluator()
    return _evaluator

# HELPERS
def get_score(result: Any) -> float:
    value = getattr(result,"value",result)
    return float(value)

def should_evaluate_quality() -> bool:
    sample_rate = max(0.0,min(1.0,QUALITY_EVAL_SAMPLE_RATE))
    return (random.random() < sample_rate)

# ONLINE EVALUATION
async def evaluate_online_quality(*,question: str,response: str,retrieved_contexts: list[str],user_id: str | None = None) -> None:
    if not retrieved_contexts:
        return
    evaluator = get_evaluator()
    try:
        # FAITHFULNESS
        faithfulness_result = (
            await evaluator.faithfulness.ascore(
                user_input=question,
                response=response,
                retrieved_contexts=retrieved_contexts
            )
        )

        faithfulness = get_score(faithfulness_result)

        # ANSWER RELEVANCY
        relevancy_result = await evaluator.answer_relevancy.ascore(
                           user_input=question,
                           response=response
                           )
        answer_relevancy = get_score(relevancy_result)

        # CONTEXT UTILIZATION
        utilization_result = await evaluator.context_utilization.ascore(
                user_input=question,
                response=response,
                retrieved_contexts=retrieved_contexts
               )
        
        context_utilization = get_score(utilization_result)

        # OPERATIONAL DERIVED METRICS
        groundedness = faithfulness
        hallucination_rate = max(0.0,min(1.0,1.0 - faithfulness))

        # RECORD OTEL / PROMETHEUS METRICS
        quality_evaluation_counter.add(1)
        quality_faithfulness.record(faithfulness)
        quality_answer_relevancy.record(answer_relevancy)
        quality_context_utilization.record(context_utilization)
        quality_groundedness.record(groundedness)
        quality_hallucination_rate.record(hallucination_rate)

        # STRUCTURED LOG
        logfire.info("RAG quality evaluation completed",
            rag_event="rag.quality.online",
            rag_user_id=user_id,
            faithfulness=faithfulness,
            answer_relevancy=answer_relevancy,
            context_utilization=context_utilization,
            groundedness=groundedness,
            hallucination_rate=hallucination_rate,
            retrieved_context_count=len(retrieved_contexts)
        )
    except Exception as exc:
        quality_evaluation_errors.add(1)
        logfire.exception("RAG online quality evaluation failed",
            rag_event="rag.quality.online_error",
            error_type=type(exc).__name__,
        )