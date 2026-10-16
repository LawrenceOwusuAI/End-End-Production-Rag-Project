from __future__ import annotations
from mcp.server import MCPServer
from prometheus_mcp.prometheus_client import get_prometheus_alerts,query_prometheus

mcp = MCPServer("rag-prometheus-observability")

# TOOL 1 REQUEST RATE
@mcp.tool()
async def get_request_rate() -> dict:

    """
    Get the current RAG request rate.

    Use this tool when the user asks about:
    request rate, RPS, QPS, traffic or throughput.
    """

    query = """
    sum(
        rate(
            rag_requests_total[5m]
        )
    )
    """

    result = await query_prometheus(query)
    return {
        "metric":"request_rate",
        "unit":"requests_per_second",
        "result":result,
    }

# TOOL 2 ERROR RATE
@mcp.tool()
async def get_error_rate() -> dict:

    """
    Get percentage of RAG requests resulting in errors.
    """

    query = """
    (
        sum(
            rate(
                rag_errors_total[5m]
            )
        )
        /
        clamp_min(
            sum(
                rate(
                    rag_requests_total[5m]
                )
            ),
            0.000001
        )
    ) * 100
    """

    result = await query_prometheus(query)
    return {
        "metric":"error_rate",
        "unit":"percent",
        "result":result,
    }

@mcp.tool()
async def get_total_rag_queries() -> dict:
    """
    Return the cumulative total number of RAG queries processed.

    Use this tool when the user asks:
    - how many RAG queries have been processed
    - total number of RAG requests
    - total queries handled so far
    - cumulative number of RAG queries

    Do NOT use this tool for:
    - request rate
    - requests per second
    - throughput
    """

    query = """
    sum(rag_requests_total)
    """

    result = await query_prometheus(
        query
    )

    return {
        "metric": "total_rag_queries",
        "unit": "requests",
        "result": result,
    }

@mcp.tool()
async def get_rag_queries_last_10_minutes() -> dict:
    """
    Return the number of RAG queries processed in the last 10 minutes.

    Use this tool when the user asks:
    - how many RAG queries were processed in the last 10 minutes
    - number of recent RAG queries in the past 10 minutes

    Do NOT use this tool for:
    - cumulative total queries
    - request rate
    - requests per second
    """

    query = """
    sum(
        increase(
            rag_requests_total[10m]
        )
    )
    """

    result = await query_prometheus(
        query
    )

    return {
        "metric": "rag_queries_last_10_minutes",
        "unit": "requests",
        "window": "10m",
        "result": result,
    }

@mcp.tool()
async def get_rag_query_count(window: str = "10m") -> dict:
    """
    Return the number of RAG queries processed in a recent time window.

    Allowed windows:
    - 5m
    - 10m
    - 15m
    - 30m
    - 1h
    """

    allowed_windows = {
        "5m",
        "10m",
        "15m",
        "30m",
        "1h",
    }

    if window not in allowed_windows:
        return {
            "error": f"Unsupported window: {window}",
            "allowed_windows": sorted(allowed_windows),
        }

    query = f"""
    round(
        sum(
            increase(
                rag_requests_total[{window}]
            )
        )
    )
    """

    result = await query_prometheus(query)

    # Prometheus returns:
    # [{"metric": {}, "value": [timestamp, "count"]}]
    try:
        value = result[0]["value"][1]
        count = int(float(value))
    except (IndexError, KeyError, TypeError, ValueError):
        return {
            "metric": "rag_query_count",
            "window": window,
            "error": "Unable to extract query count from Prometheus result.",
            "raw_result": result,
        }

    return {
        "metric": "rag_query_count",
        "window": window,
        "unit": "requests",
        "count": count,
    }

@mcp.tool()
async def get_p50_latency() -> dict:

    """
    Get median end-to-end RAG request latency.
    """

    query = """
    histogram_quantile(
        0.50,
        sum(
            rate(
                rag_request_duration_milliseconds_bucket[5m]
            )
        ) by (le)
    )
    """

    result = await query_prometheus(query)
    return {
        "metric":"p50_latency",
        "unit":"milliseconds",
        "result":result,
    }

# TOOL 4 P95 LATENCY
@mcp.tool()
async def get_p95_latency() -> dict:

    """
    Get p95 end-to-end RAG request latency.
    """

    query = """
    histogram_quantile(
        0.95,
        sum(
            rate(
                rag_request_duration_milliseconds_bucket[5m]
            )
        ) by (le)
    )
    """

    result = await query_prometheus(query)
    return {
        "metric":"p95_latency",
        "unit":"milliseconds",
        "result":result,
    }

# TOOL 5 P99 LATENCY
@mcp.tool()
async def get_p99_latency() -> dict:

    """
    Get p99 end-to-end RAG request latency.
    """

    query = """
    histogram_quantile(
        0.99,
        sum(
            rate(
                rag_request_duration_milliseconds_bucket[5m]
            )
        ) by (le)
    )
    """

    result = await query_prometheus(query)
    return {
        "metric":"p99_latency",
        "unit":"milliseconds",
        "result":result,
    }

# TOOL 6 CPU
@mcp.tool()
async def get_cpu_usage(window: str = "5m") -> dict:
    """
    Return average CPU usage of the RAG backend over a recent time window.

    Allowed windows:
    - 1m
    - 5m
    - 10m
    - 15m
    - 30m
    - 1h

    Use this tool when the user asks:
    - current CPU usage
    - average CPU usage
    - CPU usage over the last 5, 10, 15, or 30 minutes
    - CPU usage over the last hour

    Do NOT use this tool for memory usage.
    """

    allowed_windows = {
        "1m",
        "5m",
        "10m",
        "15m",
        "30m",
        "1h",
    }

    if window not in allowed_windows:
        return {
            "error": f"Unsupported window: {window}",
            "allowed_windows": sorted(allowed_windows),
        }

    query = f"""
    100 *
    sum(
        rate(
            container_cpu_usage_seconds_total{{
                name=~".*rag-backend.*"
            }}[{window}]
        )
    )
    """

    result = await query_prometheus(query)

    return {
        "metric": "rag_backend_cpu_usage",
        "unit": "percent",
        "window": window,
        "result": result,
    }


@mcp.tool()
async def get_memory_usage(window: str = "5m") -> dict:
    """
    Return average memory usage of the RAG backend over a recent time window.

    Allowed windows:
    - 1m
    - 5m
    - 10m
    - 15m
    - 30m
    - 1h

    Use this tool when the user asks:
    - current memory usage
    - average memory usage
    - memory usage over the last 5, 10, 15, or 30 minutes
    - memory usage over the last hour

    Do NOT use this tool for CPU usage.
    """

    allowed_windows = {
        "1m",
        "5m",
        "10m",
        "15m",
        "30m",
        "1h",
    }

    if window not in allowed_windows:
        return {
            "error": f"Unsupported window: {window}",
            "allowed_windows": sorted(allowed_windows),
        }

    query = f"""
    avg_over_time(
        container_memory_working_set_bytes{{
            name=~".*rag-backend.*"
        }}[{window}]
    )
    / 1024 / 1024
    """

    result = await query_prometheus(query)
    return {
        "metric": "rag_backend_memory_usage",
        "unit": "MB",
        "window": window,
        "result": result,
    }


# RETRIEVAL LATENCY
@mcp.tool()
async def get_retrieval_latency() -> dict:

    """
    Get average RAG retrieval and reranking latency.
    """

    query = """
    sum(
        rate(
            rag_retrieval_duration_milliseconds_sum[5m]
        )
    )
    /
    clamp_min(
        sum(
            rate(
                rag_retrieval_duration_milliseconds_count[5m]
            )
        ),
        0.000001
    )
    """
    result = await query_prometheus(query)
    return {
        "metric":"retrieval_latency",
        "unit":"milliseconds",
        "result":result,
    }

# TOOL 9 GENERATION LATENCY
@mcp.tool()
async def get_generation_latency() -> dict:

    """
    Get average final LLM answer-generation latency.
    """

    query = """
    sum(
        rate(
            rag_llm_duration_milliseconds_sum[5m]
        )
    )
    /
    clamp_min(
        sum(
            rate(
                rag_llm_duration_milliseconds_count[5m]
            )
        ),
        0.000001
    )
    """
    result = await query_prometheus(query)
    return {
        "metric":"generation_latency",
        "unit":"milliseconds",
        "result":result,
    }

# TOOL 10 RERANKER LATENCY
@mcp.tool()
async def get_reranker_latency() -> dict:

    """
    Get average cross-encoder reranker latency.
    """

    query = """
    sum(
        rate(
            rag_reranker_duration_milliseconds_sum[5m]
        )
    )
    /
    clamp_min(
        sum(
            rate(
                rag_reranker_duration_milliseconds_count[5m]
            )
        ),
        0.000001
    )
    """
    result = await query_prometheus(query)
    return {
        "metric":"reranker_latency",
        "unit":"milliseconds",
        "result":result,
    }

# TOOL 11 EMBEDDING LATENCY
@mcp.tool()
async def get_embedding_latency() -> dict:

    """
    Get average embedding model latency.
    """

    query = """
    sum(
        rate(
            rag_embedding_duration_milliseconds_sum[5m]
        )
    )
    /
    clamp_min(
        sum(
            rate(
                rag_embedding_duration_milliseconds_count[5m]
            )
        ),
        0.000001
    )
    """

    result = await query_prometheus(query)
    return {
        "metric":"embedding_latency",
        "unit":"milliseconds",
        "result": result,
    }


# TOOL 12 VECTOR DATABASE ERRORS
@mcp.tool()
async def get_vector_db_errors() -> dict:

    """
    Get Pinecone/vector database error rate.
    """

    query = """
    sum(
        rate(
            rag_vector_db_errors_total[5m]
        )
    )
    """

    result = await query_prometheus(query)
    return {
        "metric":"vector_db_error_rate",
        "unit":"errors_per_second",
        "result":result,
    }

# TOOL 13 LLM ERRORS
@mcp.tool()
async def get_llm_error_rate() -> dict:

    """
    Get final answer-generation LLM error rate.
    """

    query = """
    sum(
        rate(
            rag_llm_errors_total[5m]
        )
    )
    """


    result = await query_prometheus(
        query
    )


    return {
        "metric":
            "llm_error_rate",

        "unit":
            "errors_per_second",

        "result":
            result,
    }

# TOOL 14 ACTIVE REQUESTS
@mcp.tool()
async def get_active_requests() -> dict:

    """
    Get current number of active RAG requests.
    """

    query = """
    sum(
        rag_active_requests
    )
    """


    result = await query_prometheus(
        query
    )


    return {
        "metric":
            "active_requests",

        "unit":
            "requests",

        "result":
            result,
    }

# TOOL 15 RAG HEALTH
@mcp.tool()
async def get_rag_health() -> dict:

    """
    Get a high-level health snapshot of the RAG system.

    Use when the user asks:
    - Is the RAG healthy?
    - How is the application doing?
    - Is anything wrong?
    """

    request_rate = (
        await get_request_rate()
    )

    error_rate = (
        await get_error_rate()
    )

    p95_latency = (
        await get_p95_latency()
    )

    cpu_usage = (
        await get_cpu_usage()
    )

    memory_usage = (
        await get_memory_usage()
    )


    return {
        "request_rate":
            request_rate,

        "error_rate":
            error_rate,

        "p95_latency":
            p95_latency,

        "cpu_usage":
            cpu_usage,

        "memory_usage":
            memory_usage,
    }

# SAFE TIME WINDOWS
ALLOWED_WINDOWS = {
    "1m",
    "5m",
    "10m",
    "15m",
    "30m",
    "1h",
}


def _validate_window(window: str) -> str:
    """
    Prevent the LLM from inserting arbitrary PromQL ranges.
    """

    if window not in ALLOWED_WINDOWS:
        raise ValueError(
            f"Unsupported window '{window}'. "
            f"Allowed windows: {sorted(ALLOWED_WINDOWS)}"
        )

    return window

# PROMETHEUS RESULT HELPER
def _extract_prometheus_scalar(result):
    """
    Extract the actual numeric value from a Prometheus instant-vector result.

    Handles common result shapes such as:

    [
        {
            "metric": {},
            "value": [timestamp, "4"]
        }
    ]

    and full Prometheus API responses.
    """

    if result is None:
        return None

    try:

        if isinstance(result, dict) and "data" in result:

            result = result["data"].get(
                "result",
                [],
            )

        if isinstance(result, list):

            if not result:
                return None

            item = result[0]

            value = item.get("value")

            if value and len(value) >= 2:

                return float(
                    value[1]
                )

        return None

    except (
        TypeError,
        ValueError,
        KeyError,
        IndexError,
    ):

        return None

# 1. SUCCESS RATE
@mcp.tool()
async def get_success_rate(
    window: str = "5m",
) -> dict:
    """
    Return the percentage of RAG requests that completed successfully.

    Use this tool when the user asks:
    - what is the RAG success rate
    - what percentage of requests succeeded
    - how reliable is the RAG application
    - success rate over the last 5, 10, 30 minutes, etc.

    Allowed windows:
    - 1m
    - 5m
    - 10m
    - 15m
    - 30m
    - 1h
    """

    window = _validate_window(
        window
    )

    query = f"""
    100 *
    (
        1
        -
        (
            (
                sum(
                    rate(
                        rag_errors_total[{window}]
                    )
                )
                or vector(0)
            )
            /
            clamp_min(
                sum(
                    rate(
                        rag_requests_total[{window}]
                    )
                ),
                0.000001
            )
        )
    )
    """

    result = await query_prometheus(
        query
    )

    value = _extract_prometheus_scalar(
        result
    )

    if value is None:

        return {
            "metric": "rag_success_rate",
            "window": window,
            "unit": "percent",
            "error": "No success-rate data was returned by Prometheus.",
        }

    return {
        "metric": "rag_success_rate",
        "window": window,
        "unit": "percent",
        "value": round(value, 2),
    }

# 2. PEAK ACTIVE REQUESTS
@mcp.tool()
async def get_peak_active_requests(
    window: str = "30m",
) -> dict:
    """
    Return the highest number of concurrent RAG requests
    observed during a recent time window.

    Use this tool when the user asks:
    - what was peak concurrency
    - maximum active requests
    - highest number of simultaneous RAG requests
    - peak load during the last 30 minutes
    """

    window = _validate_window(
        window
    )

    query = f"""
    max(
        max_over_time(
            rag_active_requests[{window}]
        )
    )
    """

    result = await query_prometheus(
        query
    )

    value = _extract_prometheus_scalar(
        result
    )

    if value is None:

        return {
            "metric": "peak_active_requests",
            "window": window,
            "unit": "requests",
            "error": "No active-request data was returned by Prometheus.",
        }

    return {
        "metric": "peak_active_requests",
        "window": window,
        "unit": "requests",
        "value": int(round(value)),
    }

# 3. MEMORY LIMIT UTILIZATION
@mcp.tool()
async def get_memory_limit_percent() -> dict:
    """
    Return the percentage of the RAG backend container's
    memory limit that is currently being used.

    Use this tool when the user asks:
    - how close is the RAG backend to its memory limit
    - what percentage of memory capacity is being used
    - is the backend running out of memory
    - memory saturation
    """

    query = """
    100 *
    (
        sum(
            container_memory_working_set_bytes{
                container_label_com_docker_compose_service="rag-backend"
            }
        )
        /
        clamp_min(
            sum(
                container_spec_memory_limit_bytes{
                    container_label_com_docker_compose_service="rag-backend"
                }
            ),
            1
        )
    )
    """

    result = await query_prometheus(
        query
    )

    value = _extract_prometheus_scalar(
        result
    )

    if value is None:

        return {
            "metric": "rag_backend_memory_limit_utilization",
            "unit": "percent",
            "error": (
                "No memory-limit data was returned. "
                "The container may not have a configured memory limit."
            ),
        }

    return {
        "metric": "rag_backend_memory_limit_utilization",
        "unit": "percent",
        "value": round(value, 2),
    }

# 4. AVERAGE DOCUMENTS RETRIEVED
@mcp.tool()
async def get_documents_retrieved_avg(
    window: str = "5m",
) -> dict:
    """
    Return the average number of documents retrieved per RAG query.

    Use this tool when the user asks:
    - how many documents are retrieved per query
    - average retrieved document count
    - average number of contexts returned
    - retrieval depth
    """

    window = _validate_window(
        window
    )

    query = f"""
    sum(
        rate(
            rag_documents_retrieved_sum[{window}]
        )
    )
    /
    clamp_min(
        sum(
            rate(
                rag_documents_retrieved_count[{window}]
            )
        ),
        0.000001
    )
    """

    result = await query_prometheus(
        query
    )

    value = _extract_prometheus_scalar(
        result
    )

    if value is None:

        return {
            "metric": "average_documents_retrieved",
            "window": window,
            "unit": "documents_per_query",
            "error": "No document-retrieval metric was returned.",
        }

    return {
        "metric": "average_documents_retrieved",
        "window": window,
        "unit": "documents_per_query",
        "value": round(value, 2),
    }

# INTERNAL LATENCY QUERY HELPER
async def _average_histogram_latency(metric_prefix: str,window: str):
    """
    Calculate average latency from an OpenTelemetry/
    Prometheus histogram.

    Example:

        rag_llm_duration_milliseconds_sum
        rag_llm_duration_milliseconds_count
    """

    query = f"""
    sum(
        rate(
            {metric_prefix}_sum[{window}]
        )
    )
    /
    clamp_min(
        sum(
            rate(
                {metric_prefix}_count[{window}]
            )
        ),
        0.000001
    )
    """

    result = await query_prometheus(
        query
    )

    return _extract_prometheus_scalar(
        result
    )

# INTERNAL LATENCY BREAKDOWN HELPER
async def _get_latency_breakdown(window: str) -> dict:

    request_ms = await _average_histogram_latency(
        "rag_request_duration_milliseconds",
        window,
    )

    retrieval_ms = await _average_histogram_latency(
        "rag_retrieval_duration_milliseconds",
        window,
    )

    reranker_ms = await _average_histogram_latency(
        "rag_reranker_duration_milliseconds",
        window,
    )

    embedding_ms = await _average_histogram_latency(
        "rag_embedding_duration_milliseconds",
        window,
    )

    llm_ms = await _average_histogram_latency(
        "rag_llm_duration_milliseconds",
        window,
    )

    return {
        "request_ms": request_ms,
        "retrieval_ms": retrieval_ms,
        "reranker_ms": reranker_ms,
        "embedding_ms": embedding_ms,
        "llm_ms": llm_ms,
    }


# 5. REQUEST LATENCY BREAKDOWN
@mcp.tool()
async def get_request_latency_breakdown(
    window: str = "5m",
) -> dict:
    """
    Return a latency breakdown of the RAG pipeline.

    Components:
    - end-to-end request
    - retrieval
    - reranking
    - embedding
    - LLM generation

    Use this tool when the user asks:
    - why is the RAG system slow
    - show me the latency breakdown
    - how long does each RAG component take
    - compare retrieval and LLM latency
    """

    window = _validate_window(
        window
    )

    breakdown = await _get_latency_breakdown(
        window
    )

    cleaned = {}

    for name, value in breakdown.items():

        cleaned[name] = (
            round(value, 2)
            if value is not None
            else None
        )

    return {
        "metric": "rag_latency_breakdown",
        "window": window,
        "unit": "milliseconds",
        "components": cleaned,
    }

# 6. SLOWEST RAG COMPONENT
@mcp.tool()
async def get_slowest_component(
    window: str = "5m",
) -> dict:
    """
    Identify the slowest major component of the RAG pipeline.

    Components compared:
    - retrieval
    - reranking
    - embedding
    - LLM generation

    Use this tool when the user asks:
    - what is the RAG bottleneck
    - what component is slowest
    - why is the application slow
    - is retrieval or generation slower
    """

    window = _validate_window(
        window
    )

    breakdown = await _get_latency_breakdown(
        window
    )

    # Do not compare the full request duration because it
    # contains the other component durations.

    components = {
        "retrieval": breakdown.get(
            "retrieval_ms"
        ),
        "reranker": breakdown.get(
            "reranker_ms"
        ),
        "embedding": breakdown.get(
            "embedding_ms"
        ),
        "llm_generation": breakdown.get(
            "llm_ms"
        ),
    }

    # Remove components for which Prometheus returned no data.

    available_components = {
        name: value
        for name, value
        in components.items()
        if value is not None
    }

    if not available_components:

        return {
            "metric": "slowest_rag_component",
            "window": window,
            "error": "No component latency data was returned by Prometheus.",
        }

    slowest_component = max(
        available_components,
        key=available_components.get,
    )

    slowest_latency = (
        available_components[
            slowest_component
        ]
    )

    formatted_components = {
        name: round(value, 2)
        for name, value
        in available_components.items()
    }

    return {
        "metric": "slowest_rag_component",
        "window": window,
        "unit": "milliseconds",
        "slowest_component": slowest_component,
        "average_latency_ms": round(
            slowest_latency,
            2,
        ),
        "components": formatted_components,
    }

# RAG HEALTH SUMMARY
@mcp.tool()
async def get_rag_health_summary(
    window: str = "5m",
) -> dict:
    """
    Return a consolidated health summary for the RAG application.

    This tool combines:
    - request rate
    - error rate
    - p95 end-to-end latency
    - active requests
    - CPU usage
    - memory usage
    - retrieval latency
    - LLM generation latency

    Use this tool when the user asks:
    - is the RAG system healthy
    - give me a health summary
    - what is the current state of the RAG application
    - are there any performance problems
    - is the RAG backend overloaded
    - give me an operational overview

    Allowed windows:
    - 1m
    - 5m
    - 10m
    - 15m
    - 30m
    - 1h
    """

    allowed_windows = {
        "1m",
        "5m",
        "10m",
        "15m",
        "30m",
        "1h",
    }

    if window not in allowed_windows:
        return {
            "error": f"Unsupported window: {window}",
            "allowed_windows": sorted(allowed_windows),
        }

    # REQUEST RATE

    request_rate_query = f"""
    sum(
        rate(
            rag_requests_total[{window}]
        )
    )
    """

    # ERROR RATE

    error_rate_query = f"""
    100 *
    (
        (
            sum(
                rate(
                    rag_errors_total[{window}]
                )
            )
            or vector(0)
        )
        /
        clamp_min(
            sum(
                rate(
                    rag_requests_total[{window}]
                )
            ),
            0.000001
        )
    )
    """

    # P95 END-TO-END LATENCY

    p95_latency_query = f"""
    histogram_quantile(
        0.95,
        sum by (le) (
            rate(
                rag_request_duration_milliseconds_bucket[{window}]
            )
        )
    )
    """

    # ACTIVE REQUESTS

    active_requests_query = """
    sum(
        rag_active_requests
    )
    """

    # CPU USAGE

    cpu_query = f"""
    100 *
    sum(
        rate(
            container_cpu_usage_seconds_total{{
                container_label_com_docker_compose_service="rag-backend"
            }}[{window}]
        )
    )
    """

    # MEMORY USAGE IN MB

    memory_query = f"""
    avg_over_time(
        container_memory_working_set_bytes{{
            container_label_com_docker_compose_service="rag-backend"
        }}[{window}]
    )
    / 1024 / 1024
    """

    # AVERAGE RETRIEVAL LATENCY
  
    retrieval_latency_query = f"""
    sum(
        rate(
            rag_retrieval_duration_milliseconds_sum[{window}]
        )
    )
    /
    clamp_min(
        sum(
            rate(
                rag_retrieval_duration_milliseconds_count[{window}]
            )
        ),
        0.000001
    )
    """

    # AVERAGE LLM GENERATION LATENCY
  
    llm_latency_query = f"""
    sum(
        rate(
            rag_llm_duration_milliseconds_sum[{window}]
        )
    )
    /
    clamp_min(
        sum(
            rate(
                rag_llm_duration_milliseconds_count[{window}]
            )
        ),
        0.000001
    )
    """

 # RUN PROMETHEUS QUERIES
    request_rate_result = await query_prometheus(
        request_rate_query
    )

    error_rate_result = await query_prometheus(
        error_rate_query
    )

    p95_latency_result = await query_prometheus(
        p95_latency_query
    )

    active_requests_result = await query_prometheus(
        active_requests_query
    )

    cpu_result = await query_prometheus(
        cpu_query
    )

    memory_result = await query_prometheus(
        memory_query
    )

    retrieval_latency_result = await query_prometheus(
        retrieval_latency_query
    )

    llm_latency_result = await query_prometheus(
        llm_latency_query
    )

 
# HELPER TO EXTRACT THE REAL PROMETHEUS VALUE
    def extract_value(result):

        try:
            return float(
                result[0]["value"][1]
            )

        except (
            IndexError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return None

    request_rate = extract_value(
        request_rate_result
    )

    error_rate = extract_value(
        error_rate_result
    )

    p95_latency = extract_value(
        p95_latency_result
    )

    active_requests = extract_value(
        active_requests_result
    )

    cpu_usage = extract_value(
        cpu_result
    )

    memory_usage = extract_value(
        memory_result
    )

    retrieval_latency = extract_value(
        retrieval_latency_result
    )

    llm_latency = extract_value(
        llm_latency_result
    )
    # SIMPLE HEALTH CLASSIFICATION
   
    issues = []

    if error_rate is not None and error_rate > 5:
        issues.append(
            "High error rate"
        )

    if p95_latency is not None and p95_latency > 5000:
        issues.append(
            "High p95 request latency"
        )

    if cpu_usage is not None and cpu_usage > 85:
        issues.append(
            "High CPU usage"
        )

    if retrieval_latency is not None and retrieval_latency > 3000:
        issues.append(
            "High retrieval latency"
        )

    if llm_latency is not None and llm_latency > 3000:
        issues.append(
            "High LLM generation latency"
        )

    if not issues:
        health_status = "healthy"

    elif len(issues) <= 2:
        health_status = "degraded"

    else:
        health_status = "unhealthy"


    # RETURN CLEAN STRUCTURED DATA
   
    return {
        "metric": "rag_health_summary",
        "window": window,
        "status": health_status,

        "traffic": {
            "request_rate_per_second": (
                round(request_rate, 4)
                if request_rate is not None
                else None
            ),
            "active_requests": (
                int(round(active_requests))
                if active_requests is not None
                else None
            ),
        },

        "errors": {
            "error_rate_percent": (
                round(error_rate, 2)
                if error_rate is not None
                else None
            ),
        },

        "latency": {
            "p95_request_latency_ms": (
                round(p95_latency, 2)
                if p95_latency is not None
                else None
            ),
            "retrieval_latency_ms": (
                round(retrieval_latency, 2)
                if retrieval_latency is not None
                else None
            ),
            "llm_generation_latency_ms": (
                round(llm_latency, 2)
                if llm_latency is not None
                else None
            ),
        },

        "resources": {
            "cpu_usage_percent": (
                round(cpu_usage, 2)
                if cpu_usage is not None
                else None
            ),
            "memory_usage_mb": (
                round(memory_usage, 2)
                if memory_usage is not None
                else None
            ),
        },

        "issues": issues,
    }

# SHARED HELPERS

MONITORING_WINDOWS = {
    "1m",
    "5m",
    "10m",
    "15m",
    "30m",
    "1h",
}


def _safe_window(window: str) -> str:
    if window not in MONITORING_WINDOWS:
        raise ValueError(
            f"Unsupported window: {window}. "
            f"Allowed: {sorted(MONITORING_WINDOWS)}"
        )
    return window


def _scalar(result):
    """
    Extract the actual metric value from:

    [
        {
            "metric": {},
            "value": [timestamp, "123"]
        }
    ]
    """

    try:
        if not result:
            return None

        return float(
            result[0]["value"][1]
        )

    except (
        TypeError,
        KeyError,
        IndexError,
        ValueError,
    ):
        return None

# 1. DEPENDENCY / SCRAPE HEALTH
@mcp.tool()
async def get_dependency_health() -> dict:
    """
    Check the health of services currently visible to Prometheus.

    Use when the user asks:
    - are monitoring dependencies healthy
    - which monitored service is down
    - are Prometheus targets reachable
    - is the telemetry stack healthy
    """

    query = """
    up
    """

    result = await query_prometheus(
        query
    )

    dependencies = []

    for item in result or []:

        labels = item.get(
            "metric",
            {},
        )

        try:
            value = float(
                item["value"][1]
            )
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ):
            value = None

        dependencies.append(
            {
                "job": labels.get(
                    "job",
                    "unknown",
                ),
                "instance": labels.get(
                    "instance",
                    "unknown",
                ),
                "healthy": value == 1,
            }
        )

    unhealthy = [
        item
        for item in dependencies
        if item["healthy"] is False
    ]

    return {
        "metric": "dependency_health",
        "status": (
            "healthy"
            if not unhealthy
            else "degraded"
        ),
        "targets": dependencies,
        "unhealthy_targets": unhealthy,
    }

# 2. ERROR BREAKDOWN
@mcp.tool()
async def get_error_breakdown(
    window: str = "5m",
) -> dict:
    """
    Break HTTP errors into 4xx and 5xx categories.

    Use when the user asks:
    - what kinds of errors are happening
    - are failures client or server errors
    - show me the error breakdown
    - how many 4xx and 5xx errors are occurring
    """

    window = _safe_window(
        window
    )

    client_query = f"""
    sum(
        rate(
            http_server_duration_milliseconds_count{{
                job="rag-api",
                http_status_code=~"4.."
            }}[{window}]
        )
    )
    """

    server_query = f"""
    sum(
        rate(
            http_server_duration_milliseconds_count{{
                job="rag-api",
                http_status_code=~"5.."
            }}[{window}]
        )
    )
    """

    client_result = await query_prometheus(
        client_query
    )

    server_result = await query_prometheus(
        server_query
    )

    client_rate = _scalar(
        client_result
    )

    server_rate = _scalar(
        server_result
    )

    return {
        "metric": "error_breakdown",
        "window": window,
        "unit": "errors_per_second",
        "client_4xx_rate": round(
            client_rate or 0,
            5,
        ),
        "server_5xx_rate": round(
            server_rate or 0,
            5,
        ),
    }


# 3. TIMEOUT COUNT
@mcp.tool()
async def get_timeout_count(
    window: str = "30m",
) -> dict:
    """
    Return the number of HTTP 504 timeout responses.

    Use when the user asks:
    - how many requests timed out
    - were there request timeouts
    - how many gateway timeout responses occurred

    Note:
    This measures HTTP 504 responses. Internal LLM/retrieval
    timeouts should later be instrumented separately.
    """

    window = _safe_window(
        window
    )

    query = f"""
    round(
        sum(
            increase(
                http_server_duration_milliseconds_count{{
                    job="rag-api",
                    http_status_code="504"
                }}[{window}]
            )
        )
    )
    """

    result = await query_prometheus(
        query
    )

    value = _scalar(
        result
    )

    return {
        "metric": "request_timeouts",
        "window": window,
        "unit": "timeouts",
        "count": int(
            round(value or 0)
        ),
    }

# 4. CONTAINER RESTART DETECTION
@mcp.tool()
async def get_container_restart_count(
    window: str = "1h",
) -> dict:
    """
    Estimate whether the RAG backend container restarted.

    Uses changes in the container start-time metric.

    Use when the user asks:
    - did the backend restart
    - how many container restarts occurred
    - has the RAG backend been unstable
    """

    window = _safe_window(
        window
    )

    query = f"""
    sum(
        changes(
            container_start_time_seconds{{
                container_label_com_docker_compose_service="rag-backend"
            }}[{window}]
        )
    )
    """

    result = await query_prometheus(
        query
    )

    value = _scalar(
        result
    )

    return {
        "metric": "rag_backend_restarts",
        "window": window,
        "unit": "restarts",
        "count": int(
            round(value or 0)
        ),
    }

# 5. REQUEST SUCCESS SLO
@mcp.tool()
async def get_request_success_slo(
    window: str = "30m",
    target_percent: float = 99.0,
) -> dict:
    """
    Check whether RAG request success meets the configured SLO.

    Default SLO:
        99% successful requests.

    Use when the user asks:
    - are we meeting our availability SLO
    - what is request success percentage
    - is reliability within target
    """

    window = _safe_window(
        window
    )

    query = f"""
    100 *
    (
        1 -
        (
            (
                sum(
                    rate(
                        rag_errors_total[{window}]
                    )
                )
                or vector(0)
            )
            /
            clamp_min(
                sum(
                    rate(
                        rag_requests_total[{window}]
                    )
                ),
                0.000001
            )
        )
    )
    """

    result = await query_prometheus(
        query
    )

    success_rate = _scalar(
        result
    )

    if success_rate is None:
        return {
            "metric": "request_success_slo",
            "window": window,
            "error": "No success-rate data available.",
        }

    success_rate = round(
        success_rate,
        2,
    )

    return {
        "metric": "request_success_slo",
        "window": window,
        "target_percent": target_percent,
        "actual_percent": success_rate,
        "meeting_slo": (
            success_rate
            >= target_percent
        ),
        "difference_percentage_points": round(
            success_rate
            - target_percent,
            2,
        ),
    }


# 6. TOKEN USAGE
@mcp.tool()
async def get_token_usage(
    window: str = "30m",
) -> dict:
    """
    Return LLM token consumption over a recent period.

    Requires these counters from the RAG backend:
    - rag_llm_prompt_tokens_total
    - rag_llm_completion_tokens_total
    - rag_llm_tokens_total
    """

    window = _safe_window(
        window
    )

    prompt_query = f"""
    sum(
        increase(
            rag_llm_prompt_tokens_total[{window}]
        )
    )
    """

    completion_query = f"""
    sum(
        increase(
            rag_llm_completion_tokens_total[{window}]
        )
    )
    """

    total_query = f"""
    sum(
        increase(
            rag_llm_tokens_total[{window}]
        )
    )
    """

    prompt_result = await query_prometheus(
        prompt_query
    )

    completion_result = await query_prometheus(
        completion_query
    )

    total_result = await query_prometheus(
        total_query
    )

    prompt = _scalar(
        prompt_result
    )

    completion = _scalar(
        completion_result
    )

    total = _scalar(
        total_result
    )

    return {
        "metric": "llm_token_usage",
        "window": window,
        "prompt_tokens": int(
            round(prompt or 0)
        ),
        "completion_tokens": int(
            round(completion or 0)
        ),
        "total_tokens": int(
            round(total or 0)
        ),
    }

@mcp.tool()
async def get_llm_cost() -> dict:
    """
    Return cumulative estimated LLM cost since the backend metric
    process started.
    """

    query = """
    sum(
        rag_llm_cost_usd_USD_total
    )
    """

    result = await query_prometheus(query)

    cost = _scalar(result)

    if cost is None:
        return {
            "metric": "llm_cost",
            "unit": "USD",
            "error": "No LLM cost data was returned by Prometheus.",
        }

    return {
        "metric": "llm_cost",
        "unit": "USD",
        "estimated_cost_usd": round(cost, 8),
        "formatted_cost": f"${cost:.8f}",
        "instruction": (
            "Report formatted_cost exactly. "
            "Do not round a non-zero cost to $0.00."
        ),
    }


@mcp.tool()
async def get_predictive_health_alerts(
    window: str = "5m",
) -> dict:
    """
    Perform an early-warning health assessment of the RAG backend.

    Checks:
    - CPU utilization %
    - CPU upward trend
    - Memory utilization %
    - Request error rate %
    - Request success SLO %
    - HTTP 504 timeouts
    - Backend container restarts

    Allowed windows:
    1m, 5m, 10m, 15m, 30m, 1h
    """

    window = _safe_window(window)

    # 1. CURRENT CPU UTILIZATION 

    cpu_query = """
    100 *
    sum(
        rate(
            container_cpu_usage_seconds_total{
                container_label_com_docker_compose_service="rag-backend"
            }[2m]
        )
    )
    """


    # 2. CPU BASELINE OVER LAST 15 MINUTES

    cpu_baseline_query = """
    avg_over_time(
        (
            100 *
            sum(
                rate(
                    container_cpu_usage_seconds_total{
                        container_label_com_docker_compose_service="rag-backend"
                    }[2m]
                )
            )
        )[15m:1m]
    )
    """

    
    # 3. MEMORY UTILIZATION 

    memory_percent_query = """
    100 *
    (
        max(
            container_memory_working_set_bytes{
                container_label_com_docker_compose_service="rag-backend",
                container!=""
            }
        )
        /
        clamp_min(
            max(
                container_spec_memory_limit_bytes{
                    container_label_com_docker_compose_service="rag-backend",
                    container!=""
                }
            ),
            1
        )
    )
    """

 
    # 4. CURRENT MEMORY USAGE IN GiB
 
    memory_usage_query = """
    max(
        container_memory_working_set_bytes{
            container_label_com_docker_compose_service="rag-backend",
            container!=""
        }
    )
    / 1024 / 1024 / 1024
    """

    # 5. CONFIGURED MEMORY LIMIT IN GiB

    memory_limit_query = """
    max(
        container_spec_memory_limit_bytes{
            container_label_com_docker_compose_service="rag-backend",
            container!=""
        }
    )
    / 1024 / 1024 / 1024
    """

    
    # 6. REQUEST ERROR RATE %
   
    error_rate_query = f"""
    100 *
    (
        sum(
            rate(
                rag_errors_total[{window}]
            )
        )
        /
        clamp_min(
            sum(
                rate(
                    rag_requests_total[{window}]
                )
            ),
            0.000001
        )
    )
    """

    # 7. REQUEST SUCCESS RATE %

    success_rate_query = f"""
    100 *
    (
        1 -
        (
            sum(
                rate(
                    rag_errors_total[{window}]
                )
            )
            /
            clamp_min(
                sum(
                    rate(
                        rag_requests_total[{window}]
                    )
                ),
                0.000001
            )
        )
    )
    """

    # 8. HTTP 504 TIMEOUTS

    timeout_query = f"""
    sum(
        increase(
            http_server_duration_milliseconds_count{{
                job="rag-api",
                http_status_code="504"
            }}[{window}]
        )
    )
    """

 
    # 9. BACKEND CONTAINER RESTARTS
    
    restart_query = f"""
    sum(
        changes(
            container_start_time_seconds{{
                container_label_com_docker_compose_service="rag-backend"
            }}[{window}]
        )
    )
    """

# EXECUTE PROMETHEUS QUERIES
    
    cpu_result = await query_prometheus(cpu_query)
    cpu_baseline_result = await query_prometheus(cpu_baseline_query)
    memory_percent_result = await query_prometheus(memory_percent_query)
    memory_usage_result = await query_prometheus(memory_usage_query)
    memory_limit_result = await query_prometheus(memory_limit_query)
    error_result = await query_prometheus( error_rate_query)
    success_result = await query_prometheus(success_rate_query)
    timeout_result = await query_prometheus(timeout_query)
    restart_result = await query_prometheus(restart_query)

    
    # EXTRACT SCALAR VALUES
    cpu = _scalar(cpu_result)
    cpu_baseline = _scalar(cpu_baseline_result)
    memory_percent = _scalar(memory_percent_result)
    memory_usage_gib = _scalar(memory_usage_result)
    memory_limit_gib = _scalar(memory_limit_result)
    error_rate = _scalar(error_result)
    success_rate = _scalar(success_result)
    timeouts = _scalar(timeout_result)
    restarts = _scalar(restart_result)

    # SAFE DEFAULTS
    cpu = cpu if cpu is not None else 0.0
    cpu_baseline = cpu_baseline if cpu_baseline is not None else 0.0
    memory_percent = memory_percent if memory_percent is not None else 0.0
    memory_usage_gib = memory_usage_gib if memory_usage_gib is not None else 0.0
    memory_limit_gib = memory_limit_gib if memory_limit_gib is not None else 0.0
    error_rate = error_rate if error_rate is not None else 0.0
    success_rate = success_rate if success_rate is not None else 100.0
    timeouts = timeouts if timeouts is not None else 0.0
    restarts = restarts if restarts is not None else 0.0
    cpu_change = cpu - cpu_baseline
    
    alerts = []
    # CPU UTILIZATION ALERTS
    # < 75%  healthy
    # 75-84% warning
    # 85-94% high warning
    # >=95% critical
  
    if cpu >= 95:
        alerts.append({
            "severity": "critical",
            "component": "rag-backend",
            "metric": "cpu_utilization",
            "value_percent": round(cpu, 2),
            "threshold_percent": 95,
            "message": (
                "CPU utilization is critically high "
                "and the backend is approaching saturation."
            ),
            "recommended_action": (
                "Scale the backend, increase CPU allocation, "
                "or investigate CPU-intensive requests immediately."
            ),
        })

    elif cpu >= 85:
        alerts.append({
            "severity": "warning",
            "component": "rag-backend",
            "metric": "cpu_utilization",
            "value_percent": round(cpu, 2),
            "threshold_percent": 85,
            "message": (
                "CPU utilization is high and approaching "
                "the critical saturation threshold."
            ),
            "recommended_action": (
                "Investigate backend workload and consider "
                "scaling before CPU reaches saturation."
            ),
        })

    elif cpu >= 75:
        alerts.append({
            "severity": "warning",
            "component": "rag-backend",
            "metric": "cpu_utilization",
            "value_percent": round(cpu, 2),
            "threshold_percent": 75,
            "message": (
                "CPU utilization is elevated."
            ),
            "recommended_action": (
                "Monitor CPU growth and investigate "
                "increasing workload."
            ),
        })

    # CPU TREND ALERT

    if (
        cpu >= 70
        and cpu_change >= 15
    ):

        alerts.append({
            "severity": "warning",
            "component": "rag-backend",
            "metric": "cpu_trend",

            "current_cpu_percent": round(
                cpu,
                2,
            ),

            "baseline_cpu_percent": round(
                cpu_baseline,
                2,
            ),

            "increase_percentage_points": round(
                cpu_change,
                2,
            ),

            "message": (
                "CPU utilization is rising rapidly compared "
                "with its recent 15-minute baseline."
            ),

            "recommended_action": (
                "Investigate workload growth before CPU "
                "reaches the saturation threshold."
            ),
        })

   
    # MEMORY TELEMETRY SANITY CHECK
    if memory_percent > 100:
        alerts.append({
            "severity": "warning",
            "component": "monitoring",
            "metric": "memory_telemetry",

            "value_percent": round(
                memory_percent,
                2,
            ),

            "memory_used_gib": round(
                memory_usage_gib,
                2,
            ),

            "memory_limit_gib": round(
                memory_limit_gib,
                2,
            ),

            "message": (
                "Calculated memory utilization exceeds 100%, "
                "which suggests a monitoring or metric "
                "aggregation problem."
            ),

            "recommended_action": (
                "Verify cAdvisor working-set and container "
                "memory-limit metrics before treating this "
                "as genuine memory saturation."
            ),
        })

   
    # MEMORY UTILIZATION ALERTS
    # < 75%  healthy
    # 75-84% warning
    # 85-94% high warning
    # >=95% critical
  
    elif memory_percent >= 95:
        alerts.append({
            "severity": "critical",
            "component": "rag-backend",
            "metric": "memory_utilization",

            "value_percent": round(
                memory_percent,
                2,
            ),

            "threshold_percent": 95,

            "memory_used_gib": round(
                memory_usage_gib,
                2,
            ),

            "memory_limit_gib": round(
                memory_limit_gib,
                2,
            ),

            "message": (
                "Memory utilization is critically high. "
                "The backend is approaching its configured "
                "memory limit and may be terminated by the OOM killer."
            ),

            "recommended_action": (
                "Investigate memory growth immediately. "
                "Check loaded models, caches, large objects, "
                "request accumulation, and possible memory leaks."
            ),
        })

    elif memory_percent >= 85:

        alerts.append({
            "severity": "warning",
            "component": "rag-backend",
            "metric": "memory_utilization",

            "value_percent": round(
                memory_percent,
                2,
            ),

            "threshold_percent": 85,

            "memory_used_gib": round(
                memory_usage_gib,
                2,
            ),

            "memory_limit_gib": round(
                memory_limit_gib,
                2,
            ),

            "message": (
                "Memory utilization is high and approaching "
                "the critical memory threshold."
            ),

            "recommended_action": (
                "Investigate memory consumption and consider "
                "increasing resources or reducing memory usage."
            ),
        })

    elif memory_percent >= 75:

        alerts.append({
            "severity": "warning",
            "component": "rag-backend",
            "metric": "memory_utilization",

            "value_percent": round(
                memory_percent,
                2,
            ),

            "threshold_percent": 75,

            "memory_used_gib": round(
                memory_usage_gib,
                2,
            ),

            "memory_limit_gib": round(
                memory_limit_gib,
                2,
            ),

            "message": (
                "Memory utilization is elevated."
            ),

            "recommended_action": (
                "Monitor memory growth and investigate "
                "large in-memory objects, model loading, "
                "caching, or increasing concurrent requests."
            ),
        })

    # ERROR RATE ALERTS
    if error_rate >= 5:
        alerts.append({
            "severity": "critical",
            "component": "rag-backend",
            "metric": "error_rate",

            "value_percent": round(
                error_rate,
                2,
            ),

            "threshold_percent": 5,

            "message": (
                "RAG request error rate is critically high."
            ),

            "recommended_action": (
                "Inspect recent errors and traces immediately."
            ),
        })

    elif error_rate >= 2:

        alerts.append({
            "severity": "warning",
            "component": "rag-backend",
            "metric": "error_rate",

            "value_percent": round(
                error_rate,
                2,
            ),

            "threshold_percent": 2,

            "message": (
                "RAG request error rate is elevated."
            ),

            "recommended_action": (
                "Investigate recent failures before "
                "availability degrades."
            ),
        })

    # REQUEST SUCCESS SLO
    if success_rate < 99:
        alerts.append({
            "severity": "critical",
            "component": "rag-backend",
            "metric": "request_success_slo",

            "value_percent": round(
                success_rate,
                2,
            ),

            "target_percent": 99,

            "message": (
                "The RAG service is violating its "
                "99% request-success SLO."
            ),

            "recommended_action": (
                "Investigate failed requests and affected "
                "dependencies immediately."
            ),
        })

    elif success_rate < 99.5:
        alerts.append({
            "severity": "warning",
            "component": "rag-backend",
            "metric": "request_success_slo",

            "value_percent": round(
                success_rate,
                2,
            ),

            "target_percent": 99,

            "message": (
                "Request success rate is approaching "
                "the 99% SLO boundary."
            ),

            "recommended_action": (
                "Investigate recent errors before "
                "the SLO is violated."
            ),
        })

    # TIMEOUT ALERTS
    if timeouts >= 5:
        alerts.append({
            "severity": "critical",
            "component": "rag-backend",
            "metric": "http_504_timeouts",

            "count": int(
                timeouts
            ),

            "message": (
                "Multiple HTTP 504 request timeouts "
                "were detected."
            ),

            "recommended_action": (
                "Inspect retrieval latency, LLM latency, "
                "dependencies, CPU, and memory pressure."
            ),
        })

    elif timeouts >= 1:

        alerts.append({
            "severity": "warning",
            "component": "rag-backend",
            "metric": "http_504_timeouts",

            "count": int(
                timeouts
            ),

            "message": (
                "At least one HTTP 504 timeout was detected."
            ),

            "recommended_action": (
                "Inspect the associated trace before "
                "timeout frequency increases."
            ),
        })

    # CONTAINER RESTART ALERTS
    if restarts >= 3:
        alerts.append({
            "severity": "critical",
            "component": "rag-backend",
            "metric": "container_restarts",

            "count": int(
                restarts
            ),

            "message": (
                "Repeated backend container restarts "
                "indicate service instability."
            ),

            "recommended_action": (
                "Inspect container logs, memory pressure, "
                "OOM events, CPU pressure, and application crashes."
            ),
        })

    elif restarts >= 1:

        alerts.append({
            "severity": "warning",
            "component": "rag-backend",
            "metric": "container_restarts",

            "count": int(
                restarts
            ),

            "message": (
                "The backend container restarted recently."
            ),

            "recommended_action": (
                "Inspect the backend container logs and "
                "determine why the process restarted."
            ),
        })

    # DETERMINE OVERALL STATUS
    has_critical = any(
        alert["severity"] == "critical"
        for alert in alerts
    )

    has_warning = any(
        alert["severity"] == "warning"
        for alert in alerts
    )

    if has_critical:
        status = "critical"

    elif has_warning:
        status = "warning"

    else:
        status = "healthy"

    # RETURN RESULT TO OBSERVABILITY AGENT
    return {
        "metric": "predictive_health_alerts",
        "window": window,
        "status": status,
        "alert_count": len(
            alerts
        ),

        "current_state": {
            "cpu_percent": round(
                cpu,
                2,
            ),

            "cpu_15m_baseline_percent": round(
                cpu_baseline,
                2,
            ),

            "cpu_change_percentage_points": round(
                cpu_change,
                2,
            ),

            "memory_percent": round(
                memory_percent,
                2,
            ),

            "memory_used_gib": round(
                memory_usage_gib,
                2,
            ),

            "memory_limit_gib": round(
                memory_limit_gib,
                2,
            ),

            "error_rate_percent": round(
                error_rate,
                2,
            ),

            "success_rate_percent": round(
                success_rate,
                2,
            ),

            "timeouts": int(
                timeouts
            ),

            "backend_restarts": int(
                restarts
            ),
        },

        "thresholds": {

            "cpu": {
                "warning_percent": 75,
                "high_warning_percent": 85,
                "critical_percent": 95,
            },

            "memory": {
                "warning_percent": 75,
                "high_warning_percent": 85,
                "critical_percent": 95,
            },

            "error_rate": {
                "warning_percent": 2,
                "critical_percent": 5,
            },

            "success_slo_percent": 99,

            "timeouts": {
                "warning": 1,
                "critical": 5,
            },

            "restarts": {
                "warning": 1,
                "critical": 3,
            },
        },

        "alerts": alerts,

        "instruction": (
            "Perform an early-warning health assessment. "
            "Report CPU and memory as percentages. "
            "For memory also report used GiB and configured "
            "memory limit GiB. "
            "Clearly state whether the system is healthy, "
            "warning, or critical. "
            "For each alert report the current value, "
            "threshold, likely risk, and recommended action. "
            "If memory utilization exceeds 100%, treat this "
            "as a monitoring or telemetry anomaly rather than "
            "claiming that the container is genuinely using "
            "more than its enforced memory limit. "
            "Do not state that system failure is guaranteed."
        ),
    }


@mcp.tool()
async def get_active_alerts() -> dict:
    """
    Get all currently pending or firing Prometheus alerts.

    Use this tool whenever the user asks:
    - whether any alerts are active
    - whether an alert has fired
    - what alerts are currently firing
    - alert severity
    - affected service
    - alert start time
    - alert metric value
    - alert descriptions

    This tool queries Prometheus /api/v1/alerts directly and should be
    treated as the authoritative source for current alert state.
    """

    alerts = await get_prometheus_alerts()

    normalized_alerts = []

    for alert in alerts:

        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        normalized_alerts.append(
            {
                "alert_name": labels.get("alertname"),
                "state": alert.get("state"),
                "severity": labels.get("severity"),
                "service": labels.get("service"),
                "category": labels.get("category"),
                "active_since": alert.get("activeAt"),
                "current_value": alert.get("value"),
                "summary": annotations.get("summary"),
                "description": annotations.get("description"),
                "labels": labels,
            }
        )

    firing = [
        alert
        for alert in normalized_alerts
        if alert["state"] == "firing"
    ]

    pending = [
        alert
        for alert in normalized_alerts
        if alert["state"] == "pending"
    ]

    return {
        "total_alerts": len(normalized_alerts),
        "firing_count": len(firing),
        "pending_count": len(pending),
        "has_firing_alerts": len(firing) > 0,
        "firing_alerts": firing,
        "pending_alerts": pending,
        "all_alerts": normalized_alerts,
    }

@mcp.tool()
async def get_alert_by_name(
    alert_name: str,
) -> dict:
    """
    Get the current state and details of a specific Prometheus alert.

    Example alert names:
    - RAGBackendHighCPU
    - RAGBackendHighMemory
    - RAGHighErrorRate
    - RAGRequestSuccessSLOBreach
    """

    alerts = await get_prometheus_alerts()

    matches = []

    for alert in alerts:

        labels = alert.get("labels", {})

        if labels.get("alertname") != alert_name:
            continue

        annotations = alert.get(
            "annotations",
            {},
        )

        matches.append(
            {
                "alert_name":
                    labels.get("alertname"),

                "state":
                    alert.get("state"),

                "severity":
                    labels.get("severity"),

                "service":
                    labels.get("service"),

                "category":
                    labels.get("category"),

                "active_since":
                    alert.get("activeAt"),

                "current_value":
                    alert.get("value"),

                "summary":
                    annotations.get("summary"),

                "description":
                    annotations.get("description"),

                "labels":
                    labels,
            }
        )


    return {
        "alert_name": alert_name,
        "found": len(matches) > 0,
        "count": len(matches),
        "alerts": matches,
    }
@mcp.tool()
async def get_alert_summary() -> dict:
    """
    Return a concise summary of current Prometheus alert status.

    Use for questions such as:
    - Are there any alerts?
    - Is the system alerting?
    - What alerts are firing?
    """

    alerts = await get_prometheus_alerts()

    firing = []
    pending = []

    for alert in alerts:

        labels = alert.get("labels", {})

        item = {
            "alert_name":
                labels.get("alertname"),

            "severity":
                labels.get("severity"),

            "service":
                labels.get("service"),

            "state":
                alert.get("state"),

            "active_since":
                alert.get("activeAt"),

            "current_value":
                alert.get("value"),
        }

        if alert.get("state") == "firing":
            firing.append(item)

        elif alert.get("state") == "pending":
            pending.append(item)


    if firing:

        overall_status = "ALERTING"

    elif pending:

        overall_status = "WARNING"

    else:

        overall_status = "HEALTHY"


    return {
        "overall_status":
            overall_status,

        "firing_count":
            len(firing),

        "pending_count":
            len(pending),

        "firing_alerts":
            firing,

        "pending_alerts":
            pending,
    }


# ONLINE RAG QUALITY / RAGAS METRICS
@mcp.tool()
async def get_rag_faithfulness() -> dict:
    """
    Return the current average online RAG faithfulness score measured by RAGAS.

    Use this tool when the user asks whether generated RAG answers are grounded
    in, supported by, or faithful to the retrieved context.

    Typical user questions:
    - "What is the faithfulness score?"
    - "How faithful are the RAG answers?"
    - "Are the generated answers grounded in the retrieved documents?"
    - "Is the model making unsupported claims?"
    - "How well are answers supported by retrieval?"
    - "What is the current RAGAS faithfulness metric?"

    Interpretation:
    - Usually between 0 and 1.
    - Higher is better.
    - Values near 1 indicate that generated claims are strongly supported by
      retrieved context.
    - Lower values suggest more unsupported generation.

    Do NOT use this tool for answer relevancy, context utilization, latency,
    CPU, memory, request rate, or application errors.
    """

    query = """
    sum(rag_quality_faithfulness_sum)
    /
    sum(rag_quality_faithfulness_count)
    """

    return await query_prometheus(query)


@mcp.tool()
async def get_rag_answer_relevancy() -> dict:
    """
    Return the current average online RAG answer relevancy score measured by RAGAS.

    Use this tool when the user asks whether generated answers directly address
    user questions, stay on topic, or align with the user's intent.

    Typical user questions:
    - "What is the answer relevancy score?"
    - "How relevant are the RAG answers?"
    - "Are responses staying on topic?"
    - "Does the RAG answer users' questions directly?"
    - "How well are responses aligned with user intent?"

    Interpretation:
    - Usually between 0 and 1.
    - Higher is better.
    - Values near 1 indicate strong alignment between the user question and
      generated answer.
    - Lower values may indicate off-topic, incomplete, or poorly focused answers.

    Do NOT use this tool for faithfulness, context utilization, infrastructure
    health, latency, CPU, memory, or request failures.
    """

    query = """
    sum(rag_quality_answer_relevancy_sum)
    /
    sum(rag_quality_answer_relevancy_count)
    """

    return await query_prometheus(query)


@mcp.tool()
async def get_rag_context_utilization() -> dict:
    """
    Return the current average online RAG context-utilization score measured by RAGAS.

    Use this tool when the user asks how effectively retrieved context is being
    used by the generator or whether retrieved chunks contribute to the answer.

    Typical user questions:
    - "What is the context utilization score?"
    - "Is the LLM using the retrieved context?"
    - "How effectively is retrieved context being used?"
    - "Are retrieved chunks contributing to the answer?"
    - "Is the generator ignoring the retrieved documents?"

    Interpretation:
    - Usually between 0 and 1.
    - Higher is better.
    - Values near 1 indicate that retrieved context is highly useful for
      generating the answer.
    - Lower values may indicate irrelevant retrieval, noisy context, excessive
      context, or weak use of retrieved information.

    This metric is different from offline retrieval precision and retrieval recall.

    Do NOT use this tool for answer faithfulness, latency, CPU, memory,
    application errors, or request rate.
    """

    query = """
    sum(rag_quality_context_utilization_sum)
    /
    sum(rag_quality_context_utilization_count)
    """

    return await query_prometheus(query)


@mcp.tool()
async def get_rag_groundedness() -> dict:
    """
    Return the current average online groundedness score for generated RAG answers.

    Use this tool when the user explicitly asks about groundedness or whether
    answers are supported by retrieved evidence.

    Typical user questions:
    - "What is the groundedness score?"
    - "How grounded are the RAG answers?"
    - "Are responses grounded in retrieved documents?"
    - "How well are responses supported by source context?"

    IMPORTANT:
    In the current implementation, groundedness is a proxy derived directly
    from the RAGAS faithfulness score.

        groundedness = faithfulness

    It is not currently an independently evaluated metric.

    Interpretation:
    - Usually between 0 and 1.
    - Higher is better.
    - Values near 1 indicate stronger grounding in retrieved context.

    Do NOT use this tool for answer relevancy, latency, CPU, memory,
    request rate, or application errors.
    """

    query = """
    sum(rag_quality_groundedness_sum)
    /
    sum(rag_quality_groundedness_count)
    """

    return await query_prometheus(query)


@mcp.tool()
async def get_rag_hallucination_rate() -> dict:
    """
    Return the current average online hallucination-rate proxy for the RAG system.

    Use this tool when the user asks whether the model is hallucinating,
    generating unsupported information, or producing claims not grounded in
    retrieved context.

    Typical user questions:
    - "What is the hallucination rate?"
    - "Is the RAG hallucinating?"
    - "How much unsupported content is the model producing?"
    - "Are generated answers making unsupported claims?"
    - "How frequently are answers ungrounded?"

    IMPORTANT:
    This is currently a proxy derived from faithfulness:

        hallucination_rate = 1 - faithfulness

    It is not an independent factual-hallucination detector.

    Interpretation:
    - Usually between 0 and 1.
    - Lower is better.
    - 0 indicates no hallucination according to this proxy.
    - Higher values indicate greater evidence of unsupported generation.

    Do NOT use this tool for latency, CPU, memory, traffic, or answer relevancy.
    """

    query = """
    sum(rag_quality_hallucination_rate_sum)
    /
    sum(rag_quality_hallucination_rate_count)
    """

    return await query_prometheus(query)


@mcp.tool()
async def get_rag_quality_evaluation_count() -> dict:
    """
    Return the number of online RAG queries that have actually been evaluated
    by the RAGAS quality-monitoring pipeline.

    Use this tool when the user asks:
    - "How many queries have been evaluated?"
    - "How many RAGAS evaluations have run?"
    - "How many samples are the quality scores based on?"
    - "What is the sample size for the online quality metrics?"
    - "Has online quality evaluation run yet?"

    IMPORTANT:
    This is NOT necessarily the total number of RAG queries.

    Online evaluation may be sampled. For example, if
    QUALITY_EVAL_SAMPLE_RATE=0.10, only approximately 10 percent of queries are
    expected to be evaluated.

    Use this tool when discussing confidence in the current quality averages.

    Do NOT use this tool for total RAG traffic or request volume.
    """

    query = """
    sum(rag_quality_faithfulness_count)
    """

    return await query_prometheus(query)


@mcp.tool()
async def get_rag_quality_summary() -> dict:
    """
    Return a combined summary of the primary online RAG quality metrics.

    Use this tool when the user asks a broad question about overall RAG quality.

    Typical user questions:
    - "How is the RAG quality?"
    - "Give me the current RAGAS metrics."
    - "Show me the online quality metrics."
    - "How is the RAG performing from a quality perspective?"
    - "Is the RAG producing good answers?"
    - "Give me a quality summary."
    - "What are the faithfulness, relevancy, and hallucination scores?"
    - "Summarize the online RAG evaluation."

    Returns results for:
    - faithfulness
    - answer relevancy
    - context utilization
    - groundedness proxy
    - hallucination-rate proxy
    - evaluation count

    Interpretation:
    - faithfulness: higher is better
    - answer relevancy: higher is better
    - context utilization: higher is better
    - groundedness: higher is better
    - hallucination rate: lower is better
    - evaluation count: number of evaluated samples

    IMPORTANT:
        groundedness = faithfulness
        hallucination_rate = 1 - faithfulness

    Prefer this tool for broad quality questions instead of calling all
    individual quality tools separately.

    Do NOT use this tool for CPU, memory, latency, infrastructure health,
    request rate, or application errors.
    """

    queries = {
        "faithfulness": """
            sum(rag_quality_faithfulness_sum)
            /
            sum(rag_quality_faithfulness_count)
        """,

        "answer_relevancy": """
            sum(rag_quality_answer_relevancy_sum)
            /
            sum(rag_quality_answer_relevancy_count)
        """,

        "context_utilization": """
            sum(rag_quality_context_utilization_sum)
            /
            sum(rag_quality_context_utilization_count)
        """,

        "groundedness": """
            sum(rag_quality_groundedness_sum)
            /
            sum(rag_quality_groundedness_count)
        """,

        "hallucination_rate": """
            sum(rag_quality_hallucination_rate_sum)
            /
            sum(rag_quality_hallucination_rate_count)
        """,

        "evaluation_count": """
            sum(rag_quality_faithfulness_count)
        """,
    }

    results = {}

    for name, query in queries.items():
        results[name] = await query_prometheus(query)

    return results


@mcp.tool()
async def get_cluster_node_count():
    """
    Return the total number of Kubernetes nodes currently known to
    kube-state-metrics.

    Use this tool when the user asks questions such as:
    - How many nodes are in the Kubernetes cluster?
    - What is the cluster node count?
    - How many worker/control-plane machines are being monitored?

    This tool measures Kubernetes node inventory using kube_node_info.
    It does not count pods, containers, virtual machines outside the
    Kubernetes cluster, or application replicas.

    Returns:
        The total number of Kubernetes nodes visible to Prometheus.
    """

    query = """
    count(kube_node_info)
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_node_cpu_utilization():
    """
    Return CPU utilization percentage for every Kubernetes node.

    Use this tool when the user asks:
    - What is the CPU utilization of the nodes?
    - Which Kubernetes node is using the most CPU?
    - Is worker-node-1 CPU overloaded?
    - Show node CPU usage.

    CPU utilization is calculated from node-exporter CPU counters as
    100 minus the percentage of CPU time spent idle during the last
    five minutes.

    The result includes the node-exporter instance and operating-system
    node name when available.

    Values are percentages where approximately:
        0   = almost completely idle
        100 = fully utilized CPU capacity

    Do not use this tool for pod or container CPU utilization.
    """

    query = """
    (
      100 *
      (
        1 -
        avg by (instance) (
          rate(node_cpu_seconds_total{mode="idle"}[5m])
        )
      )
    )
    * on(instance) group_left(nodename)
      node_uname_info
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_node_memory_utilization():
    """
    Return memory utilization percentage for every Kubernetes node.

    Use this tool when the user asks:
    - How much memory are the cluster nodes using?
    - Which node has the highest memory usage?
    - What is worker-node memory utilization?
    - Are any nodes running low on available memory?

    Utilization is calculated from total physical memory and Linux
    MemAvailable reported by node-exporter.

    A higher percentage indicates that more node memory is currently
    unavailable for additional workloads.

    This measures machine-level memory usage, not individual pod,
    container, or namespace memory consumption.
    """

    query = """
    (
      100 *
      (
        1 -
        (
          node_memory_MemAvailable_bytes
          /
          node_memory_MemTotal_bytes
        )
      )
    )
    * on(instance) group_left(nodename)
      node_uname_info
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_node_disk_utilization():
    """
    Return filesystem utilization percentage for disks mounted on
    Kubernetes nodes.

    Use this tool when the user asks:
    - How full are the node disks?
    - Which Kubernetes node is running out of disk space?
    - What is disk utilization on the cluster nodes?
    - Which filesystem has the highest utilization?

    The tool calculates used filesystem capacity from node-exporter
    filesystem size and available-space metrics.

    Temporary, virtual, container overlay, and other non-persistent
    pseudo filesystems are excluded to reduce noise.

    Results may contain multiple filesystems or mount points per node.
    """

    query = """
    (
      100 *
      (
        1 -
        (
          node_filesystem_avail_bytes{
            fstype!~"tmpfs|overlay|squashfs|proc|sysfs|devtmpfs"
          }
          /
          node_filesystem_size_bytes{
            fstype!~"tmpfs|overlay|squashfs|proc|sysfs|devtmpfs"
          }
        )
      )
    )
    * on(instance) group_left(nodename)
      node_uname_info
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_node_network_io():
    """
    Return network receive and transmit throughput for Kubernetes nodes.

    Use this tool when the user asks:
    - What is node network traffic?
    - How much data are the nodes receiving or transmitting?
    - Which node has the highest network I/O?
    - Is Kubernetes generating heavy network traffic?

    Network traffic is calculated from node-exporter byte counters over
    the previous five minutes.

    Results are measured in bytes per second and include a direction
    label identifying receive or transmit traffic.

    Loopback interfaces are excluded.
    """

    query = """
    (
      label_replace(
        sum by(instance, device) (
          rate(node_network_receive_bytes_total{device!="lo"}[5m])
        ),
        "direction", "receive", "device", ".*"
      )
      * on(instance) group_left(nodename)
        node_uname_info
    )
    or
    (
      label_replace(
        sum by(instance, device) (
          rate(node_network_transmit_bytes_total{device!="lo"}[5m])
        ),
        "direction", "transmit", "device", ".*"
      )
      * on(instance) group_left(nodename)
        node_uname_info
    )
    """

    return await query_prometheus(query)


@mcp.tool()
async def get_node_load_average():
    """
    Return Linux load averages for every Kubernetes node.

    Use this tool when the user asks:
    - What is the load average of the nodes?
    - Are any Kubernetes nodes heavily loaded?
    - Show 1-minute, 5-minute, and 15-minute node load.
    - Is worker-node system load increasing?

    The tool returns Linux system load averages from node-exporter for
    1-minute, 5-minute, and 15-minute periods.

    Load average represents runnable or uninterruptible processes and
    should be interpreted relative to the number of CPU cores available
    on the node.
    """

    query = """
    (
      label_replace(node_load1, "period", "1m", "instance", ".*")
      * on(instance) group_left(nodename)
        node_uname_info
    )
    or
    (
      label_replace(node_load5, "period", "5m", "instance", ".*")
      * on(instance) group_left(nodename)
        node_uname_info
    )
    or
    (
      label_replace(node_load15, "period", "15m", "instance", ".*")
      * on(instance) group_left(nodename)
        node_uname_info
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_node_status():
    """
    Return important Kubernetes node health conditions.

    Use this tool when the user asks:
    - Are all Kubernetes nodes healthy?
    - Which nodes are Ready?
    - Is any node experiencing pressure?
    - What is the health status of the cluster nodes?

    The tool reports Kubernetes conditions including Ready,
    MemoryPressure, DiskPressure, PIDPressure, and NetworkUnavailable.

    Important interpretation:
    - Ready=true is healthy.
    - MemoryPressure=true indicates a problem.
    - DiskPressure=true indicates a problem.
    - PIDPressure=true indicates a problem.
    - NetworkUnavailable=true indicates a networking problem.

    Use this for Kubernetes node health rather than CPU or memory usage.
    """

    query = """
    kube_node_status_condition{
      condition=~"Ready|MemoryPressure|DiskPressure|PIDPressure|NetworkUnavailable",
      status="true"
    } == 1
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_pod_count_by_namespace():
    """
    Return the number of Kubernetes pods in every namespace.

    Use this tool when the user asks:
    - How many pods are running in each namespace?
    - How many pods exist in the rag namespace?
    - Which namespace has the most pods?
    - What is the pod distribution across the cluster?

    This tool counts pod objects known to kube-state-metrics and groups
    the results by Kubernetes namespace.

    It does not measure CPU, memory, container count, or replica health.
    """

    query = """
    count by(namespace) (
      kube_pod_info
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_pod_cpu_utilization():
    """
    Return current CPU consumption for Kubernetes pods.

    Use this tool when the user asks:
    - Which pod is using the most CPU?
    - What is CPU usage of the RAG backend pod?
    - Show CPU consumption for Kubernetes pods.
    - Are any pods consuming excessive CPU?

    CPU usage is calculated from cAdvisor container CPU counters over
    the previous five minutes and aggregated by namespace and pod.

    Values are expressed in CPU cores:
    - 1.0 means approximately one full CPU core.
    - 0.5 means approximately half of one CPU core.

    Infrastructure sandbox/POD containers are excluded.
    """

    query = """
    sum by(namespace, pod) (
      rate(
        container_cpu_usage_seconds_total{
          container!="",
          container!="POD",
          pod!=""
        }[5m]
      )
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_pod_memory_utilization():
    """
    Return current working-set memory usage for Kubernetes pods.

    Use this tool when the user asks:
    - Which pod is using the most memory?
    - How much memory is the RAG backend consuming?
    - Show Kubernetes pod memory usage.
    - Are any pods consuming excessive memory?

    The tool sums container working-set memory for each pod.

    Results are returned in bytes and grouped by namespace and pod.
    Working-set memory is preferred for operational monitoring because
    it excludes much of the easily reclaimable cache.

    This is pod-level memory consumption, not node memory utilization.
    """

    query = """
    sum by(namespace, pod) (
      container_memory_working_set_bytes{
        container!="",
        container!="POD",
        pod!=""
      }
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_pod_restart_count():
    """
    Return cumulative container restart counts aggregated by Kubernetes pod.

    Use this tool when the user asks:
    - Which pods have restarted?
    - How many times has a pod restarted?
    - Are there unstable pods in the cluster?
    - Which pod has the highest restart count?

    Restart counts come from kube-state-metrics and are summed across
    all containers belonging to each pod.

    A high or increasing restart count may indicate application crashes,
    failed health probes, OOM kills, configuration failures, or other
    workload instability.

    Results are sorted from highest restart count to lowest.
    """

    query = """
    sort_desc(
      sum by(namespace, pod) (
        kube_pod_container_status_restarts_total
      )
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_unhealthy_pods():
    """
    Identify Kubernetes pods that are not currently healthy.

    Use this tool when the user asks:
    - Are there unhealthy pods?
    - Which pods are having problems?
    - Is every workload healthy?
    - Show pods that require investigation.

    The tool identifies pods in Pending, Failed, or Unknown phases and
    pods whose Kubernetes Ready condition is false.

    This is a broad pod-health tool. For specific failure states such as
    CrashLoopBackOff, Pending, or Failed, use the dedicated tools when
    the user's question specifically mentions those conditions.
    """

    query = """
    (
      max by(namespace, pod, phase) (
        kube_pod_status_phase{
          phase=~"Pending|Failed|Unknown"
        } == 1
      )
    )
    or
    (
      max by(namespace, pod) (
        kube_pod_status_ready{
          condition="false"
        } == 1
      )
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_crashlooping_pods():
    """
    Identify containers and pods currently in CrashLoopBackOff.

    Use this tool when the user asks:
    - Are any pods crash looping?
    - Which containers are in CrashLoopBackOff?
    - Why does Kubernetes keep restarting a workload?
    - Show repeatedly crashing pods.

    CrashLoopBackOff means Kubernetes is repeatedly attempting to restart
    a container that continues to terminate unsuccessfully.

    The result identifies the namespace, pod, container, and waiting
    reason for each currently crash-looping workload.
    """

    query = """
    kube_pod_container_status_waiting_reason{
      reason="CrashLoopBackOff"
    } == 1
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_pending_pods():
    """
    Return Kubernetes pods currently in the Pending phase.

    Use this tool when the user asks:
    - Are any pods pending?
    - Which pods cannot be scheduled or started?
    - Are workloads waiting for cluster resources?
    - Show pending Kubernetes workloads.

    A Pending pod has been accepted by Kubernetes but one or more
    containers have not yet started. Causes may include scheduling,
    image pulls, insufficient resources, storage, or initialization.

    This tool identifies the namespace and pod currently reporting the
    Pending phase.
    """

    query = """
    kube_pod_status_phase{
      phase="Pending"
    } == 1
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_failed_pods():
    """
    Return Kubernetes pods currently in the Failed phase.

    Use this tool when the user asks:
    - Are there failed pods?
    - Which Kubernetes workloads have failed?
    - Did any pod terminate unsuccessfully?
    - Show failed workloads in the cluster.

    A Failed pod indicates that all containers terminated and at least
    one terminated unsuccessfully or the pod otherwise could not
    complete successfully.

    Results include namespace and pod labels supplied by
    kube-state-metrics.
    """

    query = """
    kube_pod_status_phase{
      phase="Failed"
    } == 1
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_container_cpu_utilization():
    """
    Return CPU consumption for individual Kubernetes containers.

    Use this tool when the user asks:
    - Which container uses the most CPU?
    - What is CPU usage for a specific container?
    - Is one container causing high pod CPU?
    - Compare CPU usage between containers.

    CPU usage is calculated over the previous five minutes from cAdvisor
    CPU counters and returned in CPU cores.

    Results are grouped by namespace, pod, and container.

    Use get_pod_cpu_utilization when the user wants total pod CPU rather
    than individual container CPU.
    """

    query = """
    sum by(namespace, pod, container) (
      rate(
        container_cpu_usage_seconds_total{
          container!="",
          container!="POD",
          pod!=""
        }[5m]
      )
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_container_memory_utilization():
    """
    Return working-set memory consumption for individual Kubernetes containers.

    Use this tool when the user asks:
    - Which container consumes the most memory?
    - How much memory does a particular container use?
    - Which container is responsible for high pod memory?
    - Compare memory consumption between containers.

    Results are returned in bytes and grouped by namespace, pod, and
    container.

    Sandbox/POD containers are excluded.

    Use get_pod_memory_utilization when the user requests aggregated
    memory consumption for an entire pod.
    """

    query = """
    sum by(namespace, pod, container) (
      container_memory_working_set_bytes{
        container!="",
        container!="POD",
        pod!=""
      }
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_namespace_cpu_utilization():
    """
    Return total CPU consumption grouped by Kubernetes namespace.

    Use this tool when the user asks:
    - Which namespace uses the most CPU?
    - How much CPU is the rag namespace consuming?
    - Compare CPU usage across namespaces.
    - What is namespace-level CPU consumption?

    CPU usage is calculated from cAdvisor metrics over the previous five
    minutes and aggregated across all non-infrastructure containers.

    Values are expressed in CPU cores.

    This tool is useful for understanding resource consumption at the
    Kubernetes namespace or application-domain level.
    """

    query = """
    sum by(namespace) (
      rate(
        container_cpu_usage_seconds_total{
          container!="",
          container!="POD",
          namespace!=""
        }[5m]
      )
    )
    """

    return await query_prometheus(query)


@mcp.tool()
async def get_namespace_memory_utilization():
    """
    Return total working-set memory consumption grouped by Kubernetes namespace.

    Use this tool when the user asks:
    - Which namespace uses the most memory?
    - How much memory is the rag namespace using?
    - Compare namespace memory consumption.
    - What is cluster memory usage by namespace?

    Container working-set memory is summed across all workload containers
    belonging to each namespace.

    Results are measured in bytes.

    This measures actual namespace workload memory consumption rather
    than configured memory requests or limits.
    """

    query = """
    sum by(namespace) (
      container_memory_working_set_bytes{
        container!="",
        container!="POD",
        namespace!=""
      }
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_deployment_replica_status():
    """
    Return desired, ready, available, and unavailable replica counts for
    Kubernetes Deployments.

    Use this tool when the user asks:
    - Are all deployments healthy?
    - Does every deployment have the expected replicas?
    - Which deployment has unavailable replicas?
    - Is the RAG backend deployment fully available?

    Each result contains a replica_state label identifying whether the
    value represents desired, ready, available, or unavailable replicas.

    A healthy deployment normally has desired, ready, and available
    replica counts aligned and zero unavailable replicas.
    """

    query = """
    label_replace(
      kube_deployment_spec_replicas,
      "replica_state", "desired", "deployment", ".*"
    )
    or
    label_replace(
      kube_deployment_status_replicas_ready,
      "replica_state", "ready", "deployment", ".*"
    )
    or
    label_replace(
      kube_deployment_status_replicas_available,
      "replica_state", "available", "deployment", ".*"
    )
    or
    label_replace(
      kube_deployment_status_replicas_unavailable,
      "replica_state", "unavailable", "deployment", ".*"
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_daemonset_status():
    """
    Return scheduling and availability status for Kubernetes DaemonSets.

    Use this tool when the user asks:
    - Are all DaemonSets healthy?
    - Is kube-proxy running on every node?
    - Are node-level agents missing from any nodes?
    - How many desired and available DaemonSet pods exist?

    Results distinguish desired, ready, available, and unavailable
    DaemonSet instances using the daemonset_state label.

    Healthy DaemonSets generally have desired, ready, and available
    counts equal with zero unavailable instances.
    """

    query = """
    label_replace(
      kube_daemonset_status_desired_number_scheduled,
      "daemonset_state", "desired", "daemonset", ".*"
    )
    or
    label_replace(
      kube_daemonset_status_number_ready,
      "daemonset_state", "ready", "daemonset", ".*"
    )
    or
    label_replace(
      kube_daemonset_status_number_available,
      "daemonset_state", "available", "daemonset", ".*"
    )
    or
    label_replace(
      kube_daemonset_status_number_unavailable,
      "daemonset_state", "unavailable", "daemonset", ".*"
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_statefulset_status():
    """
    Return replica status for Kubernetes StatefulSets.

    Use this tool when the user asks:
    - Are all StatefulSets healthy?
    - Does a StatefulSet have all expected replicas?
    - Are StatefulSet replicas ready and updated?
    - Is a stateful workload degraded?

    The query reports desired, ready, current, and updated replica
    counts using the statefulset_state label.

    Comparing these values helps detect incomplete rollouts, unavailable
    replicas, and stateful workloads that have not converged to their
    desired state.
    """

    query = """
    label_replace(
      kube_statefulset_replicas,
      "statefulset_state", "desired", "statefulset", ".*"
    )
    or
    label_replace(
      kube_statefulset_status_replicas_ready,
      "statefulset_state", "ready", "statefulset", ".*"
    )
    or
    label_replace(
      kube_statefulset_status_replicas_current,
      "statefulset_state", "current", "statefulset", ".*"
    )
    or
    label_replace(
      kube_statefulset_status_replicas_updated,
      "statefulset_state", "updated", "statefulset", ".*"
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_service_endpoint_health():
    """
    Return Kubernetes endpoint availability and not-ready endpoint counts.

    Use this tool when the user asks:
    - Do Kubernetes Services have healthy endpoints?
    - Which service has no available backend endpoints?
    - Are service endpoints ready?
    - Can Kubernetes Services route traffic to workloads?

    The tool uses kube-state-metrics endpoint metrics and labels results
    as either available or not_ready.

    A service or endpoint object with zero available addresses or
    non-zero not-ready addresses may indicate failed readiness probes,
    missing pods, selector problems, or workload outages.

    This checks Kubernetes endpoint registration; it does not perform an
    external synthetic HTTP request.
    """

    query = """
    label_replace(
      kube_endpoint_address_available,
      "endpoint_state", "available", "endpoint", ".*"
    )
    or
    label_replace(
      kube_endpoint_address_not_ready,
      "endpoint_state", "not_ready", "endpoint", ".*"
    )
    """

    return await query_prometheus(query)


@mcp.tool()
async def get_unhealthy_prometheus_targets():
    """
    Return all Prometheus scrape targets that are currently DOWN.

    Use this tool when the user asks:
    - Are all Prometheus targets healthy?
    - Which monitoring endpoints are down?
    - Is Prometheus failing to scrape anything?
    - Which ServiceMonitor targets are unhealthy?
    - Is the monitoring system healthy?

    Prometheus exposes the synthetic 'up' metric for every scrape target.
    A value of 0 means the most recent scrape failed.

    This tool is one of the primary checks for monitoring coverage and
    endpoint availability.
    """

    query = """
    up == 0
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_active_alerts():
    """
    Return Prometheus alerts that are currently in the firing state.

    Use this tool when the user asks:
    - What alerts are firing?
    - Are there active cluster alerts?
    - Is Prometheus reporting any current problems?
    - What operational conditions require attention?

    This queries the Prometheus ALERTS time series and returns alerts
    whose alertstate is firing.

    Results may include infrastructure, Kubernetes, application, or
    custom RAG alerts depending on the rules loaded into Prometheus.

    Watchdog may intentionally remain continuously active depending on
    the kube-prometheus-stack configuration.
    """

    query = """
    ALERTS{
      alertstate="firing"
    } == 1
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_node_filesystem_pressure():
    """
    Identify Kubernetes nodes whose root filesystem utilization exceeds 85%.

    Use this tool when the user asks:
    - Are any node filesystems close to full?
    - Which nodes are experiencing filesystem capacity pressure?
    - Is root disk utilization dangerously high?
    - Which node should have disk space investigated?

    This is an operational filesystem-capacity check based on
    node-exporter metrics rather than the Kubernetes DiskPressure
    condition.

    A returned node has root filesystem utilization above 85 percent.
    Use get_node_disk_pressure for the Kubernetes kubelet DiskPressure
    condition.
    """

    query = """
    (
      100 *
      (
        1 -
        (
          node_filesystem_avail_bytes{
            mountpoint="/",
            fstype!~"tmpfs|overlay|squashfs"
          }
          /
          node_filesystem_size_bytes{
            mountpoint="/",
            fstype!~"tmpfs|overlay|squashfs"
          }
        )
      )
      > 85
    )
    * on(instance) group_left(nodename)
      node_uname_info
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_node_memory_pressure():
    """
    Return Kubernetes nodes currently reporting MemoryPressure.

    Use this tool when the user asks:
    - Are any nodes under memory pressure?
    - Is kubelet reporting insufficient available memory?
    - Which Kubernetes nodes have memory pressure?
    - Could memory pressure be affecting pod scheduling?

    MemoryPressure is an official Kubernetes node condition maintained
    by kubelet.

    Only nodes where MemoryPressure=true are returned.

    This differs from get_node_memory_utilization, which reports memory
    usage percentages even when Kubernetes has not declared pressure.
    """

    query = """
    kube_node_status_condition{
      condition="MemoryPressure",
      status="true"
    } == 1
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_node_disk_pressure():
    """
    Return Kubernetes nodes currently reporting DiskPressure.

    Use this tool when the user asks:
    - Are any Kubernetes nodes under disk pressure?
    - Is kubelet reporting insufficient disk capacity?
    - Which nodes have DiskPressure?
    - Could disk pressure be preventing pod scheduling?

    DiskPressure is an official Kubernetes node condition generated by
    kubelet when filesystem or image-storage resources become constrained.

    Only nodes where DiskPressure=true are returned.

    Use get_node_disk_utilization for detailed filesystem usage
    percentages.
    """

    query = """
    kube_node_status_condition{
      condition="DiskPressure",
      status="true"
    } == 1
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_node_network_pressure():
    """
    Identify Kubernetes nodes currently experiencing measurable network
    packet errors or drops.

    Use this tool when the user asks:
    - Are there network problems on any nodes?
    - Are nodes dropping packets?
    - Are network interfaces reporting errors?
    - Could network problems be affecting the cluster?

    Kubernetes does not expose a standard NetworkPressure node condition,
    so this tool defines operational network pressure as a non-zero rate
    of receive/transmit errors or packet drops during the previous five
    minutes.

    Loopback interfaces are excluded.

    Returned values represent errors/drops per second aggregated by node.
    """

    query = """
    (
      sum by(instance) (
        rate(node_network_receive_errs_total{device!="lo"}[5m])
        +
        rate(node_network_transmit_errs_total{device!="lo"}[5m])
        +
        rate(node_network_receive_drop_total{device!="lo"}[5m])
        +
        rate(node_network_transmit_drop_total{device!="lo"}[5m])
      )
      > 0
    )
    * on(instance) group_left(nodename)
      node_uname_info
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_cluster_cpu_utilization():
    """
    Return aggregate CPU utilization percentage across the Kubernetes cluster.

    Use this tool when the user asks:
    - What is total cluster CPU utilization?
    - How busy is the Kubernetes cluster overall?
    - Is cluster CPU usage high?
    - What percentage of cluster CPU is currently being used?

    CPU utilization is derived from node-exporter CPU idle time across
    all monitored cluster nodes over the previous five minutes.

    The result is a single cluster-wide percentage.

    Use get_node_cpu_utilization when the user needs CPU usage broken
    down by individual node.
    """

    query = """
    100 *
    (
      1 -
      avg(
        rate(
          node_cpu_seconds_total{
            mode="idle"
          }[5m]
        )
      )
    )
    """

    return await query_prometheus(query)

@mcp.tool()
async def get_cluster_memory_utilization():
    """
    Return aggregate physical-memory utilization percentage across all
    monitored Kubernetes nodes.

    Use this tool when the user asks:
    - What is total cluster memory utilization?
    - How much Kubernetes cluster memory is being used?
    - Is overall cluster memory usage high?
    - What percentage of cluster memory remains available?

    The calculation compares the sum of MemAvailable across nodes with
    the sum of total physical memory.

    The result is one cluster-wide utilization percentage.

    Use get_node_memory_utilization for per-node memory usage and
    get_namespace_memory_utilization for workload usage by namespace.
    """

    query = """
    100 *
    (
      1 -
      (
        sum(node_memory_MemAvailable_bytes)
        /
        sum(node_memory_MemTotal_bytes)
      )
    )
    """

    return await query_prometheus(query)


if __name__ == "__main__":

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
        stateless_http=True,
        json_response=True,
    )

