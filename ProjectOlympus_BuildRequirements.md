### **System Overview**

#### **Components**

1. **Backend (Hephaestus)**:
   - FastAPI for implementing MCP and RAG APIs.
   - Integration with ArangoDB (H.A.D.E.S.) for graph-based queries and FAISS for vector similarity search.

2. **Frontend (Athena)**:
   - Streamlit for basic chat functionality, file upload, and context/query management.

3. **Database (H.A.D.E.S.)**:
   - ArangoDB for document storage, relationships, and semantic queries.
   - Milvus for Vector store
   	**references to FAISS below shoudl be removed as we will be using Milvus for our vector store.**
   - H.A.D.E.S. is a standalone entity and integral part of Olympus but seprate none the less.
   		- the specialized nature of RAG (security and data-management) require segregation from the rest of the application
   		- this means for now a seprate container and an adjacent but semi-seprate development cycle.

4. **Security**:
   - HTTPS implementation with Let's Encrypt.
   - Docker security practices including non-root users, resource limits, and read-only file systems.

---

### **Detailed Steps**

#### **1. Initial Setup for Hephaestus**

**Dockerfile for Hephaestus**

dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    TZ=Etc/UTC

# System dependencies
RUN apt-get update && apt-get install -y \
    python3.9 python3.9-distutils python3-pip \
    git wget curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set Python symlink
RUN ln -sf /usr/bin/python3.9 /usr/bin/python

# Python dependencies
RUN python3 -m pip install --upgrade pip && \
    pip install transformers accelerate bitsandbytes huggingface_hub faiss-cpu

# Additional tools
RUN pip install jupyterlab ipywidgets matplotlib

# Working directory
WORKDIR /workspace

# Expose Jupyter port
EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--allow-root"]



## Adding Pheonix Arize AI monitoring to Hephaestus

1. **Identify Connection Details**  
   - Confirm the host/port or endpoint URL your self-hosted Phoenix instance exposes. For example, PHOENIX_BASE_URL=http://phoenix.internal:9000/.  
   - If Phoenix uses an API key or token, have that ready to pass along in HTTP requests.

2. **Install Phoenix/Arize Client Libraries**  
   - Ensure your Hephaestus Dockerfile (or environment) has the Python SDK for Phoenix installed. You can typically do:

     

bash
     pip install arize-phoenix



   - If you’re using a custom or internal version of the Phoenix package (depending on how your LadonStack is configured), update your installation steps accordingly.

3. **Configure Environment Variables**  
   - In your .env or Docker Compose file, define any necessary environment variables. For instance:

     

bash
        # .env
        PHOENIX_COLLECTOR_ENDPOINT='http://0.0.0.0:6006'



   - If you store them in .env, ensure your code reads these values securely (e.g., via os.getenv in Python).

4. **Add Logging Calls in Hephaestus**  
   - In your FastAPI routes (or wherever you generate embeddings/inferences), log data to Phoenix. Here’s a simplified example:

     

python
     import os
     import numpy as np
     import structlog
     from fastapi import FastAPI
     from arize_phoenix import log_data  # or your internal Phoenix import path

     app = FastAPI()
     logger = structlog.get_logger("olympus")

     PHOENIX_BASE_URL = os.getenv("PHOENIX_BASE_URL")
     PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY")

     @app.post("/mcp/{session_id}/query")
     def query_context(session_id: str, query: dict):
         user_input = query["input"]
         # Generate embedding
         user_input_embedding = model.encode(user_input)

         # Example call to your Phoenix instance
         log_data(
             embedding=user_input_embedding,
             text=user_input,
             session_id=session_id,
             metadata={"source": "Hephaestus", "api_key": PHOENIX_API_KEY},
             base_url=PHOENIX_BASE_URL
         )

         # Continue with your FAISS/Arango retrieval
         distances, indices = faiss_index.search(np.array([user_input_embedding]), k=5)
         ...
         return {"results": "some results"}



   - Adjust parameters for your actual usage:
     - **metadata**: Add fields like user ID, timestamp, model version, or environment.  
     - **base_url** & **api_key**: Pass them however your internal Phoenix library expects.

5. **Validate in LadonStack**  
   - After you deploy Hephaestus, send a test query and confirm the data flows into your Phoenix dashboards or logs.  
   - If you have pre-existing dashboards or visualizations, ensure they pick up new fields (e.g., embedding vectors) from Hephaestus.

---

## **Additional Considerations**

1. **Batch Logging vs. Real-Time**  
   - Depending on traffic, real-time logging can be resource-intensive. If you expect high throughput, consider a background queue or batch mechanism to avoid slowing down your inference pipeline.

2. **Data Privacy & Redaction**  
   - If queries contain sensitive info, you may need to redact or anonymize them before sending to Phoenix.  
   - Check your company’s data governance policies to ensure compliance.

3. **Alerts & Thresholds**  
   - Since you already have LadonStack in place, it’s worth creating automated rules or alerts (e.g., on embedding drift or high error rates).  
   - Phoenix can visualize embedding outliers, but hooking it into your existing alert manager (like Prometheus, Grafana, etc.) can give you complete coverage.

4. **Versioning**  
   - If you plan on iterative model updates, ensure you include **model version** in the metadata. This way, you can compare performance over time as you push new LLM releases.

5. **Performance Implications**  
   - If you’re adding calls to Phoenix for every single user query, pay attention to latencies. Caching or asynchronous logging can help if you notice slowdowns.

---

### **Conclusion**

Because you already have a self-hosted Phoenix within your LadonStack, the main task is to:

1. **Install the Phoenix/Arize client in your Hephaestus environment.**  
2. **Add logging calls to your inference and embedding flows.**  
3. **Pass the correct base URL and credentials for your local Phoenix instance.**

Once done, you’ll have real-time monitoring and observability of embeddings and LLM interactions—allowing for easy debugging, drift detection, and performance insights.

## **Hugging Face Workflow**

1. **Model Download and Management**:
   - Use the transformers library to download models from Hugging Face.
   - Cache models in a RAMFS directory for fast access during testing.

2. **Model Inference Example**:

   

python
   from transformers import AutoTokenizer, AutoModelForCausalLM

   # Load model and tokenizer
   model_name = "gpt2"
   tokenizer = AutoTokenizer.from_pretrained(model_name)
   model = AutoModelForCausalLM.from_pretrained(model_name)

   # Perform inference
   input_text = "Translate this sentence into French: Hello, how are you?"
   inputs = tokenizer(input_text, return_tensors="pt")
   outputs = model.generate(**inputs)
   print(tokenizer.decode(outputs[0], skip_special_tokens=True))



3. **Quantization for Larger Models**:
   - Use bitsandbytes for model quantization to reduce memory usage.
   - Example:

     

python
     from transformers import AutoModelForCausalLM
     from bitsandbytes.optim import GlobalOptimManager

     model = AutoModelForCausalLM.from_pretrained("bigscience/bloom", load_in_8bit=True)



4. **Integration with FAISS**:
   - Generate embeddings for documents using Hugging Face models.
   - Store embeddings in FAISS for vector similarity searches.

---

### **2. Backend Setup (H.A.D.E.S.)**

**Dockerfile for H.A.D.E.S.**

dockerfile
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip install fastapi uvicorn pydantic python-arango numpy faiss-cpu transformers structlog

# Set working directory
WORKDIR /app

# Copy application files
COPY . /app

# Expose API port
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]



#### **API Endpoints**

1. **Context Management**:
   - **Add Context**:

     

python
     @app.post("/mcp/{session_id}/add_context")
     def add_context(session_id: str, context: dict):
         context_store[session_id] = context_store.get(session_id, "") + " " + context["content"]
         return {"message": f"Context added for session {session_id}."}



   - **Get Context**:

     

python
     @app.get("/mcp/{session_id}/get_context")
     def get_context(session_id: str):
         return {"session_id": session_id, "context": context_store.get(session_id, "")}



   - **Clear Context**:

     

python
     @app.delete("/mcp/{session_id}/clear_context")
     def clear_context(session_id: str):
         context_store[session_id] = ""
         return {"message": f"Context cleared for session {session_id}."}



2. **Query MCP with H.A.D.E.S.**:

   

python
   @app.post("/mcp/{session_id}/query")
   def query_context(session_id: str, query: dict):
       # Generate query embedding
       query_embedding = model.encode(query["input"])

       # Perform FAISS search
       distances, indices = faiss_index.search(np.array([query_embedding]), k=5)

       # Fetch related metadata from H.A.D.E.S.
       results = []
       for idx in indices[0]:
           doc_id = document_ids[idx]
           doc_data = arango_client.collection("documents").get(doc_id)
           results.append(doc_data)

       return {
           "session_context": context_store.get(session_id, ""),
           "retrieved_documents": results,
       }



3. **Add Document to H.A.D.E.S.**:

   

python
   @app.post("/rag/add_document")
   def add_document(document: dict):
       text_chunks = split_text(document["content"])
       embeddings = [model.encode(chunk) for chunk in text_chunks]
       for embedding in embeddings:
           faiss_index.add(np.array([embedding]))
       arango_client.collection("documents").insert({"_key": document["filename"], "chunks": len(text_chunks)})
       return {"message": "Document added successfully"}



#### **Logging Implementation**

python
import structlog
import logging.config

logging.config.dictConfig({
    "version": 1,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "olympus": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
})

logger = structlog.get_logger("olympus")



---

#### **3. Frontend Setup (Athena)**

**Streamlit Front End**

python
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.sidebar.title("Navigation")
option = st.sidebar.selectbox("Select an option", ["Chat with Model", "Upload Files", "Query Context"])

if option == "Chat with Model":
    st.title("Athena: Chat Interface")
    ...

elif option == "Upload Files":
    st.title("Upload Files for Embedding")
    uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True)
    if st.button("Process Files"):
        for file in uploaded_files:
            content = file.read().decode("utf-8")
            payload = {"filename": file.name, "content": content}
            response = requests.post(f"{API_URL}/rag/add_document", json=payload)
            if response.status_code == 200:
                st.success(f"File {file.name} processed successfully!")
            else:
                st.error(f"Failed to process file {file.name}.")

elif option == "Query Context":
    st.title("Query MCP Context via Athena")
    session_id = st.text_input("Session ID", "default_session")
    query_input = st.text_input("Your Query")
    if st.button("Submit Query"):
        payload = {"input": query_input}
        response = requests.post(f"{API_URL}/mcp/{session_id}/query", json=payload)
        if response.status_code == 200:
            results = response.json()
            st.write("Session Context:", results.get("session_context"))
            st.write("Retrieved Documents:", results.get("retrieved_documents"))
        else:
            st.error("Failed to query the context.")



---

### **Deployment Steps**

1. **Installation Script**

   

bash
   #!/bin/bash
   # install.sh

   # Check system requirements
   check_requirements() {
     command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
     command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }
   }

   # Setup environment
   setup_environment() {
     # Generate secure random keys
     echo "ARANGO_ROOT_PASSWORD=$(openssl rand -hex 24)" > .env
     echo "API_KEY=$(openssl rand -hex 32)" >> .env
   }

   # Main installation flow
   main() {
     check_requirements
     setup_environment
     docker-compose up -d
     echo "Project Olympus is now running! Access Athena at https://localhost:8501"
   }

   main



2. **Build Backend**:

   

bash
   docker-compose up -d --build



3. **Access Athena**:
   - Navigate to http://localhost:8501 for the Athena interface.

4. **Test MCP Functionality**:
   - Use endpoints for context management and querying via H.A.D.E.S.

5. **Integrate Models**:
   - Load Hugging Face models into Hephaestus for embeddings and completions.

---

### **Future Enhancements**

1. **Real-Time Token Streaming**:
   - Add WebSocket support for streaming token outputs.
2. **

model = AutoModelForCausalLM.from_pretrained("bigscience/bloom", load_in_8bit=True)



4. **Integration with FAISS**:

   - Generate embeddings for documents using Hugging Face models.
   - Store embeddings in FAISS for vector similarity searches.

---

#### **2. Backend Setup**

**Dockerfile for Backend**

dockerfile
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip install fastapi uvicorn pydantic python-arango numpy faiss-cpu transformers structlog

# Set working directory
WORKDIR /app

# Copy application files
COPY . /app

# Expose API port
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]



**API Endpoints**

1. **Context Management**:
   - **Add Context**:

     

python
     @app.post("/mcp/{session_id}/add_context")
     def add_context(session_id: str, context: dict):
         context_store[session_id] = context_store.get(session_id, "") + " " + context["content"]
         return {"message": f"Context added for session {session_id}."}



   - **Get Context**:

     

python
     @app.get("/mcp/{session_id}/get_context")
     def get_context(session_id: str):
         return {"session_id": session_id, "context": context_store.get(session_id, "")}



   - **Clear Context**:

     

python
     @app.delete("/mcp/{session_id}/clear_context")
     def clear_context(session_id: str):
         context_store[session_id] = ""
         return {"message": f"Context cleared for session {session_id}."}



2. **Query MCP with ArangoDB and FAISS**:

   

python
   @app.post("/mcp/{session_id}/query")
   def query_context(session_id: str, query: dict):
       # Generate query embedding
       query_embedding = model.encode(query["input"])

       # Perform FAISS search
       distances, indices = faiss_index.search(np.array([query_embedding]), k=5)

       # Fetch related metadata from ArangoDB
       results = []
       for idx in indices[0]:
           doc_id = document_ids[idx]
           doc_data = arango_client.collection("documents").get(doc_id)
           results.append(doc_data)

       return {
           "session_context": context_store.get(session_id, ""),
           "retrieved_documents": results,
       }



3. **Add Document to RAG**:

   

python
   @app.post("/rag/add_document")
   def add_document(document: dict):
       text_chunks = split_text(document["content"])
       embeddings = [model.encode(chunk) for chunk in text_chunks]
       for embedding in embeddings:
           faiss_index.add(np.array([embedding]))
       arango_client.collection("documents").insert({"_key": document["filename"], "chunks": len(text_chunks)})
       return {"message": "Document added successfully"}



**Logging Implementation**

python
import structlog
import logging.config

logging.config.dictConfig({
    "version": 1,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "olympus": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
})

logger = structlog.get_logger("olympus")



---

#### **3. Frontend Setup**

**Streamlit Front End**

python
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.sidebar.title("Navigation")
option = st.sidebar.selectbox("Select an option", ["Chat with Model", "Upload Files", "Query Context"])

if option == "Chat with Model":
    st.title("Chat with Model")
    ...

elif option == "Upload Files":
    st.title("Upload Files for Embedding")
    uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True)
    if st.button("Process Files"):
        for file in uploaded_files:
            content = file.read().decode("utf-8")
            payload = {"filename": file.name, "content": content}
            response = requests.post(f"{API_URL}/rag/add_document", json=payload)
            if response.status_code == 200:
                st.success(f"File {file.name} processed successfully!")
            else:
                st.error(f"Failed to process file {file.name}.")

elif option == "Query Context":
    st.title("Query MCP Context")
    session_id = st.text_input("Session ID", "default_session")
    query_input = st.text_input("Your Query")
    if st.button("Submit Query"):
        payload = {"input": query_input}
        response = requests.post(f"{API_URL}/mcp/{session_id}/query", json=payload)
        if response.status_code == 200:
            results = response.json()
            st.write("Session Context:", results.get("session_context"))
            st.write("Retrieved Documents:", results.get("retrieved_documents"))
        else:
            st.error("Failed to query the context.")



---

#### **4. Database Setup**

**ArangoDB Configuration**

1. Create collections:
   - documents: Stores document metadata.
   - edges: Stores relationships between documents.

**Sample AQL Queries**

- Retrieve all documents:

  

aql
  FOR doc IN documents RETURN doc



- Graph traversal:

  

aql
  FOR v, e, p IN 1..3 OUTBOUND "documents/doc_id" edges RETURN v



---

### **Deployment Steps**

1. **Installation Script**

   

bash
   #!/bin/bash
   # install.sh

   # Check system requirements
   check_requirements() {
     command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
     command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }
   }

   # Setup environment
   setup_environment() {
     # Generate secure random keys
     echo "ARANGO_ROOT_PASSWORD=$(openssl rand -hex 24)" > .env
     echo "API_KEY=$(openssl rand -hex 32)" >> .env
   }

   # Main installation flow
   main() {
     check_requirements
     setup_environment
     docker-compose up -d
     echo "Olympus is now running! Access the interface at https://localhost:8501"
   }

   main



2. **Build Backend**:

   

bash
   docker-compose up -d --build



3. **Access Frontend**:
   - Navigate to http://localhost:8501 for Streamlit.

4. **Test MCP Functionality**:
   - Use endpoints for context management and querying.

5. **Integrate Models**:
   - Load Hugging Face models into the backend for embeddings and completions.

---

### **Future Enhancements**

1. **Real-Time Token Streaming**:
   - Add WebSocket support for streaming token outputs.
2. **Advanced Graph Traversals**:
   - Implement custom graph algorithms in ArangoDB.
3. **Persistent Context Storage**:
   - Store session contexts in ArangoDB for long-term use.
4. **User Management**:
   - Prepare database schema for user authentication and roles.
5. **Monitoring and Scaling**:
   - Add endpoints for system health and metrics.
