import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { askCodeAssistant } from '../../api/codeAssistantClient'
import { CodeAssistantOverlay } from './CodeAssistantOverlay'

vi.mock('../../api/codeAssistantClient', () => ({
  askCodeAssistant: vi.fn(),
}))

const mockedAskCodeAssistant = vi.mocked(askCodeAssistant)

describe('CodeAssistantOverlay', () => {
  beforeEach(() => {
    mockedAskCodeAssistant.mockReset()
  })

  it('opens without changing the surrounding application layout', async () => {
    const user = userEvent.setup()
    render(<CodeAssistantOverlay />)

    await user.click(screen.getByRole('button', { name: 'Open code assistant' }))

    expect(screen.getByRole('complementary', { name: 'Code assistant' })).toHaveClass(
      'rag-assistant-panel-open',
    )
    expect(screen.getByRole('heading', { name: 'How can I help you?' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Annotation mode is not available yet' })).toBeDisabled()
  })

  it('renders the retrieved answer as Markdown', async () => {
    mockedAskCodeAssistant.mockResolvedValue({
      answer: '## Customer lookup\n\nUse `0000000000` for a random customer.',
      answer_model: 'openai/gpt-oss-120b',
      sources: [
        {
          file_id: 'frontend/app/src/features/customerInquiry/CustomerInquiryPage.tsx',
          start_line: 150,
          end_line: 180,
          cosine_similarity: 0.71,
        },
      ],
    })

    const user = userEvent.setup()
    render(<CodeAssistantOverlay />)

    await user.click(screen.getByRole('button', { name: 'Open code assistant' }))
    await user.type(screen.getByRole('textbox', { name: 'Codebase question' }), 'How do I find a random customer?')
    await user.click(screen.getByRole('button', { name: 'Send question' }))

    expect(await screen.findByRole('heading', { name: 'Customer lookup' })).toBeInTheDocument()
    expect(screen.getByText('0000000000')).toBeInTheDocument()
    expect(screen.getByText('1 retrieved chunks')).toBeInTheDocument()
  })
})
