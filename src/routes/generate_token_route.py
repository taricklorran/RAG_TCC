from fastapi import APIRouter

from controllers.generate_token_controller import generate_token

router = APIRouter()

@router.post("/generate_token")
def generate_token_route():
    return generate_token("tarick")