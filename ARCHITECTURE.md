# Theophysics Plugin System - Complete Architecture Guide

**For Beginning Programmers**

*This document explains the entire system in plain English, breaking down what each piece does and how they all work together.*

---

## Table of Contents

1. [What Is This System?](#what-is-this-system)
2. [The Three Main Parts](#the-three-main-parts)
3. [How Data Flows Through the System](#how-data-flows-through-the-system)
4. [Tab-by-Tab Breakdown](#tab-by-tab-breakdown)
5. [The Obsidian Plugin (Frontend)](#the-obsidian-plugin-frontend)
6. [The Python Backend (Brain)](#the-python-backend-brain)
7. [SQLite (Local Cache)](#sqlite-local-cache)
8. [PostgreSQL (Global Database)](#postgresql-global-database)
9. [The Smart Linking System](#the-smart-linking-system)
10. [Putting It All Together](#putting-it-all-together)

---

## What Is This System?

Think of this like a **smart research assistant** that lives inside your Obsidian vault. It can:

- **Read your notes** and understand what they're about
- **Tag important concepts** like axioms, claims, and evidence
- **Link related ideas** together automatically
- **Define terms** by looking them up or using your own definitions
- **Remember everything** in a database so nothing gets lost
- **Show you connections** between all your research

The system has three main parts that talk to each other:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│    OBSIDIAN     │ ──── │     PYTHON      │ ──── │    DATABASES    │
│    PLUGIN       │      │     BACKEND     │      │  SQLite + PG    │
│                 │      │                 │      │                 │
│  (What you see) │      │  (Does the work)│      │ (Remembers it)  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

## The Three Main Parts

### 1. The Obsidian Plugin (Frontend)
**What it is:** The part you actually see and click on in Obsidian.

**Think of it like:** The steering wheel and dashboard of a car. You use it to control things, and it shows you what's happening.

**It handles:**
- Showing buttons, menus, and tabs
- Displaying your notes with highlighted links
- Right-click menus for quick actions
- Sending requests to the Python backend
- Showing results back to you

### 2. The Python Backend (Brain)
**What it is:** A program running on your computer that does all the heavy thinking.

**Think of it like:** The engine of a car. You don't see it, but it does all the real work.

**It handles:**
- Running AI to classify your notes
- Finding proper nouns and keywords
- Looking up definitions from the internet
- Creating and managing unique IDs (UUIDs)
- Reading and writing to databases
- Processing multiple notes at once (batch)

### 3. The Databases (Memory)
**What they are:** Two databases that remember everything.

**SQLite** = Your local, fast notepad (works offline)
**PostgreSQL** = Your permanent filing cabinet (syncs everywhere)

**Think of it like:** SQLite is sticky notes on your desk. PostgreSQL is the master binder in the archive room. The sticky notes get filed into the binder regularly.

---

## How Data Flows Through the System

Here's what happens when you tag something in a note:

```
Step 1: You click "Classify Note" in Obsidian
            │
            ▼
Step 2: Plugin sends note text to Python backend
            │
            ▼
Step 3: Python runs AI to find axioms, claims, etc.
            │
            ▼
Step 4: Python creates tag blocks like:
        %%tag::Claim::uuid123::"Light bends"::sentence456%%
            │
            ▼
Step 5: Python saves to SQLite (instant, local)
            │
            ▼
Step 6: Python adds tag blocks to your note file
            │
            ▼
Step 7: Plugin shows you the results
            │
            ▼
Step 8: (Later) SQLite syncs to PostgreSQL
```

---

## Tab-by-Tab Breakdown

Your plugin will have several tabs. Here's what each one does:

---

### Tab 1: Axiom / Claim / Evidence Prompts

**What it does:** Let you customize the instructions the AI uses when tagging.

**Example:** You might tell the AI:
> "When looking for axioms, find statements that are assumed to be true without proof."

| Who Does What | Responsibility |
|---------------|----------------|
| **Plugin** | Shows text boxes where you type prompts for each tag type (Axiom, Claim, Evidence). Saves your changes. When you click "Classify", sends note + prompt to Python. |
| **Python** | Receives note + prompt. Sends to AI (like GPT). Gets back a list of found items. Formats them as tag blocks. Returns to plugin. |
| **PostgreSQL** | Stores the prompts (optional). Stores all tags that were created. |

**Visual:**
```
┌────────────────────────────────────────────┐
│  Tab: Axiom Prompt                         │
├────────────────────────────────────────────┤
│                                            │
│  Prompt for finding Axioms:                │
│  ┌──────────────────────────────────────┐  │
│  │ Find statements that are assumed    │  │
│  │ true without requiring proof. These │  │
│  │ are foundational beliefs or...      │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  [Save Prompt]  [Test on Current Note]     │
│                                            │
└────────────────────────────────────────────┘
```

---

### Tab 2: Custom Classifiers

**What it does:** Create your own rules for specific words or phrases.

**Example:** You say:
> "Every time you see 'quantum entanglement', use this special prompt to classify it."

| Who Does What | Responsibility |
|---------------|----------------|
| **Plugin** | Shows a form to enter: trigger word/phrase + custom prompt. When that word appears in a note, automatically runs classification. |
| **Python** | Stores custom rules. When processing notes, checks if any trigger words exist. Runs the custom prompt for matches. |
| **PostgreSQL** | Stores all custom classifier rules. Stores results from those classifiers. |

**Visual:**
```
┌────────────────────────────────────────────┐
│  Tab: Custom Classifiers                   │
├────────────────────────────────────────────┤
│                                            │
│  ┌─ Rule 1 ───────────────────────────┐    │
│  │ Trigger: "quantum entanglement"    │    │
│  │ Prompt: "Explain the physics..."   │    │
│  │ [Edit] [Delete] [Test]             │    │
│  └────────────────────────────────────┘    │
│                                            │
│  ┌─ Rule 2 ───────────────────────────┐    │
│  │ Trigger: "Gödel"                   │    │
│  │ Prompt: "Note any references to..."│    │
│  │ [Edit] [Delete] [Test]             │    │
│  └────────────────────────────────────┘    │
│                                            │
│  [+ Add New Rule]                          │
│                                            │
└────────────────────────────────────────────┘
```

---

### Tab 3: Batch Processing

**What it does:** Classify many notes at once from a folder.

**Example:** You select your "Research Papers" folder with 50 notes and say "Classify all of these."

| Who Does What | Responsibility |
|---------------|----------------|
| **Plugin** | Shows folder picker. Counts notes. Estimates how long it will take. Shows progress bar. Displays summary when done. |
| **Python** | Receives list of notes. Processes each one with AI. Returns tag blocks for each. Reports progress back to plugin. |
| **PostgreSQL** | Stores all generated tags. Stores batch job history (which notes processed, when, results). |

**Visual:**
```
┌────────────────────────────────────────────┐
│  Tab: Batch Processing                     │
├────────────────────────────────────────────┤
│                                            │
│  Select Folder: [Research Papers    ▼]     │
│                                            │
│  Notes Found: 47                           │
│  Estimated Tokens: ~23,500                 │
│  Estimated Cost: $0.47                     │
│                                            │
│  [Start Batch Processing]                  │
│                                            │
│  ─────────────────────────────────────     │
│  Progress: ████████████░░░░░ 64%           │
│                                            │
│  ✅ paper1.md - 3 Axioms, 1 Evidence       │
│  ✅ paper2.md - 2 Claims, 2 Evidence       │
│  ⏳ paper3.md - Processing...              │
│  ⬚ paper4.md - Queued                      │
│                                            │
└────────────────────────────────────────────┘
```

---

### Tab 4: Visual Map (Mermaid)

**What it does:** Shows a graph/flowchart of how ideas connect.

**Example:** See how an Axiom leads to a Claim which is supported by Evidence.

| Who Does What | Responsibility |
|---------------|----------------|
| **Plugin** | Displays Mermaid diagrams in a panel. Lets you click nodes to jump to notes. Toggle between single-note and multi-note views. |
| **Python** | Builds the graph structure from all your tags. Finds relationships across documents. Returns Mermaid code to plugin. |
| **PostgreSQL** | Stores relationship data (what connects to what). Provides data for complex cross-note graphs. |

**Visual:**
```
┌────────────────────────────────────────────┐
│  Tab: Visual Map                           │
├────────────────────────────────────────────┤
│                                            │
│    ┌─────────┐                             │
│    │ Axiom 1 │                             │
│    └────┬────┘                             │
│         │                                  │
│         ▼                                  │
│    ┌─────────┐     ┌─────────┐             │
│    │ Claim A │────▶│ Claim B │             │
│    └────┬────┘     └────┬────┘             │
│         │               │                  │
│         ▼               ▼                  │
│    ┌──────────┐   ┌──────────┐             │
│    │Evidence 1│   │Evidence 2│             │
│    └──────────┘   └──────────┘             │
│                                            │
│  [View: Single Note ▼] [Refresh] [Export]  │
│                                            │
└────────────────────────────────────────────┘
```

---

### Tab 5: UUID + Semantic Layers

**What it does:** Track exactly what part of a note a tag refers to (note, paragraph, sentence, or word level).

**What's a UUID?** A "Universally Unique Identifier" - a random code that uniquely identifies something. Like a social security number for your data.

| Who Does What | Responsibility |
|---------------|----------------|
| **Plugin** | Assigns UUIDs when tags are created. Shows which level (note/paragraph/sentence) a tag applies to. Adds UUID blocks at the bottom of notes. |
| **Python** | Master UUID generator (prevents duplicates). Maintains parent/child relationships. Builds semantic tree structure. |
| **PostgreSQL** | Stores all UUIDs. Tracks what each UUID refers to. Maintains the full hierarchy. |

**Example Tag Block:**
```markdown
%%tag::Claim::uuid-claim-7x3f::"Time dilates near mass"::sentence-uuid-9k2m%%
```

This means:
- Type: Claim
- Tag ID: uuid-claim-7x3f
- Content: "Time dilates near mass"
- Location: sentence with ID sentence-uuid-9k2m

**Visual:**
```
┌────────────────────────────────────────────┐
│  Tab: Semantic Layers                      │
├────────────────────────────────────────────┤
│                                            │
│  Note: theory_of_relativity.md             │
│                                            │
│  📄 Note Level (uuid-note-abc)             │
│   └── 📑 Paragraph 1 (uuid-para-123)       │
│       ├── 📝 Sentence 1 (uuid-sent-456)    │
│       │   └── 🏷️ Axiom: "Space is curved" │
│       └── 📝 Sentence 2 (uuid-sent-457)    │
│           └── 🏷️ Claim: "Light bends"     │
│   └── 📑 Paragraph 2 (uuid-para-124)       │
│       └── 📝 Sentence 3 (uuid-sent-458)    │
│           └── 🏷️ Evidence: "1919 eclipse" │
│                                            │
│  [Show Raw UUIDs] [Collapse All] [Export]  │
│                                            │
└────────────────────────────────────────────┘
```

---

### Tab 6: Right-Click Tools

**What it does:** Quick actions available when you right-click on text or notes.

| Who Does What | Responsibility |
|---------------|----------------|
| **Plugin** | Adds menu items to right-click context menu. Captures selected text. Sends commands to Python. Updates note with results. |
| **Python** | Performs the requested action (classify, generate map, add tag). Returns results to plugin. |
| **PostgreSQL** | Logs actions (optional). Stores any created tags or links. |

**Available Right-Click Actions:**
- "Classify This Note" - Run AI classification
- "Classify Selection" - Classify just the highlighted text
- "Show Semantic Layer" - Toggle hidden tag blocks visible
- "Generate Map" - Create Mermaid diagram
- "Add to Glossary" - Create definition for selected term
- "Link This Term" - Auto-link to known sources

---

### Tab 7: Vault Sync

**What it does:** Keep the plugin, Python backend, and databases all in sync.

| Who Does What | Responsibility |
|---------------|----------------|
| **Plugin** | Detects when notes are saved or changed. Sends update notifications to Python. Shows sync status. |
| **Python** | Compares notes to database. Finds what changed. Updates SQLite and PostgreSQL. Reports sync status. |
| **PostgreSQL** | The "source of truth" - stores the canonical version of all data. |

**Visual:**
```
┌────────────────────────────────────────────┐
│  Tab: Vault Sync                           │
├────────────────────────────────────────────┤
│                                            │
│  Sync Status: ✅ All Synced                │
│  Last Sync: 2 minutes ago                  │
│                                            │
│  ┌─────────────────────────────────────┐   │
│  │ Vault Notes:        247             │   │
│  │ SQLite Records:     247             │   │
│  │ PostgreSQL Records: 245             │   │
│  │ Pending Sync:       2               │   │
│  └─────────────────────────────────────┘   │
│                                            │
│  [Sync Now] [View Pending] [Force Refresh] │
│                                            │
│  Recent Activity:                          │
│  • paper1.md synced to PostgreSQL          │
│  • paper2.md updated in SQLite             │
│  • 3 new definitions added                 │
│                                            │
└────────────────────────────────────────────┘
```

---

## The Obsidian Plugin (Frontend)

### What the Plugin Does

The plugin is written in **TypeScript** (a safer version of JavaScript). It runs inside Obsidian and handles everything you see and click.

### Plugin Responsibilities Checklist

| Task | Description |
|------|-------------|
| ✅ Display UI | Show tabs, buttons, panels, menus |
| ✅ Handle Clicks | Respond when you click buttons or menu items |
| ✅ Read Notes | Get the content of the current note |
| ✅ Highlight Text | Show linked terms in a different color |
| ✅ Show Popups | Display definition cards on hover |
| ✅ Call Python | Send requests to the backend |
| ✅ Update Notes | Add tag blocks to note files |
| ✅ Store Settings | Remember your preferences |

### Plugin Does NOT:

| Task | Why Not |
|------|---------|
| ❌ Run AI | Too slow, would freeze Obsidian |
| ❌ Query Databases | Complex, better handled by Python |
| ❌ Web Lookups | Would slow down the interface |
| ❌ Heavy Processing | Keeps plugin fast and responsive |

---

## The Python Backend (Brain)

### What the Backend Does

The Python backend is a **separate program** that runs on your computer. The plugin talks to it (usually over HTTP on localhost).

### All Python Functions Explained

Here's every function the backend needs, explained simply:

---

#### AI & Classification Functions

```python
def classify_note(note_path, prompt_type):
    """
    What it does:
    Takes a note and a prompt type (like "axiom" or "claim")
    Sends the note text to AI (like GPT)
    Returns a list of tag blocks

    Example:
    Input: "theory.md", "axiom"
    Output: [
        {"type": "Axiom", "text": "Space is curved", "uuid": "ax-123"},
        {"type": "Axiom", "text": "Time is relative", "uuid": "ax-124"}
    ]
    """
    pass

def batch_classify(folder_path, prompt_type):
    """
    What it does:
    Same as classify_note, but for a whole folder
    Processes each note one by one
    Returns results for all notes
    """
    pass

def reclassify_with_custom_prompt(note_path, custom_prompt):
    """
    What it does:
    Uses a user-written custom prompt instead of defaults
    Useful for special classification rules
    """
    pass
```

---

#### UUID & Tag Management Functions

```python
def generate_uuid(entity_type):
    """
    What it does:
    Creates a unique ID for something

    Example:
    Input: "claim"
    Output: "claim-7x3f9k2m"

    Different prefixes for different things:
    - note_abc123 (for notes)
    - para_def456 (for paragraphs)
    - sent_ghi789 (for sentences)
    - term_jkl012 (for terms/words)
    - claim_mno345 (for claims)
    """
    pass

def write_tag_blocks(tags, note_path):
    """
    What it does:
    Takes a list of tags and adds them to the bottom of a note

    Before: (note ends normally)
    After: (note ends with)
    %%tag::Claim::uuid123::"Light bends"::sentence456%%
    """
    pass

def parse_tags(note_path):
    """
    What it does:
    Reads a note and finds all existing tag blocks
    Returns them as a list you can work with
    """
    pass
```

---

#### Linking & Definition Functions

```python
def find_terms(note_path):
    """
    What it does:
    Scans a note for:
    - Proper nouns (Einstein, Newton)
    - Capitalized terms (Quantum Mechanics)
    - Domain keywords (entropy, axiom)

    Returns a list of found terms
    """
    pass

def lookup_definition(term):
    """
    What it does:
    Checks for a definition of a term

    Order of lookup:
    1. Local Definitions folder
    2. SQLite cache
    3. Stanford Encyclopedia of Philosophy
    4. Wikipedia
    5. Other academic sources

    Returns the definition and source
    """
    pass

def create_definition_file(term, definition, source):
    """
    What it does:
    Creates a new markdown file in your Definitions folder

    Creates: Definitions/consciousness.md

    Content:
    # Consciousness

    ## Short Definition
    The awareness of internal and external existence.

    ## Source
    Wikipedia: https://en.wikipedia.org/wiki/Consciousness
    """
    pass

def auto_link_note(note_path):
    """
    What it does:
    Finds all terms in a note
    Links them to their definitions
    Updates the note with links
    """
    pass
```

---

#### Database Functions

```python
def save_to_sqlite(data, table_name):
    """
    What it does:
    Saves data to the local SQLite database
    Fast and works offline
    """
    pass

def get_from_sqlite(query):
    """
    What it does:
    Retrieves data from SQLite
    Used for quick local lookups
    """
    pass

def sync_to_postgres():
    """
    What it does:
    Compares SQLite to PostgreSQL
    Uploads any new or changed data
    Marks items as "synced"
    """
    pass

def pull_from_postgres(uuid):
    """
    What it does:
    Gets specific data from PostgreSQL
    Used when you need the latest version
    """
    pass
```

---

#### Semantic Map Functions

```python
def build_semantic_tree(note_path):
    """
    What it does:
    Creates a hierarchy of:
    Note → Paragraphs → Sentences → Terms

    Each level has a UUID
    Tags are attached to specific levels
    """
    pass

def generate_mermaid_diagram(data):
    """
    What it does:
    Takes relationship data
    Creates Mermaid code for visualization

    Output example:
    graph TD
        A[Axiom 1] --> B[Claim A]
        B --> C[Evidence 1]
    """
    pass
```

---

#### Sync Functions

```python
def scan_vault(vault_path):
    """
    What it does:
    Looks at all notes in your vault
    Detects new or changed files
    Returns list of files needing processing
    """
    pass

def compare_timestamps():
    """
    What it does:
    Checks when files were last modified
    Compares to when they were last synced
    Identifies what needs updating
    """
    pass

def perform_sync():
    """
    What it does:
    Full sync operation:
    1. Scan vault for changes
    2. Update SQLite
    3. Push changes to PostgreSQL
    4. Report results
    """
    pass
```

---

## SQLite (Local Cache)

### What is SQLite?

SQLite is a **lightweight database** that lives in a single file on your computer. No server needed!

### Why Use SQLite?

| Benefit | Explanation |
|---------|-------------|
| **Fast** | Queries return instantly |
| **Offline** | Works without internet |
| **Simple** | Just one file, no setup |
| **Local** | Your data stays on your machine |

### What SQLite Stores

```
┌─────────────────────────────────────────────────────────┐
│                    SQLite Database                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   notes     │  │    tags     │  │ definitions │     │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤     │
│  │ id          │  │ id          │  │ id          │     │
│  │ title       │  │ uuid        │  │ term        │     │
│  │ path        │  │ type        │  │ definition  │     │
│  │ uuid        │  │ content     │  │ source      │     │
│  │ modified_at │  │ note_id     │  │ cached_at   │     │
│  │ synced      │  │ parent_uuid │  │ synced      │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   links     │  │ sync_queue  │  │custom_rules │     │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤     │
│  │ id          │  │ id          │  │ id          │     │
│  │ from_uuid   │  │ table_name  │  │ trigger     │     │
│  │ to_uuid     │  │ record_id   │  │ prompt      │     │
│  │ link_type   │  │ action      │  │ enabled     │     │
│  │ created_at  │  │ queued_at   │  │ created_at  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### SQLite Table Explanations

| Table | What It Stores |
|-------|----------------|
| `notes` | Every note in your vault - title, path, UUID, when it was changed |
| `tags` | All tag blocks - axioms, claims, evidence, with their UUIDs |
| `definitions` | Cached definitions of terms (from local files or web) |
| `links` | Connections between things (note→note, term→definition) |
| `sync_queue` | Changes waiting to be sent to PostgreSQL |
| `custom_rules` | Your custom classifier rules (trigger words + prompts) |

---

## PostgreSQL (Global Database)

### What is PostgreSQL?

PostgreSQL is a **powerful database server**. It runs separately and can handle:
- Multiple users
- Huge amounts of data
- Complex queries
- Remote access

### Why Use PostgreSQL?

| Benefit | Explanation |
|---------|-------------|
| **Backup** | Your data is safe even if computer crashes |
| **Multi-device** | Access from different computers |
| **Analytics** | Run complex queries for insights |
| **Dashboards** | Power external tools and websites |
| **AI Memory** | Long-term memory for AI systems |

### How SQLite and PostgreSQL Work Together

```
Your Computer                           Server
┌─────────────────┐                    ┌─────────────────┐
│                 │                    │                 │
│  Obsidian + ────┼──▶ SQLite         │   PostgreSQL    │
│  Plugin         │    (cache)         │   (permanent)   │
│                 │        │           │                 │
└─────────────────┘        │           └────────▲────────┘
                           │                    │
                           └────────────────────┘
                              Periodic Sync
```

**Think of it like this:**
- SQLite = Your notepad (quick notes, always available)
- PostgreSQL = The official filing cabinet (permanent record)

### PostgreSQL Tables

PostgreSQL stores MORE than SQLite because it's the permanent home:

| Table | What It Stores |
|-------|----------------|
| `notes` | All notes with full metadata |
| `tags` | All tags ever created |
| `definitions` | Complete glossary |
| `links` | All relationships |
| `semantic_graph` | Full hierarchy (note→para→sentence→term) |
| `embeddings` | AI vector representations (for search) |
| `custom_rules` | Classifier rules |
| `sync_logs` | History of all sync operations |
| `user_settings` | Preferences and configurations |

---

## The Smart Linking System

### How Auto-Linking Works

When you open or save a note, the system can automatically link terms to their definitions.

```
Step 1: Python scans note for terms
        "Einstein's theory of general relativity..."

        Found: ["Einstein", "general relativity"]

Step 2: For each term, check if we have a definition

        "Einstein" → Found in Definitions/Einstein.md ✅
        "general relativity" → Not found locally ❌

Step 3: For missing terms, search external sources

        "general relativity" → Stanford Encyclopedia ✅

        Creates: Definitions/general_relativity.md

Step 4: Update the note with links

        Before: Einstein's theory of general relativity
        After:  [[Einstein]]'s theory of [[general relativity]]

Step 5: Save everything to databases
```

### Link Priority Order

When looking for definitions, the system checks sources in this order:

1. **Your Definitions Folder** (local, you control it)
2. **SQLite Cache** (previously fetched definitions)
3. **Stanford Encyclopedia of Philosophy** (academic, trusted)
4. **Other Academic Sources** (configured by you)
5. **Wikipedia** (lower priority, but comprehensive)

### Definition File Structure

When a definition is created, it looks like this:

```markdown
# General Relativity

## Short Definition
A theory of gravitation that describes gravity as a
property of the geometry of space and time.

## Long Definition
General relativity (GR) is the geometric theory of
gravitation published by Albert Einstein in 1915...

## Source
Stanford Encyclopedia of Philosophy
https://plato.stanford.edu/entries/spacetime-theories/

## Related Terms
- [[Einstein]]
- [[Special Relativity]]
- [[Spacetime]]

## Tags
- physics
- gravity
- spacetime

## Metadata
Created: 2025-12-14
Source Type: Academic
UUID: def-gr-7x9k2
```

---

## Putting It All Together

### Complete System Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                        YOUR COMPUTER                               │
│                                                                    │
│  ┌─────────────────┐    HTTP/IPC    ┌─────────────────┐           │
│  │                 │◀──────────────▶│                 │           │
│  │    OBSIDIAN     │                │     PYTHON      │           │
│  │    PLUGIN       │                │     BACKEND     │           │
│  │                 │                │                 │           │
│  │  • UI/Tabs      │                │  • AI Engine    │           │
│  │  • Right-click  │                │  • UUID Manager │           │
│  │  • Hover cards  │                │  • Link Finder  │           │
│  │  • Settings     │                │  • Sync Engine  │           │
│  │                 │                │                 │           │
│  └────────┬────────┘                └────────┬────────┘           │
│           │                                  │                     │
│           │ Read/Write                       │ Read/Write          │
│           ▼                                  ▼                     │
│  ┌─────────────────┐                ┌─────────────────┐           │
│  │                 │                │                 │           │
│  │  VAULT FILES    │                │     SQLite      │           │
│  │  (.md notes)    │                │   (local DB)    │           │
│  │                 │                │                 │           │
│  └─────────────────┘                └────────┬────────┘           │
│                                              │                     │
└──────────────────────────────────────────────┼─────────────────────┘
                                               │
                                               │ Periodic Sync
                                               ▼
                                    ┌─────────────────────┐
                                    │                     │
                                    │     PostgreSQL      │
                                    │   (cloud/server)    │
                                    │                     │
                                    │  • Permanent store  │
                                    │  • Multi-device     │
                                    │  • Analytics        │
                                    │  • AI memory        │
                                    │                     │
                                    └─────────────────────┘
```

### Summary Table

| Component | Language | Purpose | Stores Data? |
|-----------|----------|---------|--------------|
| Obsidian Plugin | TypeScript | UI, user interaction | Settings only |
| Python Backend | Python | Heavy lifting, AI, processing | No (uses DBs) |
| SQLite | SQL | Fast local cache | Yes (local) |
| PostgreSQL | SQL | Permanent global storage | Yes (server) |
| Vault Files | Markdown | Your actual notes | Yes (files) |

### What Each Technology Is Best At

| Need | Best Tool | Why |
|------|-----------|-----|
| Show buttons/menus | Plugin | Direct Obsidian integration |
| Run AI classification | Python | Can call external APIs |
| Instant lookups | SQLite | Fastest local queries |
| Long-term storage | PostgreSQL | Reliable, scalable |
| Edit notes | Plugin + Python | Plugin triggers, Python does work |
| Complex analytics | PostgreSQL | Powerful query engine |

---

## Next Steps for Development

### Phase 1: Foundation (Start Here)
1. Set up Python backend with basic structure
2. Create SQLite database schema
3. Build plugin skeleton with tabs
4. Test communication between plugin and Python

### Phase 2: Core Features
5. Implement UUID generation
6. Build tag parsing and writing
7. Create AI classification pipeline
8. Set up definition lookup

### Phase 3: Integration
9. Connect to PostgreSQL
10. Build sync engine
11. Implement auto-linking
12. Create Mermaid diagram generation

### Phase 4: Polish
13. Add batch processing
14. Build settings UI
15. Create right-click menus
16. Add progress indicators and error handling

---

*This document is the foundation for building the Theophysics Plugin System. Each section can be expanded into detailed specifications as development progresses.*
