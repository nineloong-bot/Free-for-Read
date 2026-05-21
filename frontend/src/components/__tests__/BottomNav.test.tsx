import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BottomNav } from '../BottomNav'

describe('BottomNav', () => {
  it('renders four tabs', () => {
    render(<BottomNav activeView="library" onNavigate={() => {}} />)
    expect(screen.getByText('书架')).toBeInTheDocument()
    expect(screen.getByText('解析')).toBeInTheDocument()
    expect(screen.getByText('AI')).toBeInTheDocument()
    expect(screen.getByText('设置')).toBeInTheDocument()
  })
})
