import { useState } from 'react'
import { Alert, Button, Card, Form, Input, Typography, message } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { apiFetch } from '@/lib/utils'


interface LoginPageProps {
  configured: boolean
  onSuccess: () => Promise<void> | void
}


export default function LoginPage({ configured, onSuccess }: LoginPageProps) {
  const [loading, setLoading] = useState(false)

  const submit = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const path = configured ? '/auth/login' : '/auth/bootstrap'
      await apiFetch(path, {
        method: 'POST',
        body: JSON.stringify(values),
      })
      message.success(configured ? '登录成功' : '管理员初始化成功')
      await onSuccess()
    } catch (error: any) {
      message.error(error?.message || (configured ? '登录失败' : '初始化失败'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background:
          'radial-gradient(circle at top, rgba(99,102,241,0.18), transparent 38%), linear-gradient(180deg, rgba(15,23,42,0.98), rgba(2,6,23,1))',
      }}
    >
      <Card
        style={{ width: 420, maxWidth: '100%', borderRadius: 18 }}
        bodyStyle={{ padding: 28 }}
      >
        <Typography.Title level={3} style={{ marginTop: 0, marginBottom: 8 }}>
          {configured ? '管理员登录' : '初始化管理员账号'}
        </Typography.Title>
        <Typography.Paragraph style={{ color: '#64748b', marginBottom: 20 }}>
          {configured
            ? '登录后才能访问账号、注册、设置、插件和 Gemini 网关。'
            : '系统尚未设置管理员，请先创建唯一管理员账号。'}
        </Typography.Paragraph>

        {!configured ? (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 20 }}
            message="首次初始化后，这组账号密码就是后台唯一入口。"
          />
        ) : null}

        <Form layout="vertical" onFinish={submit}>
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="admin" autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少 8 位' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="至少 8 位"
              autoComplete={configured ? 'current-password' : 'new-password'}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            {configured ? '登录' : '创建管理员账号'}
          </Button>
        </Form>
      </Card>
    </div>
  )
}
