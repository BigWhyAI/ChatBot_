from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from typing import Annotated
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import asyncio
import json
import time
import os

load_dotenv()
from openai import OpenAI

client = OpenAI(api_key= os.getenv('OPENAI_API_KEY'))

app = FastAPI()
templates = Jinja2Templates(directory="templates")

chat_log = [{'role': 'system',
                'content': 'Tu racontes des histoires, des contes, des histoires de film'
            }]

chat_responses = []

@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})


@app.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected")
    
    try:
        while True:
            user_input = await websocket.receive_text()
            print(f"Received: {user_input}")
            
            # Ajouter à l'historique
            chat_log.append({'role': 'user', 'content': user_input})
            chat_responses.append(user_input)

            try:
                # SOLUTION 1: Forcer le flush avec des paramètres optimisés
                response = client.chat.completions.create(
                    model='gpt-4',
                    messages=chat_log,
                    temperature=0.6,
                    stream=True,
                    max_tokens=2000,  # Limite pour éviter les longs chunks
                    stream_options={"include_usage": False}  # Réduire la métadata
                )

                ai_response = ''
                chunk_count = 0
                start_time = time.time()
                
                print("Starting to process stream...")
                
                for chunk in response:
                    chunk_count += 1
                    print(f"Chunk {chunk_count} received at {time.time() - start_time:.2f}s")
                    
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content is not None:
                            content = delta.content
                            ai_response += content
                            print(f"Sending content: '{content[:50]}...'")
                            
                            # SOLUTION 2: Envoyer immédiatement avec flush
                            await websocket.send_text(json.dumps({
                                "type": "chunk",
                                "content": content,
                                "chunk_id": chunk_count,
                                "timestamp": time.time()
                            }))
                            
                            # SOLUTION 3: Petite pause pour éviter la surcharge
                            await asyncio.sleep(0.001)
                
                print(f"Stream completed. Total chunks: {chunk_count}")
                
                # Signaler la fin
                await websocket.send_text(json.dumps({
                    "type": "end",
                    "full_response": ai_response,
                    "total_chunks": chunk_count
                }))
                
                # Ajouter à l'historique
                chat_log.append({'role': 'assistant', 'content': ai_response})        
                chat_responses.append(ai_response)
                
            except Exception as e:
                print(f"Error during streaming: {str(e)}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error: {str(e)}"
                }))
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")


# SOLUTION 4: Version alternative avec asyncio pour forcer le streaming
@app.websocket("/ws-async")
async def chat_ws_async(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket async connected")
    
    try:
        while True:
            user_input = await websocket.receive_text()
            print(f"Received: {user_input}")
            
            chat_log.append({'role': 'user', 'content': user_input})
            chat_responses.append(user_input)

            try:
                # Version corrigée du générateur asynchrone
                async def stream_response():
                    response = client.chat.completions.create(
                        model='gpt-4',
                        messages=chat_log,
                        temperature=0.6,
                        stream=True,
                        max_tokens=1500
                    )

                    ai_response = ''
                    chunk_count = 0
                    
                    for chunk in response:
                        chunk_count += 1
                        if chunk.choices and len(chunk.choices) > 0:
                            delta = chunk.choices[0].delta
                            if hasattr(delta, 'content') and delta.content is not None:
                                content = delta.content
                                ai_response += content
                                
                                # Envoyer immédiatement
                                yield {
                                    "type": "chunk",
                                    "content": content,
                                    "chunk_id": chunk_count,
                                    "full_response": ai_response  # Inclure la réponse partielle
                                }
                    
                    # Dernier yield pour la fin
                    yield {
                        "type": "end",
                        "full_response": ai_response,
                        "total_chunks": chunk_count
                    }
                
                # Traiter le stream de manière asynchrone
                ai_response = ''
                async for data in stream_response():
                    if data["type"] == "chunk":
                        ai_response = data["full_response"]  # Utiliser la réponse complète
                    elif data["type"] == "end":
                        ai_response = data["full_response"]
                    
                    await websocket.send_text(json.dumps(data))
                    await asyncio.sleep(0.01)  # Petite pause pour le flush
                
                # Ajouter à l'historique
                chat_log.append({'role': 'assistant', 'content': ai_response})        
                chat_responses.append(ai_response)
                
            except Exception as e:
                print(f"Error: {str(e)}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error: {str(e)}"
                }))
                
    except WebSocketDisconnect:
        print("Client disconnected")


# SOLUTION 5: Test avec chunks simulés pour déboguer
@app.websocket("/ws-test")
async def chat_ws_test(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            user_input = await websocket.receive_text()
            
            # Simuler une réponse streaming pour tester
            test_response = "Ceci est une réponse de test pour vérifier que le streaming fonctionne correctement avec des chunks séparés."
            words = test_response.split()
            
            for i, word in enumerate(words):
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "content": word + " ",
                    "chunk_id": i + 1
                }))
                await asyncio.sleep(0.1)  # Pause entre chaque mot
            
            await websocket.send_text(json.dumps({
                "type": "end",
                "full_response": test_response
            }))
            
    except WebSocketDisconnect:
        print("Test client disconnected")


# Endpoints HTTP inchangés
@app.post("/", response_class=HTMLResponse)
async def chat_http(request: Request, user_input: Annotated[str, Form()]):
    chat_log.append({'role': 'user', 'content': user_input})
    chat_responses.append(user_input)

    response = client.chat.completions.create(
        model='gpt-4',
        messages=chat_log,
        temperature=0.6
    )

    bot_response = response.choices[0].message.content
    chat_log.append({'role': 'assistant', 'content': bot_response})
    chat_responses.append(bot_response)

    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})

@app.get("/image", response_class= HTMLResponse)
async def image_page(request : Request):
    return templates.TemplateResponse("image.html", {"request": request})


@app.post("/image", response_class=HTMLResponse)
async def create_image(request: Request, user_input: Annotated[str, Form()]):
    response = client.images.generate(
        model="gpt-image-1",
        prompt=user_input,
        n=1,
        size="256x256"
    )
    image_url = response.data[0].url
    return templates.TemplateResponse("image.html", {"request": request, 'image_url': image_url})