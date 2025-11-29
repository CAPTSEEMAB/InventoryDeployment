from app.main import app

# EB expects the WSGI application to be named 'application'
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(application, host="0.0.0.0", port=8000)
