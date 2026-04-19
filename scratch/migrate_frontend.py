import os

# 读取旧版
old_path = r'e:\antigravity_project_01\web_app\static\old_version\index.html'
new_path = r'e:\antigravity_project_01\web_app\static\index.html'

with open(old_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 注入拦截器 (在 <head> 结束前)
saas_script = """
    <script>
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            let [url, config] = args;
            const token = localStorage.getItem('access_token');
            const shopCode = localStorage.getItem('shop_code');
            config = config || {};
            config.headers = config.headers || {};
            if (token) config.headers['Authorization'] = 'Bearer ' + token;
            if (shopCode) config.headers['X-Shop-Code'] = shopCode;
            const res = await originalFetch(url, config);
            if (res.status === 401) {
                localStorage.clear();
                window.location.href = '/login.html';
            }
            return res;
        };
    </script>
"""
content = content.replace('</head>', saas_script + '</head>')

# 2. 注入数据变量 (在 data() 开始后)
content = content.replace('data() {', "data() {\n                return {\n                    shopInfo: JSON.parse(localStorage.getItem('shop_info') || '{}'),")

# 3. 注入权限检查 (在 mounted() 开始后)
auth_logic = """
            mounted() {
                const token = localStorage.getItem('access_token');
                if (!token) { window.location.href = '/login.html'; return; }
"""
content = content.replace('mounted() {', auth_logic)

# 4. 在顶栏显示商家名称 (寻找合适位置插入)
# 寻找 Header 里的标题处
target_title = '<h1 class="text-xl font-bold">TimerPro</h1>'
saas_title = '<h1 class="text-xl font-bold">TimerPro <span class="text-sm font-normal opacity-70">| {{ shopInfo.shop_name }}</span></h1>'
content = content.replace(target_title, saas_title)

with open(new_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SaaS-ify 转换完成！")
