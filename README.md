# HADES

HADES (Hybrid ArangoDB and Milvus Database Engine System) is a powerful system that combines document and vector storage capabilities.

## Features

- Hybrid search combining vector similarity and document filtering
- Modular architecture for easy extension
- Async-first design
- Comprehensive test coverage
- Type-safe configuration using Pydantic

## Installation

```bash
pip install -e .
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=hades
```

## License

MIT License
