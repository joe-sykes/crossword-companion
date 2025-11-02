import os
from collections import Counter, defaultdict
import httpx
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# --- Initialize app ---
app = FastAPI()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

print("running...")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Load dictionary ---
DICT_PATH = os.path.join(os.path.dirname(__file__), "dictionary.txt")
WORDS = [line.strip().lower() for line in open(DICT_PATH, encoding="utf-8") if line.strip()]

# --- Precompute anagram map ---
def sort_letters(word: str) -> str:
    return "".join(sorted(word))

ANAGRAM_MAP = defaultdict(list)
for w in WORDS:
    key = sort_letters(w)
    if w not in ANAGRAM_MAP[key]:
        ANAGRAM_MAP[key].append(w)

# --- Endpoints ---


@app.get("/anagram")
def get_anagrams(letters: str):
    letters = letters.lower().strip()
    key = sort_letters(letters)
    matches = ANAGRAM_MAP.get(key, [])
    filtered = [w for w in matches if w != letters]
    return {"input": letters, "count": len(filtered), "anagrams": filtered}


@app.get("/anagram_pattern")
def anagram_with_wildcard(pattern: str):
    pattern = pattern.lower().strip()
    pattern_len = len(pattern)
    known_letters = [c for c in pattern if c != "?"]
    known_count = Counter(known_letters)
    wildcard_count = pattern.count("?")

    matches = []
    for w in WORDS:
        if len(w) != pattern_len:
            continue

        word_counter = Counter(w)
        temp_counter = word_counter.copy()
        valid = True

        for letter, count in known_count.items():
            if temp_counter.get(letter, 0) < count:
                valid = False
                break
            temp_counter[letter] -= count

        if not valid:
            continue

        remaining_letters = sum(temp_counter.values())
        if remaining_letters == wildcard_count:
            matches.append(w)

    return {"pattern": pattern, "count": len(matches), "matches": matches}


# --- Merriam-Webster API keys ---
MW_API_KEY = os.environ.get("MERRIAM_WEBSTER_API_KEY")
MW_THESAURUS_API_KEY = os.environ.get("MERRIAM_WEBSTER_THESAURUS_KEY")


@app.get("/dictionary")
async def dictionary_lookup(word: str):
    url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={MW_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()

        if isinstance(data, list) and data and isinstance(data[0], str):
            return {"suggestions": data}

        return data
    except httpx.RequestError as e:
        return {"error": f"Request error: {e}"}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except httpx.ReadTimeout:
        return {"error": "Request timed out. Please try again."}


@app.get("/indicator")
def get_indicator(word: str):
    CSV_PATH = os.path.join(os.path.dirname(__file__), "Indicator.csv")
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        return {"error": f"Could not read Indicator.csv: {e}"}

    if not {"Search", "Output"}.issubset(df.columns):
        return {"error": "Indicator.csv must have columns 'Search' and 'Output'"}

    matches = df[df["Search"].str.lower() == word.lower()]
    if matches.empty:
        return {"results": []}

    results = matches["Output"].dropna().unique().tolist()
    return {"results": results}


@app.get("/thesaurus")
async def thesaurus_lookup(word: str):
    url = f"https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{word}?key={MW_THESAURUS_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()

        if isinstance(data, list) and data and isinstance(data[0], str):
            return {"suggestions": data}

        results = []
        for entry in data:
            meta = entry.get("meta", {})
            fl = entry.get("fl", "")
            shortdef = entry.get("shortdef", [])

            syns = [syn for group in meta.get("syns", []) for syn in group]
            ants = [ant for group in meta.get("ants", []) for ant in group]

            results.append({
                "word": meta.get("id", word),
                "partOfSpeech": fl,
                "shortdef": shortdef,
                "synonyms": syns,
                "antonyms": ants,
            })

        return {"results": results}
    except httpx.RequestError as e:
        return {"error": f"Request error: {e}"}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except httpx.ReadTimeout:
        return {"error": "Request timed out. Please try again."}
