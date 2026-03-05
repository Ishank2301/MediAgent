"""
Web Search Agent — agentic drug/medical info lookup.
Uses DuckDuckGo Instant Answer API (free, no key needed) + scraping fallback.
Also integrates with PubMed for medical literature.
"""
import requests
from urllib.parse import quote_plus
from backend.services.llm_service import ask_llm

DDGS_URL   = "https://api.duckduckgo.com/"
PUBMED_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def ddg_search(query: str, max_results: int = 5) -> list:
    """DuckDuckGo Instant Answer API — free, no key."""
    try:
        params = {"q": query, "format": "json", "no_redirect": 1, "no_html": 1}
        r = requests.get(DDGS_URL, params=params, timeout=10)
        data = r.json()
        results = []

        # Abstract (top answer)
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data["AbstractText"][:400],
                "url": data.get("AbstractURL", ""),
                "source": data.get("AbstractSource", "Wikipedia"),
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "snippet": topic.get("Text", "")[:300],
                    "url": topic.get("FirstURL", ""),
                    "source": "DuckDuckGo",
                })

        return results[:max_results]
    except Exception as e:
        return [{"title": "Search Error", "snippet": str(e), "url": "", "source": "error"}]


def pubmed_search(query: str, max_results: int = 3) -> list:
    """Search PubMed for medical literature — free API."""
    try:
        # Search for IDs
        search_url = f"{PUBMED_URL}/esearch.fcgi"
        params = {"db": "pubmed", "term": query, "retmax": max_results,
                  "retmode": "json", "sort": "relevance"}
        r = requests.get(search_url, params=params, timeout=10)
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        # Fetch summaries
        summary_url = f"{PUBMED_URL}/esummary.fcgi"
        params2 = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        r2 = requests.get(summary_url, params2, timeout=10)
        articles = r2.json().get("result", {})

        results = []
        for pmid in ids:
            a = articles.get(pmid, {})
            if a.get("title"):
                results.append({
                    "title": a.get("title", ""),
                    "snippet": f"Published: {a.get('pubdate','')} | Authors: {', '.join([au.get('name','') for au in a.get('authors',[])[:3]])}",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "source": "PubMed",
                    "pmid": pmid,
                })
        return results
    except Exception:
        return []


def search_drug_info(drug_name: str) -> dict:
    """Comprehensive drug search: DDG + PubMed + AI summary."""
    web_results = ddg_search(f"{drug_name} drug medication uses side effects")
    pubmed_results = pubmed_search(f"{drug_name} clinical pharmacology")

    # Build context for AI summary
    context = "\n\n".join([
        f"Source: {r['source']}\n{r['title']}\n{r['snippet']}"
        for r in (web_results + pubmed_results)[:5]
        if r.get("snippet")
    ])

    prompt = (
        f"Based on these search results about {drug_name}:\n\n{context}\n\n"
        f"Provide a concise, patient-friendly summary covering: "
        f"what it's used for, common side effects, key warnings, and interactions to watch for. "
        f"Max 150 words. Use plain language."
    )
    ai_summary = ask_llm(prompt) if context else f"Search results unavailable for {drug_name}."

    return {
        "query": drug_name,
        "web_results": web_results,
        "pubmed_results": pubmed_results,
        "ai_summary": ai_summary,
        "total_results": len(web_results) + len(pubmed_results),
    }


def search_medical_news(topic: str = "drug safety") -> dict:
    """Search for latest medical news/updates."""
    results = ddg_search(f"{topic} medical news 2024 2025", max_results=6)
    pubmed = pubmed_search(topic, max_results=3)

    context = "\n\n".join([f"{r['title']}: {r['snippet']}" for r in results[:4]])
    prompt = (
        f"Summarize the latest developments about '{topic}' based on: {context}. "
        f"Keep it brief (3-4 sentences), factual, and note any important safety updates."
    )
    summary = ask_llm(prompt) if context else "No recent news found."

    return {
        "topic": topic,
        "news": results,
        "research": pubmed,
        "ai_summary": summary,
    }


def suggest_specialists(symptoms: str) -> dict:
    """Suggest medical specialists based on symptoms."""
    symptom_specialist_map = {
        "chest pain": "Cardiologist", "heart": "Cardiologist",
        "skin": "Dermatologist", "rash": "Dermatologist", "acne": "Dermatologist",
        "eye": "Ophthalmologist", "vision": "Ophthalmologist",
        "ear": "ENT Specialist", "nose": "ENT Specialist", "throat": "ENT Specialist",
        "bone": "Orthopedist", "joint": "Orthopedist", "back pain": "Orthopedist",
        "mental": "Psychiatrist", "anxiety": "Psychiatrist", "depression": "Psychiatrist",
        "stomach": "Gastroenterologist", "bowel": "Gastroenterologist",
        "kidney": "Nephrologist", "urine": "Urologist",
        "diabetes": "Endocrinologist", "thyroid": "Endocrinologist",
        "lung": "Pulmonologist", "breathing": "Pulmonologist",
        "brain": "Neurologist", "headache": "Neurologist", "seizure": "Neurologist",
        "child": "Pediatrician", "infant": "Pediatrician",
        "pregnancy": "Obstetrician", "gynecology": "Gynecologist",
        "cancer": "Oncologist", "tumor": "Oncologist",
        "blood": "Hematologist", "anemia": "Hematologist",
    }

    symptoms_lower = symptoms.lower()
    suggested = []
    for keyword, specialist in symptom_specialist_map.items():
        if keyword in symptoms_lower and specialist not in suggested:
            suggested.append(specialist)

    if not suggested:
        suggested = ["General Practitioner (GP)"]

    prompt = (
        f"For someone with symptoms: '{symptoms}'\n"
        f"Suggested specialists: {', '.join(suggested)}\n\n"
        f"Briefly explain (1-2 sentences) why each specialist is relevant and what to expect. "
        f"Always note that a GP referral is usually the first step."
    )
    explanation = ask_llm(prompt)

    return {
        "symptoms": symptoms,
        "suggested_specialists": suggested,
        "explanation": explanation,
        "note": "Always start with your GP who can provide referrals if needed.",
    }
