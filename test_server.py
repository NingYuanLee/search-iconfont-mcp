# -*- coding: utf-8 -*-
"""
Iconfont MCP Server 测试用例
使用 pytest + pytest-asyncio
"""

import os
import json
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# 8.1 单元测试 — login_manager 模块
# ---------------------------------------------------------------------------

class TestLoginManagerUnit:
    """login_manager 模块的单元测试: Cookie 存储/清除/检查。"""

    def setup_method(self):
        """每个测试前重置模块状态。"""
        import login_manager
        login_manager.clear_cookie()

    def test_cookie_stored_in_memory(self):
        """UT-LM-01: 存储 Cookie 后 get_cookie 返回正确值。"""
        import login_manager
        login_manager.set_cookie("test_cookie_abc123")
        assert login_manager.get_cookie() == "test_cookie_abc123"

    def test_cookie_cleared_on_expire(self):
        """UT-LM-02: clear_cookie 后 get_cookie 返回 None。"""
        import login_manager
        login_manager.set_cookie("test_cookie_abc123")
        login_manager.clear_cookie()
        assert login_manager.get_cookie() is None

    def test_is_logged_in_true(self):
        """UT-LM-03: 已存储 Cookie 时 is_logged_in 返回 True。"""
        import login_manager
        login_manager.set_cookie("test_cookie_abc123")
        assert login_manager.is_logged_in() is True

    def test_is_logged_in_false(self):
        """UT-LM-04: 未存储 Cookie 时 is_logged_in 返回 False。"""
        import login_manager
        assert login_manager.is_logged_in() is False

    def test_get_login_info_returns_structured_data(self):
        """UT-LM-03+: get_login_info 返回完整结构。"""
        import login_manager
        login_manager.set_cookie("test_cookie", username="13800138000")
        info = login_manager.get_login_info()
        assert info["logged_in"] is True
        assert info["username"] == "13800138000"
        assert info["login_time"] is not None

    def test_extract_cookie_from_page_found(self):
        """UT-LM-06: 从 cookies 列表中正确提取 EGG_SESS_ICONFONT。"""
        import login_manager
        cookies = [
            {"name": "cna", "value": "abc123"},
            {"name": "EGG_SESS_ICONFONT", "value": "session_cookie_value"},
            {"name": "trace", "value": "xyz"},
        ]
        result = login_manager.extract_cookie_from_page(cookies)
        assert result == "session_cookie_value"

    def test_extract_cookie_from_page_not_found(self):
        """UT-LM-06b: 无 EGG_SESS_ICONFONT 时返回 None。"""
        import login_manager
        cookies = [
            {"name": "cna", "value": "abc123"},
            {"name": "trace", "value": "xyz"},
        ]
        result = login_manager.extract_cookie_from_page(cookies)
        assert result is None


# ---------------------------------------------------------------------------
# 8.2 单元测试 — iconfont_api 模块 (Mock httpx)
# ---------------------------------------------------------------------------

class TestIconfontApiUnit:
    """iconfont_api 模块的单元测试。"""

    def setup_method(self):
        """每个测试前设置登录状态并清除旧 Cookie。"""
        import login_manager
        login_manager.set_cookie("mock_cookie_for_test", username="testuser")

    def teardown_method(self):
        import login_manager
        login_manager.clear_cookie()

    @pytest.mark.asyncio
    async def test_search_success(self):
        """UT-API-01: 搜索成功返回结构化数据。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 200,
            "data": {
                "total": 2,
                "icons": [
                    {
                        "id": 145442, "name": "用户",
                        "url": "https://img.ic.com/user.png",
                        "author_name": "设计师A",
                        "width": 1024, "height": 1024,
                    },
                    {
                        "id": 145443, "name": "用户组",
                        "url": "https://img.ic.com/group.png",
                        "author_name": "设计师B",
                        "width": 1024, "height": 1024,
                    },
                ],
            },
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            from iconfont_api import search_icons
            result = await search_icons("用户")

        assert result["total"] == 2
        assert result["page"] == 1
        assert len(result["icons"]) == 2
        assert result["icons"][0]["name"] == "用户"
        assert result["icons"][1]["id"] == "145443"

    @pytest.mark.asyncio
    async def test_search_empty_result(self):
        """UT-API-02: 搜索无结果返回空列表。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 200,
            "data": {"total": 0, "icons": []},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            from iconfont_api import search_icons
            result = await search_icons("abcdefgxyz")

        assert result["total"] == 0
        assert result["icons"] == []

    @pytest.mark.asyncio
    async def test_search_with_icon_type(self):
        """UT-API-03: 搜索带 icon_type 参数。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 200,
            "data": {"total": 1, "icons": [{"id": 1, "name": "arrow"}]},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            from iconfont_api import search_icons
            await search_icons("arrow", icon_type="line")

        # 验证请求参数中包含 icon_type
        call_kwargs = mock_post.call_args.kwargs
        assert "icon_type" in call_kwargs["data"]
        assert call_kwargs["data"]["icon_type"] == "line"

    @pytest.mark.asyncio
    async def test_search_pagination(self):
        """UT-API-04: 分页参数正确传递。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 200,
            "data": {"total": 100, "icons": []},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            from iconfont_api import search_icons
            await search_icons("user", page=2, page_size=10)

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["data"]["page"] == "2"
        assert call_kwargs["data"]["pageSize"] == "10"

    @pytest.mark.asyncio
    async def test_search_not_logged_in(self):
        """UT-API-05: 未登录时搜索抛出 RuntimeError。"""
        import login_manager
        login_manager.clear_cookie()

        from iconfont_api import search_icons
        with pytest.raises(RuntimeError, match="未登录"):
            await search_icons("home")

    @pytest.mark.asyncio
    async def test_download_success(self):
        """UT-API-06: 下载图标成功返回文件信息 (通过搜索 API)。"""
        mock_search_response = MagicMock()
        mock_search_response.json.return_value = {
            "code": 200,
            "data": {
                "icons": [{
                    "id": 145442,
                    "name": "用户",
                    "show_svg": '<svg viewBox="0 0 1024 1024"><path d="M512..."/></svg>',
                    "width": 1024,
                    "height": 1024,
                }],
            },
        }
        mock_search_response.raise_for_status = MagicMock()

        tmpdir = tempfile.mkdtemp()

        try:
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_search_response
                from iconfont_api import download_icon
                result = await download_icon("145442", output_dir=tmpdir)

            assert result["icon_id"] == "145442"
            assert result["name"] == "用户"
            assert result["svg_size"] > 0
            assert os.path.exists(result["file_path"])
            with open(result["file_path"], "r", encoding="utf-8") as f:
                content = f.read()
                assert "<svg" in content
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_download_invalid_icon_id(self):
        """UT-API-07: 无效图标ID下载抛出异常 (搜不到匹配ID)。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 200,
            "data": {"icons": [{"id": 1, "name": "other", "show_svg": "<svg></svg>"}]},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            from iconfont_api import download_icon
            with pytest.raises(RuntimeError):
                await download_icon("99999999")

    @pytest.mark.asyncio
    async def test_download_output_dir_created(self):
        """UT-API-08: 输出目录自动创建。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 200,
            "data": {
                "icons": [{
                    "id": 1,
                    "name": "test_icon",
                    "show_svg": "<svg></svg>",
                }],
            },
        }
        mock_response.raise_for_status = MagicMock()

        tmpdir = tempfile.mkdtemp()
        nested_dir = os.path.join(tmpdir, "nested", "icons")

        try:
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                from iconfont_api import download_icon
                await download_icon("1", output_dir=nested_dir)

            assert os.path.exists(nested_dir)
            files = os.listdir(nested_dir)
            assert len(files) == 1
            assert files[0].endswith(".svg")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_search_includes_show_svg(self):
        """UT-API-09: 搜索返回结果包含 show_svg 字段。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 200,
            "data": {
                "total": 1,
                "icons": [{
                    "id": 145442, "name": "用户",
                    "show_svg": "<svg>...</svg>",
                    "width": 1024, "height": 1024,
                }],
            },
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            from iconfont_api import search_icons
            result = await search_icons("用户")

        assert result["total"] == 1
        assert result["icons"][0]["show_svg"] == "<svg>...</svg>"
        assert result["icons"][0]["width"] == 1024


# ---------------------------------------------------------------------------
# 8.3 集成测试 — MCP 工具调用
# ---------------------------------------------------------------------------

class TestMCPToolsIntegration:
    """MCP 工具的集成测试 (使用 mock)。"""

    def setup_method(self):
        import login_manager
        login_manager.clear_cookie()

    def teardown_method(self):
        import login_manager
        login_manager.clear_cookie()

    @pytest.mark.asyncio
    async def test_tool_check_status_logged_out(self):
        """IT-MCP-01: 未登录时 check_status 返回 false。"""
        from server import iconfont_check_status
        result_str = await iconfont_check_status()
        result = json.loads(result_str)
        assert result["logged_in"] is False

    @pytest.mark.asyncio
    async def test_tool_check_status_logged_in(self):
        """IT-MCP-02: 已登录时 check_status 返回 true。"""
        import login_manager
        login_manager.set_cookie("test_cookie", username="testuser")

        from server import iconfont_check_status
        result_str = await iconfont_check_status()
        result = json.loads(result_str)
        assert result["logged_in"] is True
        assert result["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_tool_search_requires_login(self):
        """IT-MCP-03: 未登录搜索返回错误。"""
        from server import iconfont_search_icons
        result_str = await iconfont_search_icons("home")
        result = json.loads(result_str)
        assert "error" in result
        assert "未登录" in result["error"]

    @pytest.mark.asyncio
    async def test_tool_download_requires_login(self):
        """IT-MCP-04: 未登录下载返回错误。"""
        from server import iconfont_download_icon
        result_str = await iconfont_download_icon("123")
        result = json.loads(result_str)
        assert "error" in result
        assert "未登录" in result["error"]

    @pytest.mark.asyncio
    async def test_tool_search_returns_structured_data(self):
        """IT-MCP-05: 搜索返回含 total/icons 的结构化数据。"""
        import login_manager
        login_manager.set_cookie("test_cookie")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 200,
            "data": {
                "total": 1,
                "icons": [{
                    "id": 1, "name": "首页",
                    "url": "https://img.ic.com/home.png",
                    "author_name": "设计师A",
                    "width": 1024, "height": 1024,
                }],
            },
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            from server import iconfont_search_icons
            result_str = await iconfont_search_icons("首页")

        result = json.loads(result_str)
        assert "total" in result
        assert result["total"] == 1
        assert len(result["icons"]) == 1
        assert result["icons"][0]["name"] == "首页"

    @pytest.mark.asyncio
    async def test_tool_download_returns_file_info(self):
        """IT-MCP-06: 下载返回含 file_path/svg_size 的文件信息。"""
        import login_manager
        login_manager.set_cookie("test_cookie")

        mock_search = MagicMock()
        mock_search.json.return_value = {
            "code": 200,
            "data": {
                "icons": [{
                    "id": 1,
                    "name": "测试图标",
                    "show_svg": "<svg><path/></svg>",
                }],
            },
        }
        mock_search.raise_for_status = MagicMock()

        tmpdir = tempfile.mkdtemp()

        try:
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_search
                from server import iconfont_download_icon
                result_str = await iconfont_download_icon("1", output_dir=tmpdir)

            result = json.loads(result_str)
            assert "icon_id" in result
            assert result["icon_id"] == "1"
            assert "file_path" in result
            assert "svg_size" in result
            assert result["svg_size"] > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_tool_logout(self):
        """IT-MCP-07+: 退出登录后状态为 false。"""
        import login_manager
        login_manager.set_cookie("test_cookie")

        from server import iconfont_logout
        result_str = await iconfont_logout()
        result = json.loads(result_str)
        assert result["success"] is True

        # 确认已退出
        from server import iconfont_check_status
        status_str = await iconfont_check_status()
        status = json.loads(status_str)
        assert status["logged_in"] is False

    @pytest.mark.asyncio
    async def test_tool_login_with_direct_cookie(self):
        """登录时如果设置了 ICONFONT_COOKIE 环境变量，直接注入。"""
        with patch.dict(os.environ, {"ICONFONT_COOKIE": "direct_cookie_test"}, clear=True):
            from server import iconfont_login
            result_str = await iconfont_login()
            result = json.loads(result_str)
            assert result["success"] is True
            assert result["method"] == "direct_cookie"

    @pytest.mark.asyncio
    async def test_tool_login_missing_credentials(self):
        """无环境变量配置时返回错误提示。"""
        with patch.dict(os.environ, {}, clear=True):
            from server import iconfont_login
            result_str = await iconfont_login()
            result = json.loads(result_str)
            assert result["success"] is False
            assert "未配置登录凭据" in result["message"]

    @pytest.mark.asyncio
    async def test_tool_login_already_logged_in(self):
        """已登录时返回已登录状态。"""
        import login_manager
        login_manager.set_cookie("existing", username="testuser")

        from server import iconfont_login
        result_str = await iconfont_login()
        result = json.loads(result_str)
        assert result["success"] is True
        assert result["already_logged_in"] is True


# ---------------------------------------------------------------------------
# 运行说明
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
