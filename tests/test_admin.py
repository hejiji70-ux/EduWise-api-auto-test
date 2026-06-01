"""
test_admin.py — Admin 后台管理端接口自动化测试
覆盖：管理员登录 / 用户信息 / 学员管理 / 讲师管理 / 课程管理 / 数据统计
"""

import pytest
import allure
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import ApiClient
from utils.logger import get_logger
from utils.data_loader import load_cases, get_case_ids

logger = get_logger(__name__)


# ── 加载测试数据 ───────────────────────────────────────────────
login_cases = load_cases("admin_login.yaml")
api_cases = load_cases("admin_api.yaml")


@allure.feature("Admin 管理端")
@allure.story("管理员登录")
class TestAdminLogin:
    """Admin 登录接口测试（数据驱动，3 组数据）"""

    @pytest.mark.parametrize("case", login_cases, ids=get_case_ids(login_cases))
    def test_login(self, cfg, case):
        client = ApiClient(cfg["base_url"])
        resp = client.post(cfg["admin"]["login_url"], json=case["body"])

        if case.get("assert_fail"):
            body = ApiClient.assert_fail(resp, msg=case["title"])
            assert body["status"] != 200
            logger.info(f"[{case['title']}] status={body['status']}, message={body.get('message')}")
        else:
            data = ApiClient.assert_ok(resp, case["title"])
            expected = case.get("expected", {})
            if expected.get("has_token"):
                assert data["token"], "登录成功应返回 token"
            if expected.get("username_equals"):
                assert data["username"] == expected["username_equals"]
            logger.info(f"[{case['title']}] token=✓, username={data.get('username')}")


# ── 通用执行器（被下方所有测试类共用）────────────────────────


def _run_api_case(client: ApiClient, case: dict):
    """
    通用 API 测试执行器
    YAML 描述"测什么"，这个函数负责"怎么测"
    """
    method = case.get("method", "GET").upper()
    url = case["url"]

    if method == "POST":
        params_query = case.get("params_query", {})
        resp = client.post(url, json=case.get("body"), params=params_query or None)
    else:
        resp = client.get(url)

    if case.get("assert_fail"):
        body = resp.json()
        assert body.get("status") != 200, f"[{case['title']}] 未授权访问不应成功"
        logger.info(f"[{case['title']}] status={body.get('status')}, message={body.get('message')}")
        return

    data = ApiClient.assert_ok(resp, case["title"])
    _assert_expected(data, case.get("expected", {}), case["title"])

    # 特殊处理：从列表提取 ID 再查详情
    if case.get("extract_id_from_list") and isinstance(data, dict) and data.get("total", 0) > 0:
        item_id = data["list"][0]["id"]
        detail_url = case.get("detail_url_template", "").replace("{id}", str(item_id))
        detail_resp = client.get(detail_url)
        detail_data = ApiClient.assert_ok(detail_resp, f"{case['title']} → 详情")
        assert detail_data["id"] == item_id
        logger.info(f"[{case['title']} → 详情] id={item_id}")


def _assert_expected(data, expected: dict, title: str):
    """根据 YAML expected 规则校验响应数据"""
    if expected.get("has_field"):
        assert expected["has_field"] in data, "[%s] 缺少字段 %s" % (title, expected["has_field"])
    if expected.get("has_fields"):
        for field in expected["has_fields"]:
            assert field in data, "[%s] 缺少字段 %s" % (title, field)
    if expected.get("has_any_field"):
        has_any = any(f in data for f in expected["has_any_field"])
        assert has_any, "[%s] 应包含任一字段 %s" % (title, expected["has_any_field"])
    if expected.get("field_equals"):
        for k, v in expected["field_equals"].items():
            actual = data.get(k)
            assert actual == v, "[%s] 字段 %s: 期望=%s, 实际=%s" % (title, k, v, actual)
    if expected.get("type_is") == "list":
        assert isinstance(data, list), "[%s] 应为列表" % title
    if expected.get("not_empty"):
        assert len(data) > 0, "[%s] 不应为空" % title


@allure.feature("Admin 管理端")
@allure.story("用户信息")
class TestAdminUserInfo:
    """管理员信息查询测试（部分 case 不需要 token）"""

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "用户信息"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "用户信息"]),
    )
    def test_user_info(self, request, case):
        if case.get("need_token", True):
            client = request.getfixturevalue("admin_client")
        else:
            cfg = request.getfixturevalue("cfg")
            client = ApiClient(cfg["base_url"])
        _run_api_case(client, case)


@allure.feature("Admin 管理端")
@allure.story("学员管理")
class TestAdminMemberManagement:
    """学员管理相关接口测试"""

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "学员管理"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "学员管理"]),
    )
    def test_member(self, admin_client, case):
        _run_api_case(admin_client, case)


@allure.feature("Admin 管理端")
@allure.story("讲师管理")
class TestAdminTeacherManagement:
    """讲师管理相关接口测试"""

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "讲师管理"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "讲师管理"]),
    )
    def test_teacher(self, admin_client, case):
        _run_api_case(admin_client, case)


@allure.feature("Admin 管理端")
@allure.story("课程管理")
class TestAdminCourseManagement:
    """课程管理相关接口测试"""

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "课程管理"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "课程管理"]),
    )
    def test_course(self, admin_client, case):
        _run_api_case(admin_client, case)


@allure.feature("Admin 管理端")
@allure.story("数据统计")
class TestAdminStatistics:
    """数据统计相关接口测试"""

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "数据统计"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "数据统计"]),
    )
    def test_statistics(self, admin_client, case):
        _run_api_case(admin_client, case)
