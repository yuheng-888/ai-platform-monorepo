export type PlatformMenuEntry = {
  key: string
  label: string
}

export function buildPlatformMenuChildren(platforms: PlatformMenuEntry[]): {
  key: string
  label: string
}[]
