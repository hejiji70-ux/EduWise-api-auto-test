"""
test_app.py — App 学员端接口自动化测试
覆盖：学员登录/注册 / 公开内容 / 个人中心 / 课程互动（链式查询）
"""

import io
import time
import pytest
import allure
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import ApiClient
from utils.logger import get_logger
from utils.data_loader import load_cases, get_case_ids

logger = get_logger(__name__)


# ── 加载测试数据 ──────────────────────────────────────
login_cases = load_cases("app_login.yaml")
api_cases = load_cases("app_api.yaml")


@allure.feature("App 学员端")
@allure.story("学员登录")
class TestAppLogin:
    """学员登录接口测试"""

    @pytest.mark.parametrize("case", login_cases, ids=get_case_ids(login_cases))
    def test_login(self, cfg, case):
        client = ApiClient(cfg["base_url"])
        resp = client.post(cfg["app"]["login_url"], json=case["body"])

        if case.get("assert_fail"):
            body = ApiClient.assert_fail(resp, msg=case["title"])
            assert body["status"] != 200
            logger.info(f"[{case['title']}] status={body['status']}, message={body.get('message')}")
        else:
            data = ApiClient.assert_ok(resp, case["title"])
            expected = case.get("expected", {})
            if expected.get("has_token"):
                assert data["token"], "登录成功应返回 token"
            if expected.get("mobile_equals"):
                assert data["mobile"] == expected["mobile_equals"]
            logger.info(f"[{case['title']}] id={data.get('id')}, nickname={data.get('nickname')}")


# ── App 端通用执行器（含链式查询逻辑）─────────────────────

def _run_api_case(client: ApiClient, case: dict):
    """
    App 端通用 API 执行器
    支持链式查询：上一个接口的返回值作为下一个接口的输入参数
    """
    method = case.get("method", "GET").upper()
    url = case["url"]

    if method == "POST":
        resp = client.post(url, json=case.get("body"))
    else:
        resp = client.get(url)

    if case.get("assert_fail"):
        body = resp.json()
        assert body.get("status") != 200, f"[{case['title']}] 未授权不应成功"
        logger.info(f"[{case['title']}] status={body.get('status')}")
        return

    data = ApiClient.assert_ok(resp, case["title"])
    _assert_expected(data, case.get("expected", {}), case["title"])

    # 链式查询 A：提取课程 ID → 查课程详情
    if case.get("extract_id_for_detail") and isinstance(data, dict) and data.get("total", 0) > 0:
        item_id = data["list"][0]["id"]
        detail_url = case.get("detail_url_template", "").replace("{id}", str(item_id))
        detail_resp = client.get(detail_url)
        detail_data = ApiClient.assert_ok(detail_resp, f"{case['title']} -> 详情")
        assert detail_data["id"] == item_id
        logger.info(f"[{case['title']} -> 详情] id={item_id}")

    # 链式查询 B：提取课程 ID → 查是否已购买
    if case.get("extract_id_for_isbuy") and isinstance(data, dict) and data.get("total", 0) > 0:
        course_id = data["list"][0]["id"]
        buy_url = case.get("isbuy_url_template", "").replace("{course_id}", str(course_id))
        buy_resp = client.get(buy_url)
        ApiClient.assert_ok(buy_resp, f"{case['title']} -> 是否购买")
        logger.info(f"[{case['title']} -> 是否购买] course_id={course_id}")

    # 链式查询 C：提取课程 ID → 查章节 → 再查视频（两级链式）
    if case.get("extract_id_for_chapter") and isinstance(data, dict) and data.get("total", 0) > 0:
        course_id = data["list"][0]["id"]
        chapter_url = case.get("chapter_url_template", "").replace("{course_id}", str(course_id))
        chapter_resp = client.get(chapter_url)
        chapters = ApiClient.assert_ok(chapter_resp, f"{case['title']} -> 章节")
        logger.info(f"[{case['title']} -> 章节] course_id={course_id}, 章节数={len(chapters) if isinstance(chapters, list) else chapters}")

        if isinstance(chapters, list) and len(chapters) > 0:
            video_url = case.get("video_url_template", "").replace("{chapter_id}", str(chapters[0]["id"]))
            video_resp = client.get(video_url)
            videos = ApiClient.assert_ok(video_resp, f"{case['title']} -> 视频")
            logger.info(f"[{case['title']} -> 视频] 视频数={len(videos) if isinstance(videos, list) else videos}")

    # 链式查询 D：提取课程 ID → POST 查询评论
    if case.get("extract_id_for_comment") and isinstance(data, dict) and data.get("total", 0) > 0:
        course_id = data["list"][0]["id"]
        comment_body = case.get("comment_body", {"current": 1, "pageSize": 10})
        comment_resp = client.post(
            case.get("comment_url_template", ""),
            json={**comment_body, "courseId": course_id}
        )
        comment_data = ApiClient.assert_ok(comment_resp, f"{case['title']} -> 评论")
        total = comment_data.get("total", 0) if isinstance(comment_data, dict) else comment_data
        logger.info(f"[{case['title']} -> 评论] course_id={course_id}, total={total}")


def _assert_expected(data, expected, title):
    """通用断言处理器"""
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


@allure.feature("App 学员端")
@allure.story("公开内容")
class TestAppPublicContent:
    """公开内容接口测试（不需要登录）"""

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "公开内容"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "公开内容"]),
    )
    def test_public_content(self, base_url, case):
        client = ApiClient(base_url)
        _run_api_case(client, case)


@allure.feature("App 学员端")
@allure.story("个人中心")
class TestAppMemberInfo:
    """学员个人信息测试（部分 case 不需要 token）"""

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "个人中心"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "个人中心"]),
    )
    def test_member_info(self, request, case):
        if case.get("need_token", True):
            client = request.getfixturevalue("app_client")
        else:
            base_url = request.getfixturevalue("base_url")
            client = ApiClient(base_url)
        _run_api_case(client, case)


@allure.feature("App 学员端")
@allure.story("课程互动")
class TestAppCourseInteraction:
    """课程互动相关测试（购买/章节/视频/评论）"""

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "课程互动"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "课程互动"]),
    )
    def test_interaction(self, app_client, case):
        _run_api_case(app_client, case)
