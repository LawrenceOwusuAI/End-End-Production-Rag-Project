# observability_agent_api.py

from __future__ import annotations
import os
import smtplib
import asyncio
import logging
from email.message import EmailMessage
from fastapi import BackgroundTasks
import os
from contextlib import AsyncExitStack,asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel,Field
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter
from llm_gateway import create_portkey_llm


# ENVIRONMENT
load_dotenv(override=False)

logger = logging.getLogger(__name__)

PROMETHEUS_MCP_URL = os.getenv(
    "PROMETHEUS_MCP_URL",
    "http://prometheus-mcp:8001/mcp",
)


OPENSEARCH_MCP_URL = os.getenv(
    "OPENSEARCH_MCP_URL",
    "http://opensearch-mcp:8002/mcp",
)


OBSERVABILITY_MODEL = os.getenv(
    "OBSERVABILITY_MODEL",
    "gpt-4.1-mini",
)


# ============================================================
# REQUEST / RESPONSE
# ============================================================

class ObservabilityRequest(
    BaseModel
):

    question: str = Field(
        min_length=1
    )


class ObservabilityResponse(
    BaseModel
):

    question: str

    answer: str


# ============================================================
# SYSTEM PROMPT
# ============================================================

OBSERVABILITY_SYSTEM_PROMPT = """
You are the production observability agent for a
Retrieval-Augmented Generation application.

Your responsibility is to investigate the health,
performance, errors, logs and traces of the RAG
application.

You have approved tools from two MCP servers:

==================================================
PROMETHEUS
==================================================

Prometheus contains numerical metrics.

Use Prometheus tools for questions involving:

- requests per second
- traffic
- error rate
- active requests
- p50 latency
- p95 latency
- p99 latency
- CPU usage
- memory usage
- embedding latency
- query-routing latency
- retrieval latency
- reranking latency
- LLM generation latency
- Pinecone/vector database errors
- LLM errors
- overall application health

RAG QUALITY METRICS
-------------------

Prometheus also contains online RAGAS-derived quality metrics.

Use get_rag_faithfulness when the user asks whether generated
answers are supported by retrieved context.

Use get_rag_answer_relevancy when the user asks whether answers
directly address the user's questions.

Use get_rag_context_utilization when the user asks whether the
retrieved context is useful or actually being used by the generator.

Use get_rag_groundedness when the user explicitly asks about
groundedness. Groundedness is currently implemented as a proxy
equal to faithfulness.

Use get_rag_hallucination_rate when the user asks about hallucination,
unsupported claims, or ungrounded generation. This is currently a
proxy calculated as 1 - faithfulness.

Use get_rag_quality_evaluation_count when the user asks how many
queries were evaluated or how many observations the quality scores
are based on.

Use get_rag_quality_summary for broad questions such as:
- "How is the quality of my RAG?"
- "Show me my RAGAS metrics."
- "Give me a RAG quality summary."
- "Is my RAG producing good answers?"

For a broad quality question, prefer get_rag_quality_summary rather
than calling every individual quality tool.

Never treat quality-evaluation count as total RAG query count because
online RAGAS evaluation may be sampled.

When explaining quality scores:
- faithfulness: higher is better
- answer relevancy: higher is better
- context utilization: higher is better
- groundedness: higher is better
- hallucination rate: lower is better

Do not invent threshold interpretations unless thresholds are defined
by the application or explicitly provided.


PROMETHEUS ALERT RULES:

When the user asks whether an alert has fired, whether an alert
is currently active, what alerts are firing, or asks about alert
severity/status/start time:

1. ALWAYS call get_active_alerts or get_alert_by_name first.
2. Treat these tools as the authoritative source of Prometheus
   alert state.
3. Do NOT infer alert state only from CPU, memory, error-rate,
   latency, or SLO metrics.
4. After confirming an alert is firing, use the other Prometheus
   and OpenSearch tools to investigate its likely cause.
5. Clearly distinguish:
   - firing
   - pending
   - not active

OPENSEARCH

OpenSearch contains detailed logs and traces.

Use OpenSearch tools for questions involving:

- user queries
- retrieved documents
- retrieved chunk contents
- generated answers
- errors
- warnings
- Pinecone failures
- retrieval failures
- LLM failures
- traces
- spans
- slow requests
- trace-specific logs


==================================================
TOOL-SELECTION POLICY
==================================================

For quantitative questions, start with Prometheus.

Example:

"How slow is the RAG?"

Use latency metrics.


For diagnostic questions, use Prometheus first and
then OpenSearch.

Example:

"Why is the RAG slow?"

1. Check overall latency.
2. Check retrieval latency.
3. Check reranker latency.
4. Check embedding latency.
5. Check generation latency.
6. Identify the slow component.
7. Inspect corresponding traces and logs.
8. Explain the evidence.


For:

"Why did the last request fail?"

1. Check error rate.
2. Inspect recent errors.
3. Inspect retrieval errors.
4. Inspect LLM errors.
5. Inspect vector database errors.
6. Inspect trace/log evidence when available.


For:

"What was the latest user question?"

Use the OpenSearch user-query tool.


For:

"What chunks were retrieved?"

Use the OpenSearch retrieved-document tool.


For:

"What answer did the model generate?"

Use the OpenSearch generated-answer tool.


==================================================
SECURITY AND RELIABILITY
==================================================

Never generate PromQL yourself.

Never generate OpenSearch DSL yourself.

Only use the approved MCP tools.

Never invent metric values.

Never invent logs.

Never invent traces.

Never invent a root cause.

If telemetry does not provide enough evidence,
state that clearly.

When diagnosing a problem, correlate multiple
signals when possible.
"""


# ============================================================
# FASTAPI LIFESPAN
#
# We maintain the MCP connections for the lifetime
# of the observability-agent service.
# ============================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):

    exit_stack = AsyncExitStack()

    await exit_stack.__aenter__()


    # ========================================================
    # PROMETHEUS MCP CONNECTION
    # ========================================================

    prometheus_adapter = await (
        exit_stack.enter_async_context(
            MCPAdapter(
                PROMETHEUS_MCP_URL
            )
        )
    )


    prometheus_tools = await (
        prometheus_adapter.list_tools()
    )


    # ========================================================
    # OPENSEARCH MCP CONNECTION
    # ========================================================

    opensearch_adapter = await (
        exit_stack.enter_async_context(
            MCPAdapter(
                OPENSEARCH_MCP_URL
            )
        )
    )


    opensearch_tools = await (
        opensearch_adapter.list_tools()
    )


    # ========================================================
    # COMBINE ALL MCP TOOLS
    # ========================================================

    tools = (
        prometheus_tools
        +
        opensearch_tools
    )


    # ========================================================
    # USE YOUR EXISTING PORTKEY LLM
    # ========================================================

    llm = create_portkey_llm(

        model=
            OBSERVABILITY_MODEL,

        component=
            "observability-agent",
    )


    # ========================================================
    # LANGCHAIN TOOL-CALLING AGENT
    # ========================================================

    agent = create_agent(

        model=
            llm,

        tools=
            tools,

        system_prompt=
            OBSERVABILITY_SYSTEM_PROMPT,
    )


    # ========================================================
    # SAVE TO FASTAPI STATE
    # ========================================================

    app.state.prometheus_adapter = (
        prometheus_adapter
    )


    app.state.opensearch_adapter = (
        opensearch_adapter
    )


    app.state.tools = (
        tools
    )


    app.state.agent = (
        agent
    )


    app.state.ready = True


    print(
        "\nObservability agent started."
    )


    print(
        f"Prometheus tools: "
        f"{len(prometheus_tools)}"
    )


    print(
        f"OpenSearch tools: "
        f"{len(opensearch_tools)}"
    )


    print(
        f"Total MCP tools: "
        f"{len(tools)}"
    )


    for tool in tools:

        print(
            f"  - {tool.name}"
        )


    try:

        yield

    finally:

        app.state.ready = False

        await exit_stack.aclose()


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(

    title=
        "RAG Observability Agent",

    description=
        (
            "LangChain tool-calling agent "
            "using Prometheus and OpenSearch MCP servers."
        ),

    version=
        "1.0.0",

    lifespan=
        lifespan,
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {

        "service":
            "rag-observability-agent",

        "status":
            "running",

        "health":
            "/health",

        "observe":
            "/observe",

        "tools":
            "/tools",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {

        "status":
            (
                "healthy"

                if getattr(
                    app.state,
                    "ready",
                    False,
                )

                else

                "starting"
            ),

        "prometheus_mcp":
            PROMETHEUS_MCP_URL,

        "opensearch_mcp":
            OPENSEARCH_MCP_URL,
    }


# ============================================================
# AVAILABLE MCP TOOLS
# ============================================================

@app.get("/tools")
def available_tools():

    if not getattr(
        app.state,
        "ready",
        False,
    ):

        raise HTTPException(
            status_code=503,
            detail=(
                "Observability agent "
                "is not ready."
            ),
        )


    return {

        "count":
            len(
                app.state.tools
            ),

        "tools": [

            {

                "name":
                    tool.name,

                "description":
                    tool.description,

            }

            for tool
            in app.state.tools

        ],
    }


# ============================================================
# OBSERVABILITY QUESTION
# ============================================================

@app.post(
    "/observe",
    response_model=
        ObservabilityResponse,
)
async def observe(
    request:
        ObservabilityRequest,
):

    if not getattr(
        app.state,
        "ready",
        False,
    ):

        raise HTTPException(

            status_code=
                503,

            detail=
                (
                    "Observability agent "
                    "is not ready."
                ),
        )


    question = (
        request.question
        .strip()
    )


    if not question:

        raise HTTPException(
            status_code=400,
            detail=(
                "Question cannot be empty."
            ),
        )


    try:

        result = await (
            app.state.agent
            .ainvoke(
                {
                    "messages": [

                        {
                            "role":
                                "user",

                            "content":
                                question,
                        }

                    ]
                }
            )
        )


        final_message = (
            result[
                "messages"
            ][-1]
        )


        answer = (
            final_message.content
        )


        return ObservabilityResponse(

            question=
                question,

            answer=
                answer,
        )


    except Exception as e:

        raise HTTPException(

            status_code=
                500,

            detail=
                (
                    "Observability investigation "
                    f"failed: {str(e)}"
                ),

        ) from e

# ============================================================
# EMAIL NOTIFICATION
# ============================================================


def send_email_notification(
    subject: str,
    body: str,
) -> None:
    """
    Send an observability alert using Gmail SMTP.
    """

    smtp_host = os.getenv(
        "SMTP_HOST",
        "smtp.gmail.com",
    )

    smtp_port = int(
        os.getenv(
            "SMTP_PORT",
            "587",
        )
    )

    smtp_username = os.getenv(
        "SMTP_USERNAME"
    )

    smtp_password = os.getenv(
        "SMTP_PASSWORD"
    )

    email_from = os.getenv(
        "ALERT_EMAIL_FROM"
    )

    email_to = os.getenv(
        "ALERT_EMAIL_TO"
    )

    required_values = {
        "SMTP_USERNAME": smtp_username,
        "SMTP_PASSWORD": smtp_password,
        "ALERT_EMAIL_FROM": email_from,
        "ALERT_EMAIL_TO": email_to,
    }

    missing = [
        name
        for name, value in required_values.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing email configuration: "
            + ", ".join(missing)
        )

    message = EmailMessage()

    message["From"] = email_from
    message["To"] = email_to
    message["Subject"] = subject

    message.set_content(
        body
    )

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=20,
    ) as server:

        server.ehlo()

        server.starttls()

        server.ehlo()

        server.login(
            smtp_username,
            smtp_password,
        )

        server.send_message(
            message
        )


# ============================================================
# BUILD AGENT INVESTIGATION PROMPT
# ============================================================


def build_alert_investigation_prompt(
    alert: dict,
) -> str:

    labels = alert.get(
        "labels",
        {},
    )

    annotations = alert.get(
        "annotations",
        {},
    )

    alert_name = labels.get(
        "alertname",
        "UnknownAlert",
    )

    severity = labels.get(
        "severity",
        "unknown",
    )

    service = labels.get(
        "service",
        "unknown",
    )

    category = labels.get(
        "category",
        "unknown",
    )

    summary = annotations.get(
        "summary",
        "",
    )

    description = annotations.get(
        "description",
        "",
    )

    return f"""
A Prometheus alert has fired for the production RAG system.

Alert name:
{alert_name}

Severity:
{severity}

Service:
{service}

Category:
{category}

Summary:
{summary}

Description:
{description}

Perform an immediate observability investigation.

Use the available Prometheus and OpenSearch monitoring tools.

Check where relevant:

- predictive health
- current CPU utilization
- CPU trend
- current memory utilization
- memory used versus memory limit
- request error rate
- request-success SLO
- request latency
- timeouts
- container restarts
- recent application errors
- recent slow traces
- retrieval latency
- LLM generation latency

Answer:

1. What is happening?
2. How severe is it?
3. What evidence supports the diagnosis?
4. Are other components degrading?
5. What corrective action should the operator take now?
6. What should be monitored next?

Be concise and operational.

Do not claim that a future failure is guaranteed.
Treat warning conditions as early indicators.
"""


# ============================================================
# FORMAT EMAIL
# ============================================================


def format_alert_email(
    alert: dict,
    investigation: str,
) -> tuple[str, str]:

    labels = alert.get(
        "labels",
        {},
    )

    annotations = alert.get(
        "annotations",
        {},
    )

    severity = labels.get(
        "severity",
        "unknown",
    ).upper()

    alert_name = labels.get(
        "alertname",
        "UnknownAlert",
    )

    service = labels.get(
        "service",
        "unknown",
    )

    category = labels.get(
        "category",
        "unknown",
    )

    summary = annotations.get(
        "summary",
        "",
    )

    description = annotations.get(
        "description",
        "",
    )

    subject = (
        f"[{severity}] "
        f"RAG Observability Alert - "
        f"{alert_name}"
    )

    body = f"""
RAG OBSERVABILITY ALERT
=======================

Severity:
{severity}

Alert:
{alert_name}

Service:
{service}

Category:
{category}

Summary:
{summary}

Description:
{description}


AI INVESTIGATION
================

{investigation}


Recommended operator action:
Review the investigation above and take corrective action
if the warning or critical condition remains active.
""".strip()

    return (
        subject,
        body,
    )

# ============================================================
# REUSABLE OBSERVABILITY AGENT RUNNER
# ============================================================

async def run_observability_agent(
    query: str,
) -> str:
    """
    Run the existing LangChain observability agent and
    return the final text response.

    This uses the same app.state.agent that is initialized
    during FastAPI lifespan startup.
    """

    if not getattr(
        app.state,
        "ready",
        False,
    ):
        raise RuntimeError(
            "Observability agent is not ready."
        )

    query = query.strip()

    if not query:
        raise ValueError(
            "Observability query cannot be empty."
        )

    result = await (
        app.state.agent
        .ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": query,
                    }
                ]
            }
        )
    )

    messages = result.get(
        "messages",
        [],
    )

    if not messages:
        raise RuntimeError(
            "Observability agent returned no messages."
        )

    final_message = messages[-1]

    content = getattr(
        final_message,
        "content",
        None,
    )

    if content is None:
        return str(
            final_message
        )

    if isinstance(
        content,
        str,
    ):
        return content

    return str(
        content
    )


# ============================================================
# RETRY OBSERVABILITY AGENT
# ============================================================

async def run_with_retry(
    query: str,
) -> str:
    """
    Run the observability agent with retry handling
    for transient Portkey/LLM rate-limit errors.
    """

    delays = [
        1,
        2,
        4,
    ]

    for attempt, delay in enumerate(
        delays,
        start=1,
    ):

        try:

            return await run_observability_agent(
                query
            )

        except Exception as exc:

            message = str(
                exc
            ).lower()

            is_rate_limit = (
                "429" in message
                or "too many requests" in message
                or "rate limit" in message
            )

            # Do not retry programming errors,
            # MCP errors, authentication errors, etc.
            if not is_rate_limit:
                raise

            logger.warning(
                "LLM rate limit encountered. "
                "attempt=%s/%s error=%s",
                attempt,
                len(delays),
                exc,
            )

            # All attempts exhausted.
            if attempt == len(delays):
                raise

            await asyncio.sleep(
                delay
            )

# ============================================================
# PROCESS FIRING ALERT
# ============================================================


async def investigate_and_email_alert(
    alert: dict,
) -> None:

    try:

        prompt = build_alert_investigation_prompt(
            alert
        )

        investigation = await run_with_retry(
            prompt
        )

        if not isinstance(
            investigation,
            str,
        ):
            investigation = str(
                investigation
            )

        subject, body = format_alert_email(
            alert=alert,
            investigation=investigation,
        )

        # smtplib is blocking, so run it in a worker thread.
        await asyncio.to_thread(
            send_email_notification,
            subject,
            body,
        )

        logger.info(
            "Alert email successfully sent for %s",
            alert.get(
                "labels",
                {},
            ).get(
                "alertname",
                "unknown",
            ),
        )

    except Exception:

        logger.exception(
            "Failed to investigate or email Prometheus alert."
        )


# ============================================================
# PROCESS RESOLVED ALERT
# ============================================================


async def email_resolved_alert(
    alert: dict,
) -> None:

    labels = alert.get(
        "labels",
        {},
    )

    annotations = alert.get(
        "annotations",
        {},
    )

    alert_name = labels.get(
        "alertname",
        "UnknownAlert",
    )

    service = labels.get(
        "service",
        "unknown",
    )

    summary = annotations.get(
        "summary",
        "",
    )

    subject = (
        f"[RESOLVED] "
        f"RAG Observability Alert - "
        f"{alert_name}"
    )

    body = f"""
RAG ALERT RESOLVED
==================

Alert:
{alert_name}

Service:
{service}

Summary:
{summary}

The Prometheus alert condition is no longer firing.

Continue monitoring the service to ensure that the condition
does not return.
""".strip()

    try:

        await asyncio.to_thread(
            send_email_notification,
            subject,
            body,
        )

        logger.info(
            "Resolved alert email sent for %s",
            alert_name,
        )

    except Exception:

        logger.exception(
            "Failed to send resolved alert email."
        )


# ============================================================
# ALERTMANAGER WEBHOOK
# ============================================================


@app.post(
    "/alerts/prometheus"
)
async def receive_prometheus_alert(
    payload: dict,
    background_tasks: BackgroundTasks,
):

    """
    Receive firing/resolved alerts from Alertmanager.

    Respond quickly to Alertmanager and perform the expensive
    agent investigation in the background.
    """

    alerts = payload.get(
        "alerts",
        [],
    )

    scheduled = 0

    for alert in alerts:

        status = alert.get(
            "status",
            "firing",
        )

        if status == "firing":

            background_tasks.add_task(
                investigate_and_email_alert,
                alert,
            )

            scheduled += 1

        elif status == "resolved":

            background_tasks.add_task(
                email_resolved_alert,
                alert,
            )

            scheduled += 1

    return {
        "status": "accepted",
        "alerts_received": len(
            alerts
        ),
        "alerts_scheduled": scheduled,
    }