from sqlalchemy import Column, Integer, String
from database import Base

class DocumentEntry(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    website_name = Column(String)
    website_url = Column(String)
    file_path = Column(String)
    unique_endpoint = Column(String, unique=True)
