from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# Configurar sys.path para poder importar módulos de src desde api
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.utils.data_loader import load_json_data

app = FastAPI(
    title="Quiniela API",
    description="API que sirve las predicciones de quiniela desde MongoDB",
    version="1.0.0"
)

# Configurar CORS para permitir peticiones desde cualquier origen (ideal para desarrollo local y GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción puedes restringir esto a tu dominio de GitHub Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.utils.mongo_loader import load_mongo_data
from fastapi import Response
from dotenv import load_dotenv

load_dotenv() # Ensure env vars are loaded

@app.get("/api/predictions")
def get_predictions():
    """Obtiene las predicciones guardadas en MongoDB (colección quiniela_predictions)."""
    try:
        data = load_mongo_data("quiniela_predictions")
        
        if not data:
            return {"error": "No se encontraron predicciones en la base de datos"}
        
        import json
        return Response(content=json.dumps(data), media_type="application/json")
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"ERROR EN API: {error_msg}")
        return {"error": str(e), "traceback": error_msg}

@app.get("/")
async def root():
    return {"message": "Quiniela API funcionando. Visita /api/predictions para ver los datos o /docs para la documentación."}
