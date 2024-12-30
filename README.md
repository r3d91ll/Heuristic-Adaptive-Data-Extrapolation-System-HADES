# Heuristic Adaptive Data Extraction System H.A.D.E.S. MCP Server

This repository contains a **Model Context Protocol (MCP) Server** (nicknamed “HADES”) that integrates:

- **ArangoDB** for document storage
- **Milvus** for vector storage
- **Pydantic** for configuration and validation
- **Asyncio** and concurrency patterns to serve multiple clients

The server handles **search, query execution, and other operations** via a custom “tool” interface, enabling easy extension of capabilities.

## 1. Environment Setup

Below is how you can create a fresh **Conda** environment for **Python 3.12** and install the necessary Python packages.

1. **Create and activate** a new Conda environment:

   ```bash
   conda create -n hades python=3.12 -y
   conda activate hades
   ```

2. **Upgrade build tools** (helps avoid build issues on new Python versions):

   ```bash
   pip install --upgrade pip setuptools wheel
   ```

3. **Install project requirements**:

   ```bash
   # Inside your hades environment
   pip install -r requirements.txt
   ```

Your `requirements.txt` might look like:

```text
pydantic
pydantic-settings
arango
pymilvus
mcp
```

> **Note:**  
>
> - The `mcp` package may be your internal or private library. Ensure you have access to it if it’s not on PyPI.  
> - If `grpcio` or other native extensions fail to compile on Python 3.12, you may need to install them via conda-forge or use a specific version.

## 2. Sample Docker Setup (ArangoDB & Milvus)

Below is a minimal **Docker Compose** snippet to spin up **ArangoDB** and **Milvus** for local testing. It uses default ports and sets example passwords. **Do not** use these in production.

```yaml
version: "3.8"
services:
  arangodb:
    image: arangodb:3.12
    container_name: arangodb
    ports:
      - "8529:8529"
    environment:
      - ARANGO_ROOT_PASSWORD=p@$$W0rd

  milvus:
    image: milvusdb/milvus:2.3.0
    container_name: milvus
    ports:
      - "19530:19530"
    environment:
      - MILVUS_USER=root
      - MILVUS_PASSWORD=p@$$W0rd
```

**Steps**:

1. Save the file above as `docker-compose.yml`.  
2. Run `docker-compose up -d`.  
3. ArangoDB will be available at `http://localhost:8529` (user: `root`, pass: `p@$$W0rd`).  
4. Milvus will be listening on `localhost:19530` (user: `root`, pass: `p@$$W0rd`).  

You can now connect your MCP server to these services by configuring environment variables (e.g., `ARANGO_URL`, `ARANGO_USER`, `ARANGO_PASSWORD`, `MILVUS_HOST`, `MILVUS_PORT`, etc.).

## 3. Integrating with Your RAG Solution

This MCP server **assumes** you already have a retrieval-augmented generation pipeline or an LLM-based application that needs:

- Document queries from **ArangoDB**  
- Vector similarity searches from **Milvus**  

You can wire these services together by:

1. **Setting environment variables** that point to your local or remote ArangoDB and Milvus instances.
2. **Starting the MCP server** (e.g., `python HADES-MCP-Server.py`) or however your main entry script is named.  
3. **Sending requests** from your RAG system to the MCP server’s endpoints or via stdio protocol (depending on how your tool calls are orchestrated).

## 4. Usage

Once your databases are up and this server is installed:

1. **Run the MCP server**:

   ```bash
   python HADES-MCP-Server.py
   ```

   or whichever file provides the MCP server entry point.

2. **Check logs** to see if the server connected successfully to ArangoDB and Milvus. By **default**, logs are sent to **stdout**. You’ll see output like:

   ```text
   2024-01-02 12:34:56 - VectorDBMCPServer - INFO - <module>:123 - Vector DB MCP Server running
   2024-01-02 12:34:56 - VectorDBMCPServer - INFO - <module>:124 - Connected to ArangoDB: _system
   2024-01-02 12:34:56 - VectorDBMCPServer - INFO - <module>:125 - Connected to Milvus: localhost:19530
   ```

   If you want to **redirect logs** to a file instead of stdout, modify the `logging.basicConfig(...)` call in your script to specify a `filename=...` parameter.

3. **Send requests** from your RAG solution or any other client. For example:
   - A tool call to `execute_query` for running an AQL query  
   - A tool call to `hybrid_search` for vector+doc retrieval  

## 5. Troubleshooting

- If **grpcio** fails to install for Python 3.12, try:
  - `pip install --upgrade pip setuptools wheel`  
  - `pip install grpcio==<some-version>` that provides wheels for 3.12  
  - Or `conda install grpcio -c conda-forge`

- Check **Docker logs**:

  ```bash
  docker logs arangodb
  docker logs milvus
  ```

  to see if either service failed to start.

- Make sure **credentials** in your environment match those in the `docker-compose.yml`.

## 6. License & Support

This code is offered **as is**, with no explicit license or warranty implied. Please reach out to the repository owner or your internal support channels for assistance.

---

*Enjoy building your RAG workflows with the HADES MCP Server!*
