"""Analyze agent execution logs for debugging and optimization."""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def analyze_session(session_file: Path):
    """Analyze a single agent session log."""
    print(f"\n{'='*80}")
    print(f"Session: {session_file.name}")
    print(f"{'='*80}\n")
    
    entries = []
    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            entries.append(json.loads(line))
    
    # Summary statistics
    tool_calls = [e for e in entries if 'tool' in e]
    thoughts = [e for e in entries if e.get('type') == 'agent_thought']
    errors = [e for e in entries if e.get('metadata', {}).get('status') == 'error']
    
    print(f"📊 Session Statistics:")
    print(f"  • Total entries: {len(entries)}")
    print(f"  • Tool calls: {len(tool_calls)}")
    print(f"  • Agent thoughts: {len(thoughts)}")
    print(f"  • Errors: {len(errors)}")
    print()
    
    # Tool usage breakdown
    tool_counts = defaultdict(int)
    tool_sizes = defaultdict(list)
    
    for call in tool_calls:
        tool = call['tool']
        tool_counts[tool] += 1
        tool_sizes[tool].append(call.get('output_size', 0))
    
    print(f"🔧 Tool Usage:")
    for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
        avg_size = sum(tool_sizes[tool]) / len(tool_sizes[tool])
        print(f"  • {tool}: {count} calls, avg output: {avg_size:,.0f} chars")
    print()
    
    # Timeline of key events
    print(f"⏱️  Timeline:")
    for entry in entries[:10]:  # First 10 entries
        ts = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
        if 'tool' in entry:
            tool = entry['tool']
            inputs = entry.get('inputs', {})
            url = inputs.get('url', '')[:50]
            status = entry.get('metadata', {}).get('status', 'unknown')
            print(f"  {ts} - {tool}: {url}... [{status}]")
        elif entry.get('type') == 'agent_thought':
            thought = entry['thought'][:60]
            print(f"  {ts} - 💭 {thought}...")
    print()
    
    # Error analysis
    if errors:
        print(f"❌ Errors:")
        for error in errors:
            ts = datetime.fromisoformat(error['timestamp']).strftime("%H:%M:%S")
            tool = error.get('tool', 'unknown')
            error_type = error.get('metadata', {}).get('error_type', 'Unknown')
            error_msg = error.get('output', {}).get('error', 'No message')[:80]
            print(f"  {ts} - {tool}: {error_type} - {error_msg}")
        print()
    
    # Token/size analysis
    total_output_size = sum(e.get('output_size', 0) for e in tool_calls)
    print(f"📦 Output Size Analysis:")
    print(f"  • Total output: {total_output_size:,} chars (~{total_output_size/4:,.0f} tokens)")
    print(f"  • Per tool call: {total_output_size/len(tool_calls):,.0f} chars avg")
    print()
    
    # Show sample outputs for review
    print(f"📄 Sample Tool Outputs (first call of each type):")
    seen_tools = set()
    for call in tool_calls:
        tool = call['tool']
        if tool not in seen_tools:
            seen_tools.add(tool)
            print(f"\n  {tool}:")
            print(f"    Input: {call['inputs']}")
            output = call['output']
            if isinstance(output, dict):
                # Show structure
                print(f"    Output keys: {list(output.keys())}")
                if 'links' in output:
                    print(f"      - {len(output.get('links', []))} links")
                if 'dates_found' in output:
                    print(f"      - {len(output.get('dates_found', []))} dates")
                if 'buttons' in output:
                    print(f"      - {len(output.get('buttons', []))} buttons")
            else:
                print(f"    Output preview: {str(output)[:100]}...")

def main():
    log_dir = Path("logs/agent_traces")
    
    if not log_dir.exists():
        print(f"❌ No logs found at {log_dir}")
        return
    
    session_files = sorted(log_dir.glob("session_*.jsonl"), reverse=True)
    
    if not session_files:
        print(f"❌ No session logs found in {log_dir}")
        return
    
    print(f"\n🔍 Found {len(session_files)} session(s)")
    print(f"📁 Log directory: {log_dir.absolute()}\n")
    
    # Analyze most recent session by default
    analyze_session(session_files[0])
    
    # List other sessions
    if len(session_files) > 1:
        print(f"\n📚 Other sessions available:")
        for session_file in session_files[1:6]:  # Show up to 5 more
            print(f"  • {session_file.name}")
        print(f"\nRun: python playground/analyze_agent_logs.py <session_file> to analyze specific session")

if __name__ == "__main__":
    main()

