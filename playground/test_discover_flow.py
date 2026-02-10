"""Test the discover flow."""
from flows.discover_flow import discover_flow

def main():
    result = discover_flow(
        speaker="trump",
        start_date="2026-01-01",
        end_date=None,
        search_urls=["https://rollcall.com/factbase/trump/search/"]
    )
    print(f"Discovery flow completed: {result}")

if __name__ == "__main__":
    main()
