import os

import uvicorn
from dotenv import load_dotenv

from app import get_app

# Carrega variáveis de ambiente
env_file = ".env.test" if os.getenv("ENV") == "test" else ".env"
load_dotenv(env_file)

PORT = int(os.getenv("PORT", 3333))

if __name__ == "__main__":
    uvicorn.run(get_app(), host="0.0.0.0", port=PORT)
