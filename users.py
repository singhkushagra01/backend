from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')

# Access the database
db = client['file_sharing']

# Define ops and client users
ops_user = {
    "username": "opsuser",
    "password": "opspassword",
    "role": "ops"
}

client_user = {
    "username": "clientuser",
    "password": "clientpassword",
    "role": "client"
}

# Insert ops user
ops_users_collection = db['users']
ops_users_collection.insert_one(ops_user)
print("Ops user inserted successfully.")

# Insert client user
client_users_collection = db['users']
client_users_collection.insert_one(client_user)
print("Client user inserted successfully.")
