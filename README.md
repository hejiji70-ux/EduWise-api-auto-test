# EduWise 智课 — 接口自动化测试

## 项目简介

基于 Python + Requests + Pytest 的接口自动化测试框架，覆盖 EduWise 智课平台 Admin、Teacher、App 三端全部核心 API 接口。

## 技术栈

- Python 3.x
- Requests（HTTP 请求库）
- Pytest（测试框架）
- Pytest-html / Allure（测试报告）
- PyYAML（配置文件解析）

## 项目结构

```
EduWise-api-auto-test/
├── README.md
├── requirements.txt          # Python 依赖
├── conftest.py             # Pytest 固件（登录、Token 管理）
├── pytest.ini              # Pytest 配置
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml         # GitHub Actions CI 配置
├── config/
│   └── config.yaml        # 测试环境配置（URL、账号密码）
├── testdata/               # YAML 格式测试数据
│   ├── admin_login.yaml
│   ├── teacher_login.yaml
│   ├── app_login.yaml
│   ├── admin_api.yaml
│   ├── teacher_api.yaml
│   └── app_api.yaml
├── utils/                  # 工具类
│   ├── api_client.py       # 封装 HTTP 请求（自动处理 Token）
│   ├── data_loader.py      # YAML 数据驱动加载器
│   └── logger.py          # 日志工具
├── tests/                  # 测试用例
│   ├── test_admin.py       # Admin 端接口测试（40 个用例）
│   ├── test_teacher.py     # Teacher 端接口测试
│   └── test_app.py        # App 端接口测试
└── logs/                   # 测试日志（git 忽略）
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行 Admin 端测试
pytest tests/test_admin.py -v

# 生成 HTML 报告
pytest tests/ -v --html=reports/report.html
```

## 测试结果

- 总用例数：40
- 通过：40
- 失败：0
- 通过率：100%

## CI/CD

推送到 GitHub 后，Actions 自动运行：
- 安装 Python 依赖
- 运行全部接口自动化测试
- 上传测试报告作为 Artifacts

## 注意事项

- 运行测试前需启动本地 Docker 服务（后端监听 http://localhost:9096）
- Token 自动管理：conftest.py 在每个测试前自动登录获取 Token
- 测试数据驱动：用例参数从 `testdata/` 目录的 YAML 文件读取
