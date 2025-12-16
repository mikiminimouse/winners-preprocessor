// Инициализационный скрипт для MongoDB
print("=== MongoDB Initialization Script ===");

// Создаем базу данных для протоколов закупок
const protocolsDb = db.getSiblingDB('protocols223');

// Создаем коллекцию purchaseProtocol
protocolsDb.createCollection('purchaseProtocol');
print("Created collection: protocols223.purchaseProtocol");

// Создаем индексы для коллекции purchaseProtocol
protocolsDb.purchaseProtocol.createIndex({ "loadDate": 1 });
protocolsDb.purchaseProtocol.createIndex({ "purchaseInfo.purchaseNoticeNumber": 1 });
protocolsDb.purchaseProtocol.createIndex({ "attachments.document.url": 1 });
print("Created indexes for protocols223.purchaseProtocol");

// Создаем базу данных для метаданных обработки документов
const metadataDb = db.getSiblingDB('docling_metadata');

// Создаем коллекцию manifests
metadataDb.createCollection('manifests');
print("Created collection: docling_metadata.manifests");

// Создаем индексы для коллекции manifests
metadataDb.manifests.createIndex({ "unit_id": 1 }, { unique: true });
metadataDb.manifests.createIndex({ "created_at": 1 });
metadataDb.manifests.createIndex({ "processing.status": 1 });
print("Created indexes for docling_metadata.manifests");

// Создаем пользователей
// Пользователь с правами чтения для протоколов
protocolsDb.createUser({
  user: "readonly_user",
  pwd: "password",
  roles: [
    { role: "read", db: "protocols223" }
  ]
});
print("Created user: readonly_user");

// Пользователь с правами записи для метаданных
metadataDb.createUser({
  user: "docling_user",
  pwd: "password",
  roles: [
    { role: "readWrite", db: "docling_metadata" }
  ]
});
print("Created user: docling_user");

print("=== MongoDB Initialization Complete ===");
