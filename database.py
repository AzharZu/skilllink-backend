from pymongo import MongoClient

client = MongoClient(
    "mongodb+srv://azhar208asko:VK4afbYrlcAF6Ury@cluster0.s2j378f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
    tls=True
)

db = client.skilllink

