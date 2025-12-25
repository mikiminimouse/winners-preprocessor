# mcp_http_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
from dotenv import load_dotenv
import json
import uvicorn
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import Dict, Any, List, Union

# Загружаем переменные из .env файла
load_dotenv()

app = FastAPI(title="MCP HTTP Server", version="1.0.0")


class ToolRequest(BaseModel):
    name: str
    arguments: dict


class InitializeRequest(BaseModel):
    protocolVersion: str = "2024-11-05"
    capabilities: dict = {}
    clientInfo: dict = {"name": "http-client", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"status": "MCP HTTP Server is running"}


@app.post("/initialize")
async def initialize(request: InitializeRequest):
    return {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "mcp-http-server",
                "version": "1.0.0"
            }
        }
    }


@app.get("/tools")
async def list_tools():
    return {
        "jsonrpc": "2.0",
        "result": {
            "tools": [

                {
                    "name": "demo44_purchase",
                    "description": "Получает информацию о закупке по номеру",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "purchaseNumber": {
                                "type": "string",
                                "description": "Номер закупки"
                            }
                        },
                        "required": ["purchaseNumber"]
                    }
                },
                {
                    "name": "get_protocols_by_date_223",
                    "description": "Получает протоколы по дате и извлекает purchaseNoticeNumber, имя и URL вложений",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Дата в формате YYYY-MM-DD",
                                "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                            }
                        },
                        "required": ["date"]
                    }
                }
            ]
        }
    }


def get_protocols_by_date_223(date_str: str) -> Dict[str, Any]:
    """Получает протоколы по дате и извлекает purchaseNoticeNumber и URL"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Неверный формат даты '{date_str}'. Используйте формат YYYY-MM-DD")

    # Получаем параметры из .env
    mongo_hosts = os.getenv("mongoServer")
    username = os.getenv("readAllUser")
    password = os.getenv("readAllPassword")
    ssl_cert_path = os.getenv("sslCertPath")
    protocols_count_limit = int(os.getenv("protocolsCountLimit", "100"))

    if not all([mongo_hosts, username, password, ssl_cert_path]):
        raise HTTPException(status_code=500, detail="Не все необходимые параметры найдены в .env файле")

    try:
        # Формируем строку подключения для шардированного кластера
        url_mongo = f'mongodb://{username}:{password}@{mongo_hosts}/?authSource=protocols223'

        client = MongoClient(
            url_mongo,
            tls=True,
            authMechanism="SCRAM-SHA-1",
            tlsAllowInvalidHostnames=True,
            tlsCAFile=ssl_cert_path
        )

        # Проверяем подключение
        client.admin.command('ping')

        db = client['protocols223']
        collection = db['purchaseProtocol']

        # Создаем запрос для поиска по дате
        start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
        end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)

        query = {
            "loadDate": {
                "$gte": start_of_day,
                "$lte": end_of_day
            }
        }

        result_dict = {}

        # Выполняем запрос с ограничением количества
        protocols = collection.find(query).limit(protocols_count_limit)

        for protocol in protocols:
            purchase_info = protocol.get('purchaseInfo')
            purchase_notice_number = purchase_info.get('purchaseNoticeNumber')
            attachments = protocol.get('attachments', {})
            documents = attachments.get('document', [])
            print(purchase_notice_number, documents)

            # Если documents - это один документ (словарь), превращаем в список
            if isinstance(documents, dict):
                documents = [documents]

            urls = []
            for doc in documents:
                if isinstance(doc, dict) and 'url' in doc:
                    urls.append(doc)  # ['url'])

            if purchase_notice_number and urls:
                # Если только один URL, сохраняем как строку, иначе как список
                if len(urls) == 1:
                    result_dict[purchase_notice_number] = urls[0]
                else:
                    result_dict[purchase_notice_number] = urls
        print(result_dict)
        return result_dict

    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"MongoDB error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()


@app.post("/tools/call")
async def call_tool(request: ToolRequest):
    if request.name == "demo44_purchase":
        purchase_number = request.arguments.get("purchaseNumber", "")
        apikey = os.getenv("MULTITENDER_API_KEY")

        if not apikey:
            raise HTTPException(status_code=500, detail="API ключ не найден в .env файле")

        url = f"https://api-v2.multitender.ru/purchase/demo44?purchaseNumber={purchase_number}&apikey={apikey}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": response.text
                        }
                    ]
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при запросе: {str(e)}")

    elif request.name == "get_protocols_by_date_223":
        date_str = request.arguments.get("date", "")
        try:
            result = get_protocols_by_date_223(date_str)
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "json",  # Изменено с "text" на "json"
                            "json": result  # Добавлено поле "json" с данными
                        }
                    ]
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при работе с базой данных: {str(e)}")

    else:
        raise HTTPException(status_code=404, detail=f"Инструмент не найден: {request.name}")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )