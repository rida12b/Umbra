# full-stack-fastapi-template

web app (FastAPI + React) — https://github.com/fastapi/full-stack-fastapi-template @ `b1125d8839482cb7bbae603ddc6d0081bf87532e`

| Criterion | Result |
|---|---|
| Every file accounted for | yes: 252 files = 162 covered + 8 partial + 82 Coverage Gaps |
| 30 random Facts correct (seed 0) | yes: 30/30 |
| Initial index < 120 s for ≤ 80,000 lines | yes: 1.3 s for 21,421 lines |
| Claims | fact 1394, hypothesis 2775; secrets redacted: 1 |

## Coverage limits

Coverage Gaps (not analysed, listed by reason):
- no analyzer for yaml: 20
- no analyzer for json: 11
- no analyzer for markdown: 10
- binary: 9
- no analyzer for *.svg: 5
- link stored as text: 4
- no analyzer for html: 4
- no analyzer for *.dockerignore: 3
- no analyzer for *.gitignore: 3
- excluded: sensitive (sensitive path): 2
- no analyzer for *.lock: 2
- no analyzer for *.fastapicloudignore: 1
- no analyzer for *.gitattributes: 1
- no analyzer for *.python-version: 1
- no analyzer for LICENSE: 1
- no analyzer for ini: 1
- no analyzer for README: 1
- no analyzer for *.mako: 1
- no analyzer for *.keep: 1
- no analyzer for css: 1

Partly analysed:
- definitions unverified for bash (Hypotheses): 8
- imports not extracted for bash: 8
- calls not extracted for bash: 8

## Facts checked against the code

| | Relation | Object | Evidence | Cited line |
|---|---|---|---|---|
| ok | `imports` | `app.api.deps` | `backend/app/api/routes/login.py:9-9` | `from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser` |
| ok | `imports` | `react` | `frontend/src/components/Items/AddItem.tsx:4-4` | `import { useState } from "react"` |
| ok | `imports` | `@/lib/utils` | `frontend/src/components/ui/pagination.tsx:8-8` | `import { cn } from "@/lib/utils"` |
| ok | `defines` | `backend/tests/utils/user.py::authentication_token_from_email` | `backend/tests/utils/user.py:30-49` | `def authentication_token_from_email(` |
| ok | `imports` | `@/components/Common/DataTable` | `frontend/src/components/Admin/columns.tsx:4-4` | `import type { DataTableFeatures } from "@/components/Common/DataTable"` |
| ok | `imports` | `tailwind-merge` | `frontend/src/lib/utils.ts:2-2` | `import { twMerge } from "tailwind-merge"` |
| ok | `imports` | `class-variance-authority` | `frontend/src/components/ui/badge.tsx:3-3` | `import { cva, type VariantProps } from "class-variance-authority"` |
| ok | `defines` | `frontend/src/components/ui/sidebar.tsx::SidebarGroupAction` | `frontend/src/components/ui/sidebar.tsx:428-449` | `function SidebarGroupAction({` |
| ok | `imports` | `./client.gen` | `frontend/src/client/client/index.ts:12-12` | `export { createClient } from './client.gen';` |
| ok | `imports` | `./utils/random` | `frontend/tests/reset-password.spec.ts:3-3` | `import { randomEmail, randomPassword } from "./utils/random"` |
| ok | `defines` | `frontend/src/components/Common/Appearance.tsx::SidebarAppearance` | `frontend/src/components/Common/Appearance.tsx:25-67` | `export const SidebarAppearance = () => {` |
| ok | `imports` | `sqlmodel.sql.sqltypes` | `backend/app/alembic/versions/9c0a54914c78_add_max_length_for_string_varchar_.py:10-10` | `import sqlmodel.sql.sqltypes` |
| ok | `defines` | `frontend/src/client/client/utils.gen.ts::createQuerySerializer` | `frontend/src/client/client/utils.gen.ts:13-62` | `export const createQuerySerializer = <T = unknown>({` |
| ok | `defines` | `frontend/src/client/client/utils.gen.ts::mergeHeaders` | `frontend/src/client/client/utils.gen.ts:165-200` | `export const mergeHeaders = (` |
| ok | `imports` | `@/components/ui/input` | `frontend/src/components/ui/sidebar.tsx:7-7` | `import { Input } from "@/components/ui/input"` |
| ok | `requires` | `package:npm/@radix-ui/react-slot` | `frontend/package.json:26-26` | `"@radix-ui/react-slot": "^1.2.4",` |
| ok | `imports` | `@/lib/utils` | `frontend/src/components/ui/alert.tsx:4-4` | `import { cn } from "@/lib/utils"` |
| ok | `defines` | `frontend/src/hooks/useCopyToClipboard.ts::useCopyToClipboard` | `frontend/src/hooks/useCopyToClipboard.ts:8-32` | `export function useCopyToClipboard(): [CopiedValue, CopyFn] {` |
| ok | `defines` | `frontend/tests/utils/random.ts::randomItemTitle` | `frontend/tests/utils/random.ts:15-16` | `export const randomItemTitle = () =>` |
| ok | `defines` | `frontend/src/client/sdk.gen.ts::UsersService.deleteUserMe` | `frontend/src/client/sdk.gen.ts:137-144` | `public static deleteUserMe<ThrowOnError extends boolean = true>(options?: Options<usersDel` |
| ok | `imports` | `lucide-react` | `frontend/src/components/Items/AddItem.tsx:3-3` | `import { Plus } from "lucide-react"` |
| ok | `imports` | `react-icons/fa` | `frontend/src/components/Common/Footer.tsx:1-1` | `import { FaGithub, FaLinkedinIn } from "react-icons/fa"` |
| ok | `imports` | `react` | `frontend/src/components/ui/password-input.tsx:1-1` | `import * as React from "react"` |
| ok | `mounts` | `dir:./frontend/blob-report` | `compose.override.yml:97-97` | `- ./frontend/blob-report:/app/frontend/blob-report` |
| ok | `imports` | `uuid` | `backend/app/api/routes/items.py:1-1` | `import uuid` |
| ok | `declares` | `service:mailpit` | `compose.override.yml:71-75` | `mailpit:` |
| ok | `imports` | `lucide-react` | `frontend/src/components/ui/sonner.tsx:3-9` | `import {   CircleCheckIcon,   InfoIcon,   Loader2Icon,   OctagonXIcon,   TriangleAlertIcon` |
| ok | `imports` | `@/client` | `frontend/src/routes/reset-password.tsx:12-12` | `import { LoginService } from "@/client"` |
| ok | `defines` | `frontend/src/components/Common/Logo.tsx::Logo` | `frontend/src/components/Common/Logo.tsx:16-60` | `export function Logo({` |
| ok | `imports` | `react` | `frontend/src/components/ui/alert.tsx:1-1` | `import * as React from "react"` |
