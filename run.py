import uvicorn
import argparse

from src.booking.database import create_db_and_tables

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Booking API application.")
    parser.add_argument(
        "--log-level",
        default="warning",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set the logging level for the Uvicorn server."
    )
    args = parser.parse_args()

    create_db_and_tables()
    uvicorn.run(
        "src.booking:app", host="0.0.0.0", port=8000, reload=True,
        log_level=args.log_level
    )
