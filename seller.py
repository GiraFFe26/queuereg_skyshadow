import requests
import time
import hashlib
from datetime import datetime, timedelta
import zoneinfo
import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from requests.exceptions import ConnectTimeout, ReadTimeout
from config import API_KEY, SELLER_ID, PHRASES


class DigisellerApi:

    def __init__(self):
        self.API = API_KEY #api-key
        self.SELLER_ID = SELLER_ID #id продавца

    # ПОЛУЧЕНИЕ ТОКЕНА
    def get_token(self):
        timestamp = str(int(time.time()))
        sign = hashlib.sha256((self.API + timestamp).encode('UTF-8')).hexdigest()
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        json_data = {
            "seller_id": self.SELLER_ID,
            "timestamp": timestamp,
            "sign": sign
        }
        r = requests.post('https://api.digiseller.ru/api/apilogin', headers=headers, json=json_data).json()
        token = r['token']
        with open('token.txt', 'w', encoding='UTF-8') as file:
            file.write(token)

        # Файл, полученный в Google Developer Console
        CREDENTIALS_FILE = 'creds.json'
        # ID Google Sheets документа (можно взять из его URL)
        spreadsheet_id = ''
        # Авторизуемся и получаем service — экземпляр доступа к API
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE,
            ['https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive'])
        httpAuth = credentials.authorize(httplib2.Http())
        service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)
        # Пример записи в файл
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": f"Заказы!T1:T1",
                     "majorDimension": "ROWS",
                     "values": [[token]]}
                ]
            }
        ).execute()

    def del_lines(self):
        # Файл, полученный в Google Developer Console
        CREDENTIALS_FILE = 'creds.json'
        # ID Google Sheets документа (можно взять из его URL)
        spreadsheet_id = ''
        # Авторизуемся и получаем service — экземпляр доступа к API
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE,
            ['https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive'])
        httpAuth = credentials.authorize(httplib2.Http())
        service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)
        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'Заказы!A:H',
            majorDimension='ROWS'
        ).execute()
        values = values['values'][1:]
        k = 0
        for i in values:
            if i[0] == 'Skyshadow':
                invoice_id = i[2]
                status = self.check_date_end(invoice_id)
                if status:
                    row = values.index(i) + 1 - k
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={
                            "requests": [
                                {
                                    "deleteDimension": {
                                        "range": {
                                            "dimension": "ROWS",
                                            "startIndex": row,
                                            "endIndex": row + 1
                                        }
                                    }
                                }
                            ]
                        }
                    ).execute()
                    k += 1
            elif i[-1] == '💰':
                row = values.index(i) + 1 - k
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        "requests": [
                            {
                                "deleteDimension": {
                                    "range": {
                                        "dimension": "ROWS",
                                        "startIndex": row,
                                        "endIndex": row + 1
                                    }
                                }
                            }
                        ]
                    }
                ).execute()
                k += 1

    # ПОЛУЧАЕМ НАЗВАНИЕ ТОВАРА И КОЛ-ВОЦ
    def check_date_end(self, invoice_id):
        with open('token.txt', 'r', encoding='UTF-8') as file:
            token = file.read()
        headers = {'Accept': 'application/json'}
        r = requests.get(f'https://api.digiseller.ru/api/purchase/info/{invoice_id}?token={token}', headers=headers).json()
        state = r['content']['unique_code_state']['state']
        status = 0
        if state == 2 or state == 3:
            status = 1
        return status

    def get_sales(self):
        with open('token.txt', 'r', encoding='UTF-8') as file:
            token = file.read()
        headers = {'Content-Type': "application/json",
                   'Accept': "application/json"}
        offset = datetime.now(zoneinfo.ZoneInfo("Europe/Moscow"))
        offset = datetime.strftime(offset, "%Y-%m-%d %H:%M:%S")
        json_data = {
                  "date_start": str(datetime.strptime(offset, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=3)),
                  "date_finish": str(offset),
                  "returned": 0,
                  "page": 1,
                  "rows": 10
                }
        try:
            r = requests.post(f'https://api.digiseller.ru/api/seller-sells/v2?token={token}', headers=headers, json=json_data).json()
        except (ConnectTimeout, ReadTimeout):
            r = requests.post(f'https://api.digiseller.ru/api/seller-sells/v2?token={token}', headers=headers, json=json_data).json()
        for i in r['rows']:
            invoice_id = i['invoice_id']
            mail = i['email']
            product, cnt = self.check_for_sheets(invoice_id)
            if product != 'key':
                self.send_to_sheets('Skyshadow', mail, invoice_id, product, cnt)

    # ПОЛУЧАЕМ НАЗВАНИЕ ТОВАРА И КОЛ-ВОЦ
    def check_for_sheets(self, invoice_id):
        with open('token.txt', 'r', encoding='UTF-8') as file:
            token = file.read()
        headers = {'Accept': 'application/json'}
        r = requests.get(f'https://api.digiseller.ru/api/purchase/info/{invoice_id}?token={token}', headers=headers).json()
        r = r['content']
        item_id = int(r['item_id'])
        with open('ids.txt', 'r', encoding='UTF-8') as file:
            ids = [int(i.strip()) for i in file.readlines()]
        if item_id in ids:
            return 'key', 'key'
        check = r['options']
        for k, i in enumerate(check):
            if i["name"] in PHRASES:
                continue
            else:
                print(i["name"])
                r = check[k]
                break
        return r["name"], r["user_data"]

    def send_to_sheets(self, owner, login, password, product, cnt, comment='❌', status=0):
        # Файл, полученный в Google Developer Console
        CREDENTIALS_FILE = 'creds.json'
        # ID Google Sheets документа (можно взять из его URL)
        spreadsheet_id = ''
        # Авторизуемся и получаем service — экземпляр доступа к API
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE,
            ['https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive'])
        httpAuth = credentials.authorize(httplib2.Http())
        service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)

        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"Заказы!A:Z",
            majorDimension='ROWS'
        ).execute()
        x = len(values['values']) + 1

        # Пример записи в файл
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": f"Заказы!A{x}:G{x}",
                     "majorDimension": "ROWS",
                     "values": [[owner, login, password, product, cnt, comment, status]]}
                ]
            }
        ).execute()
        return 'Заказ добавлен в таблицу!'
