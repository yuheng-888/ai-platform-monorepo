from fastapi import APIRouter

from embedded.gemini_business2api.integration import get_gemini_status


router = APIRouter(prefix="/gemini", tags=["gemini"])


@router.get("/status")
def gemini_status():
    return get_gemini_status()
