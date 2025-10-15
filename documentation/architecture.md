# KG-Sentiment Platform Architecture

## High-Level System Overview

The KG-Sentiment platform is a state-driven, multi-stage data processing pipeline designed for analyzing political communications. The system follows a clean architecture pattern with clear separation of concerns, standardized interfaces, and robust error handling.

The core processing flow follows the pattern: `RAW → SUMMARIZE → CATEGORIZE → Complete`, where each stage is managed through a centralized state system that tracks progress and enables resumable processing.

### Project Directory Structure

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
│   ├── preprocessing/            # Data preprocessing layer
│   │   ├── summarize_endpoint.py # Summarization endpoint
│   │   ├── extractive_summarizer.py # Core summarization logic
│   │   └── pipeline.py           # Summarization pipeline
│   ├── processing/               # Content processing layer
│   │   ├── categorize_endpoint.py # Categorization endpoint
│   │   ├── content_categorizer.py # Core categorization logic
│   │   └── pipeline.py           # Categorization pipeline
│   ├── schemas.py                # Pydantic data models
│   ├── pipeline_config.py        # Pipeline stage definitions
│   └── app_config.py             # Application configuration
├── flows/                        # Prefect flow orchestration
│   ├── scrape_flow.py           # Scraping flow orchestration
│   ├── preprocessing_flow.py    # Summarization flow orchestration
│   └── processing_flow.py       # Categorization flow orchestration
├── tasks/                        # Task definitions
│   └── orchestration.py         # Orchestration utilities
├── tests/                        # Test utilities and fixtures
│   ├── test_transcript_generator.py # Mock data generation
│   └── fixtures/                 # Test data fixtures
├── data/                         # Data storage
│   ├── raw/                      # Raw scraped data
│   ├── processed/                # Processed data outputs
│   ├── outputs/                  # Final analysis outputs
│   └── state/                    # Pipeline state files
├── logs/                         # Application logs
└── playground/                   # Interactive testing notebooks
```

### System Architecture Diagram

```mermaid
graph TB
    subgraph "Orchestration Layer"
        SF[ScrapeFlow]
        PF[PreprocessingFlow] 
        CF[ProcessingFlow]
        FP[FlowProcessor]
    end
    
    subgraph "Endpoint Layer"
        SE[ScrapeEndpoint]
        SME[SummarizeEndpoint]
        CE[CategorizeEndpoint]
        BE[BaseEndpoint]
    end
    
    subgraph "Processing Layer"
        ES[ExtractiveSummarizer]
        CC[ContentCategorizer]
        SP[SummarizationPipeline]
        CP[CategorizationPipeline]
        LLM[LangChain/OpenAI]
    end
    
    subgraph "Infrastructure Layer"
        PS[PipelineStateManager]
        PD[PersistenceLayer]
        LU[LoggingUtils]
        DL[DataLoaders]
    end
    
    subgraph "Storage Layer"
        FS[("File System")]
        LS[("Logs")]
        SS[("State Files")]
    end
    
    SF --> SE
    PF --> SME
    CF --> CE
    FP --> PS
    FP --> PD
    
    SE --> BE
    SME --> BE
    CE --> BE
    
    SME --> SP
    SP --> ES
    CE --> CP
    CP --> CC
    CC --> LLM
    
    PS --> SS
    PD --> FS
    LU --> LS
    DL --> FS
    
    classDef orchestration fill:#e1f5fe
    classDef endpoint fill:#f3e5f5
    classDef processing fill:#e8f5e8
    classDef infrastructure fill:#fff3e0
    classDef storage fill:#fce4ec
    
    class SF,PF,CF,FP orchestration
    class SE,SME,CE,BE endpoint
    class ES,CC,SP,CP,LLM processing
    class PS,PD,LU,DL infrastructure
    class FS,LS,SS storage
```

## Pipeline Flow & State Management

The pipeline operates as a state-driven system where each data item progresses through defined stages. The state manager tracks the current stage, status, and metadata for each item, enabling resumable processing and error recovery.

### Pipeline Stages

- **RAW**: Initial data collection stage (scraped content)
- **SUMMARIZE**: Content summarization using extractive summarization
- **CATEGORIZE**: Content categorization using LLM-based classification

### Pipeline State Flow Diagram

```mermaid
stateDiagram-v2
    [*] --> RAW: Data Scraped
    RAW --> SUMMARIZE: Scraping Complete
    SUMMARIZE --> CATEGORIZE: Summarization Complete
    CATEGORIZE --> [*]: Processing Complete
    
    RAW --> RAW_FAILED: Scraping Error
    SUMMARIZE --> SUMMARIZE_FAILED: Summarization Error
    CATEGORIZE --> CATEGORIZE_FAILED: Categorization Error
    
    RAW_FAILED --> RAW: Retry
    SUMMARIZE_FAILED --> SUMMARIZE: Retry
    CATEGORIZE_FAILED --> CATEGORIZE: Retry
    
    note right of RAW: Scrape content from URLs<br/>Generate mock transcripts<br/>Save raw JSON files
    note right of SUMMARIZE: Extract key sentences<br/>Compress to target length<br/>Save summary JSON
    note right of CATEGORIZE: Classify policy domains<br/>Extract entities<br/>Analyze sentiment
```

## Data Models & Relationships

The system uses Pydantic models for type safety and validation. The core models define the structure for political communication analysis, including policy domains, entity extraction, and sentiment analysis.

### Core Data Models

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
        +MIXED
    }
    
    class EntityMention {
        +name: str
        +entity_type: EntityType
        +sentiment: SentimentLevel
        +relevance_score: float
        +supporting_quotes: List[str]
    }
    
    class CategoryWithEntities {
        +policy_domain: PolicyDomain
        +confidence_score: float
        +entities: List[EntityMention]
    }
    
    class CategorizationOutput {
        +primary_category: PolicyDomain
        +all_categories: List[CategoryWithEntities]
        +overall_sentiment: SentimentLevel
        +processing_metadata: dict
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
        +stages: Dict[str, StageStatus]
        +next_stage: Optional[str]
        +created_at: str
        +updated_at: str
    }
    
    CategorizationOutput --> CategoryWithEntities : contains
    CategoryWithEntities --> EntityMention : contains
    CategoryWithEntities --> PolicyDomain : uses
    EntityMention --> EntityType : uses
    EntityMention --> SentimentLevel : uses
    CategorizationOutput --> SentimentLevel : uses
```

## Processing Components

The system implements a clean architecture with standardized endpoints that inherit from a common base class. Each endpoint handles a specific stage of the pipeline with consistent error handling and response formatting.

### Component Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant Flow
    participant FlowProcessor
    participant Endpoint
    participant Processor
    participant StateManager
    participant Persistence
    
    User->>Flow: Execute Pipeline Stage
    Flow->>FlowProcessor: process_items(stage, task_func, data_type)
    FlowProcessor->>StateManager: get_next_stage_tasks(stage)
    StateManager-->>FlowProcessor: List[PipelineState]
    
    loop For each item
        FlowProcessor->>Endpoint: execute(item)
        Endpoint->>Processor: process_content(data)
        Processor-->>Endpoint: Dict[result]
        Endpoint-->>FlowProcessor: Standardized Response
        
        alt Success
            FlowProcessor->>Persistence: save_data(item_id, result, data_type)
            FlowProcessor->>StateManager: update_stage_status(item_id, stage, COMPLETED)
        else Error
            FlowProcessor->>StateManager: update_stage_status(item_id, stage, FAILED, error)
        end
    end
```

### Endpoint Architecture

All endpoints inherit from `BaseEndpoint` and implement the standardized `execute` method:

```mermaid
classDiagram
    class BaseEndpoint {
        <<abstract>>
        +endpoint_name: str
        +logger: Logger
        +execute(item: Dict) Dict
        +_create_success_response() Dict
        +_create_error_response() Dict
    }
    
    class ScrapeEndpoint {
        +execute(item: Dict) Dict
        -_generate_mock_transcript() str
    }
    
    class SummarizeEndpoint {
        +execute(item: Dict) Dict
        -_validate_input() bool
    }
    
    class CategorizeEndpoint {
        +execute(item: Dict) Dict
        -_extract_transcript() str
    }
    
    BaseEndpoint <|-- ScrapeEndpoint
    BaseEndpoint <|-- SummarizeEndpoint
    BaseEndpoint <|-- CategorizeEndpoint
```

### Flow Architecture

The system uses `FlowProcessor` to eliminate code duplication across flows:

```mermaid
classDiagram
    class FlowProcessor {
        +flow_name: str
        +logger: Logger
        +process_items(stage: str, task_func: Callable, data_type: str)
        -_handle_result() void
    }
    
    class ScrapeFlow {
        +scrape_item() Task
        +scrape_flow() Flow
    }
    
    class PreprocessingFlow {
        +summarize_item() Task
        +preprocessing_flow() Flow
    }
    
    class ProcessingFlow {
        +categorize_item() Task
        +processing_flow() Flow
    }
    
    FlowProcessor --> ScrapeFlow : uses
    FlowProcessor --> PreprocessingFlow : uses
    FlowProcessor --> ProcessingFlow : uses
```

## Complete Workflow Example

A typical end-to-end processing flow demonstrates how data moves through the system, from initial scraping through final categorization.

### End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant ScrapeFlow
    participant ScrapeEndpoint
    participant PreprocessingFlow
    participant SummarizeEndpoint
    participant ProcessingFlow
    participant CategorizeEndpoint
    participant StateManager
    participant FileSystem
    
    User->>ScrapeFlow: scrape_flow(speaker, start_date, end_date)
    ScrapeFlow->>ScrapeEndpoint: execute(item)
    ScrapeEndpoint-->>ScrapeFlow: Success Response
    ScrapeFlow->>FileSystem: save_data(item_id, raw_data, 'raw')
    ScrapeFlow->>StateManager: create_state(item_id, scrape_cycle)
    
    User->>PreprocessingFlow: preprocessing_flow()
    PreprocessingFlow->>FlowProcessor: process_items('summarize', summarize_item, 'summary')
    FlowProcessor->>StateManager: get_next_stage_tasks('summarize')
    StateManager-->>FlowProcessor: Items to process
    FlowProcessor->>SummarizeEndpoint: execute(item)
    SummarizeEndpoint-->>FlowProcessor: Success Response
    FlowProcessor->>FileSystem: save_data(item_id, summary_data, 'summary')
    FlowProcessor->>StateManager: update_stage_status(item_id, 'summarize', COMPLETED)
    
    User->>ProcessingFlow: processing_flow()
    ProcessingFlow->>FlowProcessor: process_items('categorize', categorize_item, 'categorization')
    FlowProcessor->>StateManager: get_next_stage_tasks('categorize')
    StateManager-->>FlowProcessor: Items to process
    FlowProcessor->>CategorizeEndpoint: execute(item)
    CategorizeEndpoint-->>FlowProcessor: Success Response
    FlowProcessor->>FileSystem: save_data(item_id, categorization_data, 'categorization')
    FlowProcessor->>StateManager: update_stage_status(item_id, 'categorize', COMPLETED)
```

## Data Flow & Serialization

The system handles Pydantic model serialization at the point of creation to ensure JSON compatibility throughout the pipeline:

```mermaid
flowchart LR
    A[Pydantic Model Creation] --> B[model_dump() Conversion]
    B --> C[Dictionary Storage]
    C --> D[JSON Serialization]
    D --> E[File Persistence]
    
    F[ExtractiveSummarizer._create_result] --> B
    G[ContentCategorizer.categorize_content] --> B
    H[BaseEndpoint Response] --> C
    
    style B fill:#e8f5e8
    style C fill:#e1f5fe
    style D fill:#fff3e0
```

## Technology Stack & Design Patterns

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Orchestration** | Prefect | Workflow orchestration and task management |
| **Processing** | Python 3.12+ | Core application logic |
| **AI/ML** | OpenAI GPT-4, LangChain, SentenceTransformers | Content analysis and categorization |
| **Data Validation** | Pydantic | Type safety and data validation |
| **Logging** | Python logging + tqdm | Structured logging with progress bars |
| **Storage** | JSON files | Data persistence and state management |
| **Testing** | Jupyter Notebooks | Interactive testing and validation |

### Design Patterns

- **State Machine Pattern**: Pipeline stages with defined transitions
- **Endpoint Pattern**: Standardized interfaces for all processing stages
- **Template Method Pattern**: BaseEndpoint provides common structure
- **Strategy Pattern**: Different processing strategies per stage
- **Observer Pattern**: State management tracks progress across stages
- **Factory Pattern**: FlowProcessor creates standardized processing flows
- **Singleton Pattern**: Centralized configuration and logging

### Key Architectural Principles

1. **Separation of Concerns**: Clear boundaries between orchestration, processing, and persistence
2. **Standardized Interfaces**: All endpoints follow the same execute() contract
3. **Error Resilience**: Comprehensive error handling with retry mechanisms
4. **State-Driven Processing**: Resumable workflows with progress tracking
5. **Configuration Management**: Centralized configuration with environment variables
6. **Logging Consistency**: Unified logging across all components with module-level loggers
7. **Type Safety**: Pydantic models ensure data integrity throughout the pipeline
8. **Code Deduplication**: FlowProcessor eliminates boilerplate across flows
9. **Serialization at Source**: Pydantic models converted to dicts at creation time

### Recent Architectural Improvements

1. **✅ Standardized Endpoint Architecture**: All endpoints inherit from `BaseEndpoint` with consistent interfaces
2. **✅ FlowProcessor Pattern**: Eliminated code duplication across preprocessing and processing flows
3. **✅ Consolidated Logging**: Single `get_logger()` function with module-level loggers
4. **✅ Pydantic Serialization Fix**: Models converted to dicts at creation time for JSON compatibility
5. **✅ Configuration Cleanup**: Moved implementation-specific constants back to their respective modules
6. **✅ State-Driven Pipeline**: Centralized state management with resumable processing

This architecture provides a robust, scalable foundation for political communication analysis while maintaining clean code principles and operational excellence.
