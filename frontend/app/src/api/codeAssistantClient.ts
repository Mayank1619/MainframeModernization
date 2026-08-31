export interface CodeAssistantHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export interface CodeAssistantSource {
  file_id: string
  start_line: number
  end_line: number
  cosine_similarity: number
}

export interface CodeAssistantResponse {
  answer: string
  answer_model: string
  sources: CodeAssistantSource[]
}

const ragApiUrl: string =
  import.meta.env.VITE_RAG_API_URL ?? 'http://localhost:8000/rag-api/query'

export async function askCodeAssistant(
  question: string,
  history: CodeAssistantHistoryItem[],
  signal?: AbortSignal,
): Promise<CodeAssistantResponse> {
  const response = await fetch(ragApiUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
    signal,
  })

  if (!response.ok) {
    let message = `The code assistant returned HTTP ${response.status}.`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        message = payload.detail
      }
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new Error(message)
  }

  return (await response.json()) as CodeAssistantResponse
}
