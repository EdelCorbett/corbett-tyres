from fastapi import FastAPI

app = FastAPI(title="Corbett Tyres Management System")

@app.get("/")
def health_check():
    return {"status": "ok"}
