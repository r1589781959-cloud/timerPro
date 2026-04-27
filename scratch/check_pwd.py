import bcrypt

def check():
    password = b'ryy123456'
    # 数据库里的哈希值
    db_hash = b'$2b$12$hDYaqJVa1pqml5tcXJUk.urkNnCcI28vj1w3A3KLrPa2MHtT.JfRC'
    
    result = bcrypt.checkpw(password, db_hash)
    print(f"验证结果: {result}")

if __name__ == "__main__":
    check()
