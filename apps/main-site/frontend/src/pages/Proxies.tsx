import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Descriptions,
  Divider,
  Input,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  SwapLeftOutlined,
  SwapRightOutlined,
} from '@ant-design/icons'
import { apiFetch } from '@/lib/utils'


type ProxyRow = {
  id: number
  url: string
  region: string
  success_count: number
  fail_count: number
  is_active: boolean
}

type Strategy = {
  resin_enabled: boolean
  resin_url: string
  resin_platform_chatgpt_register: string
  resin_platform_chatgpt_runtime: string
  resin_platform_gemini_register: string
  resin_platform_gemini_runtime: string
  goproxy_enabled: string
  goproxy_upstream_url: string
  goproxy_resin_sync_enabled: string
  goproxy_resin_sync_interval_seconds: string
  goproxy_resin_subscription_name: string
  goproxy_resin_min_quality: string
  goproxy_resin_max_latency_ms: string
  fallback_total: number
  fallback_active: number
}

type ConfigShape = Record<string, string>

type SyncStatus = {
  ok: boolean
  action: string
  message: string
  fetched: number
  accepted: number
  subscription_id: string
  subscription_name: string
  last_started_at: number
  last_finished_at: number
}

const RESIN_KEYS = [
  'resin_url',
  'resin_admin_token',
  'resin_proxy_token',
  'resin_platform_chatgpt_register',
  'resin_platform_chatgpt_runtime',
  'resin_platform_gemini_register',
  'resin_platform_gemini_runtime',
  'goproxy_enabled',
  'goproxy_upstream_url',
  'goproxy_webui_password',
  'goproxy_resin_sync_enabled',
  'goproxy_resin_sync_interval_seconds',
  'goproxy_resin_subscription_name',
  'goproxy_resin_min_quality',
  'goproxy_resin_max_latency_ms',
] as const


export default function Proxies() {
  const [proxies, setProxies] = useState<ProxyRow[]>([])
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [config, setConfig] = useState<ConfigShape>({})
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [newProxy, setNewProxy] = useState('')
  const [region, setRegion] = useState('')
  const [checking, setChecking] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [configData, strategyData, proxyData, syncData] = await Promise.all([
        apiFetch('/config'),
        apiFetch('/proxies/strategy'),
        apiFetch('/proxies'),
        apiFetch('/proxies/goproxy-resin-sync'),
      ])
      setConfig(configData || {})
      setStrategy(strategyData || null)
      setProxies(proxyData || [])
      setSyncStatus(syncData || null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const setField = (key: string, value: string) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  const saveStrategy = async () => {
    setSaving(true)
    try {
      const data = Object.fromEntries(RESIN_KEYS.map((key) => [key, config[key] || '']))
      await apiFetch('/config', {
        method: 'PUT',
        body: JSON.stringify({ data }),
      })
      message.success('代理策略已保存')
      await load()
    } catch (e: any) {
      message.error(`保存失败: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  const runSync = async () => {
    setSyncing(true)
    try {
      const result = await apiFetch('/proxies/goproxy-resin-sync', { method: 'POST' })
      setSyncStatus(result || null)
      if (result?.ok) {
        message.success(`同步完成: ${result.action || 'ok'}，接受 ${result.accepted || 0} 条`)
      } else {
        message.error(`同步失败: ${result?.message || 'unknown'}`)
      }
      await load()
    } catch (e: any) {
      message.error(`同步失败: ${e.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const formatTs = (value?: number) => {
    if (!value) return '-'
    try {
      return new Date(value * 1000).toLocaleString()
    } catch {
      return String(value)
    }
  }

  const add = async () => {
    if (!newProxy.trim()) return
    const lines = newProxy.trim().split('\n').map((l) => l.trim()).filter(Boolean)
    try {
      if (lines.length > 1) {
        await apiFetch('/proxies/bulk', {
          method: 'POST',
          body: JSON.stringify({ proxies: lines, region }),
        })
      } else {
        await apiFetch('/proxies', {
          method: 'POST',
          body: JSON.stringify({ url: lines[0], region }),
        })
      }
      message.success('Fallback 代理添加成功')
      setNewProxy('')
      setRegion('')
      await load()
    } catch (e: any) {
      message.error(`添加失败: ${e.message}`)
    }
  }

  const del = async (id: number) => {
    await apiFetch(`/proxies/${id}`, { method: 'DELETE' })
    message.success('删除成功')
    await load()
  }

  const toggle = async (id: number) => {
    await apiFetch(`/proxies/${id}/toggle`, { method: 'PATCH' })
    await load()
  }

  const check = async () => {
    setChecking(true)
    try {
      await apiFetch('/proxies/check', { method: 'POST' })
      message.success('Fallback 检测任务已启动')
      setTimeout(() => {
        load()
        setChecking(false)
      }, 3000)
    } catch (e: any) {
      setChecking(false)
      message.error(`检测失败: ${e.message}`)
    }
  }

  const columns: any[] = [
    {
      title: '代理地址',
      dataIndex: 'url',
      key: 'url',
      render: (text: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{text}</span>,
    },
    {
      title: '地区',
      dataIndex: 'region',
      key: 'region',
      render: (text: string) => text || '-',
    },
    {
      title: '成功/失败',
      key: 'stats',
      render: (_: any, record: ProxyRow) => (
        <Space>
          <Tag color="success">{record.success_count}</Tag>
          <span>/</span>
          <Tag color="error">{record.fail_count}</Tag>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'error'} icon={active ? <CheckCircleOutlined /> : <CloseCircleOutlined />}>
          {active ? '活跃' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ProxyRow) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={record.is_active ? <SwapLeftOutlined /> : <SwapRightOutlined />}
            onClick={() => toggle(record.id)}
          />
          <Popconfirm title="确认删除？" onConfirm={() => del(record.id)}>
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 'bold', margin: 0 }}>代理策略</h1>
          <p style={{ color: '#7a8ba3', marginTop: 4 }}>
            主链路优先走 Resin，GoProxy 作为补充源，本地代理池仅作 fallback
          </p>
        </div>
        <Space>
          <Button icon={<ReloadOutlined spin={loading || checking} />} onClick={load} loading={loading}>
            刷新
          </Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={saveStrategy} loading={saving}>
            保存策略
          </Button>
        </Space>
      </div>

      <Card title="当前生效状态">
        <Descriptions column={2} size="small">
          <Descriptions.Item label="Resin 网关">
            {strategy?.resin_enabled ? (
              <Tag color="success">已启用</Tag>
            ) : (
              <Tag color="warning">未启用，当前将回退到本地代理池</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Resin 地址">
            {strategy?.resin_url || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="GoProxy 补充源">
            {String(config.goproxy_enabled || '').trim() === '1' ? <Tag color="blue">已启用</Tag> : <Tag>未启用</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="GoProxy -> Resin 同步">
            {String(config.goproxy_resin_sync_enabled || '').trim() === '1' ? <Tag color="cyan">已启用</Tag> : <Tag>未启用</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="Fallback 代理">
            <Tag color="default">{strategy?.fallback_active || 0} / {strategy?.fallback_total || 0}</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="Resin 网关配置">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input
            value={config.resin_url || ''}
            onChange={(e) => setField('resin_url', e.target.value)}
            placeholder="http://24.199.104.104:2260"
          />
          <Space style={{ width: '100%' }} wrap>
            <Input.Password
              value={config.resin_admin_token || ''}
              onChange={(e) => setField('resin_admin_token', e.target.value)}
              placeholder="Resin 管理后台 Token"
              style={{ width: 320 }}
            />
            <Input.Password
              value={config.resin_proxy_token || ''}
              onChange={(e) => setField('resin_proxy_token', e.target.value)}
              placeholder="Resin 代理 Token"
              style={{ width: 320 }}
            />
          </Space>
        </Space>
      </Card>

      <Card title="平台映射">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space style={{ width: '100%' }} wrap>
            <Input
              value={config.resin_platform_chatgpt_register || ''}
              onChange={(e) => setField('resin_platform_chatgpt_register', e.target.value)}
              placeholder="chatgpt-register"
              addonBefore="ChatGPT 注册池"
              style={{ width: 320 }}
            />
            <Input
              value={config.resin_platform_chatgpt_runtime || ''}
              onChange={(e) => setField('resin_platform_chatgpt_runtime', e.target.value)}
              placeholder="chatgpt-runtime"
              addonBefore="ChatGPT 运行池"
              style={{ width: 320 }}
            />
          </Space>
          <Space style={{ width: '100%' }} wrap>
            <Input
              value={config.resin_platform_gemini_register || ''}
              onChange={(e) => setField('resin_platform_gemini_register', e.target.value)}
              placeholder="gemini-register"
              addonBefore="Gemini 注册池"
              style={{ width: 320 }}
            />
            <Input
              value={config.resin_platform_gemini_runtime || ''}
              onChange={(e) => setField('resin_platform_gemini_runtime', e.target.value)}
              placeholder="gemini-runtime"
              addonBefore="Gemini 运行池"
              style={{ width: 320 }}
            />
          </Space>
        </Space>
      </Card>

      <Card title="GoProxy 补充源">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Switch
              checked={String(config.goproxy_enabled || '').trim() === '1'}
              onChange={(checked) => setField('goproxy_enabled', checked ? '1' : '0')}
            />
            <span style={{ color: '#7a8ba3' }}>仅作为 Resin 的低优先级补充源，不作为主站唯一生产代理池</span>
          </div>
          <Input
            value={config.goproxy_upstream_url || ''}
            onChange={(e) => setField('goproxy_upstream_url', e.target.value)}
            placeholder="http://127.0.0.1:7778"
          />
          <Input.Password
            value={config.goproxy_webui_password || ''}
            onChange={(e) => setField('goproxy_webui_password', e.target.value)}
            placeholder="GoProxy WebUI 密码（默认 goproxy）"
          />
        </Space>
      </Card>

      <Card
        title="GoProxy -> Resin 自动同步"
        extra={
          <Button type="primary" onClick={runSync} loading={syncing}>
            立即同步
          </Button>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="最近状态">
              {syncStatus?.ok ? <Tag color="success">{syncStatus.action || 'ok'}</Tag> : <Tag color="error">{syncStatus?.message || '未执行'}</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="目标订阅">
              {syncStatus?.subscription_name || config.goproxy_resin_subscription_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="抓取数量">
              {syncStatus?.fetched ?? 0}
            </Descriptions.Item>
            <Descriptions.Item label="接受数量">
              {syncStatus?.accepted ?? 0}
            </Descriptions.Item>
            <Descriptions.Item label="开始时间">
              {formatTs(syncStatus?.last_started_at)}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间">
              {formatTs(syncStatus?.last_finished_at)}
            </Descriptions.Item>
          </Descriptions>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
            <div>
              <div style={{ marginBottom: 6 }}>启用自动同步</div>
              <Switch
                checked={String(config.goproxy_resin_sync_enabled || '').trim() === '1'}
                onChange={(checked) => setField('goproxy_resin_sync_enabled', checked ? '1' : '0')}
              />
            </div>
            <div>
              <div style={{ marginBottom: 6 }}>同步间隔（秒）</div>
              <Input
                value={config.goproxy_resin_sync_interval_seconds || ''}
                onChange={(e) => setField('goproxy_resin_sync_interval_seconds', e.target.value)}
                placeholder="600"
              />
            </div>
            <div>
              <div style={{ marginBottom: 6 }}>Resin 订阅名</div>
              <Input
                value={config.goproxy_resin_subscription_name || ''}
                onChange={(e) => setField('goproxy_resin_subscription_name', e.target.value)}
                placeholder="goproxy-pool"
              />
            </div>
            <div>
              <div style={{ marginBottom: 6 }}>最低质量等级</div>
              <Input
                value={config.goproxy_resin_min_quality || ''}
                onChange={(e) => setField('goproxy_resin_min_quality', e.target.value.toUpperCase())}
                placeholder="B"
              />
            </div>
            <div>
              <div style={{ marginBottom: 6 }}>最大延迟（毫秒）</div>
              <Input
                value={config.goproxy_resin_max_latency_ms || ''}
                onChange={(e) => setField('goproxy_resin_max_latency_ms', e.target.value)}
                placeholder="2000"
              />
            </div>
          </div>
        </Space>
      </Card>

      <Card
        title="本地 Fallback 代理池"
        extra={
          <Button icon={<ReloadOutlined spin={checking} />} onClick={check} loading={checking}>
            检测全部
          </Button>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ color: '#7a8ba3' }}>
            仅在 Resin 未配置或不可用时作为兜底。建议保留少量稳定代理，避免主链路中断时彻底无代理可用。
          </div>

          <Divider style={{ margin: '8px 0' }} />

          <Space direction="vertical" style={{ width: '100%' }}>
            <Input.TextArea
              value={newProxy}
              onChange={(e) => setNewProxy(e.target.value)}
              placeholder="http://user:pass@host:port"
              rows={3}
              style={{ fontFamily: 'monospace' }}
            />
            <Space wrap>
              <Input
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                placeholder="地区标签 (如 US, SG)"
                style={{ width: 200 }}
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={add}>
                添加 Fallback 代理
              </Button>
            </Space>
          </Space>

          <Table
            rowKey="id"
            columns={columns}
            dataSource={proxies}
            loading={loading}
            pagination={false}
          />
        </Space>
      </Card>
    </div>
  )
}
