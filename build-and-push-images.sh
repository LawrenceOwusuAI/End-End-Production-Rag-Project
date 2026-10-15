#!/usr/bin/env bash

set -e

DOCKER_USERNAME="lawrenceowusuml"
IMAGE_TAG="1.0"
PLATFORM="linux/amd64"

echo "LOGIN TO DOCKER HUB"
docker login -u "${DOCKER_USERNAME}"


# BUILD RAG BACKEND
echo "BUILDING RAG BACKEND"
docker build --platform "${PLATFORM}" -f Dockerfile.backend -t "${DOCKER_USERNAME}/rag-backend:${IMAGE_TAG}" .

# BUILD RAG FRONTEND
echo "BUILDING RAG FRONTEND"
docker build --platform "${PLATFORM}" -f Dockerfile.frontend -t "${DOCKER_USERNAME}/rag-frontend:${IMAGE_TAG}" .

# BUILD PROMETHEUS MCP"
echo "BUILDING PROMETHEUS MCP"
docker build --platform "${PLATFORM}" -f Dockerfile.prometheus-mcp -t "${DOCKER_USERNAME}/prometheus-mcp:${IMAGE_TAG}" .

# BUILD OPENSEARCH MCP
echo "BUILDING OPENSEARCH MCP"
docker build --platform "${PLATFORM}" -f Dockerfile.opensearch-mcp -t "${DOCKER_USERNAME}/opensearch-mcp:${IMAGE_TAG}" .

# BUILD OBSERVABILITY AGENT
echo "BUILDING OBSERVABILITY AGENT"
docker build --platform "${PLATFORM}" -f Dockerfile.observability-agent -t "${DOCKER_USERNAME}/observability-agent:${IMAGE_TAG}" .

# VERIFY BUILT IMAGES
echo "VERIFYING BUILT IMAGES"
docker images | grep "${DOCKER_USERNAME}"

# PUSH RAG BACKEND
echo "PUSHING RAG BACKEND"
docker push "${DOCKER_USERNAME}/rag-backend:${IMAGE_TAG}"

# PUSH RAG FRONTEND
echo "PUSHING RAG FRONTEND"
docker push "${DOCKER_USERNAME}/rag-frontend:${IMAGE_TAG}"

# PUSH PROMETHEUS MCP
echo "PUSHING PROMETHEUS MCP"
docker push "${DOCKER_USERNAME}/prometheus-mcp:${IMAGE_TAG}"

# PUSH OPENSEARCH MCP
echo "PUSHING OPENSEARCH MCP"
docker push "${DOCKER_USERNAME}/opensearch-mcp:${IMAGE_TAG}"

# PUSH OBSERVABILITY AGENT
echo "PUSHING OBSERVABILITY AGENT"
docker push "${DOCKER_USERNAME}/observability-agent:${IMAGE_TAG}"

# VERIFY THAT IMAGES CAN BE PULLED
echo "VERIFYING IMAGES FROM DOCKER HUB"
docker pull "${DOCKER_USERNAME}/rag-backend:${IMAGE_TAG}"
docker pull "${DOCKER_USERNAME}/rag-frontend:${IMAGE_TAG}"
docker pull "${DOCKER_USERNAME}/prometheus-mcp:${IMAGE_TAG}"
docker pull "${DOCKER_USERNAME}/opensearch-mcp:${IMAGE_TAG}"
docker pull "${DOCKER_USERNAME}/observability-agent:${IMAGE_TAG}"

echo "ALL IMAGES BUILT AND PUSHED SUCCESSFULLY"


#chmod +x build-and-push-images.sh
#./build-and-push-images.sh