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

@app.get("/test-templates")
async def test_templates():
    """Tester les fichiers templates"""
    results = {}
    
    try:
        # Vérifier le dossier templates
        if os.path.exists('templates'):
            results["templates_dir"] = {
                "exists": True,
                "contents": os.listdir('templates')
            }
        else:
            results["templates_dir"] = {"exists": False}
        
        # Tester chaque fichier template
        template_files = ['templates/home.html', 'templates/image.html']
        
        for template_file in template_files:
            try:
                if os.path.exists(template_file):
                    with open(template_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        results[template_file] = {
                            "exists": True,
                            "size": len(content),
                            "first_100_chars": content[:100],
                            "readable": True
                        }
                else:
                    results[template_file] = {
                        "exists": False,
                        "error": "File not found"
                    }
            except Exception as e:
                results[template_file] = {
                    "exists": os.path.exists(template_file),
                    "error": str(e)
                }
        
        return results
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

@app.get("/test-openai")
async def test_openai():
    """Tester l'initialisation OpenAI"""
    try:
        from openai import OpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {"error": "OPENAI_API_KEY not found"}
        
        # Test d'initialisation
        client = OpenAI(api_key=api_key)
        
        # Test très simple (sans faire d'appel API coûteux)
        return {
            "openai_import": "success",
            "client_creation": "success", 
            "api_key_length": len(api_key),
            "ready_for_api_calls": True
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )