# KG-Sentiment Platform Architecture

## High-Level System Overview

The KG-Sentiment platform is a state-driven, multi-stage data processing pipeline designed for analyzing political communications. The system follows a clean architecture pattern with clear separation of concerns, standardized interfaces, and robust error handling.

The core processing flow follows the pattern: `SCRAPE → SUMMARIZE → CATEGORIZE → Complete`, where each stage is managed through a centralized state system that tracks progress and enables resumable processing. Key design patterns include state-driven processing, endpoint pattern, and flow orchestration.

## System Architecture

```mermaid
graph TB
    subgraph "Orchestration Layer"
        SF["ScrapeFlow"]
        SUMF["SummarizeFlow"] 
        CF["CategorizeFlow"]
        FP["FlowProcessor"]
    end
    
    subgraph "Endpoint Layer"
        SE["ScrapeEndpoint"]
        SME["SummarizeEndpoint"]
        CE["CategorizeEndpoint"]
        BE["BaseEndpoint"]
    end
    
    subgraph "Processing Layer"
        ES["ExtractiveSummarizer"]
        CC["ContentCategorizer"]
        SP["SummarizationPipeline"]
        CP["CategorizationPipeline"]
        LLM["LangChain/OpenAI"]
    end
    
    subgraph "Infrastructure Layer"
        PSM["PipelineStateManager"]
        PD["PersistenceLayer"]
        LU["LoggingUtils"]
        DL["DataLoaders"]
    end
    
    subgraph "Storage Layer"
        FS[("File System")]
        LS[("Logs")]
        SS[("State Files")]
    end
    
    SF --> SE
    SUMF --> SME
    CF --> CE
    FP --> PSM
    FP --> PD
    
    SE --> BE
    SME --> BE
    CE --> BE
    
    SME --> SP
    SP --> ES
    CE --> CP
    CP --> CC
    CC --> LLM
    
    PSM --> SS
    PD --> FS
    LU --> LS
    DL --> FS
    
    classDef orchestration fill:#e1f5fe
    classDef endpoint fill:#f3e5f5
    classDef processing fill:#e8f5e8
    classDef infrastructure fill:#fff3e0
    classDef storage fill:#fce4ec
    
    class SF,SUMF,CF,FP orchestration
    class SE,SME,CE,BE endpoint
    class ES,CC,SP,CP,LLM processing
    class PSM,PD,LU,DL infrastructure
    class FS,LS,SS storage
```

## Pipeline Flow & State Management

The pipeline operates as a state-driven system where each data item progresses through defined stages. The state manager tracks the current stage, status, and metadata for each item, enabling resumable processing and error recovery. Items move through stages with automatic progression and retry mechanisms for failed operations.

## Pipeline State Flow

```mermaid
stateDiagram-v2
    [*] --> SCRAPE: Data Scraped
    SCRAPE --> SUMMARIZE: Scraping Complete
    SUMMARIZE --> CATEGORIZE: Summarization Complete
    CATEGORIZE --> [*]: Processing Complete
    
    SCRAPE --> SCRAPE_FAILED: Scraping Error
    SUMMARIZE --> SUMMARIZE_FAILED: Summarization Error
    CATEGORIZE --> CATEGORIZE_FAILED: Categorization Error
    
    SCRAPE_FAILED --> SCRAPE: Retry
    SUMMARIZE_FAILED --> SUMMARIZE: Retry
    CATEGORIZE_FAILED --> CATEGORIZE: Retry
    
    note right of SCRAPE: Scrape content from URLs<br/>Generate mock transcripts<br/>Calculate word count<br/>Save raw JSON files by content type
    note right of SUMMARIZE: Extract key sentences<br/>Compress to target length<br/>Save summary JSON by content type
    note right of CATEGORIZE: Classify policy domains<br/>Extract entities<br/>Analyze sentiment<br/>Save categorization JSON by content type
```

## Data Models & Relationships

The system uses Pydantic models for type safety and validation. The core models define the structure for political communication analysis, including policy domains, entity extraction, and sentiment analysis. These models ensure data integrity throughout the pipeline and provide clear contracts between components.

## Data Model Class Diagram

```mermaid
classDiagram
    class PolicyDomain {
        <<enumeration>>
        +ECONOMIC_POLICY
        +TECHNOLOGY_POLICY
        +FOREIGN_RELATIONS
        +HEALTHCARE_POLICY
        +ENERGY_POLICY
        +DEFENSE_POLICY
        +SOCIAL_POLICY
        +REGULATORY_POLICY
    }
    
    class EntityType {
        <<enumeration>>
        +COMPANY
        +COUNTRY
        +PERSON
        +POLICY_TOOL
        +OTHER
    }
    
    class SentimentLevel {
        <<enumeration>>
        +POSITIVE
        +NEGATIVE
        +NEUTRAL
        +UNCLEAR
    }
    
    class EntityMention {
        +entity_name: str
        +entity_type: EntityType
        +sentiment: SentimentLevel
        +context: str
        +quotes: List[str]
    }
    
    class CategoryWithEntities {
        +category: str
        +entities: List[EntityMention]
    }
    
    class CategorizationOutput {
        +categories: List[CategoryWithEntities]
    }
    
    class SummarizationResult {
        +summary: str
        +original_text: str
        +original_word_count: int
        +summary_word_count: int
        +compression_ratio: float
        +processing_time_seconds: float
        +target_word_count: int
        +success: bool
        +error_message: Optional[str]
    }
    
    class PipelineState {
        +id: str
        +scrape_cycle: str
        +raw_file_path: Optional[str]
        +source_url: Optional[str]
        +latest_completed_stage: Optional[str]
        +next_stage: Optional[str]
        +created_at: str
        +updated_at: str
        +error_message: Optional[str]
        +processing_time_seconds: Optional[float]
        +retry_count: int
    }
    
    CategorizationOutput --> CategoryWithEntities : contains
    CategoryWithEntities --> EntityMention : contains
    EntityMention --> EntityType : uses
    EntityMention --> SentimentLevel : uses
```

## Processing Components

The system implements a clean architecture with standardized endpoints that inherit from a common base class. Each endpoint handles a specific stage of the pipeline with consistent error handling and response formatting. The FlowProcessor eliminates code duplication across flows, while the BaseEndpoint provides common structure and error handling patterns.

## Component Interaction Diagram

```mermaid
graph TB
    subgraph "Flow Orchestration"
        SF["ScrapeFlow"]
        SUMF["SummarizeFlow"]
        CF["CategorizeFlow"]
    end
    
    subgraph "Endpoint Processing"
        SE["ScrapeEndpoint"]
        SME["SummarizeEndpoint"]
        CE["CategorizeEndpoint"]
    end
    
    subgraph "Data Management"
        PSM["PipelineStateManager"]
        PD["PersistenceLayer"]
        DL["DataLoaders"]
    end
    
    subgraph "AI Processing"
        ES["ExtractiveSummarizer"]
        CC["ContentCategorizer"]
        LLM["OpenAI GPT-4o-mini"]
    end
    
    SF --> SE
    SUMF --> SME
    CF --> CE
    
    SE --> PD
    SME --> ES
    CE --> CC
    
    ES --> LLM
    CC --> LLM
    
    SF --> PSM
    SUMF --> PSM
    CF --> PSM
    
    SME --> DL
    CE --> DL
    
    classDef flow fill:#e1f5fe
    classDef endpoint fill:#f3e5f5
    classDef data fill:#e8f5e8
    classDef ai fill:#fff3e0
    
    class SF,SUMF,CF flow
    class SE,SME,CE endpoint
    class PSM,PD,DL data
    class ES,CC,LLM ai
```

## Complete Workflow Example

A typical end-to-end processing flow demonstrates how data moves through the system, from initial scraping through final categorization. The workflow shows the interaction between flows, endpoints, state management, and data persistence.

## End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant ScrapeFlow
    participant ScrapeEndpoint
    participant SummarizeFlow
    participant SummarizeEndpoint
    participant CategorizeFlow
    participant CategorizeEndpoint
    participant StateManager
    participant FileSystem
    
    User->>ScrapeFlow: scrape_flow(speaker, start_date, end_date)
    ScrapeFlow->>ScrapeEndpoint: execute(item)
    ScrapeEndpoint-->>ScrapeFlow: Success Response
    ScrapeFlow->>FileSystem: save_data(item_id, raw_data, "scrape", content_type)
    ScrapeFlow->>StateManager: create_state(item_id, scrape_cycle)
    
    User->>SummarizeFlow: summarize_flow()
    SummarizeFlow->>StateManager: get_next_stage_tasks("summarize")
    StateManager-->>SummarizeFlow: Items to process
    SummarizeFlow->>SummarizeEndpoint: execute(item)
    SummarizeEndpoint-->>SummarizeFlow: Success Response
    SummarizeFlow->>FileSystem: save_data(item_id, summary_data, "summarize", content_type)
    SummarizeFlow->>StateManager: update_stage_status(item_id, "summarize", COMPLETED)
    
    User->>CategorizeFlow: categorize_flow()
    CategorizeFlow->>StateManager: get_next_stage_tasks("categorize")
    StateManager-->>CategorizeFlow: Items to process
    CategorizeFlow->>CategorizeEndpoint: execute(item)
    CategorizeEndpoint-->>CategorizeFlow: Success Response
    CategorizeFlow->>FileSystem: save_data(item_id, categorization_data, "categorize", content_type)
    CategorizeFlow->>StateManager: update_stage_status(item_id, "categorize", COMPLETED)
```

## Technology Stack & Design Patterns

The system leverages modern Python technologies and follows established design patterns to ensure maintainability, scalability, and reliability. The technology stack is carefully chosen to support the state-driven pipeline architecture with robust AI/ML capabilities.

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Orchestration** | Prefect 2.x | Workflow orchestration and task management |
| **Processing** | Python 3.12+ | Core application logic |
| **AI/ML** | OpenAI GPT-4o-mini, LangChain, SentenceTransformers | Content analysis and categorization |
| **Data Validation** | Pydantic | Type safety and data validation |
| **Logging** | Python logging + tqdm | Structured logging with progress bars |
| **Storage** | JSON/JSONL files | Data persistence and state management |
| **Testing** | Jupyter Notebooks | Interactive testing and validation |
| **Configuration** | python-dotenv, pyprojroot | Environment and path management |

## Design Patterns

- **State Machine Pattern**: Pipeline stages with defined transitions
- **Endpoint Pattern**: Standardized interfaces for all processing stages
- **Template Method Pattern**: BaseEndpoint provides common structure
- **Strategy Pattern**: Different processing strategies per stage
- **Observer Pattern**: State management tracks progress across stages
- **Factory Pattern**: FlowProcessor creates standardized processing flows
- **Singleton Pattern**: Centralized configuration and logging

## Key Architectural Principles

1. **Separation of Concerns**: Clear boundaries between orchestration, processing, and persistence
2. **Standardized Interfaces**: All endpoints follow the same execute() contract
3. **Error Resilience**: Comprehensive error handling with retry mechanisms
4. **State-Driven Processing**: Resumable workflows with progress tracking
5. **Configuration Management**: Centralized configuration with environment variables
6. **Logging Consistency**: Unified logging across all components with module-level loggers
7. **Type Safety**: Pydantic models ensure data integrity throughout the pipeline
8. **Code Deduplication**: FlowProcessor eliminates boilerplate across flows
9. **Serialization at Source**: Pydantic models converted to dicts at creation time
10. **Content Type Organization**: Hierarchical data organization by content type
11. **Robust Data Loading**: ID-based search across all directories
12. **Environment Isolation**: Clean separation between test and production data

## Recent Architectural Improvements

1. **✅ Standardized Endpoint Architecture**: All endpoints inherit from `BaseEndpoint` with consistent interfaces
2. **✅ FlowProcessor Pattern**: Eliminated code duplication across summarize and categorize flows
3. **✅ Consolidated Logging**: Single `get_logger()` function with module-level loggers
4. **✅ Pydantic Serialization Fix**: Models converted to dicts at creation time for JSON compatibility
5. **✅ Configuration Cleanup**: Moved implementation-specific constants back to their respective modules
6. **✅ State-Driven Pipeline**: Centralized state management with resumable processing
7. **✅ Content Type Organization**: Data organized by content type (speech/interview/debate) in subdirectories
8. **✅ Word Count Calculation**: Automatic word count calculation during scraping
9. **✅ Simplified Data Loading**: ID-based search across all directories for robust data retrieval
10. **✅ Enhanced Mock Data**: Full template content with proper placeholders and content type variation
11. **✅ JSON Field Ordering**: Transcript field positioned last for better readability
12. **✅ Environment-Based Naming**: Pipeline state files named based on environment (test/prod)

## Data Organization Strategy

The system now organizes data hierarchically by:
- **Environment** (`test`/`prod`) - Isolates test and production data
- **Speaker** - Groups data by political figure
- **Stage** (`scrape`/`summarize`/`categorize`) - Separates processing stages
- **Content Type** (`speech`/`interview`/`debate`) - Organizes by content format

This structure enables:
- **Scalable Analytics**: Easy analysis by content type or speaker
- **Robust Data Loading**: ID-based search works regardless of directory structure
- **Environment Isolation**: Clean separation between test and production data
- **Content Type Insights**: Natural grouping for content-specific analysis

## Configuration Management

### Environment Variables

- `ENVIRONMENT`: Controls data directory and state file naming (default: `test`)
- `DATA_ROOT`: Base directory for all data storage
- `LOG_LEVEL`: Logging verbosity level
- `OPENAI_API_KEY`: OpenAI API key for GPT-4o-mini model
- `AWS_REGION`: AWS region for cloud storage (default: `us-east-1`)
- `S3_BUCKET`: S3 bucket name for data storage (default: `kg-sentiment-data`)

### Pipeline State Configuration

The pipeline state file is automatically named based on environment:
- Test: `pipeline_state_test.jsonl`
- Production: `pipeline_state_prod.jsonl`

### Stage Flow Configuration

```python
STAGE_FLOW = {
    PipelineStages.SCRAPE: PipelineStages.SUMMARIZE,
    PipelineStages.SUMMARIZE: PipelineStages.CATEGORIZE,
    PipelineStages.CATEGORIZE: None  # Pipeline complete
}

# First stage to process (after raw data is available)
FIRST_PROCESSING_STAGE = PipelineStages.SUMMARIZE
```

### Pipeline Stage Status

```python
class PipelineStageStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS" 
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"
```

## Project Directory Structure

```
KG-Sentiment/
├── src/                          # Core application code
│   ├── shared/                   # Shared utilities and base classes
│   │   ├── base_endpoint.py      # Abstract base for all endpoints
│   │   ├── flow_processor.py     # Common flow processing patterns
│   │   ├── logging_utils.py      # Centralized logging setup
│   │   ├── persistence.py        # Data persistence layer
│   │   ├── pipeline_state.py     # State management system
│   │   └── data_loaders.py       # Data loading utilities
│   ├── collect/                  # Data collection layer
│   │   └── scrape_endpoint.py    # Web scraping endpoint
│   ├── summarize/                # Data summarization layer
│   │   ├── summarize_endpoint.py # Summarization endpoint
│   │   ├── extractive_summarizer.py # Core summarization logic
│   │   └── pipeline.py           # Summarization pipeline
│   ├── categorize/               # Content categorization layer
│   │   ├── categorize_endpoint.py # Categorization endpoint
│   │   ├── content_categorizer.py # Core categorization logic
│   │   └── pipeline.py           # Categorization pipeline
│   ├── schemas.py                # Pydantic data models
│   ├── pipeline_config.py        # Pipeline stage definitions
│   └── app_config.py             # Application configuration
├── flows/                        # Prefect flow orchestration
│   ├── scrape_flow.py           # Scraping flow orchestration
│   ├── summarize_flow.py        # Summarization flow orchestration
│   └── categorize_flow.py       # Categorization flow orchestration
├── tests/                        # Test utilities and fixtures
│   ├── test_transcript_generator.py # Mock data generation
│   └── transcript_templates.json # Content templates for testing
├── data/                         # Data storage (organized by environment)
│   └── {environment}/            # Environment-specific data (test/prod)
│       └── {speaker}/            # Speaker-specific data
│           ├── scrape/           # Raw scraped data
│           │   ├── speech/       # Speech content type
│           │   ├── interview/    # Interview content type
│           │   └── debate/       # Debate content type
│           ├── summarize/        # Summarized data
│           │   ├── speech/       # Speech summaries
│           │   ├── interview/    # Interview summaries
│           │   └── debate/       # Debate summaries
│           ├── categorize/       # Categorized data
│           │   ├── speech/       # Speech categorizations
│           │   ├── interview/    # Interview categorizations
│           │   └── debate/       # Debate categorizations
│           └── state/            # Pipeline state files
│               └── pipeline_state_{environment}.jsonl
├── logs/                         # Application logs
└── playground/                   # Interactive testing notebooks
```

This architecture provides a robust, scalable foundation for political communication analysis while maintaining clean code principles and operational excellence.
