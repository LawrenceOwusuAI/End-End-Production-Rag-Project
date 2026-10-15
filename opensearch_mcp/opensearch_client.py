# opensearch_mcp/opensearch_client.py
from __future__ import annotations
import os
import boto3
from dotenv import load_dotenv
from opensearchpy import OpenSearch,RequestsHttpConnection,AWSV4SignerAuth

load_dotenv(override=True)

# AWS CONFIGURATION
AWS_REGION = os.getenv("AWS_REGION","us-east-1")
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST")
if not OPENSEARCH_HOST:
    raise ValueError("OPENSEARCH_HOST was not found.")

host = (OPENSEARCH_HOST.replace("https://","",).replace("http://","",).rstrip("/"))

session = boto3.Session()
credentials = session.get_credentials()
if credentials is None:
    raise RuntimeError("AWS credentials could not be resolved.")

# AWS SIGV4
auth = AWSV4SignerAuth(credentials,AWS_REGION,"es",)

# OPENSEARCH CLIENT
client = OpenSearch(
    hosts=[
        {
            "host":host,
            "port":443,
        }
    ],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=20,
)

# INTERNAL SEARCH FUNCTION THIS FUNCTION IS PRIVATE TO THE MCP SERVICE. Therefore the LLM cannot write arbitrary
def search_opensearch(index: str, query: dict):
    return client.search(index=index, body=query)