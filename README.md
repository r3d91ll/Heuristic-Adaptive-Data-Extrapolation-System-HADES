# HADES (Heuristic Adaptive Data Extraction System)

HADES is a sophisticated system designed to perform intelligent data extraction and code generation using a combination of vector search (Milvus), graph database queries (Neo4j), and natural language processing.

## Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Front-end Setup](#front-end-setup)
4. [Back-end Setup](#back-end-setup)
5. [Database Setup](#database-setup)
6. [Docker Configuration](#docker-configuration)
7. [Running the Application](#running-the-application)
8. [Development Workflow](#development-workflow)
9. [Troubleshooting](#troubleshooting)

## Project Overview

HADES combines the power of vector search, graph databases, and natural language processing to provide a versatile system for data extraction and code generation. It uses Milvus for efficient vector similarity search, Neo4j for complex graph queries, and a custom NLP model for understanding and generating code.

## System Architecture

The HADES system consists of the following components:

1. React Front-end
2. Node.js Back-end
3. Milvus Vector Database
4. Neo4j Graph Database
5. Docker for containerization and orchestration

## Front-end Setup

The front-end is built using React with TypeScript and Vite for fast development and building. It uses Tailwind CSS for styling and Lucide React for icons.

### Key Files:

- `src/App.tsx`: Main application component
- `src/components/QueryInput.tsx`: Component for user input
- `src/components/ResultDisplay.tsx`: Component for displaying query results
- `src/utils/queryProcessor.ts`: Utility for processing queries
- `src/index.css`: Global styles and Tailwind CSS configuration

### Front-end Structure:

The front-end follows a component-based architecture:

- `App.tsx` serves as the main container, managing the overall layout and state.
- `QueryInput` handles user input and query submission.
- `ResultDisplay` renders the results returned from the back-end.
- The `queryProcessor` utility handles communication with the back-end API.

Styling is primarily done using Tailwind CSS classes, with some custom styles in `index.css` for scrollbar customization.

## Back-end Setup

The back-end is a Node.js application using Express.js for the web server. It interfaces with Milvus and Neo4j to process queries.

### Key Files:

- `server.js`: Main server file containing the Express application and route handlers

### Back-end Structure:

The `server.js` file sets up an Express server with the following features:

- CORS middleware for handling cross-origin requests
- JSON body parsing for processing request bodies
- A POST route at `/query` for handling all query requests
- Connections to Milvus and Neo4j databases
- Error handling and response formatting

The server determines the type of query (Milvus, Neo4j, or code generation) based on the input and delegates to the appropriate service.

## Database Setup

### Milvus:

Milvus is used for vector similarity search. In the current setup, it's configured with:

- Etcd for metadata storage
- MinIO for object storage

### Neo4j:

Neo4j is used for graph database queries. It's set up with basic authentication in this development environment.

## Docker Configuration

The project uses Docker for containerization and Docker Compose for orchestrating the multi-container application.

### Key Files:

- `Dockerfile.frontend`: Dockerfile for building the front-end container
- `Dockerfile.backend`: Dockerfile for building the back-end container
- `docker-compose.yml`: Docker Compose configuration for all services

### Docker Compose Services:

1. `frontend`: React application
2. `backend`: Node.js server
3. `milvus`: Milvus vector database
4. `etcd`: Distributed key-value store for Milvus
5. `minio`: Object storage for Milvus
6. `neo4j`: Neo4j graph database

## Running the Application

To run the application:

1. Ensure Docker and Docker Compose are installed on your system.
2. Navigate to the project root directory.
3. Run the following command:

   ```
   docker-compose up --build
   ```

4. Access the application at `http://localhost:5173` in your web browser.

## Development Workflow

1. Front-end development:
   - Make changes to React components in the `src` directory.
   - The Vite dev server will automatically reload changes.

2. Back-end development:
   - Modify `server.js` for API changes.
   - Restart the backend container to apply changes:
     ```
     docker-compose restart backend
     ```

3. Database modifications:
   - For significant changes to Milvus or Neo4j, update the respective sections in `docker-compose.yml`.
   - Rebuild and restart the affected services:
     ```
     docker-compose up -d --build <service_name>
     ```

## Troubleshooting

- If the front-end can't connect to the back-end, ensure the `VITE_API_URL` in `docker-compose.yml` is correct.
- For database connection issues, check the connection strings in `server.js` and ensure the database services are running.
- To view logs for a specific service:
  ```
  docker-compose logs <service_name>
  ```

For more detailed troubleshooting, refer to the documentation of individual components (React, Express, Milvus, Neo4j).

[Edit in StackBlitz next generation editor ⚡️](https://stackblitz.com/~/github.com/r3d91ll/HADES)
