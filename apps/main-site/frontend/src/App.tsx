import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { ConfigProvider, Layout, Menu, Button, Space, Spin, Typography } from 'antd'
import {
  DashboardOutlined,
  UserOutlined,
  GlobalOutlined,
  HistoryOutlined,
  SettingOutlined,
  SunOutlined,
  MoonOutlined,
} from '@ant-design/icons'
import zhCN from 'antd/locale/zh_CN'
import Dashboard from '@/pages/Dashboard'
import Accounts from '@/pages/Accounts'
import Register from '@/pages/Register'
import Proxies from '@/pages/Proxies'
import Settings from '@/pages/Settings'
import TaskHistory from '@/pages/TaskHistory'
import GeminiPage from '@/pages/Gemini'
import { darkTheme, lightTheme } from './theme'
import LoginPage from '@/pages/Login'
import { apiFetch } from '@/lib/utils'
import { buildPlatformMenuChildren } from '@/lib/navigation.js'

const { Sider, Content } = Layout

function AppContent() {
  const [themeMode, setThemeMode] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('theme') as 'dark' | 'light') || 'dark'
  )
  const [collapsed, setCollapsed] = useState(false)
  const [platforms, setPlatforms] = useState<{ key: string; label: string }[]>([])
  const [auth, setAuth] = useState({
    loading: true,
    configured: false,
    authenticated: false,
    username: '',
  })
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    document.documentElement.classList.toggle('light', themeMode === 'light')
    document.documentElement.style.setProperty(
      '--sider-trigger-border',
      themeMode === 'light' ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.15)'
    )
    localStorage.setItem('theme', themeMode)
  }, [themeMode])

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const data = await fetch('/api/auth/me', { credentials: 'same-origin' }).then((r) => r.json())
        setAuth({
          loading: false,
          configured: Boolean(data.configured),
          authenticated: Boolean(data.authenticated),
          username: data.username || '',
        })
      } catch {
        setAuth({
          loading: false,
          configured: false,
          authenticated: false,
          username: '',
        })
      }
    }

    loadAuth()

    const onUnauthorized = () => {
      setAuth((prev) => ({
        ...prev,
        loading: false,
        authenticated: false,
        username: '',
      }))
    }
    window.addEventListener('app:unauthorized', onUnauthorized)
    return () => window.removeEventListener('app:unauthorized', onUnauthorized)
  }, [])

  useEffect(() => {
    if (!auth.authenticated) {
      setPlatforms([])
      return
    }
    apiFetch('/platforms').then((d) =>
      setPlatforms(
        (d || [])
          .filter((p: any) => p.name !== 'tavily')
          .map((p: any) => ({ key: p.name, label: p.display_name }))
      )
    )
  }, [auth.authenticated])

  const isLight = themeMode === 'light'
  const currentTheme = isLight ? lightTheme : darkTheme

  const reloadAuth = async () => {
    const data = await fetch('/api/auth/me', { credentials: 'same-origin' }).then((r) => r.json())
    setAuth({
      loading: false,
      configured: Boolean(data.configured),
      authenticated: Boolean(data.authenticated),
      username: data.username || '',
    })
  }

  const logout = async () => {
    await apiFetch('/auth/logout', { method: 'POST' })
    setAuth((prev) => ({
      ...prev,
      authenticated: false,
      username: '',
    }))
  }

  const getSelectedKey = () => {
    const path = location.pathname
    if (path === '/') return ['/']
    if (path.startsWith('/accounts')) return [path]
    if (path === '/history') return ['/history']
    if (path === '/proxies') return ['/proxies']
    if (path === '/settings') return ['/settings']
    if (path === '/gemini-console') return ['/gemini-console']
    return ['/']
  }

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/accounts',
      icon: <UserOutlined />,
      label: '平台管理',
      children: buildPlatformMenuChildren(platforms),
    },
    {
      key: '/history',
      icon: <HistoryOutlined />,
      label: '任务历史',
    },
    {
      key: '/proxies',
      icon: <GlobalOutlined />,
      label: '代理管理',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '全局配置',
    },
  ]

  if (auth.loading) {
    return (
      <ConfigProvider theme={currentTheme} locale={zhCN}>
        <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
          <Space direction="vertical" align="center">
            <Spin size="large" />
            <Typography.Text type="secondary">正在检查登录状态...</Typography.Text>
          </Space>
        </div>
      </ConfigProvider>
    )
  }

  if (!auth.authenticated) {
    return (
      <ConfigProvider theme={currentTheme} locale={zhCN}>
        <LoginPage configured={auth.configured} onSuccess={reloadAuth} />
      </ConfigProvider>
    )
  }

  return (
    <ConfigProvider theme={currentTheme} locale={zhCN}>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          style={{
            background: currentTheme.token?.colorBgContainer,
            borderRight: `1px solid ${currentTheme.token?.colorBorder}`,
          }}
          width={220}
        >
          <div
            style={{
              height: 64,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderBottom: `1px solid ${currentTheme.token?.colorBorder}`,
            }}
          >
            <DashboardOutlined style={{ fontSize: 20, color: currentTheme.token?.colorPrimary }} />
            {!collapsed && (
              <span
                style={{
                  marginLeft: 8,
                  fontWeight: 600,
                  fontSize: 14,
                  color: currentTheme.token?.colorText,
                }}
              >
                Account Manager
              </span>
            )}
          </div>
          <Menu
            mode="inline"
            selectedKeys={getSelectedKey()}
            defaultOpenKeys={['/accounts']}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{
              borderRight: 0,
              background: 'transparent',
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: 16,
              left: 0,
              right: 0,
              padding: '0 16px',
            }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {!collapsed ? (
                <Typography.Text style={{ fontSize: 12, color: currentTheme.token?.colorTextSecondary }}>
                  已登录：{auth.username}
                </Typography.Text>
              ) : null}
              <Button
                block
                icon={isLight ? <SunOutlined /> : <MoonOutlined />}
                onClick={() => setThemeMode(isLight ? 'dark' : 'light')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: collapsed ? 'center' : 'space-between',
                }}
              >
                {!collapsed && (isLight ? '亮色模式' : '暗色模式')}
              </Button>
              <Button block danger onClick={logout}>
                {!collapsed ? '退出登录' : '退'}
              </Button>
            </Space>
          </div>
        </Sider>
        <Content
          style={{
            padding: 24,
            overflow: 'auto',
            background: currentTheme.token?.colorBgLayout,
          }}
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/accounts/:platform" element={<Accounts />} />
            <Route path="/register" element={<Register />} />
            <Route path="/history" element={<TaskHistory />} />
            <Route path="/proxies" element={<Proxies />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/gemini-console" element={<GeminiPage />} />
          </Routes>
        </Content>
      </Layout>
    </ConfigProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}
