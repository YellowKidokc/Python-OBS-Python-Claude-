"""
Theophysics Python Backend - Main Entry Point

This is the "brain" of the system. It runs as a local server
that the Obsidian plugin talks to.

For beginners:
- This file starts the backend server
- It imports all the modules and makes them available
- The plugin sends requests here, and we route them to the right function
"""

import os
import sys
from flask import Flask, request, jsonify

# Add our modules to the path so Python can find them
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules (we'll create these next)
from classify.ai_engine import classify_note, batch_classify
from tags.uuid_manager import generate_uuid
from tags.tag_writer import write_tag_blocks
from tags.tag_parser import parse_tags
from linking.term_finder import find_terms
from linking.definition_lookup import lookup_definition, create_definition_file
from linking.auto_linker import auto_link_note
from database.sqlite_db import save_to_sqlite, get_from_sqlite
from database.postgres_db import sync_to_postgres, pull_from_postgres
from semantic.tree_builder import build_semantic_tree
from semantic.mermaid_generator import generate_mermaid_diagram
from sync.vault_scanner import scan_vault
from sync.sync_engine import perform_sync

# Create the Flask app (this is our web server)
app = Flask(__name__)

# ============================================
# API ENDPOINTS
# These are the URLs the plugin calls
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """
    Simple endpoint to check if the backend is running.
    Plugin calls this first to make sure we're alive.
    """
    return jsonify({
        "status": "ok",
        "message": "Theophysics backend is running"
    })


@app.route('/classify', methods=['POST'])
def api_classify_note():
    """
    Classify a single note using AI.

    The plugin sends:
    - note_path: Where the note is
    - prompt_type: What kind of classification (axiom, claim, etc.)

    We return:
    - List of tag blocks to add to the note
    """
    data = request.get_json()
    note_path = data.get('note_path')
    prompt_type = data.get('prompt_type', 'default')

    try:
        result = classify_note(note_path, prompt_type)
        return jsonify({
            "status": "success",
            "tags": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/classify/batch', methods=['POST'])
def api_batch_classify():
    """
    Classify multiple notes at once.

    The plugin sends:
    - folder_path: Which folder to process
    - prompt_type: What kind of classification

    We return:
    - Results for each note
    """
    data = request.get_json()
    folder_path = data.get('folder_path')
    prompt_type = data.get('prompt_type', 'default')

    try:
        results = batch_classify(folder_path, prompt_type)
        return jsonify({
            "status": "success",
            "results": results
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/uuid/generate', methods=['POST'])
def api_generate_uuid():
    """
    Generate a new unique ID.

    The plugin sends:
    - entity_type: What kind of thing (note, claim, term, etc.)

    We return:
    - A new UUID like "claim-7x3f9k2m"
    """
    data = request.get_json()
    entity_type = data.get('entity_type', 'generic')

    try:
        new_uuid = generate_uuid(entity_type)
        return jsonify({
            "status": "success",
            "uuid": new_uuid
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/tags/write', methods=['POST'])
def api_write_tags():
    """
    Write tag blocks to a note.

    The plugin sends:
    - note_path: Where to write
    - tags: List of tag data

    We add the tag blocks to the bottom of the note.
    """
    data = request.get_json()
    note_path = data.get('note_path')
    tags = data.get('tags', [])

    try:
        write_tag_blocks(tags, note_path)
        return jsonify({
            "status": "success",
            "message": f"Wrote {len(tags)} tags to {note_path}"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/tags/parse', methods=['POST'])
def api_parse_tags():
    """
    Read existing tags from a note.

    The plugin sends:
    - note_path: Which note to read

    We return:
    - List of all tag blocks found
    """
    data = request.get_json()
    note_path = data.get('note_path')

    try:
        tags = parse_tags(note_path)
        return jsonify({
            "status": "success",
            "tags": tags
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/terms/find', methods=['POST'])
def api_find_terms():
    """
    Find proper nouns and keywords in a note.

    The plugin sends:
    - note_path: Which note to scan

    We return:
    - List of terms found
    """
    data = request.get_json()
    note_path = data.get('note_path')

    try:
        terms = find_terms(note_path)
        return jsonify({
            "status": "success",
            "terms": terms
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/definition/lookup', methods=['POST'])
def api_lookup_definition():
    """
    Look up the definition of a term.

    The plugin sends:
    - term: Word to look up

    We check local files, cache, and external sources.
    """
    data = request.get_json()
    term = data.get('term')

    try:
        definition = lookup_definition(term)
        return jsonify({
            "status": "success",
            "definition": definition
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/link/auto', methods=['POST'])
def api_auto_link():
    """
    Automatically link all terms in a note.

    The plugin sends:
    - note_path: Which note to process

    We find terms and create links to definitions.
    """
    data = request.get_json()
    note_path = data.get('note_path')

    try:
        result = auto_link_note(note_path)
        return jsonify({
            "status": "success",
            "linked_terms": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/semantic/tree', methods=['POST'])
def api_build_tree():
    """
    Build semantic tree for a note.

    Creates hierarchy: Note → Paragraphs → Sentences → Terms
    """
    data = request.get_json()
    note_path = data.get('note_path')

    try:
        tree = build_semantic_tree(note_path)
        return jsonify({
            "status": "success",
            "tree": tree
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/semantic/mermaid', methods=['POST'])
def api_generate_mermaid():
    """
    Generate a Mermaid diagram from tag data.

    Returns Mermaid code that the plugin can render.
    """
    data = request.get_json()
    tag_data = data.get('tag_data', [])

    try:
        mermaid_code = generate_mermaid_diagram(tag_data)
        return jsonify({
            "status": "success",
            "mermaid": mermaid_code
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/sync/vault', methods=['POST'])
def api_scan_vault():
    """
    Scan the vault for changes.

    Returns list of files that need processing.
    """
    data = request.get_json()
    vault_path = data.get('vault_path')

    try:
        changes = scan_vault(vault_path)
        return jsonify({
            "status": "success",
            "changes": changes
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/sync/perform', methods=['POST'])
def api_perform_sync():
    """
    Perform full sync: SQLite → PostgreSQL
    """
    try:
        result = perform_sync()
        return jsonify({
            "status": "success",
            "result": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================
# START THE SERVER
# ============================================

if __name__ == '__main__':
    # Default port is 5000
    # The plugin will connect to http://localhost:5000
    port = int(os.environ.get('BACKEND_PORT', 5000))

    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║         Theophysics Backend Starting...               ║
    ╠═══════════════════════════════════════════════════════╣
    ║  Server running at: http://localhost:{port}             ║
    ║  Health check:      http://localhost:{port}/health      ║
    ║                                                       ║
    ║  Press Ctrl+C to stop                                 ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    app.run(host='0.0.0.0', port=port, debug=True)
