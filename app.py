from __future__ import annotations
import os
from contextlib import asynccontextmanager
import shutil
import time
from pathlib import Path
import chunking as chunking_module
import vectorstore as vectorstore_module
from chunking import PDF_PATH, run_chunking_pipeline
from vectorstore import run_vectorstore_pipeline
from reranker import create_advanced_retriever,create_base_retriever
from fastapi import FastAPI,HTTPException,UploadFile,File,Depends,status
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from pydantic import BaseModel,Field
from llm_gateway import create_portkey_llm
from logger import logging,attach_logfire_handler
from sqlalchemy.orm import Session
from auth.database import Base,engine,get_db
from auth.models import User
from fastapi import BackgroundTasks
from quality_monitoring import evaluate_online_quality,should_evaluate_quality
from auth.schemas import RegisterRequest,LoginRequest
from guardrails_runtime import RAGGuardrails
from auth.security import hash_password,verify_password,create_access_token,get_current_user
from observability import (
request_counter,
    error_counter,
    active_requests,
    request_duration,
    retrieval_duration,
    llm_duration,
    documents_retrieved,
    llm_error_counter,
    llm_prompt_tokens,
    llm_completion_tokens,
    llm_total_tokens,
    llm_cost_usd,
    TimedEmbeddings,
    log_rag_query,
    log_retrieved_documents,
    log_generated_answer
)

from dotenv import load_dotenv
load_dotenv(override=False)

# LOGFIRE CONFIGURATION
import logfire
logfire.configure(service_name="rag-api",environment="development",send_to_logfire=True)

# CONNECT STANDARD PYTHON LOGGING TO LOGFIRE
attach_logfire_handler()
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_NAME = "rag-project"
NAMESPACE = PDF_PATH.stem

class QueryRequest(BaseModel):
    query: str = Field(min_length=1)

class QueryResponse(BaseModel):
    query: str
    answer: str

def create_answer_prompt():
    return (ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
You are a question-answering assistant for a
Retrieval-Augmented Generation (RAG) system.

Answer the user's question using only the provided
retrieved document context.

RULES:

1. Use only information contained in the retrieved
   context.

2. Do not introduce unsupported facts.

3. Combine information from multiple retrieved chunks
   when necessary.

4. Provide a clear, coherent, and concise answer.

5. Cite the source file and page number for factual
   statements whenever that information is available.

6. Use citations in this format:

   [Source: filename, Page: 5]

   For multiple pages:

   [Source: filename, Pages: 5-6]

7. If information comes from multiple sources or
   different pages, cite the appropriate source after
   the corresponding statement.

8. Use the SOURCE and PAGE(S) metadata supplied with
   each context chunk. Never invent a source or page
   number.

9. Do not cite a source unless the corresponding
   retrieved context supports the statement.

10. If the retrieved context does not contain enough
    information to answer the question, state that
    clearly.

11. Do not use general knowledge to fill gaps in the
    retrieved context.
                    """
                ),

                (
                    "human",
                    """
USER QUESTION:

{query}


RETRIEVED DOCUMENT CONTEXT:

{context}


Using only the retrieved context above, provide a
clear and coherent answer with source and page
citations.
                    """
                ),
            ]
        )
    )

# FASTAPI LIFESPAN
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("FastAPI RAG application startup started")
    logfire.info("RAG application startup started")

    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY was not found.")
    logging.info("Loading embedding model")
    with logfire.span("rag.startup.load_embedding_model",model=EMBEDDING_MODEL_NAME):
        base_embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL_NAME,
                model_kwargs={
                    "device":
                        "cpu"
                },
                encode_kwargs={
                    "normalize_embeddings":
                        True
                },
            )
        embeddings = (
            TimedEmbeddings(
                base_embeddings
            )
        )
    logging.info("Embedding model loaded successfully")

    # CONNECT TO PINECONE ONCE
    logging.info("Connecting to Pinecone")
    with logfire.span("rag.startup.connect_pinecone",index_name=INDEX_NAME,namespace=NAMESPACE):
        pc = Pinecone(api_key=pinecone_api_key)
        index = pc.Index(INDEX_NAME)
        stats = index.describe_index_stats()
    logging.info("Connected to Pinecone index: %s",INDEX_NAME)

    # CREATE VECTOR STORE ONCE
    vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace=NAMESPACE,
        )
    logging.info("Connected LangChain to Pinecone vector store")
    vectorstore_module.create_embedding_model = (lambda:embeddings)
    vectorstore_module.create_pinecone_client = (lambda:pc)

    # CREATE ADVANCED RETRIEVER
    logging.info("Creating advanced retriever")
    with logfire.span("rag.startup.create_retriever"):
        retriever = create_advanced_retriever(vector_store)
    logging.info("Advanced retriever created successfully")

    # CREATE ANSWER GENERATION LLM
    logging.info("Loading answer generation model")
    with logfire.span("rag.startup.create_llm",model="gpt-4.1-mini"):
        llm = create_portkey_llm(
                model="gpt-4.1-mini",
                component="answer-generator",
            )
    logging.info("Answer generation model loaded successfully")
    answer_prompt = create_answer_prompt()
    answer_chain = answer_prompt|llm
    logging.info("Loading NVIDIA NeMo Guardrails")

    with logfire.span("rag.startup.load_guardrails"):
        guardrails = RAGGuardrails("guardrails_config")
    logging.info("NVIDIA NeMo Guardrails loaded successfully")
    
    # STORE STARTUP RESOURCES
    app.state.embeddings = embeddings
    app.state.pc = pc
    app.state.index = index
    app.state.vector_store = vector_store
    app.state.retriever = retriever
    app.state.llm = llm
    app.state.answer_prompt = answer_prompt
    app.state.answer_chain = answer_chain
    app.state.guardrails = guardrails
    app.state.ready = True
    app.state.namespace = NAMESPACE
    logging.info("FastAPI RAG application startup completed successfully")
    logfire.info("RAG application startup completed",index_name=INDEX_NAME,
        namespace=NAMESPACE,
        embedding_model=EMBEDDING_MODEL_NAME
    )
    yield

    # SHUTDOWN
    logging.info("FastAPI RAG application shutdown started")
    app.state.ready = False
    logging.info("FastAPI RAG application shutdown completed")

# FASTAPI APPLICATION
app = FastAPI(title="RAG API",description="FastAPI service for the RAG application",version="1.0.0",lifespan=lifespan)

# AUTHENTICATION DATABASE
Base.metadata.create_all(bind=engine)

# LOGFIRE FASTAPI INSTRUMENTATION
def request_attributes_mapper(request,attributes):
    if attributes["errors"]:
        return {
            "errors":attributes["errors"]
        }
    return {}
logfire.instrument_fastapi(app,request_attributes_mapper=request_attributes_mapper)

# ROOT ENDPOINT
@app.get("/")
def root():
    return {
        "message":"RAG API is running",
        "docs":"/docs",
        "health":"/health",
        "documents_endpoint":"/documents",
        "query_endpoint":"/query",
    }

# HEALTH ENDPOINT
@app.get("/health")
def health():
    return {
        "status":(
                "healthy"

                if getattr(
                    app.state,
                    "ready",
                    False,
                )

                else

                "starting"
            ),

        "index":
            INDEX_NAME,

        "namespace":
            getattr(
                app.state,
                "namespace",
                NAMESPACE,
            ),

        "embedding_model":
            EMBEDDING_MODEL_NAME,
    }

# REGISTER USER
@app.post("/auth/register",status_code=status.HTTP_201_CREATED)
def register_user(request:RegisterRequest,db:Session = Depends(get_db)):
    email = request.email.lower().strip()
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("An account with this email already exists."))
    hashed_password = hash_password(request.password)
    user = User(
         full_name=request.full_name.strip(),
        email = email,
        password_hash=hashed_password,
        role = "user",
        is_active = True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "message":"Account created successfully.",
        "user": {
            "id":user.id,
            "full_name":user.full_name,
            "email":user.email,
            "role":user.role,
        }
    }

# LOGIN USER
@app.post("/auth/login")
def login_user(
    request:LoginRequest,
    db:Session = Depends(get_db)):
    email = request.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    valid_password = verify_password(request.password,user.password_hash)
    if not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled.")
    access_token = create_access_token(user_id=user.id,role=user.role)
    return {
        "access_token":access_token,
        "token_type":"bearer",
        "user": {
            "id":user.id,
            "full_name":user.full_name,
            "email":user.email,
            "role":user.role,
        },
    }

# CURRENT USER
@app.get("/auth/me")
def current_user(user:User = Depends(get_current_user)):
    return {
        "id":user.id,
        "full_name":user.full_name,
        "email":user.email,
        "role":user.role,
    }


#Document Upload
@app.post("/documents")
def upload_document(file:UploadFile = File(...),current_user:User = Depends(get_current_user)):
    if not getattr(app.state,"ready",False):
        raise HTTPException(status_code=503,detail="RAG application is not ready.")
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was uploaded.",
        )
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.")
    try:
        original_filename = Path(file.filename).name
        namespace = Path(original_filename).stem.strip().lower().replace( " ","_")
        input_directory = Path("input")
        input_directory.mkdir(parents=True,exist_ok=True)
        uploaded_pdf_path = input_directory/original_filename
        with uploaded_pdf_path.open("wb") as destination:
            shutil.copyfileobj(file.file,destination)
        logging.info("PDF uploaded: %s",uploaded_pdf_path)
        chunking_module.PDF_PATH =  uploaded_pdf_path
        
        # CHUNKING
        logging.info("Starting chunking pipeline")
        with logfire.span("rag.document.chunking",
            filename=original_filename,
            namespace=namespace):

            chunked_documents = run_chunking_pipeline()
        chunk_count = len(chunked_documents)
        logging.info(
            "Chunking completed. "
            "Chunks: %d",
            chunk_count,
        )

        vectorstore_module.PDF_PATH = uploaded_pdf_path
        vectorstore_module.NAMESPACE = namespace
        logging.info("Using Pinecone namespace: %s",namespace)

        vectorstore_module.create_embedding_model = (lambda:app.state.embeddings)
        vectorstore_module.create_pinecone_client = (lambda:app.state.pc)
        logging.info("Starting vectorstore pipeline")
        with logfire.span(
            "rag.document.vectorstore",
            filename=original_filename,
            namespace=namespace,
            chunk_count=chunk_count,
        ):
            new_vector_store = run_vectorstore_pipeline(chunked_documents)
        logging.info("Vectorstore pipeline completed")
        app.state.vector_store = new_vector_store
        new_base_retriever = create_base_retriever(new_vector_store)
        
        (
            app.state
            .retriever
            .base_retriever
            .base_retriever
        ) = (
            new_base_retriever
        )

        # CURRENT NAMESPACE
        app.state.namespace = namespace
        
        # OBSERVABILITY EVENT
        logging.info("RAG document processing completed",
            extra={
                "rag_event":"rag.document_processed",
                "document_filename":original_filename,
                "namespace":namespace,
                "chunk_count":chunk_count,
                "index_name":INDEX_NAME,
                "rag_user_id":
                    str(
                        current_user.id
                    ),
            },
        )

        return {
            "status":"success",
            "message":
                (
                    "PDF processed and "
                    "stored successfully."
                ),
            "filename":original_filename,
            "chunks_created":chunk_count,
            "index":INDEX_NAME,
            "namespace":namespace,
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(
            "Document processing failed",
            extra={
                "rag_event":"rag.document_processing_error",
                "error_type":type(e).__name__,
                "error_message":str(e),
                "rag_user_id":
                    str(
                        current_user.id
                    ),
            },
        )
        raise HTTPException(
            status_code=500,
            detail=
                (
                    "Document processing failed:"
                    f"{str(e)}"
                ),

        ) from e
    finally:
        try:
            file.file.close()
        except Exception:
            pass

@app.post("/query",response_model=QueryResponse)
async def query_rag(request:QueryRequest, background_tasks:BackgroundTasks,current_user:User = Depends(get_current_user)):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400,detail="Query cannot be empty.")
    if not getattr(app.state,"ready",False):
        raise HTTPException(status_code=503,detail="RAG models are not ready.")
    
# INPUT GUARDRAILS
    input_guard = await app.state.guardrails.check_input(query)
    logging.info("Input guardrail completed. "
        "status=%s rail=%s",
        input_guard.status,
        input_guard.rail)
    logfire.info("RAG input guardrail completed",
        guardrail_status=input_guard.status,
        guardrail_rail=str(input_guard.rail))
    if not input_guard.allowed:
        raise HTTPException(status_code=400,detail=input_guard.text)
    safe_query = input_guard.text 

    request_counter.add(1)
    active_requests.add(1)
    request_start = time.perf_counter()
    log_rag_query(logging=logging,query=query,user_id=current_user.id)
    logfire.info("RAG user query received",
              rag_event="rag.query",
              rag_query=query,
              rag_user_id=str(current_user.id),
              query_length=len(query))
    try:
        retrieval_start = time.perf_counter()
        with logfire.span(
            "rag.retrieve_and_rerank",
            query_length=len(safe_query),
            rag_query=safe_query,
            rag_user_id=str(current_user.id)) as retrieval_span:

            retrieved_documents = app.state.retriever.invoke(safe_query)
            retrieved_contexts = [document.page_content for document in retrieved_documents]
            document_count = len(retrieved_documents)
            retrieval_span.set_attribute("rag.documents.count",document_count)
        retrieval_ms = (time.perf_counter()-retrieval_start) * 1000
        retrieval_duration.record(retrieval_ms)
        documents_retrieved.record(document_count)

        # LOG ALL FINAL RETRIEVED DOCUMENTS
        log_retrieved_documents(logging=logging,
                query=query,
                retrieved_documents=retrieved_documents,
        )

        for rank, document in enumerate(retrieved_documents,start=1):
            source = document.metadata.get("source","Unknown source")
            page_numbers = (
                document.metadata.get(
                    "page_numbers",
                    [],
                )
            )
            headings = document.metadata.get(
                    "headings",
                    [],
                )
            
            chunk_id = document.metadata.get(
                    "chunk_id",
                    "Unknown chunk"
                )

            rrf_score = document.metadata.get("rrf_score")
            logfire.info(
                "RAG retrieved document",
                rag_event="rag.retrieved_document",
                rag_query=safe_query,
                retrieval_rank=rank,
                source=str(source),
                page_numbers=page_numbers,
                headings=headings,
                chunk_id=str(chunk_id),
                rrf_score=rrf_score,
                document_content=document.page_content
            )

        context_parts = []
        for document in retrieved_documents:
            source = document.metadata.get("source","Unknown source")
            page_numbers = document.metadata.get("page_numbers",[])
            headings = document.metadata.get("headings",[])
            chunk_id = document.metadata.get("chunk_id","Unknown chunk")
            
            context_part = f"""
            SOURCE: {source}
            PAGE(S): {page_numbers}
            SECTION: {headings}
            CHUNK ID: {chunk_id}

            CONTENT:
            {document.page_content}
            """
            context_parts.append(context_part)
        context = "\n\n".join(context_parts)

        logfire.info("RAG final assembled context",
            rag_event="rag.context",
            rag_query=safe_query,
            document_count=document_count,
            context=context,
        )

        # ANSWER GENERATION
        generation_start = time.perf_counter()
        with logfire.span(
            "rag.generate_answer",
             document_count=document_count,
             model="gpt-4.1-mini",
             rag_query=safe_query,
        ) as generation_span:
            try:
                response = app.state.answer_chain.invoke(
                        {
                            "query":safe_query,
                            "context":context,
                        }
                    )
               
                output_guard = await app.state.guardrails.check_output(
                        user_text=safe_query,
                        assistant_text=response.content
                       )
                logging.info(
                    "Output guardrail completed. "
                    "status=%s rail=%s",
                    output_guard.status,
                    output_guard.rail)

                logfire.info("RAG output guardrail completed",
                    guardrail_status=output_guard.status,
                    guardrail_rail=str(output_guard.rail))

                if not output_guard.allowed:
                    raise HTTPException(
                        status_code=400,
                        detail=output_guard.text,
                    )
                usage = getattr(
                    response,
                    "usage_metadata",
                    None,
                ) or {}

                prompt_token_count = int(
                    usage.get("input_tokens", 0) or 0
                )

                completion_token_count = int(
                    usage.get("output_tokens", 0) or 0
                )

                total_token_count = int(
                    usage.get(
                        "total_tokens",
                        prompt_token_count + completion_token_count,
                    )
                    or 0
                )

                llm_prompt_tokens.add(
                    prompt_token_count
                )

                llm_completion_tokens.add(
                    completion_token_count
                )

                llm_total_tokens.add(
                    total_token_count
                )


                # ============================================================
                # ESTIMATED LLM COST
                # ============================================================

                input_cost_per_1m = float(
                    os.getenv(
                        "LLM_INPUT_COST_PER_1M_TOKENS",
                        "0",
                    )
                )

                output_cost_per_1m = float(
                    os.getenv(
                        "LLM_OUTPUT_COST_PER_1M_TOKENS",
                        "0",
                    )
                )

                request_cost = (
                    (
                        prompt_token_count
                        / 1_000_000
                    )
                    * input_cost_per_1m
                ) + (
                    (
                        completion_token_count
                        / 1_000_000
                    )
                    * output_cost_per_1m
                )

                llm_cost_usd.add(
                    request_cost
                )
            except Exception as e:
                llm_error_counter.add(1)
                logging.exception(
                    "LLM generation failed",
                    extra={
                        "rag_event":"rag.llm_error",
                        "rag_query":safe_query,
                        "error_type":type(e).__name__,
                        "error_message":str(e),
                    },
                )
                logfire.exception(
                    "LLM generation failed",
                    rag_event="rag.llm_error",
                    rag_query=safe_query,
                    error_type=type(e).__name__,
                )
                raise

            generation_span.set_attribute("rag.generated_answer",response.content, )

        generation_ms = (time.perf_counter()-generation_start) * 1000
        llm_duration.record(generation_ms)

        # ANSWER EVENT THROUGH PYTHON LOGGING
        log_generated_answer(
            logging=logging,
            query=safe_query,
            answer=response.content,
            document_count=document_count,
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms
        )

        # COMPLETE ANSWER EVENT DIRECTLY TO LOGFIRE
        logfire.info(
            "RAG generated answer",
            rag_event="rag.generated_answer",
            rag_query=safe_query,
            generated_answer=response.content,
            document_count=document_count,
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
            rag_user_id=str(current_user.id)
        )

        logging.info(
            "RAG answer successfully generated",
            extra={
                "rag_event":"rag.request_success",
                "rag_query":safe_query,
                "document_count":document_count,
                "retrieval_ms":retrieval_ms,
                "generation_ms":generation_ms,
                "rag_user_id":str(current_user.id)
            }
        )

        # RESPONSE
        #return QueryResponse(query=query,answer=response.content)
        answer = response.content
        if should_evaluate_quality():
            background_tasks.add_task(
                evaluate_online_quality,
                question=safe_query,
                response=answer,
                retrieved_contexts=retrieved_contexts,
                user_id=str(current_user.id))
        return QueryResponse(query=query,answer=output_guard.text)
    except HTTPException:
        error_counter.add(1)
        raise
    except Exception as e:
        error_counter.add(1)
        logging.exception(
            "RAG query processing failed",
            extra={
                "rag_event":"rag.request_error",
                "rag_query":query,
                "error_type":type(e).__name__,
                "error_message":str(e),
                "rag_user_id":str(current_user.id)
            },
        )
        logfire.exception(
            "RAG query processing failed",
            rag_event="rag.request_error",
            rag_query=query,
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=
                (
                    "RAG query processing failed: "
                    f"{str(e)}"
                ),

        ) from e

    finally:
        active_requests.add(-1)
        total_duration_ms = (time.perf_counter()-request_start) * 1000
        request_duration.record(total_duration_ms)
        logging.info(
            "RAG request processing finished",
            extra={
                "rag_event":"rag.request_complete",
                "rag_query":query,
                "duration_ms":total_duration_ms,
                "rag_user_id":str(current_user.id)
            }
        )

        logfire.info(
            "RAG request processing finished",
            rag_event="rag.request_complete",
            rag_query=query,
            duration_ms=total_duration_ms,
            rag_user_id=str(current_user.id)
        )