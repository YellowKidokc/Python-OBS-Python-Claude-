# Theophysics Plugin System

A comprehensive Obsidian plugin system for academic research, featuring AI-powered classification, automatic linking, and semantic analysis.

## Overview

This system consists of three main components:

1. **Obsidian Plugin** (Frontend) - User interface within Obsidian
2. **Python Backend** (Brain) - AI processing, linking, and heavy computations
3. **Databases** (Memory) - SQLite (local cache) + PostgreSQL (global storage)

## Quick Start

### 1. Install Python Dependencies

```bash
cd python_backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and paths
```

### 3. Start the Backend

```bash
python main.py
```

The backend will start at `http://localhost:5000`

### 4. Install the Obsidian Plugin

(Plugin installation instructions coming soon)

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│    OBSIDIAN     │ ──── │     PYTHON      │ ──── │    DATABASES    │
│    PLUGIN       │      │     BACKEND     │      │  SQLite + PG    │
│                 │      │                 │      │                 │
│  (What you see) │      │  (Does the work)│      │ (Remembers it)  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## Features

### Tab 1: Axiom / Claim / Evidence Prompts
Customize AI prompts for different classification types.

### Tab 2: Custom Classifiers
Create your own classification rules for specific terms.

### Tab 3: Batch Processing
Classify multiple notes at once from any folder.

### Tab 4: Visual Map (Mermaid)
See relationships between concepts as flowcharts.

### Tab 5: UUID + Semantic Layers
Track exactly what part of a note each tag refers to.

### Tab 6: Right-Click Tools
Quick access to common actions via context menu.

### Tab 7: Vault Sync
Keep everything synchronized across devices.

## Project Structure

```
├── ARCHITECTURE.md          # Detailed system documentation
├── README.md                # This file
└── python_backend/
    ├── main.py              # Backend entry point
    ├── requirements.txt     # Python dependencies
    ├── classify/            # AI classification
    │   ├── ai_engine.py
    │   └── prompt_manager.py
    ├── tags/                # UUID and tag management
    │   ├── uuid_manager.py
    │   ├── tag_writer.py
    │   └── tag_parser.py
    ├── linking/             # Auto-linking and definitions
    │   ├── term_finder.py
    │   ├── definition_lookup.py
    │   └── auto_linker.py
    ├── database/            # Database operations
    │   ├── sqlite_db.py
    │   └── postgres_db.py
    ├── semantic/            # Semantic tree and diagrams
    │   ├── tree_builder.py
    │   └── mermaid_generator.py
    ├── sync/                # Vault and database sync
    │   ├── vault_scanner.py
    │   └── sync_engine.py
    ├── config/              # Configuration files
    │   └── settings.yaml
    └── prompts/             # AI prompt templates
        ├── axiom.txt
        ├── claim.txt
        └── evidence.txt
```

## Documentation

See [ARCHITECTURE.md](ARCHITECTURE.md) for comprehensive documentation including:
- Detailed explanation of each component
- All Python functions with examples
- Database schemas
- Data flow diagrams
- Step-by-step guides for beginners

## API Endpoints

### Classification & Tags
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check if backend is running |
| `/classify` | POST | Classify a single note |
| `/classify/batch` | POST | Classify multiple notes |
| `/uuid/generate` | POST | Generate a new UUID |
| `/tags/write` | POST | Write tags to a note |
| `/tags/parse` | POST | Read tags from a note |

### Paper Scanning & Linking (NEW)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scan/paper` | POST | Scan a paper, find terms, get definitions, create links |
| `/scan/folder` | POST | Scan all papers in a folder |
| `/terms/stats` | GET | Get statistics about all terms in database |
| `/terms/occurrences` | POST | Get all places where a term appears |
| `/terms/unlinked` | GET | Find terms that haven't been linked |
| `/terms/add` | POST | Manually add a term the system missed |
| `/definition/fetch` | POST | Fetch definition from Wikipedia and create file |
| `/terms/find` | POST | Find terms in a note |
| `/definition/lookup` | POST | Look up a definition |
| `/link/auto` | POST | Auto-link terms in a note |

### Semantic & Sync
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/semantic/tree` | POST | Build semantic tree |
| `/semantic/mermaid` | POST | Generate Mermaid diagram |
| `/sync/vault` | POST | Scan vault for changes |
| `/sync/perform` | POST | Perform full sync |

## Auto-Linking System

The system automatically:

1. **Scans papers** for proper nouns, technical terms, and phrases
2. **Looks up definitions** from:
   - Your local Definitions folder (highest priority)
   - SQLite cache (previously fetched)
   - Stanford Encyclopedia of Philosophy
   - Wikipedia (with full section extraction)
3. **Creates definition files** with all sections from Wikipedia
4. **Links terms** in your notes to definitions
5. **Builds a database** tracking every term and link

### Example Usage

```python
# Scan a single paper
POST /scan/paper
{
    "note_path": "/vault/papers/physics.md",
    "vault_path": "/vault"
}

# Returns:
{
    "terms_found": 15,
    "definitions_fetched": 12,
    "files_created": 10,
    "links_added": 8,
    "terms": [...]
}
```

## Configuration

Edit `python_backend/config/settings.yaml` to customize:
- Database connections
- AI provider and model
- Vault path
- Linking preferences
- Sync settings

## Environment Variables

Create a `.env` file in `python_backend/`:

```
OPENAI_API_KEY=sk-your-key-here
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=theophysics
PG_USER=postgres
PG_PASSWORD=your-password
VAULT_PATH=/path/to/your/vault
```

## Contributing

This project is in active development. See the issues for current tasks.

## License

MIT License
