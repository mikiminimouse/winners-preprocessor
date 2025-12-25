#!/usr/bin/env python3
"""
Test MongoDB connection to verify local database accessibility
"""

import sys
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Add project root to path
project_root = Path(__file__).parent
receiver_path = project_root / "receiver"
sys.path.insert(0, str(receiver_path))
sys.path.insert(0, str(project_root))

def test_mongodb_connection():
    """Test connection to local MongoDB"""
    try:
        # Load configuration
        from receiver.core.config import load_env_file, get_config
        env_file = receiver_path / ".env"
        if env_file.exists():
            load_env_file(env_file)
            print("✅ Configuration loaded")
        
        config = get_config()
        
        # Access MongoDB configuration through the correct path
        local_mongo_config = config.sync_db.local_mongo
        
        server = local_mongo_config.server
        username = local_mongo_config.user
        password = local_mongo_config.password
        database = local_mongo_config.db
            
        print(f"📡 Connecting to MongoDB at {server}")
        print(f"👤 User: {username}")
        print(f"🗄️  Database: {database}")
        
        # Create connection string
        if username and password:
            connection_string = f"mongodb://{username}:{password}@{server}/{database}?authSource=admin"
        else:
            connection_string = f"mongodb://{server}/{database}"
            
        print(f"🔗 Connection string: {connection_string.split('@')[0]}@***")
        
        # Connect to MongoDB
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB")
        
        # List databases
        databases = client.list_database_names()
        print(f"📚 Available databases: {databases}")
        
        # Check if our database exists
        if database in databases:
            print(f"✅ Database '{database}' exists")
            
            # List collections in our database
            db = client[database]
            collections = db.list_collection_names()
            print(f"📂 Collections in '{database}': {collections}")
        else:
            print(f"⚠️  Database '{database}' not found")
            
        client.close()
        return True
        
    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during MongoDB test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run MongoDB connection test"""
    print("🧪 Testing MongoDB Connection...\n")
    
    success = test_mongodb_connection()
    
    if success:
        print("\n🎉 MongoDB connection test completed successfully!")
        return 0
    else:
        print("\n💥 MongoDB connection test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())