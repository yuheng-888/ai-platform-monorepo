function platformMenuItem(platform) {
  return {
    key: `/accounts/${platform.key}`,
    label: platform.label,
  }
}

export function buildPlatformMenuChildren(platforms) {
  const items = Array.isArray(platforms) ? platforms.map(platformMenuItem) : []
  const geminiItem = {
    key: '/gemini-console',
    label: 'Gemini',
  }

  const chatgptIndex = items.findIndex((item) => item.key === '/accounts/chatgpt')
  if (chatgptIndex >= 0) {
    items.splice(chatgptIndex + 1, 0, geminiItem)
    return items
  }

  return [...items, geminiItem]
}
