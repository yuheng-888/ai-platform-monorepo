import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Tabs,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  CheckCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons'

import { apiFetch } from '@/lib/utils'

const { Text } = Typography

const MAIL_PROVIDER_OPTIONS = [
  { label: 'DuckMail', value: 'duckmail' },
  { label: 'MoeMail', value: 'moemail' },
  { label: 'Freemail', value: 'freemail' },
  { label: 'GPTMail', value: 'gptmail' },
  { label: 'Cloudflare Mail', value: 'cfmail' },
]

type GeminiStatus = {
  name: string
  mount_path: string
  ui_path: string
  ui_available: boolean
  health_path: string
  api_base_path: string
  running: boolean
  admin_key_configured: boolean
  session_secret_configured: boolean
  version: string
  commit: string
}

type GeminiAdminStats = {
  total_accounts: number
  active_accounts: number
  failed_accounts: number
  rate_limited_accounts: number
  idle_accounts: number
  success_count: number
  failed_count: number
}

type GeminiAccount = {
  id: string
  status: string
  remaining_display?: string
  is_available?: boolean
  disabled?: boolean
  disabled_reason?: string | null
  cooldown_seconds?: number
  cooldown_reason?: string | null
  conversation_count?: number
  session_usage_count?: number
}

type GeminiAccountsResponse = {
  total: number
  accounts: GeminiAccount[]
}

type GeminiTask = {
  id?: string
  status?: string
  progress?: number
  success_count?: number
  fail_count?: number
  error?: string | null
  created_at?: number
  finished_at?: number | null
}

type GeminiSettingsPayload = Record<string, any>

type GeminiLogEntry = {
  time: string
  level: string
  message: string
}

type GeminiLogPayload = {
  total: number
  logs: GeminiLogEntry[]
  stats?: {
    memory?: {
      total?: number
      by_level?: Record<string, number>
    }
    chat_count?: number
  }
}

type GeminiHistoryEntry = {
  id: string
  type: string
  status: string
  progress: number
  total: number
  success_count: number
  fail_count: number
  created_at?: number
  finished_at?: number | null
  is_live?: boolean
}

type GeminiHistoryPayload = {
  total: number
  history: GeminiHistoryEntry[]
}

type RegisterFormValues = {
  count: number
  concurrency: number
  domain?: string
  mail_provider?: string
}

type GeminiSharedSettingsValues = {
  register_max_concurrency?: number
  mail_provider?: string
  moemail_api_url?: string
  moemail_api_key?: string
  moemail_domain?: string
  freemail_api_url?: string
  freemail_admin_token?: string
  freemail_domain?: string
  duckmail_provider_url?: string
  duckmail_bearer?: string
}

type GeminiNativeSettingsValues = {
  api_key?: string
  base_url?: string
  proxy_for_auth?: string
  proxy_for_chat?: string
  browser_mode?: string
  register_domain?: string
  register_default_count?: number
  register_default_concurrency?: number
  refresh_window_hours?: number
  auto_refresh_accounts_seconds?: number
  refresh_cooldown_hours?: number
  logo_url?: string
  chat_url?: string
}

const GEMINI_SHARED_MAIL_PROVIDERS = new Set(['duckmail', 'moemail', 'freemail'])

async function geminiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {})
  if (!headers.has('Content-Type') && init?.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers,
    ...init,
  })
  const contentType = res.headers.get('content-type') || ''
  if (!res.ok) {
    const errorBody = contentType.includes('application/json')
      ? JSON.stringify(await res.json())
      : await res.text()
    throw new Error(errorBody)
  }
  if (contentType.includes('application/json')) {
    return res.json()
  }
  throw new Error('Gemini 接口未返回 JSON')
}

function formatTaskStatus(task?: GeminiTask | null) {
  if (!task || !task.status || task.status === 'idle') {
    return <Tag>空闲</Tag>
  }
  if (task.status === 'running') return <Tag color="processing">运行中</Tag>
  if (task.status === 'pending') return <Tag color="warning">等待中</Tag>
  if (task.status === 'success') return <Tag color="success">成功</Tag>
  if (task.status === 'cancelled') return <Tag color="default">已取消</Tag>
  if (task.status === 'failed') return <Tag color="error">失败</Tag>
  return <Tag>{task.status}</Tag>
}

function renderCooldown(account: GeminiAccount) {
  if (!account.cooldown_seconds || account.cooldown_seconds <= 0) {
    return <Tag color="success">正常</Tag>
  }
  const seconds = Math.max(0, Math.floor(account.cooldown_seconds))
  return (
    <Space direction="vertical" size={0}>
      <Tag color="warning">{seconds}s</Tag>
      {account.cooldown_reason ? (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {account.cooldown_reason}
        </Text>
      ) : null}
    </Space>
  )
}

export default function GeminiPage() {
  const [status, setStatus] = useState<GeminiStatus | null>(null)
  const [stats, setStats] = useState<GeminiAdminStats | null>(null)
  const [accounts, setAccounts] = useState<GeminiAccount[]>([])
  const [registerTask, setRegisterTask] = useState<GeminiTask | null>(null)
  const [loginTask, setLoginTask] = useState<GeminiTask | null>(null)
  const [activeTab, setActiveTab] = useState('accounts')
  const [settingsLoaded, setSettingsLoaded] = useState(false)
  const [logData, setLogData] = useState<GeminiLogPayload | null>(null)
  const [logsLoaded, setLogsLoaded] = useState(false)
  const [historyData, setHistoryData] = useState<GeminiHistoryPayload | null>(null)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState('')
  const [error, setError] = useState('')
  const [registerOpen, setRegisterOpen] = useState(false)
  const [registerForm] = Form.useForm<RegisterFormValues>()
  const [sharedSettingsForm] = Form.useForm<GeminiSharedSettingsValues>()
  const [nativeSettingsForm] = Form.useForm<GeminiNativeSettingsValues>()
  const sharedMailProvider = Form.useWatch('mail_provider', sharedSettingsForm)

  const hasActiveTask = useMemo(() => {
    return ['pending', 'running'].includes(registerTask?.status || '')
      || ['pending', 'running'].includes(loginTask?.status || '')
  }, [loginTask?.status, registerTask?.status])

  const load = async (silent = false) => {
    if (!silent) {
      setLoading(true)
    }
    setError('')
    try {
      const [statusData, statsData, accountsData, registerTaskData, loginTaskData] = await Promise.all([
        apiFetch('/gemini/status') as Promise<GeminiStatus>,
        geminiFetch<GeminiAdminStats>('/gemini/admin/stats'),
        geminiFetch<GeminiAccountsResponse>('/gemini/admin/accounts'),
        geminiFetch<GeminiTask>('/gemini/admin/register/current'),
        geminiFetch<GeminiTask>('/gemini/admin/login/current'),
      ])
      setStatus(statusData)
      setStats(statsData)
      setAccounts(accountsData.accounts || [])
      setRegisterTask(registerTaskData)
      setLoginTask(loginTaskData)
    } catch (e: any) {
      setError(e?.message || '加载 Gemini 状态失败')
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    if (!hasActiveTask) return
    const timer = window.setInterval(() => {
      void load(true)
    }, 5000)
    return () => window.clearInterval(timer)
  }, [hasActiveTask])

  useEffect(() => {
    if (activeTab === 'settings' && !settingsLoaded) {
      void loadSettings()
    }
    if (activeTab === 'logs' && !logsLoaded) {
      void loadLogs()
    }
    if (activeTab === 'history' && !historyLoaded) {
      void loadHistory()
    }
  }, [activeTab, historyLoaded, logsLoaded, settingsLoaded])

  const loadSettings = async () => {
    setActionLoading('load-settings')
    try {
      const [globalConfig, geminiSettings] = await Promise.all([
        apiFetch('/config') as Promise<Record<string, any>>,
        geminiFetch<GeminiSettingsPayload>('/gemini/admin/settings'),
      ])
      const basic = geminiSettings.basic || {}
      const retry = geminiSettings.retry || {}
      const publicDisplay = geminiSettings.public_display || {}

      sharedSettingsForm.setFieldsValue({
        register_max_concurrency: Number.parseInt(String(globalConfig.register_max_concurrency || basic.register_max_concurrency || 5), 10) || 5,
        mail_provider: globalConfig.mail_provider || basic.temp_mail_provider || 'duckmail',
        moemail_api_url: globalConfig.moemail_api_url || basic.moemail_base_url || '',
        moemail_api_key: globalConfig.moemail_api_key || basic.moemail_api_key || '',
        moemail_domain: globalConfig.moemail_domain || basic.moemail_domain || '',
        freemail_api_url: globalConfig.freemail_api_url || basic.freemail_base_url || '',
        freemail_admin_token: globalConfig.freemail_admin_token || basic.freemail_jwt_token || '',
        freemail_domain: globalConfig.freemail_domain || basic.freemail_domain || '',
        duckmail_provider_url: globalConfig.duckmail_provider_url || basic.duckmail_base_url || '',
        duckmail_bearer: globalConfig.duckmail_bearer || basic.duckmail_api_key || '',
      })

      nativeSettingsForm.setFieldsValue({
        api_key: basic.api_key || '',
        base_url: basic.base_url || '',
        proxy_for_auth: basic.proxy_for_auth || '',
        proxy_for_chat: basic.proxy_for_chat || '',
        browser_mode: basic.browser_mode || 'normal',
        register_domain: basic.register_domain || '',
        register_default_count: basic.register_default_count || 1,
        register_default_concurrency: basic.register_default_concurrency || basic.register_max_concurrency || 5,
        refresh_window_hours: basic.refresh_window_hours || 24,
        auto_refresh_accounts_seconds: retry.auto_refresh_accounts_seconds || 300,
        refresh_cooldown_hours: retry.refresh_cooldown_hours || 24,
        logo_url: publicDisplay.logo_url || '',
        chat_url: publicDisplay.chat_url || '',
      })
      setSettingsLoaded(true)
    } catch (e: any) {
      message.error(e?.message || '加载 Gemini 设置失败')
    } finally {
      setActionLoading('')
    }
  }

  const saveSettings = async () => {
    setActionLoading('save-settings')
    try {
      const sharedValues = await sharedSettingsForm.validateFields()
      const nativeValues = await nativeSettingsForm.validateFields()

      await apiFetch('/config', {
        method: 'PUT',
        body: JSON.stringify({
          data: {
            register_max_concurrency: String(sharedValues.register_max_concurrency || 5),
            mail_provider: String(sharedValues.mail_provider || ''),
            moemail_api_url: String(sharedValues.moemail_api_url || ''),
            moemail_api_key: String(sharedValues.moemail_api_key || ''),
            moemail_domain: String(sharedValues.moemail_domain || ''),
            freemail_api_url: String(sharedValues.freemail_api_url || ''),
            freemail_admin_token: String(sharedValues.freemail_admin_token || ''),
            freemail_domain: String(sharedValues.freemail_domain || ''),
            duckmail_provider_url: String(sharedValues.duckmail_provider_url || ''),
            duckmail_bearer: String(sharedValues.duckmail_bearer || ''),
          },
        }),
      })

      const selectedMailProvider = String(sharedValues.mail_provider || '')
      const supportsSharedMailProvider = GEMINI_SHARED_MAIL_PROVIDERS.has(selectedMailProvider)
      const basicPayload: Record<string, any> = {
        api_key: nativeValues.api_key || '',
        base_url: nativeValues.base_url || '',
        proxy_for_auth: nativeValues.proxy_for_auth || '',
        proxy_for_chat: nativeValues.proxy_for_chat || '',
        browser_mode: nativeValues.browser_mode || 'normal',
        register_domain: nativeValues.register_domain || '',
        register_default_count: nativeValues.register_default_count || 1,
        register_default_concurrency: nativeValues.register_default_concurrency || sharedValues.register_max_concurrency || 5,
        register_max_concurrency: sharedValues.register_max_concurrency || 5,
        refresh_window_hours: nativeValues.refresh_window_hours || 24,
      }

      if (supportsSharedMailProvider) {
        basicPayload.temp_mail_provider = selectedMailProvider
      }
      if (selectedMailProvider === 'moemail') {
        basicPayload.moemail_base_url = sharedValues.moemail_api_url || ''
        basicPayload.moemail_api_key = sharedValues.moemail_api_key || ''
        basicPayload.moemail_domain = sharedValues.moemail_domain || ''
      }
      if (selectedMailProvider === 'freemail') {
        basicPayload.freemail_base_url = sharedValues.freemail_api_url || ''
        basicPayload.freemail_jwt_token = sharedValues.freemail_admin_token || ''
        basicPayload.freemail_domain = sharedValues.freemail_domain || ''
      }
      if (selectedMailProvider === 'duckmail') {
        basicPayload.duckmail_base_url = sharedValues.duckmail_provider_url || ''
        basicPayload.duckmail_api_key = sharedValues.duckmail_bearer || ''
      }

      await geminiFetch('/gemini/admin/settings', {
        method: 'PUT',
        body: JSON.stringify({
          basic: basicPayload,
          retry: {
            auto_refresh_accounts_seconds: nativeValues.auto_refresh_accounts_seconds || 300,
            refresh_cooldown_hours: nativeValues.refresh_cooldown_hours || 24,
          },
          public_display: {
            logo_url: nativeValues.logo_url || '',
            chat_url: nativeValues.chat_url || '',
          },
        }),
      })
      if (!supportsSharedMailProvider && selectedMailProvider) {
        message.warning(`全局邮箱渠道 ${selectedMailProvider} 目前不会自动映射到 Gemini，Gemini 将继续沿用自身邮箱渠道。`)
      } else {
        message.success('Gemini 设置已保存')
      }
      setSettingsLoaded(true)
    } catch (e: any) {
      message.error(e?.message || '保存 Gemini 设置失败')
    } finally {
      setActionLoading('')
    }
  }

  const loadLogs = async () => {
    setActionLoading('load-logs')
    try {
      const data = await geminiFetch<GeminiLogPayload>('/gemini/admin/log?limit=200')
      setLogData(data)
      setLogsLoaded(true)
    } catch (e: any) {
      message.error(e?.message || '加载 Gemini 日志失败')
    } finally {
      setActionLoading('')
    }
  }

  const clearLogs = async () => {
    setActionLoading('clear-logs')
    try {
      await geminiFetch('/gemini/admin/log?confirm=yes', {
        method: 'DELETE',
      })
      message.success('Gemini 日志已清空')
      await loadLogs()
    } catch (e: any) {
      message.error(e?.message || '清空 Gemini 日志失败')
    } finally {
      setActionLoading('')
    }
  }

  const loadHistory = async () => {
    setActionLoading('load-history')
    try {
      const data = await geminiFetch<GeminiHistoryPayload>('/gemini/admin/task-history?limit=100')
      setHistoryData(data)
      setHistoryLoaded(true)
    } catch (e: any) {
      message.error(e?.message || '加载 Gemini 任务历史失败')
    } finally {
      setActionLoading('')
    }
  }

  const clearHistory = async () => {
    setActionLoading('clear-history')
    try {
      await geminiFetch('/gemini/admin/task-history?confirm=yes', {
        method: 'DELETE',
      })
      message.success('Gemini 任务历史已清空')
      await loadHistory()
    } catch (e: any) {
      message.error(e?.message || '清空 Gemini 任务历史失败')
    } finally {
      setActionLoading('')
    }
  }

  const openRegisterModal = () => {
    void (async () => {
      try {
        const cfg = await apiFetch('/config')
        const concurrency = Number.parseInt(String(cfg.register_max_concurrency || ''), 10)
        const mailProvider = GEMINI_SHARED_MAIL_PROVIDERS.has(String(cfg.mail_provider || ''))
          ? String(cfg.mail_provider || '')
          : 'duckmail'
        registerForm.setFieldsValue({
          count: 1,
          concurrency: Number.isFinite(concurrency) && concurrency > 0 ? concurrency : 5,
          domain: '',
          mail_provider: mailProvider,
        })
      } catch {
        registerForm.setFieldsValue({
          count: 1,
          concurrency: 5,
          domain: '',
          mail_provider: 'duckmail',
        })
      }
      setRegisterOpen(true)
    })()
  }

  const handleStartRegister = async () => {
    const values = await registerForm.validateFields()
    setActionLoading('register')
    try {
      const task = await geminiFetch<GeminiTask>('/gemini/admin/register/start', {
        method: 'POST',
        body: JSON.stringify(values),
      })
      setRegisterTask(task)
      setRegisterOpen(false)
      message.success('Gemini 注册任务已启动')
      await load(true)
    } catch (e: any) {
      message.error(e?.message || 'Gemini 注册任务启动失败')
    } finally {
      setActionLoading('')
    }
  }

  const handleLoginCheck = async () => {
    setActionLoading('login-check')
    try {
      const task = await geminiFetch<GeminiTask>('/gemini/admin/login/check', {
        method: 'POST',
      })
      setLoginTask(task)
      message.success(task?.status === 'idle' ? '当前没有需要刷新的 Gemini 登录任务' : 'Gemini 登录校验任务已启动')
      await load(true)
    } catch (e: any) {
      message.error(e?.message || 'Gemini 登录校验启动失败')
    } finally {
      setActionLoading('')
    }
  }

  const handleToggleAccount = async (account: GeminiAccount, disabled: boolean) => {
    const actionKey = `${disabled ? 'disable' : 'enable'}-${account.id}`
    setActionLoading(actionKey)
    try {
      await geminiFetch(`/gemini/admin/accounts/${account.id}/${disabled ? 'disable' : 'enable'}`, {
        method: 'PUT',
      })
      message.success(disabled ? '账号已禁用' : '账号已启用')
      await load(true)
    } catch (e: any) {
      message.error(e?.message || (disabled ? '禁用失败' : '启用失败'))
    } finally {
      setActionLoading('')
    }
  }

  const handleDeleteAccount = async (accountId: string) => {
    setActionLoading(`delete-${accountId}`)
    try {
      await geminiFetch(`/gemini/admin/accounts/${accountId}`, {
        method: 'DELETE',
      })
      message.success('账号已删除')
      await load(true)
    } catch (e: any) {
      message.error(e?.message || '删除失败')
    } finally {
      setActionLoading('')
    }
  }

  const accountColumns: ColumnsType<GeminiAccount> = [
    {
      title: '账号 ID',
      dataIndex: 'id',
      key: 'id',
      ellipsis: true,
      render: (value: string) => (
        <Text copyable={{ text: value }} style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {value || '-'}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value: string) => {
        if (value === '正常' || value === 'active') return <Tag color="success">{value}</Tag>
        if (value === '过期' || value === 'failed') return <Tag color="error">{value}</Tag>
        return <Tag>{value || '未知'}</Tag>
      },
    },
    {
      title: '禁用',
      dataIndex: 'disabled',
      key: 'disabled',
      width: 120,
      render: (value: boolean, record) =>
        value ? (
          <Space direction="vertical" size={0}>
            <Tag color="error">已禁用</Tag>
            {record.disabled_reason ? (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {record.disabled_reason}
              </Text>
            ) : null}
          </Space>
        ) : (
          <Tag color="success">启用</Tag>
        ),
    },
    {
      title: '冷却',
      key: 'cooldown',
      width: 180,
      render: (_, record) => renderCooldown(record),
    },
    {
      title: '剩余时间',
      dataIndex: 'remaining_display',
      key: 'remaining_display',
      width: 140,
      render: (value?: string) => value || '-',
    },
    {
      title: '对话数',
      dataIndex: 'conversation_count',
      key: 'conversation_count',
      width: 100,
      render: (value?: number) => value ?? 0,
    },
    {
      title: '会话使用',
      dataIndex: 'session_usage_count',
      key: 'session_usage_count',
      width: 110,
      render: (value?: number) => value ?? 0,
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      render: (_, record) => (
        <Space wrap>
          {record.disabled ? (
            <Button
              size="small"
              loading={actionLoading === `enable-${record.id}`}
              onClick={() => void handleToggleAccount(record, false)}
            >
              启用
            </Button>
          ) : (
            <Button
              size="small"
              loading={actionLoading === `disable-${record.id}`}
              onClick={() => void handleToggleAccount(record, true)}
            >
              禁用
            </Button>
          )}
          <Popconfirm
            title="确认删除这个 Gemini 账号？"
            onConfirm={() => void handleDeleteAccount(record.id)}
            okText="删除"
            cancelText="取消"
          >
            <Button size="small" danger loading={actionLoading === `delete-${record.id}`}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const logColumns: ColumnsType<GeminiLogEntry> = [
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      width: 180,
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 100,
      render: (value: string) => {
        if (value === 'ERROR' || value === 'CRITICAL') return <Tag color="error">{value}</Tag>
        if (value === 'WARNING') return <Tag color="warning">{value}</Tag>
        return <Tag>{value}</Tag>
      },
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      render: (value: string) => (
        <Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {value}
        </Text>
      ),
    },
  ]

  const historyColumns: ColumnsType<GeminiHistoryEntry> = [
    {
      title: '任务 ID',
      dataIndex: 'id',
      key: 'id',
      ellipsis: true,
      render: (value: string) => (
        <Text copyable={{ text: value }} style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {value}
        </Text>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (value: string) => <Tag color={value === 'register' ? 'blue' : 'purple'}>{value}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value: string, record) => (
        <Space size={6}>
          {formatTaskStatus({ status: value })}
          {record.is_live ? <Tag color="processing">实时</Tag> : null}
        </Space>
      ),
    },
    {
      title: '进度',
      key: 'progress',
      width: 140,
      render: (_, record) => `${record.progress ?? 0}/${record.total ?? 0}`,
    },
    {
      title: '成功',
      dataIndex: 'success_count',
      key: 'success_count',
      width: 90,
    },
    {
      title: '失败',
      dataIndex: 'fail_count',
      key: 'fail_count',
      width: 90,
    },
    {
      title: '开始时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (value?: number) => (value ? new Date(value * 1000).toLocaleString('zh-CN') : '-'),
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 'bold', margin: 0 }}>Gemini 账号管理</h1>
          <p style={{ color: '#7a8ba3', marginTop: 4, marginBottom: 0 }}>
            Gemini 现在直接并到主站账号管理里，不再以独立控制台作为主操作入口。
          </p>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined spin={loading} />} onClick={() => void load()} loading={loading}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={actionLoading === 'register'}
            onClick={openRegisterModal}
          >
            注册补货
          </Button>
          <Button
            icon={<SyncOutlined />}
            loading={actionLoading === 'login-check'}
            onClick={() => void handleLoginCheck()}
          >
            检查登录
          </Button>
        </Space>
      </div>

      {error ? <Alert type="error" message={error} showIcon /> : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={10}>
          <Card title="运行状态" extra={loading ? <Spin size="small" /> : null}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="服务">
                {status?.name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {status?.running ? (
                  <Tag color="success" icon={<CheckCircleOutlined />}>运行中</Tag>
                ) : (
                  <Tag color="default">未知</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="主站共享登录">
                <Tag color="success">已启用</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Gemini UI 资源">
                {status?.ui_available ? <Tag color="success">已部署</Tag> : <Tag color="warning">缺失</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="API Base">
                {status?.api_base_path || '/gemini/v1'}
              </Descriptions.Item>
              <Descriptions.Item label="版本">
                {status?.version || '-'}
                {status?.commit ? ` (${status.commit})` : ''}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} xl={14}>
          <Card title="当前任务">
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <Card size="small" title="注册任务">
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="状态">
                      {formatTaskStatus(registerTask)}
                    </Descriptions.Item>
                    <Descriptions.Item label="进度">
                      {registerTask?.progress ?? 0}
                    </Descriptions.Item>
                    <Descriptions.Item label="成功">
                      {registerTask?.success_count ?? 0}
                    </Descriptions.Item>
                    <Descriptions.Item label="失败">
                      {registerTask?.fail_count ?? 0}
                    </Descriptions.Item>
                    {registerTask?.error ? (
                      <Descriptions.Item label="错误">
                        <Text type="danger">{registerTask.error}</Text>
                      </Descriptions.Item>
                    ) : null}
                  </Descriptions>
                </Card>
              </Col>
              <Col xs={24} md={12}>
                <Card size="small" title="登录校验任务">
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="状态">
                      {formatTaskStatus(loginTask)}
                    </Descriptions.Item>
                    <Descriptions.Item label="进度">
                      {loginTask?.progress ?? 0}
                    </Descriptions.Item>
                    <Descriptions.Item label="成功">
                      {loginTask?.success_count ?? 0}
                    </Descriptions.Item>
                    <Descriptions.Item label="失败">
                      {loginTask?.fail_count ?? 0}
                    </Descriptions.Item>
                    {loginTask?.error ? (
                      <Descriptions.Item label="错误">
                        <Text type="danger">{loginTask.error}</Text>
                      </Descriptions.Item>
                    ) : null}
                  </Descriptions>
                </Card>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={12} md={8} xl={4}>
          <Card><Statistic title="总账号数" value={stats?.total_accounts ?? 0} /></Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card><Statistic title="可用账号" value={stats?.active_accounts ?? 0} valueStyle={{ color: '#16a34a' }} /></Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card><Statistic title="冷却账号" value={stats?.rate_limited_accounts ?? 0} valueStyle={{ color: '#d97706' }} /></Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card><Statistic title="失效账号" value={stats?.failed_accounts ?? 0} valueStyle={{ color: '#dc2626' }} /></Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card><Statistic title="成功请求" value={stats?.success_count ?? 0} /></Card>
        </Col>
        <Col xs={12} md={8} xl={4}>
          <Card><Statistic title="失败请求" value={stats?.failed_count ?? 0} valueStyle={{ color: '#dc2626' }} /></Card>
        </Col>
      </Row>

      <Card bodyStyle={{ paddingTop: 8 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'accounts',
              label: '账号',
              children: accounts.length ? (
                <Table
                  rowKey="id"
                  columns={accountColumns}
                  dataSource={accounts}
                  pagination={{ pageSize: 8, hideOnSinglePage: true }}
                  scroll={{ x: 1100 }}
                />
              ) : (
                <Empty description="暂无 Gemini 账号数据" />
              ),
            },
            {
              key: 'settings',
              label: '设置',
              children: (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <Alert
                    type="info"
                    showIcon
                    message="Gemini 优先复用主站全局配置"
                    description="邮箱渠道、共享邮箱参数和注册并发上限优先使用主站全局配置。这里仅保留 Gemini 专属字段，不再暴露整份 JSON。"
                  />
                  <Space wrap>
                    <Button onClick={() => void loadSettings()} loading={actionLoading === 'load-settings'}>
                      刷新设置
                    </Button>
                    <Button type="primary" onClick={() => void saveSettings()} loading={actionLoading === 'save-settings'}>
                      保存设置
                    </Button>
                  </Space>
                  <Card size="small" title="共享主站配置">
                    <Form form={sharedSettingsForm} layout="vertical">
                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item name="register_max_concurrency" label="主站并发上限" rules={[{ required: true, message: '请输入并发上限' }]}>
                            <InputNumber min={1} max={50} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item name="mail_provider" label="共享邮箱渠道">
                            <Select
                              allowClear
                              options={[
                                { label: 'DuckMail', value: 'duckmail' },
                                { label: 'MoeMail', value: 'moemail' },
                                { label: 'Freemail', value: 'freemail' },
                              ]}
                            />
                          </Form.Item>
                        </Col>
                      </Row>

                      {sharedMailProvider === 'moemail' ? (
                        <Row gutter={16}>
                          <Col xs={24} md={8}>
                            <Form.Item name="moemail_api_url" label="MoeMail API URL">
                              <Input placeholder="https://mail.example.com" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={8}>
                            <Form.Item name="moemail_api_key" label="MoeMail API Key">
                              <Input.Password placeholder="API Key" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={8}>
                            <Form.Item name="moemail_domain" label="MoeMail 域名">
                              <Input placeholder="moemail.app" />
                            </Form.Item>
                          </Col>
                        </Row>
                      ) : null}

                      {sharedMailProvider === 'freemail' ? (
                        <Row gutter={16}>
                          <Col xs={24} md={8}>
                            <Form.Item name="freemail_api_url" label="Freemail API URL">
                              <Input placeholder="https://mail.example.com" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={8}>
                            <Form.Item name="freemail_admin_token" label="Freemail Token">
                              <Input.Password placeholder="管理员 Token" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={8}>
                            <Form.Item name="freemail_domain" label="Freemail 域名">
                              <Input placeholder="freemail.local" />
                            </Form.Item>
                          </Col>
                        </Row>
                      ) : null}

                      {sharedMailProvider === 'duckmail' ? (
                        <Row gutter={16}>
                          <Col xs={24} md={12}>
                            <Form.Item name="duckmail_provider_url" label="DuckMail Provider URL">
                              <Input placeholder="https://api.duckmail.sbs" />
                            </Form.Item>
                          </Col>
                          <Col xs={24} md={12}>
                            <Form.Item name="duckmail_bearer" label="DuckMail Bearer">
                              <Input.Password placeholder="Bearer Token" />
                            </Form.Item>
                          </Col>
                        </Row>
                      ) : null}
                    </Form>
                  </Card>

                  <Card size="small" title="Gemini 专属配置">
                    <Form form={nativeSettingsForm} layout="vertical">
                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <Form.Item name="api_key" label="Gemini API Key">
                            <Input.Password placeholder="sk-..." />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item name="base_url" label="Gemini Base URL">
                            <Input placeholder="默认留空即可" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item name="proxy_for_auth" label="认证代理">
                            <Input placeholder="http://user:pass@host:port" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item name="proxy_for_chat" label="对话代理">
                            <Input placeholder="http://user:pass@host:port" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item name="browser_mode" label="浏览器模式">
                            <Select
                              options={[
                                { label: 'normal', value: 'normal' },
                                { label: 'silent', value: 'silent' },
                                { label: 'headless', value: 'headless' },
                              ]}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item name="register_default_count" label="默认注册数量">
                            <InputNumber min={1} max={200} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item name="register_default_concurrency" label="默认注册并发">
                            <InputNumber min={1} max={50} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item name="register_domain" label="注册域名">
                            <Input placeholder="可选" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item name="refresh_window_hours" label="刷新窗口小时数">
                            <InputNumber min={1} max={168} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item name="auto_refresh_accounts_seconds" label="自动刷新间隔（秒）">
                            <InputNumber min={30} max={86400} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item name="refresh_cooldown_hours" label="刷新冷却（小时）">
                            <InputNumber min={1} max={168} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                          <Form.Item name="logo_url" label="公开页 Logo URL">
                            <Input placeholder="https://..." />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={24}>
                          <Form.Item name="chat_url" label="公开页 Chat URL">
                            <Input placeholder="https://..." />
                          </Form.Item>
                        </Col>
                      </Row>
                    </Form>
                  </Card>
                </div>
              ),
            },
            {
              key: 'logs',
              label: '日志',
              children: (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <Space wrap>
                    <Button onClick={() => void loadLogs()} loading={actionLoading === 'load-logs'}>
                      刷新日志
                    </Button>
                    <Popconfirm title="确认清空 Gemini 日志？" onConfirm={() => void clearLogs()}>
                      <Button danger loading={actionLoading === 'clear-logs'}>
                        清空日志
                      </Button>
                    </Popconfirm>
                    <Text type="secondary">
                      当前日志 {logData?.total ?? 0} 条，对话请求 {logData?.stats?.chat_count ?? 0} 次
                    </Text>
                  </Space>
                  <Table
                    rowKey={(record, index) => `${record.time}-${index}`}
                    columns={logColumns}
                    dataSource={logData?.logs || []}
                    pagination={{ pageSize: 10, hideOnSinglePage: true }}
                    scroll={{ x: 900 }}
                    locale={{ emptyText: '暂无 Gemini 日志' }}
                  />
                </div>
              ),
            },
            {
              key: 'history',
              label: '任务历史',
              children: (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <Space wrap>
                    <Button onClick={() => void loadHistory()} loading={actionLoading === 'load-history'}>
                      刷新历史
                    </Button>
                    <Popconfirm title="确认清空 Gemini 任务历史？" onConfirm={() => void clearHistory()}>
                      <Button danger loading={actionLoading === 'clear-history'}>
                        清空历史
                      </Button>
                    </Popconfirm>
                    <Text type="secondary">
                      当前记录 {historyData?.total ?? 0} 条
                    </Text>
                  </Space>
                  <Table
                    rowKey="id"
                    columns={historyColumns}
                    dataSource={historyData?.history || []}
                    pagination={{ pageSize: 10, hideOnSinglePage: true }}
                    scroll={{ x: 1000 }}
                    locale={{ emptyText: '暂无 Gemini 任务历史' }}
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>

      {!status?.ui_available ? (
        <Alert
          type="warning"
          showIcon
          message="Gemini 独立控制台静态资源缺失"
          description="这不会影响当前主站原生账号管理页。只是如果你想回看历史独立控制台，需要后续再补齐 Gemini 静态资源。"
        />
      ) : null}

      <Modal
        title="启动 Gemini 注册任务"
        open={registerOpen}
        onCancel={() => setRegisterOpen(false)}
        onOk={() => void handleStartRegister()}
        confirmLoading={actionLoading === 'register'}
        okText="启动"
        cancelText="取消"
      >
        <Form form={registerForm} layout="vertical">
          <Form.Item name="count" label="数量" rules={[{ required: true, message: '请输入注册数量' }]}>
            <InputNumber min={1} max={200} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="concurrency" label="并发" rules={[{ required: true, message: '请输入并发数量' }]}>
            <InputNumber min={1} max={50} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="mail_provider" label="邮箱渠道">
            <Select options={MAIL_PROVIDER_OPTIONS} allowClear />
          </Form.Item>
          <Form.Item name="domain" label="指定域名">
            <Input placeholder="可选，不填则使用默认邮箱配置" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
