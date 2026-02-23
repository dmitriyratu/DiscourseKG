"""Test the discover flow."""
from flows.discover_flow import discover_flow

def main():
    result = discover_flow(
        start_date="2026-02-04", 
        end_date="2026-02-04",
        search_urls=["https://rollcall.com/factbase/trump/search/"]
    )
    print(f"Discovery flow completed: {result}")

if __name__ == "__main__":
    main()
