from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

username = os.getenv('MONGODB_USER')
password = os.getenv('MONGODB_PSWD')
uri = f"mongodb+srv://{username}:{password}@github-extracts.ide0ptg.mongodb.net/?retryWrites=true&w=majority&appName=github-extracts"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

def get_commits(collection_name):
    db = client['Turma14']
    collection = db[collection_name]
    documents = collection.find()
    return documents

def insert_document(collection_name, commit):
    db = client['Turma14']
    collection = db[collection_name]
    document = collection.insert_one(commit)
    return document.inserted_id

def ping_database():
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)