"""Web search agent API routes."""
from fastapi import APIRouter
from backend.services.search_agent import (
    search_drug_info, search_medical_news, suggest_specialists,
)
 
router = APIRouter()


@router.get("/search/drug/{drug_name}")
def drug_search(drug_name: str):
    """Search latest drug info from web + PubMed with AI summary."""
    return search_drug_info(drug_name)


@router.get("/search/news")
def medical_news(topic: str = "drug safety medication"):
    """Search for latest medical news on a topic."""
    return search_medical_news(topic)


@router.get("/search/specialists")
def find_specialists(symptoms: str):
    """Suggest medical specialists based on symptoms."""
    return suggest_specialists(symptoms)
