# DiscourseKG Graph Topology

This document defines the structure of the DiscourseKG knowledge graph - how nodes and relationships are organized to enable market intelligence and relationship discovery.

---

## Overview

The DiscourseKG graph uses a hierarchical structure with 5 node types and 4 relationship types, designed to capture communications from influential speakers and extract actionable intelligence about entities, topics, and sentiment.

**Core Design Principle**: Enable queries like "How does Trump discuss Bitcoin?" or "Show all entities mentioned positively in Technology topics" or "Track sentiment changes for China across multiple communications."

---

## Graph Structure

```mermaid
graph TB
    subgraph "Level 1: Speaker & Communication"
        S["<b>Speaker</b><br/>────────────────────<br/>name<br/>display_name<br/>role<br/>organization<br/>industry<br/>region<br/>date_of_birth<br/>bio"]
        C["<b>Communication</b><br/>────────────────────<br/>id<br/>title<br/>content_type<br/>content_date<br/>source_url<br/>full_text<br/>word_count<br/>was_summarized<br/>compression_ratio"]
    end
    
    subgraph "Level 2: Entity & Topics"
        E["<b>Entity</b><br/>────────────────────<br/>entity_name<br/>entity_type"]
        T1["<b>Topic</b><br/>────────────────────<br/>topic<br/>topic_summary<br/>speaker"]
        T2["<b>Topic</b><br/>────────────────────<br/>topic<br/>topic_summary<br/>speaker"]
    end
    
    subgraph "Level 3: Claims"
        CL1["<b>Claim</b><br/>────────────────────<br/>claim_label<br/>sentiment<br/>summary<br/>passages[]"]
        CL2["<b>Claim</b><br/>────────────────────<br/>claim_label<br/>sentiment<br/>summary<br/>passages[]"]
        CL3["<b>Claim</b><br/>────────────────────<br/>claim_label<br/>sentiment<br/>summary<br/>passages[]"]
    end
    
    S -->|DELIVERED| C
    C -->|HAS_TOPIC| T1
    C -->|HAS_TOPIC| T2
    T1 -->|REFERS_TO| E
    T2 -->|REFERS_TO| E
    T1 -->|HAS_CLAIM| CL1
    T1 -->|HAS_CLAIM| CL2
    T2 -->|HAS_CLAIM| CL3
    
    style S fill:#2C3E50,color:#fff
    style C fill:#27AE60,color:#fff
    style E fill:#F39C12,color:#fff
    style T1 fill:#8E44AD,color:#fff
    style T2 fill:#8E44AD,color:#fff
    style CL1 fill:#E74C3C,color:#fff
    style CL2 fill:#E74C3C,color:#fff
    style CL3 fill:#E74C3C,color:#fff
```

---

## Node Types

### 1. Speaker
**Represents**: The person who delivered the communication

**Properties**:
- `name` (string, unique): Canonical name (e.g., "Donald Trump", "Joe Biden")
- `display_name` (string): Full formatted name for display purposes
- `role` (string): Position/title (e.g., "President", "CEO", "Senator")
- `organization` (string): Affiliated organization or institution
- `industry` (string): Domain/sector (e.g., "Politics", "Technology", "Finance")
- `region` (string): Geographic location (e.g., "United States", "California")
- `date_of_birth` (date): Speaker's birth date
- `bio` (string): Biographical information about the speaker
- `influence_score` (float, optional): Market-moving power metric (0-100)

**Cardinality**: One per unique speaker
**Example**: Speaker {name: "Donald Trump", display_name: "Donald J. Trump", role: "President", organization: "United States Government", industry: "Politics", region: "United States"}

---

### 2. Communication
**Represents**: A single transcript, speech, interview, or debate

**Properties**:
- `id` (string, unique): Unique identifier from pipeline (e.g., "discovered-item-1-20251026_135658")
- `title` (string): Communication title
- `content_type` (string): Type of communication ("speech", "interview", "debate")
- `content_date` (date): When communication occurred
- `source_url` (string): Original source URL
- `full_text` (string): Complete scraped transcript
- `word_count` (integer): Number of words in full_text
- `was_summarized` (boolean): Whether content was condensed before categorization
- `compression_ratio` (float, optional): Summary length / original length (if summarized)

**Cardinality**: One per transcript/communication
**Source**: Pipeline stages (discover, scrape, summarize)

---

### 3. Entity
**Represents**: A real-world entity mentioned in communications

**Properties**:
- `entity_name` (string, unique): Entity name (e.g., "Apple", "China", "Bitcoin")
- `entity_type` (enum): Type of entity
  - `organization`: Companies, institutions, government bodies
  - `location`: Countries, regions, cities
  - `person`: Individuals, public figures
  - `program`: Initiatives, policies, projects
  - `product`: Products, services, platforms
  - `event`: Conferences, summits, incidents
  - `other`: Anything else

**Cardinality**: One per unique entity across all communications
**Reusability**: Same entity node referenced by multiple topics

---

### 4. Topic
**Represents**: A discussion of an entity within a specific topic category in a communication, attributed to a specific speaker

**Properties**:
- `topic` (enum): Topic category where entity was discussed
  - `economics`, `immigration`, `elections`, `technology`, `foreign_affairs`, `healthcare`, `energy_climate`, `defense`, `social`, `government`, `legal`, `media`, `personnel`, `sports`, `other`
- `topic_summary` (string): 10-500 char summary of how entity was discussed in this topic
- `speaker` (string): Speaker who discussed this topic (from matched_speakers)

**Relationships**: `HAS_CLAIM` → Claim nodes (specific claims made in this topic)

**Cardinality**: One per unique (communication, entity, speaker, topic) combination
**Constraint**: An entity can only appear once per (speaker, topic) per communication

---

### 5. Claim
**Represents**: A specific 1-3 word claim made about an entity within a topic

**Properties**:
- `claim_label` (string): 1-3 word label (e.g., "Coal Plants", "Trade Policy", "Job Creation") — stored as both `name` and `subject_name` in Neo4j
- `sentiment` (enum): Speaker's feeling toward this claim
  - `positive`: Supportive, favorable
  - `negative`: Critical, opposing
  - `neutral`: Factual, no emotion
  - `unclear`: Cannot determine
- `summary` (string): News-style summary weaving in the speaker's verbatim quotes where possible
- `passages` (array of strings): Full verbatim transcript passages from the extract stage that support this claim

**Cardinality**: One per distinct claim within a (speaker, topic)
**Granularity**: Enables fine-grained sentiment analysis (e.g., positive on "Regulatory Approval" but negative on "Security Concerns" for same entity)


