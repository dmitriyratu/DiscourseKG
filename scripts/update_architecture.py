"""
Dynamically update architecture documentation by analyzing the codebase.
Uses AST parsing to extract real code structure.
"""

import ast
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def analyze_python_file(file_path):
    """Extract key information from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        info = {
            'classes': [],
            'functions': [],
            'decorators': set(),
            'imports': set()
        }
        
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                info['classes'].append(node.name)
            elif isinstance(node, ast.FunctionDef):
                info['functions'].append(node.name)
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name):
                        info['decorators'].add(dec.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        info['imports'].add(alias.name.split('.')[0])
                elif node.module:
                    info['imports'].add(node.module.split('.')[0])
        
        return info
    except:
        return None


def scan_codebase(root):
    """Scan entire codebase and categorize modules."""
    flows = []
    pipelines = []
    processors = []
    
    # Scan flows
    flows_dir = root / "flows"
    if flows_dir.exists():
        for py_file in flows_dir.glob("*.py"):
            if py_file.stem.startswith('__'):
                continue
            info = analyze_python_file(py_file)
            if info:
                flows.append({
                    'name': py_file.stem,
                    'path': f"flows/{py_file.name}",
                    'is_flow': 'flow' in info['decorators'],
                    'is_task': 'task' in info['decorators'],
                    'functions': info['functions'],
                    'classes': info['classes']
                })
    
    # Scan pipeline
    pipeline_dir = root / "pipeline"
    if pipeline_dir.exists():
        for py_file in pipeline_dir.glob("*.py"):
            if py_file.stem.startswith('__'):
                continue
            info = analyze_python_file(py_file)
            if info:
                pipelines.append({
                    'name': py_file.stem,
                    'path': f"pipeline/{py_file.name}",
                    'functions': info['functions'],
                    'classes': info['classes']
                })
    
    # Scan src/processing and src/preprocessing
    src_dir = root / "src"
    for subdir in ['processing', 'preprocessing']:
        proc_dir = src_dir / subdir
        if proc_dir.exists():
            for py_file in proc_dir.glob("*.py"):
                if py_file.stem.startswith('__'):
                    continue
                info = analyze_python_file(py_file)
                if info:
                    processors.append({
                        'name': py_file.stem,
                        'path': f"src/{subdir}/{py_file.name}",
                        'type': subdir,
                        'functions': info['functions'],
                        'classes': info['classes']
                    })
    
    return flows, pipelines, processors


def generate_flow_nodes(flows):
    """Generate Mermaid nodes for flows."""
    lines = []
    for flow in flows:
        if flow['is_flow']:
            node_id = flow['name'].upper().replace('_', '')
            display = flow['name'].replace('_', ' ').title()
            lines.append(f"        {node_id}[{display}<br/>{flow['path']}]")
    return lines if lines else ["        FLOW[Flow Modules<br/>flows/]"]


def generate_architecture_doc(flows, pipelines, processors):
    """Generate the complete architecture markdown."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate flow nodes
    flow_nodes = generate_flow_nodes(flows)
    flow_list = [f for f in flows if f['is_flow']]
    
    # Count components
    flow_count = len([f for f in flows if f['is_flow']])
    task_count = len([f for f in flows if f['is_task']])
    pipeline_count = len(pipelines)
    processor_count = len(processors)
    
    doc = f"""# KG-Sentiment Platform Architecture

*Last Updated: {timestamp}*  
*Auto-generated from codebase analysis*

## 📊 Component Summary

| Component Type | Count | Details |
|---------------|-------|---------|
| Prefect Flows | {flow_count} | {', '.join([f['name'] for f in flow_list]) or 'None'} |
| Prefect Tasks | {task_count} | Distributed processing units |
| Pipeline Modules | {pipeline_count} | {', '.join([p['name'] for p in pipelines]) or 'None'} |
| Processors | {processor_count} | {', '.join([p['name'] for p in processors]) or 'None'} |

## System Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        WEB[Web Sources<br/>Speeches, Interviews]
    end
    
    subgraph "Orchestration Layer (Prefect)"
{chr(10).join(flow_nodes)}
        TASKS[tasks.py<br/>Core Task Functions]
    end
    
    subgraph "Pipeline Management"
        PSM[PipelineStateManager<br/>pipeline/pipeline_state.py]
        PC[PipelineConfig<br/>Stage Flow Definition]
        STATE[(pipeline_state.jsonl<br/>JSONL State File)]
    end
    
    subgraph "Core Processing Components"
        ES[ExtractiveSummarizer<br/>Semantic Ranking]
        CC[ContentCategorizer<br/>LangChain + GPT]
    end
    
    subgraph "Data Storage"
        RAW[(data/raw/<br/>JSON files)]
        PROC_DATA[(data/processed/<br/>outputs)]
        META[(data/metadata/)]
    end
    
    subgraph "Configuration"
        SCHEMAS[schemas.py<br/>Pydantic Models]
        CONFIG[config.py<br/>Settings]
    end
    
    %% Data Flow
    WEB -->|scrape| {flow_nodes[0].split('[')[0].strip() if flow_nodes[0] != '        FLOW[Flow Modules<br/>flows/]' else 'FLOW'}
    {flow_nodes[0].split('[')[0].strip() if flow_nodes[0] != '        FLOW[Flow Modules<br/>flows/]' else 'FLOW'} -->|ingest| RAW
    {flow_nodes[0].split('[')[0].strip() if flow_nodes[0] != '        FLOW[Flow Modules<br/>flows/]' else 'FLOW'} -->|create state| PSM
    PSM <-->|read/write| STATE
    
    TASKS -->|query| PSM
    PSM -->|return tasks| TASKS
    TASKS -->|load raw| RAW
    TASKS -->|process| ES
    TASKS -->|process| CC
    TASKS -->|save| PROC_DATA
    TASKS -->|update| PSM
    
    %% Configuration
    PC -.->|rules| PSM
    SCHEMAS -.->|validate| PSM
    CONFIG -.->|settings| ES
    CONFIG -.->|settings| CC
    
    style ES fill:#fff4e1
    style CC fill:#fff4e1
    style PSM fill:#f0e1ff
    style RAW fill:#e8f5e9
    style PROC_DATA fill:#e8f5e9
    style STATE fill:#f0e1ff
```

## Pipeline Stage Flow

```mermaid
stateDiagram-v2
    [*] --> RAW: Scraping
    RAW --> SUMMARIZE: preprocess_content()
    SUMMARIZE --> CATEGORIZE: process_content()
    CATEGORIZE --> [*]: Complete
    
    SUMMARIZE --> SUMMARIZE: Retry on failure
    CATEGORIZE --> CATEGORIZE: Retry on failure
    
    note right of RAW
        Raw transcript JSON
        stored in data/raw/
    end note
    
    note right of SUMMARIZE
        ExtractiveSummarizer
        semantic sentence ranking
    end note
    
    note right of CATEGORIZE
        ContentCategorizer
        entity + sentiment extraction
    end note
```

## Data Model Relationships

```mermaid
classDiagram
    class PipelineState {{
        +string id
        +string scrape_cycle
        +string raw_file_path
        +string source_url
        +string latest_completed_stage
        +string next_stage
        +datetime created_at
        +datetime updated_at
        +string error_message
        +float processing_time_seconds
    }}
    
    class CategorizationOutput {{
        +List~CategoryWithEntities~ categories
    }}
    
    class CategoryWithEntities {{
        +string category
        +List~EntityMention~ entities
    }}
    
    class EntityMention {{
        +string entity_name
        +EntityType entity_type
        +SentimentLevel sentiment
        +string context
        +List~string~ quotes
    }}
    
    class SummarizationResult {{
        +string summary
        +string original_text
        +int original_word_count
        +int summary_word_count
        +float compression_ratio
        +float processing_time_seconds
        +bool success
    }}
    
    PipelineState "1" --> "1" SummarizationResult: tracks
    PipelineState "1" --> "1" CategorizationOutput: tracks
    CategorizationOutput "1" --> "*" CategoryWithEntities: contains
    CategoryWithEntities "1" --> "*" EntityMention: contains
```

## Component Details

### Flows
{chr(10).join([f"- **{f['name']}** ({f['path']}): {len(f['functions'])} functions, {len(f['classes'])} classes" for f in flows]) or "None detected"}

### Pipelines
{chr(10).join([f"- **{p['name']}** ({p['path']}): {len(p['functions'])} functions, {len(p['classes'])} classes" for p in pipelines]) or "None detected"}

### Processors
{chr(10).join([f"- **{p['name']}** ({p['path']}): {len(p['functions'])} functions, {len(p['classes'])} classes" for p in processors]) or "None detected"}

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | Prefect |
| LLM Framework | LangChain |
| LLM Provider | OpenAI GPT |
| Embeddings | sentence-transformers |
| Validation | Pydantic |
| Storage | File-based (JSON/JSONL) |
| Logging | Python logging |

## Directory Structure

```
KG-Sentiment/
├── flows/                  # Prefect orchestration
├── pipeline/              # State management
├── src/                   # Core processing
│   ├── preprocessing/     # Summarization
│   ├── processing/        # Categorization
│   ├── schemas.py         # Data models
│   └── config.py          # Configuration
├── data/                  # Storage
└── playground/           # Testing
```

---

*Auto-generated by `scripts/update_architecture.py`*
"""
    
    return doc


def main():
    """Main entry point."""
    # Fix Windows encoding
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    root = Path(__file__).parent.parent
    output = root / "documentation" / "ARCHITECTURE.md"
    
    print("🔍 Analyzing codebase...")
    flows, pipelines, processors = scan_codebase(root)
    
    print(f"📊 Found: {len(flows)} flow modules, {len(pipelines)} pipelines, {len(processors)} processors")
    
    print("📝 Generating documentation...")
    doc = generate_architecture_doc(flows, pipelines, processors)
    
    output.parent.mkdir(exist_ok=True)
    output.write_text(doc, encoding='utf-8')
    
    print(f"✅ Updated {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

