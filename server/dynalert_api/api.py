from fastapi import FastAPI

app = FastAPI()

@app.get("/api/user/{user_id}")
async def get_user(user_id: str):
    return {"user_id": user_id, "name": "John Doe"}
