import { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Row,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ApiOutlined,
  CheckCircleOutlined,
  LinkOutlined,
  ReloadOutlined,
} from '@ant-design/icons'

import { apiFetch } from '@/lib/utils'

const { Text } = Typography

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

async function geminiFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
    },
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

function formatCooldown(account: GeminiAccount) {
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
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
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
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const accountColumns: ColumnsType<GeminiAccount> = [
    {
      title: '账号 ID',
      dataIndex: 'id',
      key: 'id',
      ellipsis: true,
      render: (value: string) => value || '-',
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
      width: 100,
      render: (value: boolean) => (value ? <Tag color="error">已禁用</Tag> : <Tag color="success">启用</Tag>),
    },
    {
      title: '冷却',
      key: 'cooldown',
      width: 180,
      render: (_, record) => formatCooldown(record),
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
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 'bold', margin: 0 }}>Gemini Gateway</h1>
          <p style={{ color: '#7a8ba3', marginTop: 4, marginBottom: 0 }}>
            Gemini 已切回主站原生页展示，不再使用内嵌 iframe 面板。
          </p>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined spin={loading} />} onClick={() => void load()} loading={loading}>
            刷新状态
          </Button>
          <Button icon={<LinkOutlined />} onClick={() => window.open('/gemini/', '_blank', 'noopener,noreferrer')}>
            打开 Gemini 控制台
          </Button>
          <Button icon={<ApiOutlined />} onClick={() => window.open('/gemini/public/logs', '_blank', 'noopener,noreferrer')}>
            打开公开日志
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
              <Descriptions.Item label="控制台路径">
                <a href={status?.ui_path || '/gemini/'} target="_blank" rel="noreferrer">
                  {status?.ui_path || '/gemini/'}
                </a>
              </Descriptions.Item>
              <Descriptions.Item label="Health 路径">
                {status?.health_path || '/gemini/health'}
              </Descriptions.Item>
              <Descriptions.Item label="API Base">
                {status?.api_base_path || '/gemini/v1'}
              </Descriptions.Item>
              <Descriptions.Item label="主站共享登录">
                <Tag color="success">已启用</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Gemini 静态资源">
                {status?.ui_available ? <Tag color="success">已部署</Tag> : <Tag color="warning">缺失</Tag>}
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

      <Card
        title="账号概览"
        extra={accounts.length ? <Tag color="blue">{accounts.length} 个账号</Tag> : null}
      >
        {accounts.length ? (
          <Table
            rowKey="id"
            columns={accountColumns}
            dataSource={accounts}
            pagination={{ pageSize: 8, hideOnSinglePage: true }}
            scroll={{ x: 960 }}
          />
        ) : (
          <Empty description="暂无 Gemini 账号数据" />
        )}
      </Card>

      {!status?.ui_available ? (
        <Alert
          type="warning"
          showIcon
          message="Gemini 控制台静态资源缺失"
          description="后端已挂载 Gemini，但完整控制台资源还没部署到服务器。当前主站原生页仍可查看状态和账号概览，等静态资源补齐后再用“打开 Gemini 控制台”进入完整面板。"
        />
      ) : null}
    </div>
  )
}
