from database import engine

try:
    with engine.connect() as connection:
        print("Connected to potrage sql")
except Exception as e:
    print("connection failed:")
    print(e)