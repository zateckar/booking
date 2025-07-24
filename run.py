import uvicorn

from src.booking.database import create_db_and_tables

if __name__ == "__main__":
    create_db_and_tables()
    uvicorn.run("src.booking:app", host="0.0.0.0", port=8000, reload=True)
