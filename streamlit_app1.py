import os
import requests
import streamlit as st

BASE_API_URL = os.getenv("BASE_API_URL","http://rag-backend:8000")
OBSERVABILITY_BASE_URL = os.getenv("OBSERVABILITY_BASE_URL","http://127.0.0.1:8003")
API_URL = f"{BASE_API_URL}/query"
DOCUMENTS_API_URL = f"{BASE_API_URL}/documents"
REGISTER_API_URL = f"{BASE_API_URL}/auth/register"
LOGIN_API_URL = f"{BASE_API_URL}/auth/login"
ME_API_URL = f"{BASE_API_URL}/auth/me"

# OBSERVABILITY AGENT BACKEND
OBSERVABILITY_BASE_URL = os.getenv("OBSERVABILITY_BASE_URL","http://127.0.0.1:8003")
OBSERVABILITY_API_URL = f"{OBSERVABILITY_BASE_URL}/observe"
OBSERVABILITY_HEALTH_URL = f"{OBSERVABILITY_BASE_URL}/health"

# PAGE CONFIGURATION
st.set_page_config(page_title=
       "AI Research Assistant",
       page_icon="🤖",
       layout="wide",
       initial_sidebar_state="collapsed",
)

# SESSION STATE
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "observability_messages" not in st.session_state:
    st.session_state["observability_messages"] = []

# CUSTOM CSS
st.markdown(
    """
<style>
.stApp {

    background:

        radial-gradient(
            circle at 10% 10%,
            rgba(91, 124, 250, 0.13),
            transparent 30%
        ),

        radial-gradient(
            circle at 90% 15%,
            rgba(151, 117, 250, 0.10),
            transparent 28%
        ),

        linear-gradient(
            135deg,
            #edf4fb 0%,
            #e6eef8 45%,
            #edf1f8 100%
        );

    color:
        #172033;
}

.block-container {

    max-width:
        1100px;

    padding-top:
        2rem;

    padding-bottom:
        4rem;
}


header[data-testid="stHeader"] {

    background:
        transparent;
}

.main-title {

    text-align:
        center;

    font-size:
        3.2rem;

    font-weight:
        800;

    margin-bottom:
        0.4rem;

    background:
        linear-gradient(
            90deg,
            #304ffe,
            #5f3dc4,
            #7048e8
        );

    -webkit-background-clip:
        text;

    -webkit-text-fill-color:
        transparent;
}


.subtitle {

    text-align:
        center;

    color:
        #526375;

    font-size:
        1.05rem;

    margin-bottom:
        1rem;
}

.status-box {

    text-align:
        center;

    margin-bottom:
        2rem;

    color:
        #526375;

    font-size:
        0.92rem;

    font-weight:
        500;
}


.status-dot {

    display:
        inline-block;

    width:
        9px;

    height:
        9px;

    border-radius:
        50%;

    background:
        #2f9e44;

    margin-right:
        7px;

    box-shadow:
        0 0 8px
        rgba(47, 158, 68, 0.50);
}

.section-card {

    background:
        rgba(
            255,
            255,
            255,
            0.88
        );

    border:
        1px solid #d9e2ec;

    border-radius:
        20px;

    padding:
        20px 24px;

    margin-top:
        1rem;

    margin-bottom:
        1rem;

    box-shadow:
        0 10px 30px
        rgba(30, 50, 80, 0.08);
}


.section-title {

    color:
        #172033;

    font-size:
        1.35rem;

    font-weight:
        700;

    margin-bottom:
        5px;
}


.section-description {

    color:
        #536273;

    font-size:
        0.95rem;

    line-height:
        1.6;
}


.stMarkdown,
.stCaption {

    color:
        #26364a;
}

button[data-baseweb="tab"] {

    font-size:
        1rem;

    font-weight:
        700;

    color:
        #344054;
}


button[data-baseweb="tab"][aria-selected="true"] {

    color:
        #4338ca;
}


[data-testid="stFileUploader"] {

    background:
        #ffffff;

    border:
        1px solid #d7e0ea;

    border-radius:
        16px;

    padding:
        15px;
}


[data-testid="stFileUploader"] label {

    color:
        #172033 !important;
}


[data-testid="stFileUploader"] section {

    background:
        #f8fafc !important;

    border:
        1px dashed #9fb1c5 !important;

    border-radius:
        12px !important;
}


[data-testid="stFileUploader"] section div {

    color:
        #26364a !important;
}

.stTextInput input {

    background-color:
        #ffffff !important;

    color:
        #172033 !important;

    border-radius:
        12px !important;

    border:
        1px solid #cbd6e2 !important;
}

.stTextArea textarea {

    background-color:
        #ffffff !important;

    color:
        #172033 !important;

    border-radius:
        15px !important;

    border:
        1px solid #cbd6e2 !important;

    font-size:
        1rem !important;

    min-height:
        125px !important;

    padding:
        16px !important;

    box-shadow:
        0 4px 15px
        rgba(30, 50, 80, 0.05) !important;
}


.stTextArea textarea:focus {

    border:
        1px solid #5c7cfa !important;

    box-shadow:
        0 0 0 2px
        rgba(92, 124, 250, 0.15) !important;
}


.stTextArea textarea::placeholder {

    color:
        #8291a3 !important;

    opacity:
        1 !important;
}

.stButton button,
div[data-testid="stFormSubmitButton"] button {

    width:
        100%;

    height:
        3rem;

    border:
        none !important;

    border-radius:
        12px !important;

    font-size:
        1rem !important;

    font-weight:
        700 !important;

    color:
        white !important;

    background:
        linear-gradient(
            90deg,
            #4263eb,
            #6741d9
        ) !important;

    box-shadow:
        0 6px 18px
        rgba(66, 99, 235, 0.20);

    transition:
        all 0.2s ease;
}


.stButton button:hover,
div[data-testid="stFormSubmitButton"] button:hover {

    transform:
        translateY(-1px);

    box-shadow:
        0 10px 24px
        rgba(66, 99, 235, 0.28);
}


.stButton button p,
div[data-testid="stFormSubmitButton"] button p {

    color:
        white !important;
}

[data-testid="stChatMessage"] {

    background:
        #ffffff !important;

    border:
        1px solid #d7e0ea !important;

    border-radius:
        18px !important;

    padding:
        16px !important;

    margin-top:
        12px !important;

    margin-bottom:
        14px !important;

    box-shadow:
        0 6px 20px
        rgba(30, 50, 80, 0.07) !important;
}


[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li {

    color:
        #1c2735 !important;

    font-size:
        1rem !important;

    line-height:
        1.75 !important;
}


[data-testid="stChatMessage"]
[data-testid="stMarkdownContainer"] {

    color:
        #1c2735 !important;
}


[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] h4 {

    color:
        #172033 !important;
}


[data-testid="stChatMessage"] strong {

    color:
        #111827 !important;

    font-weight:
        700 !important;
}


[data-testid="stChatMessage"] a {

    color:
        #364fc7 !important;

    font-weight:
        600;
}


[data-testid="stChatMessage"] code {

    color:
        #b42318 !important;

    background:
        #f2f4f7 !important;

    padding:
        2px 5px;

    border-radius:
        5px;
}

[data-testid="stMetric"] {

    background:
        rgba(
            255,
            255,
            255,
            0.90
        );

    border:
        1px solid #d7e0ea;

    padding:
        14px;

    border-radius:
        14px;
}

[data-testid="stCaptionContainer"] p {

    color:
        #617285 !important;
}


[data-testid="stSpinner"] {

    color:
        #253858 !important;
}

[data-testid="stForm"] {

    background:
        rgba(
            255,
            255,
            255,
            0.30
        );

    border:
        1px solid
        rgba(
            190,
            205,
            220,
            0.55
        );

    border-radius:
        18px;

    padding:
        14px;
}

.observability-info {

    background:
        rgba(
            238,
            242,
            255,
            0.95
        );

    border:
        1px solid #c7d2fe;

    border-radius:
        16px;

    padding:
        18px;

    margin-top:
        1rem;

    margin-bottom:
        1rem;

    color:
        #312e81;
}


.observability-info strong {

    color:
        #312e81;
}

footer {

    visibility:
        hidden;
}

</style>
""",

    unsafe_allow_html=True,
)


# REGISTER USER
def register_user(full_name,email,password,):
    try:
        response = requests.post(
            REGISTER_API_URL,
            json={"full_name":full_name,
                "email":email,
                "password":password,
            },
            timeout= 15,
        )
        return response
    except requests.RequestException:
        return None

# LOGIN USER
def login_user(email,password):
    try:
        response = requests.post(
            LOGIN_API_URL,
            json={
                "email":email,
                "password":password,
            },
            timeout=15,
        )
        return response
    except requests.RequestException:
        return None

# AUTHENTICATION PAGE
if not st.session_state["access_token"]:
    st.markdown(
        """
<div class="main-title">
AI Research Assistant
</div>
        """,

        unsafe_allow_html=True,
    )


    st.markdown(
        """
<div class="subtitle">

Sign in or create an account
to access your research assistant.

</div>
        """,

        unsafe_allow_html=True,
    )


    login_tab, register_tab = (
        st.tabs(
            [
                "🔐 Login",
                "👤 Create Account",
            ]
        )
    )

    # LOGIN TAB
    with login_tab:
        st.subheader("Welcome Back")
        with st.form("login_form"):
            login_email = st.text_input("Email Address",key="login_email",)
            login_password = st.text_input("Password",
                    type="password",
                    key="login_password")
            
            login_button = (
                st.form_submit_button(

                    "Login",

                    use_container_width=
                        True,
                )
            )


        if login_button:

            response = login_user(

                login_email,

                login_password,
            )


            if response is None:

                st.error(
                    "Unable to connect "
                    "to the authentication server."
                )


            elif (
                response.status_code
                ==
                200
            ):

                data = (
                    response.json()
                )


                st.session_state[
                    "access_token"
                ] = (
                    data[
                        "access_token"
                    ]
                )


                st.session_state[
                    "user"
                ] = (
                    data[
                        "user"
                    ]
                )


                st.rerun()


            else:

                try:

                    message = (

                        response
                        .json()
                        .get(
                            "detail",
                            "Login failed.",
                        )
                    )


                except Exception:

                    message = (
                        "Login failed."
                    )


                st.error(
                    message
                )

    # REGISTER TAB
   
    with register_tab:

        st.subheader("Create Your Account")

        with st.form("registration_form"):

            full_name = (
                st.text_input(
                    "Full Name",
                    key="register_full_name",
                )
            )

            register_email = (
                st.text_input(
                    "Email Address",
                    key="register_email",
                )
            )

            register_password = (
                st.text_input(
                    "Password",
                    type="password",
                    key="register_password"
                )
            )

            confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    key="confirm_password",
                )
            
            register_button = st.form_submit_button(
                    "Create Account",
                    use_container_width=True
                )
            
        if register_button:

            if not full_name.strip():

                st.error("Please enter your full name.")

            elif not register_email.strip():

                st.error("Please enter your email.")

            elif register_password != confirm_password:

                st.error("Passwords do not match.")

            elif len(register_password) < 8:

                st.error("Password must contain at least 8 characters.")

            else:

                response = register_user(
                        full_name,

                        register_email,

                        register_password,
                    )
                
                if response is None:

                    st.error("Unable to connect to the authentication server.")

                elif response.status_code == 201:

                    st.success("Account created successfully. Please log in.")

                else:

                    try:

                        message = response.json().get(
                                "detail",
                                "Registration failed.",
                            )
                        
                    except Exception:

                        message = ("Registration failed.")

                    st.error(message)

    # Stop rendering authenticated application
    st.stop()

# AUTHENTICATED USER
current_user = st.session_state["user"]


# SIDEBAR
with st.sidebar:

    st.markdown("### 👤 Account")

    st.write(current_user["full_name"])

    st.caption(current_user["email"])

    st.divider()

    st.markdown("### 🔗 Services")

    st.caption(f"RAG Backend:\n{BASE_API_URL}")

    st.caption(
        "Observability Agent:\n"
        f"{OBSERVABILITY_BASE_URL}"
    )

    st.divider()

    if st.button(

        "🚪 Logout",

        key="sidebar_logout_button",

        use_container_width=True):

        st.session_state["access_token"] = None

        st.session_state["user"] = None

        st.session_state["observability_messages"] = []

        st.rerun()

# HEADER

st.markdown(
    """
<div class="main-title">
AI Research Assistant
</div>
    """,

    unsafe_allow_html=True,
)


st.markdown(
    """
<div class="subtitle">

Query your documents and monitor the health,
metrics, logs and traces of your RAG application.

</div>
    """,

    unsafe_allow_html=True,
)


st.markdown(
    """
<div class="status-box">

<span class="status-dot"></span>

AI Research Platform Online

</div>
    """,

    unsafe_allow_html=True,
)

# MAIN APPLICATION TABS

rag_tab, observability_tab = (
    st.tabs(
        [
            "📚 RAG Assistant",
            "📊 Observability Assistant",
        ]
    )
)


# TAB 1 RAG ASSISTANT

with rag_tab:

    # DOCUMENT UPLOAD SECTION
  
    st.markdown(
        """
<div class="section-card">

<div class="section-title">
📄 Upload Document
</div>

<div class="section-description">

Upload a PDF document. The document will be sent
to the FastAPI backend, processed by Docling,
divided into RAG chunks, embedded, and stored
in Pinecone.

</div>

</div>
        """,

        unsafe_allow_html=True,
    )


    uploaded_file = (
        st.file_uploader(

            "Upload your PDF",

            type=[
                "pdf"
            ],

            accept_multiple_files=
                False,

            key=
                "rag_pdf_uploader",
        )
    )

    # PROCESS DOCUMENT
  
    if uploaded_file is not None:

        st.caption(
            f"Selected document: "
            f"{uploaded_file.name}"
        )


        process_document = (
            st.button(

                "📚 Process Document",

                use_container_width=
                    True,

                key=
                    "process_document_button",
            )
        )


        if process_document:

            with st.spinner( "Processing document..."):

                try:

                    files = {

                        "file": (

                            uploaded_file.name,

                            uploaded_file.getvalue(),

                            "application/pdf",
                        )
                    }


                    headers = {

                        "Authorization":

                            f"Bearer "
                            f"{st.session_state.access_token}"
                    }


                    response = requests.post(

                            DOCUMENTS_API_URL,

                            files=files,

                            headers=headers,

                            timeout=900,
                        )
                    


                    
                    # EXPIRED AUTH TOKEN
                    if response.status_code == 401:

                        st.session_state["access_token"] = None

                        st.session_state["user"] = None

                        st.error("Your session has expired. Please log in again.")

                        st.rerun()

                    response.raise_for_status()

                    # RESPONSE

                    data = response.json()
                    
                    st.success("Document processed successfully.")


                    col1, col2, col3 = st.columns(3)
                    
                    with col1:

                        st.metric(

                            "Chunks Created",

                            data.get(
                                "chunks_created",
                                0,
                            ),
                        )


                    with col2:

                        st.metric(

                            "Index",

                            data.get(
                                "index",
                                "N/A",
                            ),
                        )


                    with col3:

                        st.metric(

                            "Namespace",

                            data.get(
                                "namespace",
                                "N/A",
                            ),
                        )


                    st.info(
                        f"Uploaded file: "
                        f"{data.get('filename')}"
                    )


                except requests.exceptions.ConnectionError:

                    st.error(
                        "Unable to connect to the "
                        "FastAPI RAG backend at "
                        f"{BASE_API_URL}."
                    )


                except requests.exceptions.Timeout:

                    st.error(
                        "Document processing "
                        "took too long."
                    )


                except requests.exceptions.HTTPError:

                    try:

                        error_data = (
                            response.json()
                        )


                        error_message = (
                            error_data.get(
                                "detail",
                                "Document processing failed.",
                            )
                        )


                    except Exception:

                        error_message = (
                            "Document processing failed."
                        )


                    st.error(
                        error_message
                    )


                except Exception as e:

                    st.error(
                        "Something went wrong: "
                        f"{str(e)}"
                    )

    # DIVIDER
    
    st.divider()

    # RAG QUERY SECTION
 
    st.markdown(
        """
<div class="section-card">

<div class="section-title">
💬 Ask Your Document
</div>

<div class="section-description">

Ask a question about the uploaded document.
The answer will be generated only from retrieved
document evidence.

</div>

</div>
        """,

        unsafe_allow_html=True,
    )

    # RAG QUERY FORM

    with st.form("query_form",clear_on_submit=True):

        query = (
            st.text_area(

                "Your question",

                placeholder=(
                    "Ask a question "
                    "about your document..."
                ),

                label_visibility="collapsed",

                key="rag_query"
            )
        )


        submit_button = (
            st.form_submit_button(

                "✨ Ask Question",

                use_container_width=
                    True,
            )
        )


    # SEND QUERY TO FASTAPI RAG BACKEND


    if submit_button:

        query = query.strip()
        
        if not query:

            st.warning("Please enter a question before submitting.")

        else:

            with st.spinner("Retrieving documents and generating an answer..."):

                try:

                    headers = {

                        "Authorization":

                            f"Bearer "
                            f"{st.session_state.access_token}"
                    }


                    response = (
                        requests.post(

                            API_URL,

                            json={
                                "query":query
                            },

                            headers=headers,

                            timeout=120,
                        )
                    )

                    # EXPIRED AUTH TOKEN

                    if response.status_code == 401:

                        st.session_state["access_token"] = None

                        st.session_state["user"] = None

                        st.error("Your session has expired. Please log in again.")

                        st.rerun()

                    response.raise_for_status()

                    data = response.json()
                    

                    answer = data["answer"]
                    
                    # USER QUESTION
                 
                    with st.chat_message("user"):

                        st.markdown(query)

                    # RAG ANSWER
                    
                    with st.chat_message("assistant"):

                        st.markdown(answer)

                except requests.exceptions.ConnectionError:

                    st.error(
                        "Unable to connect to the "
                        "FastAPI RAG backend at "
                        f"{BASE_API_URL}."
                    )


                except requests.exceptions.Timeout:

                    st.error("The RAG request took too long. Please try again.")

                except requests.exceptions.HTTPError:

                    try:

                        error_data = response.json()
                        

                        error_message = error_data.get("detail",
                                "FastAPI returned an error.",
                            )
                        
                    except Exception:

                        error_message = ("FastAPI returned an error.")

                    st.error(error_message)

                except Exception as e:

                    st.error(
                        "Something went wrong: "
                        f"{str(e)}"
                    )


# TAB 2 OBSERVABILITY ASSISTANT
with observability_tab:

    st.markdown(
        """
<div class="section-card">

<div class="section-title">
📊 RAG Observability Assistant
</div>

<div class="section-description">

Ask natural-language questions about the
performance, metrics, logs, traces, errors and
health of your RAG application.

Your question is sent to a LangChain tool-calling
agent. The agent automatically chooses approved
Prometheus MCP and OpenSearch MCP tools.

</div>

</div>
        """,

        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="observability-info">

<strong>How it works</strong><br><br>

You ask a natural-language question.<br>

Streamlit → LangChain Observability Agent →
Prometheus MCP / OpenSearch MCP →
Prometheus / AWS OpenSearch.

<br><br>

The LLM does <strong>not</strong> create arbitrary
PromQL or OpenSearch queries. It can only call
the approved MCP tools exposed by your servers.

</div>
        """,

        unsafe_allow_html=True,
    )


    
    # EXAMPLE OBSERVABILITY QUESTIONS

    st.markdown(
        "### 💡 Example Questions"
    )


    example_col1, example_col2 = (
        st.columns(2)
    )


    with example_col1:

        st.markdown(
            """
**Metrics**
- How many nodes are in the Kubernetes cluster?
- What is the CPU utilization of each node in the Kubernetes cluster?
- Which pod is consuming the most CPU?
- Are there any CrashLoopBackOff pods?
- How much memory is the rag namespace consuming?
- Is my RAG application healthy?
- What is my retrieval latency?
- Are all Prometheus targets healthy?

            """
        )


    with example_col2:

        st.markdown(
            """
**Logs and Traces**
- Why did the last request fail?
- Show me recent RAG errors.
- Show me recent Pinecone errors.
- What was the latest user query?
- What documents were retrieved?
- What answer did the RAG generate?
- Why did the last request fail?
- Show me recent slow traces.
            """
        )

    st.divider()

    # DISPLAY OBSERVABILITY CHAT HISTORY
    
    for message in st.session_state["observability_messages"]:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

    # OBSERVABILITY QUERY FORM

    with st.form("observability_query_form",clear_on_submit=True):

        observability_question = st.text_area(

                "Observability question",

                placeholder=(
                    "Example: Why has my RAG "
                    "application been slow during "
                    "the last 30 minutes?"
                ),

                label_visibility="collapsed",

                key="observability_question",
            )
        

        investigate_button = (
            st.form_submit_button(

                "🔎 Investigate System",

                use_container_width=True,
            )
        )

    # SEND QUERY TO OBSERVABILITY AGENT
   
    if investigate_button:

        observability_question = observability_question.strip()
        
        if not observability_question:

            st.warning("Please enter an observability question.")

        else:

            st.session_state["observability_messages"].append(
                {
                    "role":"user",

                    "content": observability_question,
                }
            )

            # DISPLAY USER MESSAGE

            with st.chat_message("user"):

                st.markdown(observability_question)

            # CALL LANGCHAIN OBSERVABILITY AGENT
           
            with st.spinner("Investigating metrics, logs and traces..."):

                try:

                    response = requests.post(

                            OBSERVABILITY_API_URL,

                            json={
                                "question":observability_question
                            },

                            timeout=180,
                        )
                    
                    response.raise_for_status()

                    data = response.json()
                    
                    observability_answer = data["answer"]
                    
                    # STORE AGENT RESPONSE
                    st.session_state["observability_messages"].append(
                        {
                            "role":"assistant",

                            "content":observability_answer,
                        }
                    )

                    # DISPLAY AGENT RESPONSE
                    with st.chat_message("assistant"):

                        st.markdown(observability_answer)

                # CONNECTION ERROR
                except requests.exceptions.ConnectionError:

                    error_message = (
                        "Unable to connect to the "
                        "observability agent at "
                        f"{OBSERVABILITY_BASE_URL}."
                    )

                    st.error(error_message)

                    st.session_state["observability_messages"].append(
                        {
                            "role":"assistant",

                            "content":
                                (
                                    "⚠️ "
                                    f"{error_message}"
                                ),
                        }
                    )

                # TIMEOUT
                except requests.exceptions.Timeout:

                    error_message = ("The observability investigation took too long.")

                    st.error(error_message)

                # HTTP ERROR

                except requests.exceptions.HTTPError:

                    try:

                        error_data = response.json()
                    
                        error_message = (
                            error_data.get(
                                "detail",
                                (
                                    "Observability "
                                    "request failed."
                                ),
                            )
                        )


                    except Exception:

                        error_message = (
                            "Observability "
                            "request failed."
                        )

                    st.error(error_message)

                # GENERAL ERROR

                except Exception as e:

                    st.error(
                        "Something went wrong: "
                        f"{str(e)}"
                    )


    # CLEAR OBSERVABILITY CHAT
  
    if st.session_state["observability_messages"]:

        st.divider()

        clear_col1, clear_col2, clear_col3 = (
            st.columns(
                [
                    1,
                    2,
                    1,
                ]
            )
        )


        with clear_col2:

            if st.button(

                "🗑️ Clear Observability Chat",

                key="clear_observability_chat",

                use_container_width=True,
            ):

                st.session_state["observability_messages"] = []

                st.rerun()