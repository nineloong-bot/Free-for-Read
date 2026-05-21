const COVER_GRADIENTS = [
  'linear-gradient(150deg, #d4641a, #e88a3a)',
  'linear-gradient(150deg, #4a90d9, #6bb5e0)',
  'linear-gradient(150deg, #2d8a6e, #4ab89a)',
  'linear-gradient(150deg, #c44a6a, #e0688a)',
  'linear-gradient(150deg, #8b5cf6, #a78bfa)',
  'linear-gradient(150deg, #f59e0b, #fbbf24)',
]

export function coverGradient(index: number): string {
  return COVER_GRADIENTS[index % COVER_GRADIENTS.length]
}
