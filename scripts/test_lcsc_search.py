import httpx
import json

def test_lcsc_search(keyword: str):
    # Search results said: "jlcsearch.tscircuit.com API... obtain JSON responses by appending .json"
    # Maybe https://jlcsearch.tscircuit.com/search.json?q=...
    
    urls_to_try = [
        "https://jlcsearch.tscircuit.com/search.json",
        "https://jlcsearch.tscircuit.com/api/search",
    ]
    
    headers = {
        "User-Agent": "TripleT-KiCad-Agent/0.1"
    }
    
    params = {
        "q": keyword,
    }

    for url in urls_to_try:
        print(f"Testing {url} with query '{keyword}'...")
        try:
            response = httpx.get(url, params=params, headers=headers)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(json.dumps(data, indent=2))
                    return # Success
                except json.JSONDecodeError:
                    print(f"Not JSON. Content start: {response.text[:100]}")
            else:
                print(f"Error: {response.status_code}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    test_lcsc_search("STM32F103")
