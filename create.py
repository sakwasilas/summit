from connections import Base, engine
from models import User,Admin  


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")