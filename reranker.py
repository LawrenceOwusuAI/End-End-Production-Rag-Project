from logger import logging
from typing import Any
import time
import logfire
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_classic.retrievers import ContextualCompressionRetriever

from langchain_classic.retrievers.document_compressors import (
    CrossEncoderReranker,
)

from pydantic import BaseModel,Field,ConfigDict
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from exception import CustomException
from llm_gateway import create_portkey_llm
from observability import TimedCrossEncoderReranker,vector_db_error_counter,query_router_duration,query_transformation_duration

QUERY_MODEL = "gpt-4.1-mini"
CROSS_ENCODER_MODEL = "BAAI/bge-reranker-base"
BASE_K = 15
MAX_CANDIDATES = 15
FINAL_TOP_N = 4
RRF_K = 60

# QUERY ROUTE MODEL
class QueryRoute(BaseModel):
    route: str = Field(description=("Route the query to either 'direct' or 'transform'."))
    reason: str = Field(description="Short reason explaining the routing decision.")
    
# QUERY TRANSFORMATION MODEL
class QueryTransformation(BaseModel):
    rewritten_query: str = Field(description=("Optimized version of the user's original query."))
    expanded_queries: list[str] = Field(
        default_factory=list,
        description=(
            "Alternative search queries using synonyms, "
            "technical terminology, abbreviations, "
            "related expressions, and alternative "
            "formulations of the same information need."
        ),
    )
    decomposed_queries: list[str] = Field(
        default_factory=list,
        description=(
            "Independent and self-contained subquestions "
            "created when the original query contains "
            "multiple distinct information needs."
        ),
    )

# QUERY ROUTER
class QueryRouter:
    def __init__(self):
        logging.info("Creating query routing model")
        llm = create_portkey_llm(model=QUERY_MODEL,component="query-router")
        structured_llm = llm.with_structured_output(QueryRoute)
        self.prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """
You are the routing component of a
Retrieval-Augmented Generation (RAG)
system.

Your job is NOT to answer the query.

Your job is to decide whether the query
should:

1. go DIRECTLY to vector retrieval

OR

2. go through QUERY TRANSFORMATION
   before retrieval.


DIRECT

Route to "direct" when the query is:

- clear;
- specific;
- self-contained;
- a single information need;
- straightforward;
- already suitable for semantic search.

Examples:

"What is Docling?"

"What is a vector database?"

"Explain reciprocal rank fusion."

"What embedding model is used?"

"How does OCR work?"

"What is the chunk size?"

These queries normally do NOT need
rewriting, expansion or decomposition.


TRANSFORM

Route to "transform" when the query is:

- ambiguous;
- vague;
- poorly formulated;
- conversational and context-dependent;
- multi-part;
- composed of multiple information needs;
- likely to benefit from synonyms or
  alternative terminology;
- likely to require decomposition.

Examples:

"How does it work?"

"Explain how the system parses PDFs,
creates embeddings, stores them and
retrieves documents."

"How does it read scanned documents and
extract tables?"

"Compare the retrieval methods and
explain their advantages and
disadvantages."


IMPORTANT:

Prefer "direct" when the query is already
clear and retrieval-ready.

Do NOT transform a query simply because
it is technical.

Do NOT transform a query simply because
it is long.

Complexity should come from ambiguity,
multiple information needs, or a genuine
need for query expansion/decomposition.

Return only the structured output.
                        """
                    ),

                    (
                        "human",
                        """
Determine the retrieval route for:

{query}
                        """
                    ),
                ]
            )
        


        self.chain = (
            self.prompt
            |
            structured_llm
        )


    def route(self,query: str) -> QueryRoute:
        logging.info("Routing user query")
        start = time.perf_counter()
        try:
            with logfire.span("rag.query_router",rag_query=query):
                decision = (
                    self.chain.invoke(
                        {
                            "query":
                                query
                        }
                    )
                )
            logging.info("Query route: %s",decision.route)
            logging.info("Routing reason: %s",decision.reason)
            return decision
        finally:
            duration_ms = (time.perf_counter()-start) * 1000
            query_router_duration.record(duration_ms)

# QUERY TRANSFORMER
class QueryTransformer:
    def __init__(self):
        logging.info("Creating query transformation model")
        llm = create_portkey_llm(model=QUERY_MODEL,component="query-transformer",)
        structured_llm = llm.with_structured_output(QueryTransformation)
        self.prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """
You are the query-transformation component of a
Retrieval-Augmented Generation (RAG) system.

Your responsibility is to transform a user's question
into high-quality search queries that maximize the
probability of retrieving relevant document chunks
from a semantic vector database.

You are NOT responsible for answering the user's
question.

You MUST NOT answer the question.

You MUST NOT fabricate information.

Your only responsibility is to improve document
retrieval.


For every user query, perform THREE separate operations:


1. QUERY REWRITING

Create exactly ONE improved version of the original
query.

The purpose of rewriting is to express the same
information more clearly and in terminology that
is suitable for semantic retrieval.

The rewritten query must:

- preserve the meaning of the original query;
- preserve all important entities and concepts;
- preserve conditions and constraints;
- correct unclear grammar or spelling;
- replace vague wording with precise terminology when
  the intended meaning is clear;
- expand obvious abbreviations when useful;
- convert conversational wording into a concise,
  retrieval-friendly formulation.

Do NOT introduce unrelated information.

Do NOT change the user's intent.

Do NOT answer the question.


2. QUERY EXPANSION

Generate approximately 2 to 4 alternative search
queries when useful.

The purpose of query expansion is to improve
RETRIEVAL RECALL.

Expanded queries may include:

- synonyms;
- technical terminology;
- domain-specific terminology;
- abbreviations;
- expanded forms of abbreviations;
- alternative names for the same concept;
- closely related terminology;
- alternative grammatical formulations;
- broader terminology when directly relevant;
- narrower terminology when directly relevant.

Every expanded query must remain directly related to
the original information need.

Do NOT generate unrelated queries.

Do NOT answer the user's question.


3. QUERY DECOMPOSITION

Determine whether the original query contains multiple
distinct information needs.

If it does, break it into smaller, independent,
self-contained search questions.

Each decomposed query should:

- represent one information need;
- make sense when searched independently;
- preserve important context;
- preserve important entities;
- avoid unnecessary overlap with other subquestions.

Do NOT decompose a simple single-topic question.

If decomposition is unnecessary, return an empty list.


OUTPUT REQUIREMENTS

Return only the structured output required by the
schema.

The output contains:

rewritten_query:
    One improved retrieval query.

expanded_queries:
    Alternative formulations representing the same
    information need.

decomposed_queries:
    Independent subquestions when decomposition is
    necessary.

Do not answer the user's question.

Do not provide explanations outside the structured
output.

Do not invent document-specific facts.

Your goal is exclusively to maximize the probability
of retrieving relevant document chunks.
                        """
                    ),

                    (
                        "human",
                        """
Transform the following user query for document
retrieval:

{query}
                        """
                    ),
                ]
            )
        


        self.chain = self.prompt | structured_llm
        
    def transform(self,query: str) -> QueryTransformation:
        logging.info("Transforming user query")
        start = time.perf_counter()
        try:
            with logfire.span("rag.query_transformation",rag_query=query,):
                transformation = self.chain.invoke(
                        {
                            "query":query
                        }
                    )
            logging.info("Rewritten query: %s",transformation.rewritten_query)
            logging.info("Expanded queries: %s",transformation.expanded_queries)
            logging.info("Decomposed queries: %s",transformation.decomposed_queries)
            return transformation
        finally:
            duration_ms = (time.perf_counter()-start) * 1000
            query_transformation_duration.record(duration_ms)

# BASE RETRIEVER
def create_base_retriever(vector_store):
    logging.info("Creating Pinecone base retriever")
    retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k":BASE_K
            }
        )
    return retriever

# TRANSFORMED QUERY RETRIEVER
class TransformedQueryRetriever(BaseRetriever):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    base_retriever: Any
    query_transformer: Any
    query_router: Any
    max_candidates: int = MAX_CANDIDATES
    rrf_k: int = RRF_K
    total_queries: int = 0
    direct_queries: int = 0
    transformed_queries: int = 0

    # REMOVE DUPLICATE QUERIES
    def _unique_queries(self,queries: list[str]) -> list[str]:
        unique_queries = []
        seen = set()
        for query in queries:
            normalized_query = query.strip().lower()
            if normalized_query not in seen:
                seen.add(normalized_query)
                unique_queries.append(query.strip())
        return unique_queries

    # DOCUMENT KEY
    def _get_document_key(self,document: Document):
        chunk_id = document.metadata.get("chunk_id")
        if chunk_id:
            return (
                "chunk_id",
                chunk_id,
            )
        return (
            "content",
            document.page_content,
        )

    # RECIPROCAL RANK FUSION
    def _reciprocal_rank_fusion(self,retrieval_results:list[list[Document]],) -> list[Document]:
        logging.info("Applying Reciprocal Rank Fusion")
        with logfire.span(
            "rag.reciprocal_rank_fusion",
            retrieval_result_sets=len(retrieval_results)):
            rrf_scores = {}
            document_map = {}
            for documents in retrieval_results:
                for rank, document in enumerate(documents,start=1):
                    document_key = self._get_document_key(document)
                    document_map[document_key] = document
                    score = (1/(self.rrf_k + rank))
                    rrf_scores[document_key] = (rrf_scores.get(document_key,0.0) + score)
            ranked_document_keys = sorted(
                    rrf_scores,
                    key=lambda key: rrf_scores[key],
                    reverse=True,
                )
            ranked_documents = []
            for document_key in ranked_document_keys:
                document = document_map[document_key]
                document.metadata["rrf_score"] = (rrf_scores[document_key])
                ranked_documents.append(document)
        logging.info("Documents after RRF ranking: %d",len(ranked_documents),)
        return ranked_documents

    # ROUTING METRICS
    def _log_routing_metrics(self):
        if self.total_queries == 0:
            return
        direct_percentage = (self.direct_queries / self.total_queries) * 100
        transformed_percentage = (self.transformed_queries/self.total_queries) * 100
        logging.info("QUERY ROUTING METRICS")
        logging.info("Total queries: %d",self.total_queries)
        logging.info(
            "Direct retrieval queries: "
            "%d (%.2f%%)",
            self.direct_queries,
            direct_percentage,
        )
        logging.info(
            "Transformed queries: "
            "%d (%.2f%%)",
            self.transformed_queries,
            transformed_percentage,
        )

    # Document Retrieval from PINECONE
    def _safe_retrieve(self,query: str):
        try:
            with logfire.span("rag.pinecone_retrieval",search_query=query):
                documents = self.base_retriever.invoke(query)
            logging.info("Pinecone retrieval completed. "
                "documents=%d",
                len( documents)
        )
            return documents
        except Exception as e:
            vector_db_error_counter.add(1)
            logging.exception(
                "Pinecone/vector retrieval failed",
                extra={
                    "rag_event":"rag.vector_db_error",
                    "vector_operation":"retrieval",
                    "search_query":query,
                    "error_type":type(e).__name__,
                    "error_message":str(e),
                }
            )
            raise

    # MAIN RETRIEVAL LOGIC
    def _get_relevant_documents(self,query: str,*,run_manager=None) -> list[Document]:
        logging.info("Running routed retrieval")
        self.total_queries += 1
        decision = self.query_router.route(query)
        logging.info("Original query: %s",query)
        logging.info("Selected retrieval route: %s",decision.route)
        logging.info( "Routing reason: %s",decision.reason)
        
        # DIRECT RETRIEVAL
        if decision.route == "direct":
            self.direct_queries += 1
            logging.info("Using direct retrieval")
            with logfire.span("rag.direct_retrieval",rag_query=query):
                documents = self._safe_retrieve(query)
                candidate_documents = documents[:self.max_candidates]
            logging.info(
                "Documents sent to "
                "cross encoder: %d",
                len(candidate_documents))
            self._log_routing_metrics()
            return candidate_documents
            
        # COMPLEX / AMBIGUOUS QUERY
        self.transformed_queries += 1
        logging.info("Using query transformation")
        with logfire.span(
            "rag.transformed_retrieval",
            rag_query=query):

            # TRANSFORM QUERY
            transformation = self.query_transformer.transform(query)
            
            # BUILD SEARCH QUERIES
            search_queries = [
                query,
                transformation.rewritten_query,
                *transformation.expanded_queries,
                *transformation.decomposed_queries,
            ]
            search_queries = self._unique_queries(search_queries)
            logging.info(
                "Total unique retrieval "
                "queries: %d",
                len(
                    search_queries
                ),
            )

            # SEARCH PINECONE FOR EACH QUERY
            retrieval_results = []
            for search_query in search_queries:
                logging.info(
                    "Searching Pinecone "
                    "with query: %s",
                    search_query,
                )
                documents = self._safe_retrieve(search_query)
                retrieval_results.append(documents)

            ranked_documents = self._reciprocal_rank_fusion(retrieval_results)
            candidate_documents = ranked_documents[:self.max_candidates]
        logging.info(
            "Documents sent to "
            "cross encoder: %d",
            len(candidate_documents)
        )
        self._log_routing_metrics()
        return candidate_documents
        
# CROSS ENCODER
def create_cross_encoder():
    logging.info("Loading cross-encoder model: %s",CROSS_ENCODER_MODEL)
    cross_encoder = HuggingFaceCrossEncoder(
            model_name=CROSS_ENCODER_MODEL,
            model_kwargs={
                "device":"cpu"
            },
        )
    return cross_encoder

def create_cross_encoder_reranker():
    logging.info("Creating cross-encoder reranker")
    cross_encoder = (create_cross_encoder())
    reranker = TimedCrossEncoderReranker(
            model=cross_encoder,
            top_n=FINAL_TOP_N
        )
    return reranker

def create_advanced_retriever(vector_store):
    logging.info("Creating advanced retrieval pipeline")
    base_retriever = create_base_retriever(vector_store)
    query_transformer = QueryTransformer()
    query_router = QueryRouter()
    transformed_retriever = TransformedQueryRetriever(
            base_retriever=base_retriever,
            query_transformer=query_transformer,
            query_router=query_router,
            max_candidates=MAX_CANDIDATES,
            rrf_k=RRF_K
        )
    
    # CROSS-ENCODER
    reranker = create_cross_encoder_reranker()
    
    # FINAL RETRIEVER
    final_retriever = ContextualCompressionRetriever(
            base_retriever=transformed_retriever,
            base_compressor=reranker
        )
    logging.info("Advanced retriever created successfully")
    return final_retriever