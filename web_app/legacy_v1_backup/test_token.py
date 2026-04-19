import requests, json

BASE = "http://127.0.0.1:8000"

def login():
    # 使用 init_db.py 中初始化的用户名 admin 和对应的密码 admin123
    resp = requests.post(f"{BASE}/api/merchants/login", json={
        "shop_code": "starbilliards",
        "phone": "admin",
        "password": "admin123"
    })
    print('Login response:', resp.status_code, resp.text)
    data = resp.json()
    return data.get('access_token'), data.get('shop', {}).get('shop_code')

def test_access(token, shop_code):
    headers = {"Authorization": f"Bearer {token}", "X-Shop-Code": shop_code}
    resp = requests.get(f"{BASE}/api/merchants/info", headers=headers)
    print('Info response:', resp.status_code, resp.text)

if __name__ == "__main__":
    token, shop_code = login()
    if token and shop_code:
        test_access(token, shop_code)
    else:
        print('Login failed, cannot test token')
