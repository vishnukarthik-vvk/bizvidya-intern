from aqlachemy import Column , Integer , String
from database import Base

class User(Base):
    __tablename__  = "users"

    id = Column(Integer,primary_key = True,index = True)
    full_name = Column(String)
    age = Column(Integer)
    edcutation_level = Column(String)
    work_exprience = Column(String)
    current_role = Column(String)
    preffred_language = Column(String)