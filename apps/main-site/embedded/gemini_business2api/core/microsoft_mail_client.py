import imaplib
import time
from datetime import datetime, timedelta
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from typing import Optional

import requests

from embedded.gemini_business2api.core.mail_utils import extract_verification_code

# 常量定义
CANCELLATION_CHECK_INTERVAL_SECONDS = 5  # 取消检查间隔（秒）


class MicrosoftMailClient:
    def __init__(
        self,
        client_id: str,
        refresh_token: str,
        tenant: str = "consumers",
        proxy: str = "",
        log_callback=None,
    ) -> None:
        self.client_id = client_id
        self.refresh_token = refresh_token
        self.tenant = tenant or "consumers"
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.log_callback = log_callback
        self.email: Optional[str] = None

    def set_credentials(self, email: str, password: Optional[str] = None) -> None:
        self.email = email

    def _get_access_token(self) -> Optional[str]:
        url = f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        try:
            self._log("info", f"🔑 正在获取 Microsoft OAuth 令牌...")
            res = requests.post(url, data=data, proxies=self.proxies, timeout=15)
            if res.status_code != 200:
                self._log("error", f"❌ Microsoft 令牌获取失败: HTTP {res.status_code}")
                return None
            payload = res.json() if res.content else {}
            token = payload.get("access_token")
            if not token:
                self._log("error", "❌ Microsoft 令牌响应中缺少 access_token")
                return None
            self._log("info", "✅ Microsoft OAuth 令牌获取成功")
            return token
        except Exception as exc:
            self._log("error", f"❌ Microsoft 令牌获取异常: {exc}")
            return None

    def fetch_verification_code(self, since_time: Optional[datetime] = None) -> Optional[str]:
        if not self.email:
            return None

        self._log("info", "📬 正在获取验证码...")
        token = self._get_access_token()
        if not token:
            self._log("error", "❌ 无法获取访问令牌，跳过邮箱检查")
            return None

        auth_string = f"user={self.email}\x01auth=Bearer {token}\x01\x01".encode()
        client = imaplib.IMAP4_SSL("outlook.office365.com", 993)
        try:
            self._log("info", f"🔐 正在使用 IMAP XOAUTH2 认证: {self.email}")
            client.authenticate("XOAUTH2", lambda _: auth_string)
            self._log("info", "✅ IMAP 认证成功，已连接到邮箱")
        except Exception as exc:
            self._log("error", f"❌ IMAP 认证失败: {exc}")
            try:
                client.logout()
            except Exception:
                pass
            return None

        search_since = since_time or (datetime.now() - timedelta(minutes=5))
        self._log("info", f"🔍 搜索 {search_since.strftime('%Y-%m-%d %H:%M:%S')} 之后的邮件")

        try:
            for mailbox in ("INBOX", "Junk"):
                try:
                    status, _ = client.select(mailbox, readonly=True)
                    if status != "OK":
                        self._log("warning", f"⚠️ 无法选择邮箱: {mailbox}")
                        continue
                    self._log("info", f"📂 正在检查邮箱: {mailbox}")
                except Exception as e:
                    self._log("warning", f"⚠️ 选择邮箱 {mailbox} 时出错: {e}")
                    continue

                # 搜索所有邮件
                status, data = client.search(None, "ALL")
                if status != "OK" or not data or not data[0]:
                    self._log("info", f"📭 邮箱 {mailbox} 中没有邮件")
                    continue

                ids = data[0].split()[-5:]  # 只检查最近 5 封
                self._log("info", f"📨 在 {mailbox} 中发现 {len(ids)} 封邮件")

                checked_count = 0
                for msg_id in reversed(ids):
                    status, msg_data = client.fetch(msg_id, "(RFC822)")
                    if status != "OK" or not msg_data:
                        continue
                    raw_bytes = None
                    for item in msg_data:
                        if isinstance(item, tuple) and len(item) > 1:
                            raw_bytes = item[1]
                            break
                    if not raw_bytes:
                        continue

                    msg = message_from_bytes(raw_bytes)
                    msg_date = self._parse_message_date(msg.get("Date"))

                    # 按时间过滤（静默跳过旧邮件）
                    if msg_date and msg_date < search_since:
                        continue

                    checked_count += 1
                    content = self._message_to_text(msg)
                    import re
                    match = re.search(r'[A-Z0-9]{6}', content)
                    if match:
                        code = match.group(0)
                        self._log("info", f"🎉 在 {mailbox} 中找到验证码: {code}")
                        return code

                if checked_count > 0:
                    self._log("info", f"🔍 已检查 {mailbox} 中 {checked_count} 封近期邮件，未找到验证码")

            self._log("warning", "⚠️ 所有邮箱中均未找到验证码")
        finally:
            try:
                client.logout()
            except Exception:
                pass

        return None

    def poll_for_code(
        self,
        timeout: int = 120,
        interval: int = 4,
        since_time: Optional[datetime] = None,
    ) -> Optional[str]:
        if not self.email:
            return None

        max_retries = max(1, timeout // interval)
        self._log("info", f"⏱️ 开始轮询验证码 (超时 {timeout}秒, 间隔 {interval}秒, 最多 {max_retries} 次)")

        for i in range(1, max_retries + 1):
            # 检查任务是否被取消（通过 log 触发 TaskCancelledError）
            self._log("info", f"🔄 第 {i}/{max_retries} 次轮询...")
            code = self.fetch_verification_code(since_time=since_time)
            if code:
                self._log("info", f"🎉 验证码获取成功: {code}")
                return code
            if i < max_retries:
                # 分段 sleep，每5秒检查一次取消状态
                for _ in range(interval // CANCELLATION_CHECK_INTERVAL_SECONDS):
                    time.sleep(CANCELLATION_CHECK_INTERVAL_SECONDS)
                    # 通过 log 检查取消状态（使用有意义的日志）
                    self._log("debug", f"等待验证码中... ({(_ + 1) * CANCELLATION_CHECK_INTERVAL_SECONDS}/{interval}秒)")
                # 处理剩余的秒数
                remaining = interval % CANCELLATION_CHECK_INTERVAL_SECONDS
                if remaining > 0:
                    time.sleep(remaining)

        self._log("error", "❌ 验证码获取超时")
        return None

    @staticmethod
    def _message_to_text(msg) -> str:
        if msg.is_multipart():
            parts = []
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type not in ("text/plain", "text/html"):
                    continue
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                parts.append(payload.decode(charset, errors="ignore"))
            return "".join(parts)
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")
        return str(payload) if payload else ""

    @staticmethod
    def _parse_message_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = parsedate_to_datetime(value)
            if parsed is None:
                return None
            if parsed.tzinfo:
                return parsed.astimezone(tz=None).replace(tzinfo=None)
            return parsed
        except Exception:
            return None

    def _log(self, level: str, message: str) -> None:
        if self.log_callback:
            try:
                self.log_callback(level, message)
            except TaskCancelledError:
                raise
            except Exception:
                pass
