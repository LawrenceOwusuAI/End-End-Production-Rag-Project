from __future__ import annotations
import os
import sys
import time
import logfire
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import ServerlessSpec
from pinecone import Pinecone
from chunking import PDF_PATH
from chunking import run_chunking_pipeline
from exception import CustomException
from logger import  logging
from observability import TimedEmbeddings,vector_db_error_counter

EMBEDDING_MODEL_NAME = ("sentence-transformers/all-MiniLM-L6-v2")
INDEX_NAME = "rag-project"
NAMESPACE = PDF_PATH.stem

# PINECONE API KEY
def get_pinecone_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY was not found in the .env file.")
    return api_key

def create_embedding_model():
    logging.info("Creating embedding model: %s",EMBEDDING_MODEL_NAME)
    base_embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={
                "device":"cpu"
            },
            encode_kwargs={
                "normalize_embeddings":True
            },
        )
    
    embeddings = TimedEmbeddings(base_embeddings)
    logging.info("Embedding model created successfully")
    return embeddings

#Embedding dimension
def get_embedding_dimension(embeddings) -> int:
    logging.info("Determining embedding dimension")
    test_embedding = embeddings.embed_query("embedding dimension test")
    dimension = len(test_embedding)
    logging.info("Embedding dimension: %d",dimension)
    return dimension

# PREPARE DOCUMENTS FOR PINECONE
def prepare_documents_for_pinecone(langchain_documents:list[Document]) -> list[Document]:
    pinecone_documents: list[Document] = []
    for document in langchain_documents:
        metadata = document.metadata.copy()
        metadata["page_numbers"] = [
            str(page_number)
            for page_number
            in metadata.get("page_numbers",[])
        ]
        metadata["headings"] = [
            str(heading)
            for heading
            in metadata.get("headings",[])
        ]
        metadata["captions"] = [
            str(caption)
            for caption
            in metadata.get("captions",[])
        ]
        pinecone_documents.append(
            Document(page_content=document.page_content, metadata=metadata)
        )
    return pinecone_documents

# CREATE PINECONE CLIENT
def create_pinecone_client():
    api_key = get_pinecone_api_key()
    logging.info("Creating Pinecone client")
    try:
        with logfire.span("rag.pinecone.create_client"):
            pc = Pinecone(api_key=api_key)
        logging.info("Pinecone client created successfully")
        return pc
    except Exception as e:
        vector_db_error_counter.add(1)
        logging.exception(
            "Failed to create Pinecone client",
            extra={
                "rag_event":"rag.vector_db_error",
                "vector_operation":"create_client",
                "error_type": type(e).__name__,
                "error_message":str(e)
            }
        )
        raise

# CREATE OR GET INDEX
def create_or_get_index(pc,embedding_dimension: int):
    logging.info("Checking Pinecone index: %s",INDEX_NAME)
    try:
        with logfire.span(
            "rag.pinecone.index_setup",
            index_name=INDEX_NAME,
            embedding_dimension=embedding_dimension,
        ):
            if not pc.has_index(INDEX_NAME):
                logging.info("Creating Pinecone index: %s",INDEX_NAME)
                print(f"Creating Pinecone index: "
                    f"{INDEX_NAME}"
                )
                pc.create_index(name=INDEX_NAME,
                    dimension=embedding_dimension,
                    metric="cosine",
                    spec=
                        ServerlessSpec(
                            cloud="aws",
                            region= "us-east-1"
                        )
                )

            while True:
                description = pc.describe_index(name=INDEX_NAME)
                if description.status["ready"]:
                    break
                logging.info("Waiting for Pinecone index to become ready")
                print("Waiting for Pinecone index to be ready")
                time.sleep(2)
            logging.info("Pinecone index ready: %s",INDEX_NAME)
            print(f"Pinecone index ready: {INDEX_NAME}")
            index = pc.Index(INDEX_NAME)
            return index
    except Exception as e:
        vector_db_error_counter.add(1)
        logging.exception("Pinecone index operation failed",
            extra={
                "rag_event":"rag.vector_db_error",
                "vector_operation":"index_setup",
                "index_name":INDEX_NAME,
                "embedding_dimension":embedding_dimension,
                "error_type":type(e).__name__,
                "error_message":str(e),
            }
        )
        raise

# CREATE VECTOR STORE
def create_vector_store(index,embeddings):
    logging.info("Creating LangChain Pinecone vector store")
    vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace=NAMESPACE
        )
    logging.info("LangChain Pinecone vector store created successfully")
    return vector_store

# STORE DOCUMENTS
def store_documents(vector_store,documents:list[Document]) -> None:
    chunk_ids = [document.metadata["chunk_id"] for document in documents]
    logging.info("Starting Pinecone document upsert. "
        "documents=%d",
        len(documents),
    )
    try:
        with logfire.span("rag.pinecone.upsert_documents",
            document_count=len(documents),
            namespace=NAMESPACE,
            index_name=INDEX_NAME):

            vector_store.add_documents(
                documents=documents,
                ids=chunk_ids,
            )
    except Exception as e:
        vector_db_error_counter.add(1)
        logging.exception("Pinecone document upsert failed",
            extra={
                "rag_event":"rag.vector_db_error",
                "vector_operation":"upsert_documents",
                "index_name":INDEX_NAME,
                "namespace":NAMESPACE,
                "document_count":len(documents),
                "error_type":type(e).__name__,
                "error_message":str(e),
            }
        )
        raise
    logging.info(
        "Pinecone document upsert completed. "
        "documents=%d namespace=%s",
        len(documents),
        NAMESPACE,
    )
    print(
        f"\nSuccessfully embedded "
        f"and stored "
        f"{len(documents)} "
        f"chunks in Pinecone."
    )

# COMPLETE VECTORSTORE PIPELINE
def run_vectorstore_pipeline(langchain_documents:list[Document]):
    logging.info( "Vectorstore pipeline started")
    print("\nCreating embedding model...")
    embeddings = create_embedding_model()
    dimension = get_embedding_dimension(embeddings)
    print(
        f"Embedding dimension: "
        f"{dimension}"
    )
    # PREPARE DOCUMENTS
    pinecone_documents = prepare_documents_for_pinecone(langchain_documents)
    logging.info(
        "Documents prepared for Pinecone. "
        "documents=%d",
        len(
            pinecone_documents
        ),
    )

    # PINECONE CLIENT
    pc = create_pinecone_client()
    index = create_or_get_index(
            pc=pc,
            embedding_dimension=dimension
        )
    
    # VECTOR STORE
    vector_store = create_vector_store(
            index=index,
            embeddings=embeddings
        )
    
    # STORE DOCUMENTS
    store_documents(vector_store=vector_store,documents=pinecone_documents)
    try:
        with logfire.span("rag.pinecone.describe_index_stats",index_name=INDEX_NAME):
            stats = index.describe_index_stats()
    except Exception as e:
        vector_db_error_counter.add(1)
        logging.exception(
            "Failed to read Pinecone index statistics",
            extra={
                "rag_event":"rag.vector_db_error",
                "vector_operation":"describe_index_stats",
                "index_name":INDEX_NAME,
                "error_type":type(e).__name__,
                "error_message":str(e),
            }
        )
        raise
    print( "\nPinecone index statistics:")
    print(stats)
    logging.info("Vectorstore pipeline completed successfully")
    return vector_store

if __name__ == "__main__":
    logging.info("Chunking of document has started")
    try:
        chunkedDoclingDocument = run_chunking_pipeline()
    except Exception as e:
        logging.exception("Document chucking failed")
        raise CustomException(e,sys)
    logging.info("Chucking has succeeded")
    logging.info("Upserting of embeddings in Pinecone has started")
    try:
        run_vectorstore_pipeline(chunkedDoclingDocument)
    except Exception as e:
        logging.exception("Document upsert into pinecone failed")
        raise CustomException(e,sys)
    logging.info("Upserting of embeddings in Pinecone has succeeded")