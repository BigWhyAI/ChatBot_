from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import traceback

app = FastAPI()

# Handler d'erreur global pour capturer toutes les exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "traceback": traceback.format_exc(),
            "url": str(request.url)
        }
    )

@app.get("/")
async def root():
    """Page d'accueil ultra-simple pour tester"""
    try:
        return {
            "message": "Hello from FastAPI on Render!",
            "status": "success",
            "environment": {
                "python_path": os.getcwd(),
                "files_in_directory": os.listdir('.'),
                "openai_key_exists": bool(os.getenv('OPENAI_API_KEY')),
                "templates_dir_exists": os.path.exists('templates')
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

@app.get("/health")
async def health():
    """Endpoint de santé"""
    return {"status": "healthy", "message": "Service is running"}

@app.get("/debug")
async def debug():
    """Informations de debug détaillées"""
    try:
        import sys
        return {
            "python_version": sys.version,
            "working_directory": os.getcwd(),
            "directory_contents": os.listdir('.'),
            "environment_variables": {
                "OPENAI_API_KEY": "SET" if os.getenv('OPENAI_API_KEY') else "NOT SET",
                "PATH": os.getenv('PATH', 'NOT SET')[:100] + "...",
            },
            "sys_path": sys.path[:3]  # Premiers 3 éléments seulement
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )