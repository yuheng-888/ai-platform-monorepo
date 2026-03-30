import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Descriptions, Row, Spin, Tag } from 'antd'
import {
  ApiOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { apiFetch } from '@/lib/utils'


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


export default function GeminiPage() {
  const [status, setStatus] = useState<GeminiStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch('/gemini/status')
      setStatus(data)
    } catch (e: any) {
      setError(e?.message || '加载 Gemini 状态失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 'bold', margin: 0 }}>Gemini Gateway</h1>
          <p style={{ color: '#7a8ba3', marginTop: 4 }}>在当前后台内直接查看 Gemini Business2API 运行状态与管理面板</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button icon={<ReloadOutlined spin={loading} />} onClick={load} loading={loading}>
            刷新状态
          </Button>
          <Button
            icon={<ApiOutlined />}
            onClick={() => window.open('/gemini/', '_blank', 'noopener,noreferrer')}
          >
            新窗口打开
          </Button>
          <Button
            icon={<SafetyOutlined />}
            onClick={() => setIframeKey((value) => value + 1)}
          >
            重载面板
          </Button>
        </div>
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
              <Descriptions.Item label="UI 路径">
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
              <Descriptions.Item label="Admin Key">
                {status?.admin_key_configured ? <Tag color="success">已配置</Tag> : <Tag color="warning">未配置</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="Session Secret">
                {status?.session_secret_configured ? <Tag color="success">已配置</Tag> : <Tag color="warning">未配置</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="版本">
                {status?.version || '-'}
                {status?.commit ? ` (${status.commit})` : ''}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} xl={14}>
          <Card
            title="内嵌面板"
            bodyStyle={{ padding: 0 }}
            extra={<Tag color="blue">/gemini/</Tag>}
          >
            {status && !status.ui_available ? (
              <div style={{ padding: 20 }}>
                <Alert
                  type="warning"
                  showIcon
                  message="Gemini 管理面板静态资源缺失"
                  description="当前后端已挂载 Gemini 服务，但前端构建产物没有部署到服务器，所以 /gemini/ 无法打开。补齐 embedded/gemini_business2api/static 后刷新即可恢复。"
                />
              </div>
            ) : (
              <iframe
                key={iframeKey}
                src="/gemini/"
                title="Gemini Business2API"
                style={{
                  width: '100%',
                  minHeight: '76vh',
                  border: 0,
                  background: '#fff',
                }}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
