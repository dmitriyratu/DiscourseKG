# KG-Sentiment Platform Architecture

## High-Level System Overview

The KG-Sentiment platform is a state-driven, multi-stage data processing pipeline designed for analyzing political communications. The system follows a clean architecture pattern with clear separation of concerns, standardized interfaces, and robust error handling.

The core processing flow follows the pattern: `SCRAPE → SUMMARIZE → CATEGORIZE → Complete`, where each stage is managed through a centralized state system that tracks progress and enables resumable processing.

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

## System Architecture

```mermaid
graph TB
    subgraph "Orchestration Layer"
        SF[ScrapeFlow]
        SUMF[SummarizeFlow] 
        CF[CategorizeFlow]
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
        PSM[PipelineStateManager]
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

The pipeline operates as a state-driven system where each data item progresses through defined stages. The state manager tracks the current stage, status, and metadata for each item, enabling resumable processing and error recovery.

### Pipeline State Flow

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

## Data Flow & Content Type Management

The system processes multiple content types (speech, interview, debate) through a unified pipeline while maintaining content-specific organization and analysis capabilities.

### Content Type Processing Flow

```mermaid
graph LR
    subgraph "Content Types"
        S[Speech]
        I[Interview] 
        D[Debate]
    end
    
    subgraph "Processing Pipeline"
        SCR[ScrapeFlow]
        SUM[SummarizeFlow]
        CAT[CategorizeFlow]
    end
    
    subgraph "Data Organization"
        FS[File System]
        ST[State Tracking]
    end
    
    S --> SCR
    I --> SCR
    D --> SCR
    
    SCR --> SUM
    SUM --> CAT
    
    SCR --> FS
    SUM --> FS
    CAT --> FS
    
    SCR --> ST
    SUM --> ST
    CAT --> ST
    
    classDef content fill:#e3f2fd
    classDef processing fill:#f3e5f5
    classDef storage fill:#e8f5e8
    
    class S,I,D content
    class SCR,SUM,CAT processing
    class FS,ST storage
```

### Data Persistence Strategy

The system uses a hierarchical directory structure that organizes data by content type:

```
data/{environment}/{speaker}/{stage}/{content_type}/{filename}
```

**Benefits:**
- **Content Type Analytics**: Easy analysis by speech/interview/debate
- **Scalable Organization**: Natural grouping for content-specific insights
- **Robust Data Loading**: ID-based search works across all content types
- **Environment Isolation**: Clean separation between test and production

## Data Models & Relationships

The system uses Pydantic models for type safety and validation. The core models define the structure for political communication analysis, including policy domains, entity extraction, and sentiment analysis.

### Data Model Class Diagram

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

The system implements a clean architecture with standardized endpoints that inherit from a common base class. Each endpoint handles a specific stage of the pipeline with consistent error handling and response formatting.

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
    
    class SummarizeFlow {
        +summarize_item() Task
        +summarize_flow() Flow
    }
    
    class CategorizeFlow {
        +categorize_item() Task
        +categorize_flow() Flow
    }
    
    FlowProcessor --> ScrapeFlow : uses
    FlowProcessor --> SummarizeFlow : uses
    FlowProcessor --> CategorizeFlow : uses
```

## Complete Workflow Example

A typical end-to-end processing flow demonstrates how data moves through the system, from initial scraping through final categorization.

### End-to-End Sequence Diagram

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
    ScrapeFlow->>FileSystem: save_data(item_id, raw_data, 'scrape', content_type)
    ScrapeFlow->>StateManager: create_state(item_id, scrape_cycle)
    
    User->>SummarizeFlow: summarize_flow()
    SummarizeFlow->>FlowProcessor: process_items('summarize', summarize_item, 'summary')
    FlowProcessor->>StateManager: get_next_stage_tasks('summarize')
    StateManager-->>FlowProcessor: Items to process
    FlowProcessor->>SummarizeEndpoint: execute(item)
    SummarizeEndpoint-->>FlowProcessor: Success Response
    FlowProcessor->>FileSystem: save_data(item_id, summary_data, 'summarize', content_type)
    FlowProcessor->>StateManager: update_stage_status(item_id, 'summarize', COMPLETED)
    
    User->>CategorizeFlow: categorize_flow()
    CategorizeFlow->>FlowProcessor: process_items('categorize', categorize_item, 'categorization')
    FlowProcessor->>StateManager: get_next_stage_tasks('categorize')
    StateManager-->>FlowProcessor: Items to process
    FlowProcessor->>CategorizeEndpoint: execute(item)
    CategorizeEndpoint-->>FlowProcessor: Success Response
    FlowProcessor->>FileSystem: save_data(item_id, categorization_data, 'categorize', content_type)
    FlowProcessor->>StateManager: update_stage_status(item_id, 'categorize', COMPLETED)
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

### Pipeline State Configuration

The pipeline state file is automatically named based on environment:
- Test: `pipeline_state_test.jsonl`
- Production: `pipeline_state_prod.jsonl`

### Stage Flow Configuration

```python
STAGE_FLOW = {
    PipelineStages.SCRAPE: PipelineStages.SUMMARIZE,
    PipelineStages.SUMMARIZE: PipelineStages.CATEGORIZE,
    PipelineStages.CATEGORIZE: None  # Final stage
}
```

This architecture provides a robust, scalable foundation for political communication analysis while maintaining clean code principles and operational excellence.
