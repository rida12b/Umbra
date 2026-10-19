# morphic

AI app (Next.js) — https://github.com/miurla/morphic @ `a95b1d7aa17f729fd8cae7e9896fa8d32b76989d`

| Criterion | Result |
|---|---|
| Every file accounted for | yes: 575 files = 493 covered + 1 partial + 81 Coverage Gaps |
| 30 random Facts correct (seed 0) | yes: 30/30 |
| Initial index < 120 s for ≤ 80,000 lines | yes: 3.8 s for 86,054 lines |
| Claims | fact 3905, hypothesis 18216; secrets redacted: 10 |

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
- no analyzer for json: 24
- no analyzer for sql: 20
- no analyzer for yaml: 9
- no analyzer for markdown: 9
- no analyzer for *.svg: 6
- binary: 4
- no analyzer for *.dockerignore: 1
- no analyzer for *.example: 1
- no analyzer for *.gitignore: 1
- no analyzer for *.prettierignore: 1
- link stored as text: 1
- no analyzer for LICENSE: 1
- no analyzer for css: 1
- no analyzer for *.lock: 1
- no analyzer for toml: 1

Partly analysed:
- definitions unverified for bash (Hypotheses): 1
- imports not extracted for bash: 1
- calls not extracted for bash: 1

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
| ok | `imports` | `@/lib/analytics/posthog-client` | `components/chat-panel.tsx:28-28` | `import { captureClient } from '@/lib/analytics/posthog-client'` |
| ok | `requires` | `package:npm/vaul` | `package.json:100-100` | `"vaul": "^1.1.2",` |
| ok | `imports` | `@/lib/utils` | `components/ui/dialog.tsx:8-8` | `import { cn } from '@/lib/utils'` |
| ok | `defines` | `lib/utils/citation.ts::isCitationLabel` | `lib/utils/citation.ts:17-19` | `export function isCitationLabel(label: string): boolean {` |
| ok | `imports` | `@/lib/analytics` | `lib/actions/account.ts:5-5` | `import { trackAccountDeleted } from '@/lib/analytics'` |
| ok | `imports` | `@/components/ui/sidebar` | `components/__tests__/app-sidebar.test.tsx:4-4` | `import { SidebarProvider } from '@/components/ui/sidebar'` |
| ok | `imports` | `@/lib/errors/public-error` | `components/chat.tsx:14-17` | `import {   getPublicRateLimitDetails,   toPublicErrorPayload } from '@/lib/errors/public-e` |
| ok | `defines` | `lib/config/ollama-validator.ts::validateOllamaModel` | `lib/config/ollama-validator.ts:156-187` | `export function validateOllamaModel(modelId: string): {` |
| ok | `imports` | `@/lib/types` | `components/message-actions.tsx:19-19` | `import type { SearchResultItem } from '@/lib/types'` |
| ok | `imports` | `./attempt-id` | `lib/usage-budget/index.ts:7-7` | `export { isValidUsageAttemptId } from './attempt-id'` |
| ok | `imports` | `@/components/library/library-context` | `components/sidebar/library-menu-item.tsx:9-9` | `import { useLibrary } from '@/components/library/library-context'` |
| ok | `defines` | `lib/tools/search/providers/tavily.ts::toAsciiHostname` | `lib/tools/search/providers/tavily.ts:41-47` | `const toAsciiHostname = (domain: string): string => {` |
| ok | `defines` | `components/ui/dropdown-menu.tsx::DropdownMenuCheckboxItem` | `components/ui/dropdown-menu.tsx:90-114` | `function DropdownMenuCheckboxItem({` |
| ok | `imports` | `@/components/ui/badge` | `components/admin/invitations-manager.tsx:11-11` | `import { Badge } from '@/components/ui/badge'` |
| ok | `defines` | `components/question-confirmation.tsx::QuestionInput` | `components/question-confirmation.tsx:29-35` | `interface QuestionInput {` |
| ok | `imports` | `../utils/message-utils` | `lib/streaming/create-chat-stream-response.ts:25-25` | `import { getTextFromParts } from '../utils/message-utils'` |
| ok | `imports` | `./search/providers/recoverable-error` | `lib/tools/search.ts:24-27` | `import {   classifyRecoverableSearchError,   RecoverableSearchFailure } from './search/pro` |
| ok | `requires` | `package:npm/sonner` | `package.json:95-95` | `"sonner": "^1.4.41",` |
| ok | `imports` | `ai` | `lib/streaming/helpers/summarize-carried-context.ts:1-1` | `import type { UIMessage } from 'ai'` |
| ok | `defines` | `components/usage-dialog.tsx::UsageDialog` | `components/usage-dialog.tsx:31-94` | `export function UsageDialog({ open, onOpenChange, usage }: UsageDialogProps) {` |
| ok | `defines` | `app/api/chat/route.ts::POST` | `app/api/chat/route.ts:59-540` | `export async function POST(req: Request) {` |
| ok | `imports` | `@json-render/react` | `lib/render/components/grid.tsx:3-3` | `import type { ComponentFn } from '@json-render/react'` |
| ok | `defines` | `lib/streaming/helpers/__tests__/cap-historical-answer-text.test.ts::ci` | `lib/streaming/helpers/__tests__/cap-historical-answer-text.test.ts:46-72` | `function citedAssistantTurn(id: string, text: string): UIMessage {` |
| ok | `defines` | `lib/db/actions.ts::deleteUserChats` | `lib/db/actions.ts:408-420` | `export async function deleteUserChats(` |
| ok | `imports` | `./types` | `lib/usage-budget/refund-handler.ts:1-1` | `import type { RefundResult } from './types'` |
| ok | `imports` | `@/lib/utils/markdown` | `lib/actions/notes.ts:7-7` | `import { stripMarkdownText } from '@/lib/utils/markdown'` |
| ok | `defines` | `lib/analytics/track-adaptive-limit-event.ts::AdaptiveLimitEventData` | `lib/analytics/track-adaptive-limit-event.ts:3-12` | `export interface AdaptiveLimitEventData {` |
| ok | `imports` | `@/lib/types` | `components/artifact/search-artifact-content.tsx:3-3` | `import type { SearchResults as TypeSearchResults } from '@/lib/types'` |
| ok | `imports` | `@/lib/db/schema` | `lib/actions/files.ts:6-6` | `import type { LibraryFile } from '@/lib/db/schema'` |
| ok | `imports` | `./types` | `lib/analytics/index.ts:19-24` | `export type {   ChatEventData,   QueryLang,   QueryLenBucket,   QueryShape } from './types` |
