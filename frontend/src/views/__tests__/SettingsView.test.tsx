import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SettingsView } from '../SettingsView'

describe('SettingsView', () => {
  it('renders AI provider section', () => {
    render(<SettingsView />)
    expect(screen.getByText('AI 提供商')).toBeInTheDocument()
  })

  it('renders reading preferences section', () => {
    render(<SettingsView />)
    const items = screen.getAllByText('默认字号')
    expect(items.length).toBeGreaterThan(0)
  })
})
