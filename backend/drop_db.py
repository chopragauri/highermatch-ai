from app.database import engine, Base
from app import models
print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Done.")
