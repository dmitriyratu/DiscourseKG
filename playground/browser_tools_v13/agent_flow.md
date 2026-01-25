# ScrapingAgent Flow Diagram

```mermaid
flowchart TD
    Start([Start: run url, start_date, end_date]) --> Init[Initialize Browser Session]
    Init --> LoopStart{For each page<br/>max_pages limit}
    
    LoopStart --> CheckVisited{Action already<br/>visited?}
    CheckVisited -->|Yes| Stop1[Stop: action_already_visited]
    CheckVisited -->|No| Observe[Observe Page]
    
    Observe --> ExecuteJS{Action Type?}
    
    ExecuteJS -->|action = None| JumpWait[Jump to bottom<br/>Wait for DOM growth<br/>Poll for 1.5s]
    ExecuteJS -->|action = click| Click[Click element<br/>Wait 1s for navigation<br/>Jump to bottom<br/>Wait for DOM growth]
    
    JumpWait --> Extract
    Click --> Extract
    
    Extract[Extract Markdown<br/>LLM extracts articles<br/>+ next_action]
    
    Extract --> TrackAll[Track all articles<br/>in all_articles]
    TrackAll --> Filter[Filter Articles]
    
    Filter --> FilterCheck{Article valid?}
    FilterCheck -->|URL in seen_urls| Skip[Skip duplicate]
    FilterCheck -->|date_confidence LOW/NONE| Skip
    FilterCheck -->|No publication_date| Skip
    FilterCheck -->|Date outside range| Skip
    FilterCheck -->|Valid| AddValid[Add to collected<br/>Mark URL as seen]
    
    Skip --> CheckStop
    AddValid --> CheckStop
    
    CheckStop{Check Stop<br/>Conditions}
    CheckStop -->|Oldest article < stop_date| Stop2[Stop: date_threshold]
    CheckStop -->|All articles duplicates| Stop3[Stop: duplicate_content]
    CheckStop -->|Continue| GetNextAction
    
    GetNextAction[Get next_action<br/>from LLM]
    
    GetNextAction --> NextActionType{next_action<br/>is None?}
    
    NextActionType -->|Yes| CheckValid{Found target<br/>articles?}
    CheckValid -->|Yes| Stop4[Stop: no_navigation<br/>Found what we need]
    CheckValid -->|No| CheckNew{Any new articles<br/>not duplicates?}
    CheckNew -->|No| Stop5[Stop: exhausted_content<br/>No more content]
    CheckNew -->|Yes| Repeat[Set next_action = None<br/>Repeat jump/wait/extract]
    
    NextActionType -->|next_action = click| UpdateURL[Extract URL from selector<br/>Update current_url]
    UpdateURL --> LoopStart
    
    Repeat --> LoopStart
    
    Stop1 --> Complete
    Stop2 --> Complete
    Stop3 --> Complete
    Stop4 --> Complete
    Stop5 --> Complete
    LoopStart -->|max_pages reached| Stop6[Stop: max_pages]
    Stop6 --> Complete
    
    Complete[Complete: Return collected articles]
    
    style Start fill:#e1f5e1
    style Complete fill:#e1f5e1
    style Stop1 fill:#ffe1e1
    style Stop2 fill:#ffe1e1
    style Stop3 fill:#ffe1e1
    style Stop4 fill:#ffe1e1
    style Stop5 fill:#ffe1e1
    style Stop6 fill:#ffe1e1
    style Repeat fill:#fff4e1
    style UpdateURL fill:#fff4e1
```

## Key Components

### 1. **Page Observation**
- **action = None**: Jump to bottom, wait for DOM growth (infinite scroll preparation)
- **action = click**: Click element, wait for navigation, then jump/wait (pagination)
- **Delta extraction**: On *repeat* (same URL, action=None, not first load), only the new markdown tail is sent to the LLM; first load and after clicks use full markdown.

### 2. **Article Filtering**
Articles must pass all checks:
- Not already seen (deduplication)
- Date confidence HIGH or MEDIUM
- Has publication_date
- Date within start_date to end_date range

### 3. **Navigation Logic**
- **next_action = None**: 
  - If target articles found → Stop
  - If no new articles → Stop (exhausted)
  - If new articles → Repeat jump/wait/extract (infinite scroll)
- **next_action = click**: Navigate to next page

### 4. **Stop Conditions**
1. Action already visited (loop detection)
2. Date threshold (went too far back)
3. Duplicate content (no new articles)
4. No navigation needed (found target articles)
5. Content exhausted (infinite scroll done)
6. Max pages reached
