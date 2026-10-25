# - Is the RAG system healthy right now?
# - Give me a health summary of the RAG application over the last 5 minutes.
# - Was the RAG application healthy over the last 30 minutes?
# - Are there any current performance problems with the RAG backend?
# - Is the RAG backend overloaded right now?
# - Give me an operational overview of the RAG system.
# - Are CPU, memory, errors, or latency currently concerning?
# - What is causing the RAG system to be degraded?
# - How healthy was the RAG system over the last hour?
# - Summarize traffic, errors, latency, CPU, and memory for the last 10 minutes.
# The most useful diagnostic question is:
# Is the RAG system healthy over the last 30 minutes, and if not, what is causing the degradation?

# What was the RAG success rate over the last 30 minutes?

# What was the peak number of active requests in the last hour?

# What percentage of the RAG backend memory limit is currently being used?

# How many documents were retrieved per query on average over the last 30 minutes?

# Show me the RAG latency breakdown over the last 10 minutes.

# What was the slowest component of the RAG pipeline over the last 30 minutes?
# How much memory is available to the RAG backend?
# How much memory is the RAG backend using?
# What percentage of its memory limit is the RAG backend using?
# How much CPU is the RAG backend currently consuming?
# Is the RAG backend close to its CPU or memory limit?
# What was the average CPU usage of the RAG backend over the last 30 minutes?
# What was the average memory usage of the RAG backend over the last 10 minutes?
# What was the CPU usage over the last hour?
# What was the memory usage over the last 5 minutes?
# Are all monitored dependencies healthy right now?
# Which monitored service is currently unhealthy?Perform a predictive health check of the RAG system for the last 5 minutes.
# Check the health of all Prometheus targets.
# Break down RAG errors over the last 30 minutes.
# Were there more 4xx or 5xx errors in the last hour?
# Show me the client-error rate and server-error rate for the last 10 minutes.
# How many RAG requests timed out in the last 30 minutes?
# Were there any HTTP 504 timeouts in the last hour?
# Count request timeouts over the last 10 minutes.
# Has the RAG backend restarted in the last hour?
# How many times did the RAG backend restart in the last 30 minutes?
# Was there any backend container instability recently?
# Are we meeting our 99% request-success SLO over the last 30 minutes?
# What is the RAG success rate over the last hour?
# How far above or below the 99% SLO are we?
# How many LLM tokens were used in the last 30 minutes?
# Show prompt tokens, completion tokens, and total tokens for the last hour.
# How many completion tokens did the RAG system use in the last 10 minutes?
# What was the estimated LLM cost in the last 30 minutes?
# How much did the RAG system spend on LLM usage in the last hour?
# What is the estimated LLM cost for the last 10 minutes?
# Show me the slowest RAG traces recently.
# Which recent requests were slowest?
# Find slow traces and tell me whether retrieval or generation caused the delay.
# Investigate the RAG system over the last 30 minutes. Check dependency health, error breakdown, timeouts, backend restarts, SLO compliance, token usage, LLM cost, and recent slow traces. Tell me what is abnormal.
# 
# Are there any CPU or memory saturation risks right now?
#What percentage of CPU and memory is the RAG backend currently using, and are either approaching a dangerous level?

#OPENSEARCH LOG QUESTIONS
#Why did the last request fail?

#Show me the latest RAG errors.

#What was the latest user query?

#What documents were retrieved?

#Show me the slowest recent trace.

#Which stage caused the latency?

#Show me recent Pinecone errors.

#Show me recent LLM gateway errors.

#Which service generated the most errors?

#Show me all logs associated with the latest failed trace.

#INFRASTRUCTURAL QUESTIONS
#How many nodes are in the cluster?

#What is the CPU utilization of each node?

#Which node is using the most memory?

#Are any nodes under disk pressure?

#Which pod is consuming the most CPU?

#How much memory is the rag namespace consuming?

#Are there any CrashLoopBackOff pods?

#Which pods have restarted?

#Are all deployments healthy?

#Is kube-proxy healthy on every node?

#Are all Prometheus targets healthy?

#What alerts are currently firing?

#Are there any network errors on the nodes?

#What is total cluster CPU utilization?

#What is total cluster memory utilization?
