"""
test_teacher.py — Teacher 讲师端接口自动化测试
覆盖：讲师登录 / 个人信息 / 课程管理（含创建删除生命周期） / 章节管理 / 数据统计
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
login_cases = load_cases("teacher_login.yaml")
api_cases = load_cases("teacher_api.yaml")


# ── 登录模块 ──────────────────────────────────────────

@allure.feature("Teacher 讲师端")
@allure.story("讲师登录")
class TestTeacherLogin:
    """讲师登录接口测试（mobile 手机号登录）"""

    @pytest.mark.parametrize("case", login_cases, ids=get_case_ids(login_cases))
    def test_login(self, cfg, case):
        client = ApiClient(cfg["base_url"])
        resp = client.post(
            cfg["teacher"]["login_url"],
            json=case["body"],
        )

        if case.get("assert_fail"):
            body = ApiClient.assert_fail(resp, msg=case["title"])
            assert body["status"] != 200
            logger.info("[%s] status=%s, message=%s" % (case["title"], body["status"], body.get("message")))
        else:
            data = ApiClient.assert_ok(resp, case["title"])
            expected = case.get("expected", {})
            if expected.get("has_token"):
                assert data["token"], "登录成功应返回 token"
            if expected.get("mobile_equals"):
                assert data["mobile"] == expected["mobile_equals"]
            logger.info("[%s] name=%s" % (case["title"], data.get("name")))


# ── 通用执行器 ────────────────────────────────────────

def _run_api_case(client: ApiClient, case: dict):
    """
    Teacher 端通用 API 执行器
    支持 extract_id_for_chapter 链式查询：课程列表 → 章节列表
    """
    method = case.get("method", "GET").upper()
    url = case["url"]

    if method == "POST":
        resp = client.post(url, json=case.get("body"))
    else:
        resp = client.get(url)

    if case.get("assert_fail"):
        body = resp.json()
        assert body.get("status") != 200, "[%s] 不应成功" % case["title"]
        logger.info("[%s] status=%s" % (case["title"], body.get("status")))
        return

    data = ApiClient.assert_ok(resp, case["title"])
    _assert_expected(data, case.get("expected", {}), case["title"])

    # 提取课程ID → 查章节列表
    if (case.get("extract_id_for_chapter")
            and isinstance(data, dict) and data.get("total", 0) > 0):
        course_id = data["list"][0]["id"]
        template = case.get("chapter_url_template", "")
        chapter_url = template.replace("{course_id}", str(course_id))
        chapter_resp = client.get(chapter_url)
        chapter_data = ApiClient.assert_ok(chapter_resp, "%s -> 章节" % case["title"])
        cnt = len(chapter_data) if isinstance(chapter_data, list) else chapter_data
        logger.info("[%s -> 章节] course_id=%s, 章节数=%s" % (case["title"], course_id, cnt))


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
    if case.get("expected", {}).get("not_empty"):
        assert len(data) > 0


# ── 个人信息 ──────────────────────────────────────────

@allure.feature("Teacher 讲师端")
@allure.story("个人信息")
class TestTeacherProfile:

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "个人信息"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "个人信息"]),
    )
    def test_profile(self, teacher_client, case):
        _run_api_case(teacher_client, case)


# ── 课程管理（含 CRUD 生命周期测试）────────────────────

@allure.feature("Teacher 讲师端")
@allure.story("课程管理")
class TestTeacherCourseManagement:
    """课程管理：YAML 驱动查询 + 完整 CRUD 生命周期"""

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "课程管理" and not c.get("is_lifecycle_test")],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "课程管理" and not c.get("is_lifecycle_test")]),
    )
    def test_course(self, teacher_client, case):
        _run_api_case(teacher_client, case)

    @allure.title("创建课程草稿并验证后删除（完整生命周期）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_and_delete_course(self, teacher_client):
        """
        创建课程 → 验证详情 → 删除（完整生命周期测试）
        multipart/form-data 上传封面图，动态获取学科 ID 和讲师 ID
        """

        # 从 YAML 读取创建参数
        lifecycle_config = next(
            (c for c in api_cases if c.get("is_lifecycle_test")), {}
        )
        create_params = lifecycle_config.get("create_data", {})

        # 前置准备：获取学科分类和讲师 ID
        with allure.step("前置准备: 获取学科分类和讲师信息"):
            subject_resp = teacher_client.get("/api/teacher/subject/get")
            subjects = ApiClient.assert_ok(subject_resp, "获取分类")
            if not subjects:
                pytest.skip("暂无学科分类，跳过")

            subject_id = None
            for parent in subjects:
                children = parent.get("children") or []
                if children:
                    subject_id = children[0]["id"]
                    break

            if subject_id is None:
                pytest.skip("暂无二级分类，跳过")

            info_resp = teacher_client.get("/api/teacher/user/info")
            info = ApiClient.assert_ok(info_resp, "获取讲师信息")
            teacher_id = info["id"]

        # 构造测试数据
        ts = int(time.time())
        course_title = "AutoTest_%d" % ts

        # 最小有效 1x1 PNG 作为课程封面
        png_1x1 = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR'
            b'\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f'
            b'\x00\x00\x01\x01\x00\x05\x18\xd8N'
            b'\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        cover_file = ("cover.png", io.BytesIO(png_1x1), "image/png")

        # Step 1: 创建课程
        with allure.step("Step 1: 创建课程"):
            create_resp = teacher_client.post(
                "/api/teacher/course/create",
                data={
                    "title": course_title,
                    "teacherId": teacher_id,
                    "subjectId": subject_id,
                    **create_params,
                },
                files={"file": cover_file},
            )
            result = ApiClient.assert_ok(create_resp, "创建课程")
            course_id = result.get("id") if isinstance(result, dict) else result
            assert course_id, "创建课程应返回课程ID"

        # Step 2: 验证详情
        with allure.step("Step 2: 查询课程详情验证"):
            detail_resp = teacher_client.get("/api/teacher/course/info/%s" % course_id)
            detail = ApiClient.assert_ok(detail_resp, "课程详情")
            assert detail["id"] == course_id
            assert course_title in detail["title"]
            assert detail["status"] == "DRAFT"

        # Step 3: 清理
        with allure.step("Step 3: 删除课程清理测试数据"):
            delete_resp = teacher_client.post("/api/teacher/course/delete/%s" % course_id)
            ApiClient.assert_ok(delete_resp, "删除课程")


# ── 章节管理 ──────────────────────────────────────────

@allure.feature("Teacher 讲师端")
@allure.story("章节管理")
class TestTeacherChapterManagement:

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "章节管理"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "章节管理"]),
    )
    def test_chapter(self, teacher_client, case):
        _run_api_case(teacher_client, case)


# ── 数据统计 ──────────────────────────────────────────

@allure.feature("Teacher 讲师端")
@allure.story("数据统计")
class TestTeacherStatistics:

    @pytest.mark.parametrize(
        "case",
        [c for c in api_cases if c.get("feature") == "数据统计"],
        ids=get_case_ids([c for c in api_cases if c.get("feature") == "数据统计"]),
    )
    def test_stats(self, teacher_client, case):
        _run_api_case(teacher_client, case)
