import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from googleapiclient.errors import HttpError
from typing import Optional, List, Dict
import markdown
from bs4 import BeautifulSoup

# .envファイルから環境変数をロード
load_dotenv()

# Google Docs APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']

def get_credentials():
    """
    Google APIの認証情報を取得する関数
    
    戻り値:
        Credentials: Google APIの認証情報
    """
    creds = None
    # トークンファイルが存在する場合はそれを使用
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # 有効な認証情報がない場合、ユーザーにログインを要求
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # credentials.jsonファイルが必要
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 次回のために認証情報を保存
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def save_to_google_docs(content, filename, folder_id=None, format_options=None):
    """
    テキスト内容をGoogle Docsに保存する関数
    
    引数:
        content (str): 保存するテキスト内容
        filename (str): Google Docsのドキュメント名
        folder_id (str, optional): 保存先のGoogle DriveフォルダのID
        format_options (dict, optional): テキストのフォーマットオプション
    
    戻り値:
        str: 作成されたドキュメントのURL
    """
    try:
        # 認証情報を取得
        creds = get_credentials()
        
        # Google Docs APIとDrive APIのサービスを構築
        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 新しいドキュメントを作成
        document = {
            'title': filename
        }
        doc = docs_service.documents().create(body=document).execute()
        document_id = doc.get('documentId')
        
        # テキスト内容を追加
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': content
                }
            }
        ]
        
        # フォーマットオプションがある場合、適用する
        if format_options:
            # format_optionsの内容に応じてリクエストを追加
            pass
        
        # バッチ更新を実行
        docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()
        
        # 特定のフォルダに保存する場合
        if folder_id:
            # 既存のドキュメントの親を変更
            file = drive_service.files().get(
                fileId=document_id, 
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents'))
            
            # ファイルを指定されたフォルダに移動
            file = drive_service.files().update(
                fileId=document_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
        
        # ドキュメントのURLを返す
        return f"https://docs.google.com/document/d/{document_id}/edit"
    
    except Exception as e:
        print(f"Google Docsへの保存中にエラーが発生しました: {str(e)}")
        return None


def insert_to_google_docs(document_id: str, markdown_text: str) -> Optional[str]:
    """
    マークダウンテキストをGoogle Docsに挿入する関数
    
    引数:
        document_id (str): Google DocsのドキュメントID
        markdown_text (str): 挿入するマークダウンテキスト
    
    戻り値:
        Optional[str]: 成功時はドキュメントのURL、失敗時はNone
    """
    try:
        # 認証情報の設定
        creds = Credentials.from_authorized_user_info(
            {
                'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
                'refresh_token': os.getenv('GOOGLE_REFRESH_TOKEN')
            }
        )
        
        # Google Docs APIクライアントの初期化
        service = build('docs', 'v1', credentials=creds)
        

        
        # バッチ更新を実行
        result = service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': markdown_text}
        ).execute()
        
        # ドキュメントのURLを返す
        return f"https://docs.google.com/document/d/{document_id}"
    
    except HttpError as error:
        print(f"Google Docs APIでエラーが発生しました: {error}")
        return None
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {str(e)}")
        return None

# 使用例:
# document_url = insert_to_google_docs("document_id", "# 見出し\n\n本文") 