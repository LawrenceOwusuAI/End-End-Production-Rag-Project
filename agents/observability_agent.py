# agents/observability_agent.py

from __future__ import annotations

import asyncio

from langchain.agents import (
    create_agent,
)

from llm_gateway import (
    create_portkey_llm,
)

from monitoring.mcp_tools import (
    ObservabilityTools,
)


async def main():

    # ========================================================
    # CONNECT TO BOTH MCP SERVERS
    # ========================================================

    observability = (
        ObservabilityTools()
    )


    tools = await (
        observability.start()
    )


    print(
        "\n=================================="
    )

    print(
        "LANGCHAIN OBSERVABILITY TOOLS"
    )

    print(
        "=================================="
    )


    for tool in tools:

        print(
            f"- {tool.name}"
        )


    try:

        # ====================================================
        # USE YOUR EXISTING PORTKEY LLM
        # ====================================================

        llm = create_portkey_llm(

            model=
                "gpt-4.1-mini",

            component=
                "observability-agent",
        )


        # ====================================================
        # CREATE LANGCHAIN AGENT
        # ====================================================

        agent = create_agent(

            model=
                llm,

            tools=
                tools,

            system_prompt=
                """
You are a production observability engineer
for a Retrieval-Augmented Generation system.

You have access to two categories of tools.


================================================
PROMETHEUS TOOLS
================================================

Use Prometheus tools for numerical system
measurements such as:

- request rate
- error rate
- p50 latency
- p95 latency
- p99 latency
- active requests
- CPU utilization
- memory usage
- embedding latency
- retrieval latency
- reranking latency
- LLM generation latency
- vector database error rate
- LLM error rate
- application health


================================================
OPENSEARCH TOOLS
================================================

Use OpenSearch tools to inspect:

- user questions
- retrieved document contents
- document metadata
- generated RAG answers
- application logs
- warning logs
- errors
- Pinecone/vector errors
- LLM errors
- OpenTelemetry traces
- slow traces
- retrieval spans
- answer-generation spans


================================================
DIAGNOSTIC STRATEGY
================================================

If the user asks:

"How slow is my RAG?"

Use Prometheus.


If the user asks:

"Why is my RAG slow?"

First use Prometheus to identify which
component is slow.

Then inspect OpenSearch traces and logs
for that component.


If the user asks:

"What questions have users asked?"

Use OpenSearch query tools.


If the user asks:

"What documents were retrieved?"

Use the retrieved-document tools.


If the user asks:

"What answer was generated?"

Use generated-answer tools.


If the user asks:

"Why did the request fail?"

Use:

1. Prometheus error metrics.
2. OpenSearch error logs.
3. Failed component logs.
4. Trace data when useful.


================================================
IMPORTANT RULES
================================================

Never invent telemetry.

Never invent metric values.

Never invent logs.

Never invent trace information.

Never claim a root cause unless the
observability evidence supports it.

Use multiple tools when necessary.
                """,
        )


        # ====================================================
        # EXAMPLE QUESTION
        # ====================================================

        result = await agent.ainvoke(

            {

                "messages": [

                    {

                        "role":
                            "user",

                        "content":
                            (
                                "Why is my RAG "
                                "application slow?"
                            ),
                    }

                ]

            }

        )


        print(
            "\n=================================="
        )

        print(
            "AGENT RESPONSE"
        )

        print(
            "=================================="
        )


        print(
            result[
                "messages"
            ][-1].content
        )


    finally:

        # ====================================================
        # ALWAYS CLOSE MCP CONNECTIONS
        # ====================================================

        await (
            observability.close()
        )


if __name__ == "__main__":

    asyncio.run(
        main()
    )